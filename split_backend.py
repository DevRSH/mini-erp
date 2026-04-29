import re
import os

with open("main.py", "r") as f:
    code = f.read()

# Make directories
os.makedirs("routers", exist_ok=True)
os.makedirs("schemas", exist_ok=True)
os.makedirs("services", exist_ok=True)

print("Directories created.")
