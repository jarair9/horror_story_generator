import sys
import os
sys.path.append(os.getcwd())

print("Checking app.py syntax...")
try:
    with open("app.py", "r", encoding="utf-8") as f:
        compile(f.read(), "app.py", "exec")
    print("app.py OK")
except Exception as e:
    print(f"app.py ERROR: {e}")

print("Checking src/generators/image.py syntax...")
try:
    with open("src/generators/image.py", "r", encoding="utf-8") as f:
        compile(f.read(), "src/generators/image.py", "exec")
    print("src/generators/image.py OK")
except Exception as e:
    print(f"src/generators/image.py ERROR: {e}")
