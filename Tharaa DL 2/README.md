# Face Recognition Attendance System

A beginner-friendly college project that registers students with face images, marks attendance from a webcam (or manually), stores everything in SQLite, and exports CSV reports. All processing runs **locally** on your PC — no API keys or paid services.

## Features

- Register students (ID, name, face from webcam or upload)
- Automatic attendance via face matching
- Duplicate check: one attendance per student per day
- View records with date filter and CSV export
- Manual attendance when recognition fails
- Delete student (removes face encodings, thumbnail, and attendance)
- Consent checkbox on registration; accuracy disclaimer in the app

## Requirements

- Windows 10/11 (macOS/Linux supported with the notes below)
- **Python 3.10, 3.11, or 3.12** (strongly recommended on Windows)
- Webcam (for live capture)
- Internet for **first-time** `pip install` only

> **Why not Python 3.13+ / 3.14?** The `face_recognition` library needs **dlib**. On Windows there is often no pre-built `dlib` wheel for the newest Python versions, so `pip` tries to compile from source and fails unless you install Visual Studio C++. Using **Python 3.11** plus **dlib-bin** avoids that.

## Setup (Windows) — recommended

1. Install **Python 3.11** from [python.org](https://www.python.org/downloads/) and enable **“Add Python to PATH”**.

2. Open **PowerShell** in this project folder and run **one** of the following.

   **Option A — copy/paste full install (easiest):**

   ```powershell
   cd "C:\Users\tejes\OneDrive\Desktop\Tharaa DL 2"
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install dlib-bin
   pip install face-recognition==1.3.0 --no-deps
   pip install -r requirements.txt
   ```

   **Option B — if you already have a `.venv` but install failed:**

   ```powershell
   cd "C:\Users\tejes\OneDrive\Desktop\Tharaa DL 2"
   Remove-Item -Recurse -Force .venv
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install dlib-bin
   pip install face-recognition==1.3.0 --no-deps
   pip install -r requirements.txt
   ```

3. **Webcam:** When you run the app, allow camera access in Chrome or Edge.

### Windows install notes

| Step | Purpose |
|------|---------|
| `py -3.11 -m venv .venv` | Uses Python 3.11 even if 3.14 is your default |
| `pip install dlib-bin` | Pre-built **dlib** (no Visual Studio required) |
| `pip install face-recognition --no-deps` | Installs the library without pulling source **dlib** |
| `pip install -r requirements.txt` | Streamlit, OpenCV, models, etc. |

If you **must** use Python 3.14 or compile from source, install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with **“Desktop development with C++”**, then try `pip install dlib` before `face-recognition` (slower and error-prone).

## Setup (macOS / Linux)

```bash
cd "/path/to/Tharaa DL 2"
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install face-recognition==1.3.0
```

On some systems you may need system packages for `dlib` (e.g. `cmake`, `build-essential`). If `pip install face-recognition` fails, check your distro’s docs for building **dlib**.

## Run the app

```powershell
cd "C:\Users\tejes\OneDrive\Desktop\Tharaa DL 2"
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

Browser URL: **http://localhost:8501**

## Project files (6 total)

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI |
| `database.py` | SQLite students & attendance |
| `face_utils.py` | OpenCV detection + face matching |
| `requirements.txt` | Python dependencies (see Windows steps for `face-recognition`) |
| `README.md` | This guide |
| `.gitignore` | Ignores venv and local DB |

## Data & privacy

- Face **encodings** (numbers, not photos sent online) and optional **JPEG thumbnails** are stored in `attendance.db` in this folder.
- To remove one person: **Register → Delete student**.
- To wipe all data: close the app and delete `attendance.db`.
- Only enroll people who have given **consent**. The app does not name or identify unregistered individuals.

## Limitations (honest expectations)

- Recognition accuracy depends on lighting, camera quality, and pose; review attendance manually for grades.
- `face_recognition` uses a CPU-friendly model (`hog`); it is fine for demos, not high-security identification.
- One face per frame for auto check-in.
- Streamlit’s camera widget captures still frames; it is not a continuous video pipeline.

## Quick test flow

1. **Register:** consent → ID/name → webcam photo → Save.
2. **Mark attendance:** same person → Recognize and mark.
3. **Records & export:** pick dates → Download CSV.

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| `dlib` / CMake / Visual Studio error on `pip install` | Use **Python 3.11** venv and the **Option A** commands (`dlib-bin` + `face-recognition --no-deps`) |
| `No module named 'face_recognition'` | Activate `.venv`, run the Windows install steps again |
| Wrong Python in venv | `Remove-Item -Recurse .venv` then `py -3.11 -m venv .venv` |
| Camera not showing | Browser permission; close other apps using the webcam |
| “No face detected” | Brighter room, face the camera, single person in frame |
| Duplicate attendance | Expected — only one mark per student per calendar day |
