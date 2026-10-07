"""
Face Recognition Attendance System — Streamlit UI.
Run: streamlit run app.py
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime

import streamlit as st

import database as db
import face_utils as faces

DISCLAIMER = (
    "**Accuracy notice:** Automated face recognition can make mistakes (lighting, angles, "
    "similar-looking faces). Attendance marked by this app should be reviewed by an instructor. "
    "This system only matches people who have been registered with consent; it does not identify "
    "unknown individuals."
)

PRIVACY_NOTE = (
    "Face data (numeric encodings and a thumbnail image) is stored **only on this computer** "
    "in the local `attendance.db` file. To remove someone completely, use **Delete student** "
    "on the Register page, or delete `attendance.db` to reset everything."
)


def init_app() -> None:
    db.init_db()


def page_register() -> None:
    st.subheader("Register student")
    st.caption(PRIVACY_NOTE)

    st.markdown("Step 1: capture a face from the webcam **or** upload a clear front-facing photo.")
    cam = st.camera_input("Webcam capture (optional if you upload a file)")
    upload = st.file_uploader("Or upload photo (JPG/PNG)", type=["jpg", "jpeg", "png"])

    image_bytes = None
    if upload is not None:
        image_bytes = upload.getvalue()
    elif cam is not None:
        image_bytes = cam.getvalue()

    with st.form("register_form", clear_on_submit=False):
        st.markdown("Step 2: enter details and confirm consent.")
        student_id = st.text_input("Student ID", placeholder="e.g. CS101-042")
        name = st.text_input("Full name", placeholder="e.g. Alex Kumar")
        consent = st.checkbox(
            "I confirm this person has given consent to enroll their face for attendance on this device.",
        )
        submitted = st.form_submit_button("Save student")

    if submitted:
        if not consent:
            st.error("Consent is required before enrolling a face.")
            return
        if not student_id.strip() or not name.strip():
            st.error("Please enter both Student ID and name.")
            return
        if not image_bytes:
            st.error("Provide a webcam capture or upload a photo.")
            return
        try:
            enc_bytes, thumb_bytes, preview_bytes = faces.process_registration_image(image_bytes)
            db.add_student(student_id, name, enc_bytes, thumb_bytes)
            st.success(f"Registered {name.strip()} ({student_id.strip()}).")
            st.image(preview_bytes, caption="Detected face (preview)", use_container_width=True)
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Registration failed: {exc}")

    st.divider()
    st.subheader("Registered students")
    students = db.list_students()
    if not students:
        st.info("No students registered yet.")
    else:
        for s in students:
            cols = st.columns([1, 3, 2, 1])
            img_bytes = db.get_student_face_image(s["student_id"])
            with cols[0]:
                if img_bytes:
                    st.image(img_bytes, width=80)
                else:
                    st.write("—")
            cols[1].write(f"**{s['name']}**")
            cols[2].write(s["student_id"])
            cols[3].write(s["created_at"][:10])

    st.divider()
    st.subheader("Delete student (removes face data and attendance)")
    del_id = st.selectbox(
        "Select student to delete",
        options=[""] + [s["student_id"] for s in students],
        format_func=lambda x: "— choose —" if x == "" else x,
        key="delete_select",
    )
    confirm = st.checkbox("I understand this permanently deletes face data and attendance for this student.")
    if st.button("Delete selected student", type="primary", disabled=not del_id or not confirm):
        if db.delete_student(del_id):
            st.success(f"Deleted student {del_id} and their records.")
            st.rerun()
        else:
            st.error("Student not found.")


def page_attendance() -> None:
    st.subheader("Mark attendance")
    st.markdown(DISCLAIMER)

    registered = db.get_student_encodings()
    tab_auto, tab_manual = st.tabs(["Automatic (webcam)", "Manual"])

    with tab_auto:
        st.caption("Show one registered student's face to the camera, then capture.")
        frame = st.camera_input("Webcam for attendance", key="attendance_cam")
        if st.button("Recognize and mark attendance", key="btn_auto"):
            if frame is None:
                st.warning("Capture an image from the webcam first.")
            else:
                try:
                    bgr = faces.image_bytes_to_bgr(frame.getvalue())
                    rgb = faces.bgr_to_rgb(bgr)
                    result = faces.match_face_against_registered(rgb, registered)
                    if result["matched"]:
                        sid = result["student_id"]
                        if db.has_attendance_today(sid):
                            st.warning(
                                f"{result['name']} ({sid}) is already marked present today."
                            )
                        else:
                            rec = db.mark_attendance(sid, method="auto")
                            st.success(
                                f"Present: {result['name']} at {rec['time']} (automatic)."
                            )
                    else:
                        st.info(result["message"])
                except Exception as exc:
                    st.error(f"Recognition error: {exc}")

    with tab_manual:
        st.caption("Use when recognition fails or the webcam is unavailable.")
        students = db.list_students()
        if not students:
            st.info("Register students first.")
        else:
            options = {f"{s['name']} ({s['student_id']})": s["student_id"] for s in students}
            label = st.selectbox("Student", list(options.keys()))
            if st.button("Mark present manually", key="btn_manual"):
                sid = options[label]
                try:
                    if db.has_attendance_today(sid):
                        st.warning(f"Already marked present today for {sid}.")
                    else:
                        rec = db.mark_attendance(sid, method="manual")
                        st.success(f"Manual attendance recorded at {rec['time']}.")
                except ValueError as exc:
                    st.error(str(exc))


def page_records() -> None:
    st.subheader("Attendance records")
    col1, col2 = st.columns(2)
    with col1:
        from_d = st.date_input("From date", value=date.today().replace(day=1))
    with col2:
        to_d = st.date_input("To date", value=date.today())

    if from_d > to_d:
        st.error("'From date' must be on or before 'To date'.")
        return

    rows = db.get_attendance(from_date=from_d, to_date=to_d)
    if not rows:
        st.info("No attendance records for this date range.")
    else:
        st.dataframe(
            [
                {
                    "Date": r["attend_date"],
                    "Time": r["attend_time"],
                    "Student ID": r["student_id"],
                    "Name": r["name"],
                    "Method": r["method"],
                }
                for r in rows
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.divider()
    st.subheader("Export to CSV")
    st.caption(f"Exports {len(rows)} record(s) for the selected date range.")
    if rows:
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=["attend_date", "attend_time", "student_id", "name", "method"],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    "attend_date": r["attend_date"],
                    "attend_time": r["attend_time"],
                    "student_id": r["student_id"],
                    "name": r["name"],
                    "method": r["method"],
                }
            )
        st.download_button(
            label="Download CSV",
            data=buf.getvalue(),
            file_name=f"attendance_{from_d.isoformat()}_to_{to_d.isoformat()}.csv",
            mime="text/csv",
        )


def main() -> None:
    st.set_page_config(
        page_title="Face Recognition Attendance",
        page_icon="🎓",
        layout="wide",
    )
    init_app()

    st.title("Face Recognition Attendance System")
    st.caption("College project demo — local storage only, consent required for enrollment.")

    page = st.sidebar.radio(
        "Menu",
        ["Register", "Mark attendance", "Records & export"],
        index=0,
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown(PRIVACY_NOTE)

    if page == "Register":
        page_register()
    elif page == "Mark attendance":
        page_attendance()
    else:
        page_records()


if __name__ == "__main__":
    main()
