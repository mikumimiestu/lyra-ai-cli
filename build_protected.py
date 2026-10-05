#!/usr/bin/env python3
"""
Script otomatis untuk mengeksekusi enkripsi & enkapsulasi source code
menggunakan PyArmor sehingga source code rahasia milik Anda aman 100%.
"""

import subprocess
import sys
import os

def build():
    print("🔒 Memulai proses penguncian & enkripsi source code...")
    python_bin = sys.executable
    # Try finding python3 with pyarmor
    for p in ["/usr/local/bin/python3", sys.executable, "python3"]:
        res = subprocess.run([p, "-c", "import pyarmor"], capture_output=True)
        if res.returncode == 0:
            python_bin = p
            break

    cmd = [
        python_bin, "-m", "pyarmor.cli", "gen",
        "-O", "dist",
        "app.py", "styling.py", "spinner.py", "tools.py", "config.py"
    ]
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print("\n✅ Enkripsi berhasil! File rahasia aman di folder 'dist/'")
    else:
        print("\n❌ Gagal melakukan enkripsi.")


if __name__ == "__main__":
    build()
