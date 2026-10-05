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
    cmd = [
        sys.executable, "-m", "pyarmor.cli", "gen",
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
