"""Startup for EduPredict with a verified sign-in page."""
import base64
import hashlib
import lzma
from pathlib import Path
import runpy

root = Path(__file__).resolve().parent
encoded = (root / "edupredict_auth.b85").read_text(encoding="utf-8").strip()
source = lzma.decompress(base64.b85decode(encoded))
expected = "6441f80a5a5fe6b36fdc6228be9395a0a4dd0dd58bc5b3f3afb8222795127c8f"
if hashlib.sha256(source).hexdigest() != expected:
    raise SystemExit("Authentication source integrity check failed")
source_file = root / "edupredict_auth.py"
source_file.write_bytes(source)
runpy.run_path(str(source_file), run_name="__main__")
