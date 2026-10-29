"""
Michelle HR — Windows Executable Builder
Uses PyInstaller to bundle the FastAPI backend, ML artifacts, and web dashboard
into a self-contained, standalone Windows executable (.exe).
"""
import os
import sys
import subprocess


def build():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.chdir(project_root)

    print("=" * 70)
    print("📦 BUILDING STANDALONE EXECUTABLE: Michelle_HR.exe")
    print("=" * 70)

    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=Michelle_HR",
        "--onedir",
        "--windowed",  # Suppresses terminal window on launch if desired
        f"--add-data={os.path.join(project_root, 'frontend')};frontend",
        f"--add-data={os.path.join(project_root, 'backend', 'app', 'ml', 'artifacts')};backend/app/ml/artifacts",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=sklearn",
        "--hidden-import=joblib",
        "--hidden-import=pypdf",
        "--hidden-import=docx",
        os.path.join(project_root, "desktop", "run_desktop.py")
    ]

    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print("\n[SUCCESS] Standalone Michelle HR application built in 'dist/Michelle_HR/'")
    else:
        print(f"\n[ERROR] Build exited with code {result.returncode}")


if __name__ == "__main__":
    build()
