# Amagi CLI - AI Terminal Client & Agent

[Bahasa Indonesia](#indonesian-versi-bahasa-indonesia) | [English](#english-version)

---

## INDONESIAN (Versi Bahasa Indonesia)

Amagi CLI adalah klien chat AI berbasis terminal yang modern dan interaktif untuk asisten AI **AstByte Lyra**. Aplikasi ini dilengkapi dengan antarmuka estetis, animasi loading spinner, manajemen API Key yang aman, dan kemampuan agen AI lokal untuk mengelola file serta mengeksekusi perintah terminal secara aman.

### Fitur Utama
*   **Desain Estetis:** Tampilan logo gradasi True Color (Biru ➔ Ungu ➔ Pink) dan chat prompt berwarna.
*   **Animasi Spinner:** Loading spinner dinamis berjalan di background thread saat AI sedang berpikir.
*   **Agen AI Lokal (Tool Calling):** AI bisa mendaftar isi folder, membaca file, menulis file baru, dan menjalankan perintah terminal.
*   **Konfirmasi Keamanan:** Setiap tindakan memodifikasi file (`write_file`) atau eksekusi perintah terminal (`execute_command`) wajib mendapatkan konfirmasi persetujuan (`y/n`) langsung dari pengguna.
*   **API Key Persisten:** API Key disimpan secara lokal di `~/.amagi_cli_config.json` pada eksekusi pertama sehingga tidak perlu diisi kembali.

---

### Cara Instalasi

#### Metode 1: Instalasi Cepat Satu Baris (Rekomendasi)
Jalankan perintah ini di terminal Anda untuk mengunduh dan memasang Amagi CLI secara otomatis:
```bash
curl -sSf https://raw.githubusercontent.com/mikumimiestu/lyra-ai-cli/main/install.sh | bash
```

#### Metode 2: Menggunakan Pip (Langsung dari GitHub)
```bash
pip install git+https://github.com/mikumimiestu/lyra-ai-cli.git
```

#### Metode 3: Instalasi Lokal (Developer Mode)
1. Clone repositori ini:
   ```bash
   git clone https://github.com/mikumimiestu/lyra-ai-cli.git
   cd lyra-ai-cli
   ```
2. Jalankan script installer lokal:
   ```bash
   bash install.sh
   ```

---

### Cara Memperbarui (Update)
Jika terdapat pembaruan kode di repositori GitHub, Anda dapat memperbarui aplikasi Anda dengan cara:
- **Jika menggunakan metode Curl:** Jalankan kembali perintah instalasi Curl di Metode 1.
- **Jika menggunakan metode Pip:** Jalankan perintah berikut di terminal Anda:
  ```bash
  pip install --upgrade git+https://github.com/mikumimiestu/lyra-ai-cli.git
  ```

*(Pembaruan ini tidak akan menghapus API Key yang sudah Anda simpan).*

---

### Cara Menggunakan

Setelah instalasi selesai, jalankan perintah ini di terminal Anda:
```bash
amagi
```
*(Atau gunakan `python app.py` jika Anda berada di direktori project).*

#### Contoh Interaksi Agen
Cobalah mengetikkan perintah-perintah ini untuk melihat cara kerja agen AI:
1.  **Melihat Daftar File:**
    > *“coba list folder saat ini”*
2.  **Membaca File:**
    > *?tolong baca isi file styling.py”*
3.  **Membuat File Baru & Menjalankannya:**
    > *“tolong buat file baru namanya hitung.py berisi fungsi fibonacci dan jalankan filenya”*

---

## ENGLISH (English Version)

Amagi CLI is a modern, interactive, and beautifully styled terminal chat client for **AstByte Lyra**. It features rich ANSI styling, thread-based loading spinner, persistent secure API key management, and local agentic capabilities to safely interact with your file system and run terminal commands.

### Key Features
*   **Rich Aesthetics:** True Color gradient logo (Blue ➔ Purple ➔ Pink) and colored prompt inputs.
*   **Micro-Animations:** Background thread spinner loader during API calls.
*   **Local AI Agent (Tool Calling):** The AI can list directory contents, read files, write files, and execute terminal commands.
*   **Safety Approvals:** Writing files (`write_file`) or running terminal commands (`execute_command`) always prompts for user confirmation (`y/n`).
*   **Persistent API Key:** Automatically prompts for the API Key on first run and saves it securely to `~/.amagi_cli_config.json`.

---

### Installation

#### Method 1: Quick One-Liner Install (Recommended)
Run the following command in your terminal to automatically download and set up Amagi CLI:
```bash
curl -sSf https://raw.githubusercontent.com/mikumimiestu/lyra-ai-cli/main/install.sh | bash
```

#### Method 2: Via Pip (Directly from GitHub)
```bash
pip install git+https://github.com/mikumimiestu/lyra-ai-cli.git
```

#### Method 3: Local Clone Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/mikumimiestu/lyra-ai-cli.git
   cd lyra-ai-cli
   ```
2. Execute the local installer:
   ```bash
   bash install.sh
   ```

---

### How to Update
If there are updates in the GitHub repository, you can update your installed CLI by:
- **If installed via Curl:** Re-run the Curl installation command in Method 1.
- **If installed via Pip:** Run the following command in your terminal:
  ```bash
  pip install --upgrade git+https://github.com/mikumimiestu/lyra-ai-cli.git
  ```

*(Updating will not delete or reset your saved API Key).*

---

### Usage

Once installed, run the program globally by typing:
```bash
amagi
```
*(Or use `python app.py` directly from the project directory).*

#### Examples of Agent Interaction
Try the following prompts to experience the local agent features:
1.  **Listing Directories:**
    > *“list the current directory”*
2.  **Reading File Content:**
    > *“read app.py and summarize the tool calling loop”*
3.  **Coding and Running Scripts:**
    > *“create a test.py script that prints the current date and run it”*
