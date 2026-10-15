"""EduPredict deployment launcher for Render.
The compressed bundle contains only the project's source files and dataset.
"""
import base64
import hashlib
import io
import lzma
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parent
APP = ROOT / "edupredict_app"
BUNDLE = ROOT / "edupredict_bundle.b85"
EXPECTED_SHA256 = "ec490daac9b61e75279a3304d3e33b9692a2ed26132e0692a79da5350e898130"
ALLOWED = {
    "app.py", "train_model.py", "requirements.txt",
    "static/index.html", "static/css/style.css", "static/js/app.js",
    "data/student_performance.csv",
}

def unpack():
    compressed = base64.b85decode(BUNDLE.read_text(encoding="utf-8").strip())
    actual = hashlib.sha256(compressed).hexdigest()
    if actual != EXPECTED_SHA256:
        raise RuntimeError("Deployment bundle hash mismatch")
    with tarfile.open(fileobj=io.BytesIO(lzma.decompress(compressed)), mode="r:") as archive:
        members = archive.getmembers()
        names = {m.name for m in members}
        if names != ALLOWED or not all(m.isfile() for m in members):
            raise RuntimeError("Unexpected files in deployment archive")
        for member in members:
            destination = APP / member.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
    print(f"Verified and unpacked {len(ALLOWED)} application files", flush=True)

def main():
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "build":
        unpack()
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(APP / "requirements.txt")], check=True)
        subprocess.run([sys.executable, str(APP / "train_model.py")], check=True)
    elif command == "serve":
        if not (APP / "app.py").exists():
            unpack()
        os.execv(sys.executable, [sys.executable, str(APP / "app.py")])
    elif command == "unpack":
        unpack()
    else:
        raise SystemExit("Usage: python edupredict_bootstrap.py [build|serve|unpack]")

if __name__ == "__main__":
    main()
