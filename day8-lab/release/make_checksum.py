import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
file_path = BASE_DIR / "ai-ready-dataset.csv"

sha256 = hashlib.sha256()

with file_path.open("rb") as file:
    while chunk := file.read(8192):
        sha256.update(chunk)

checksum = sha256.hexdigest()

print(checksum)