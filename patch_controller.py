import re
with open("myapi/meeting_controller.py", "r") as f:
    content = f.read()

content = content.replace(
    'destination.write(chunk)',
    'destination.write(chunk)\n            logger.info(f"Wrote file {file_path}, size: {os.path.getsize(file_path)}")'
)

with open("myapi/meeting_controller.py", "w") as f:
    f.write(content)
