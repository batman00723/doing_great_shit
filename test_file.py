import os

os.makedirs("recordings", exist_ok=True)
file_path = "recordings/test.txt"
with open(file_path, "wb+") as f:
    f.write(b"hello")

print("File exists:", os.path.exists(file_path))
