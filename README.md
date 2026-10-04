# Amagi CLI - AI Terminal Client & Agent

```text
   ██╗  ██╗   ██╗██████╗  █████╗     ██████╗██╗     ██╗
   ██║  ╚██╗ ██╔╝██╔══██╗██╔══██╗   ██╔════╝██║     ██║
   ██║   ╚████╔╝ ██████╔╝███████║   ██║     ██║     ██║
   ██║    ╚██╔╝  ██╔══██║██╔══██║   ██║     ██║     ██║
   ███████╗██║   ██║  ██║██║  ██║   ╚██████╗███████╗██║
   ╚══════╝╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝    ╚═════╝╚══════╝╚═╝
```

[Bahasa Indonesia](#indonesian-versi-bahasa-indonesia) | [English](#english-version)

---

## INDONESIAN (Versi Bahasa Indonesia)

Amagi CLI adalah klien chat AI berbasis terminal yang modern dan interaktif untuk asisten AI **AstByte Lyra**. Aplikasi ini dilengkapi dengan antarmuka estetis full-page, render tabel grid presisi, pilihan model AI generasi baru, pengaturan tingkat penalaran (reasoning effort), animasi loading spinner, manajemen API Key yang aman, serta kemampuan agen AI lokal untuk mengelola file dan mengeksekusi perintah terminal secara aman.

### Fitur Utama
*   **Desain Estetis Full-Page:** Tampilan logo gradasi True Color (Biru ➔ Ungu ➔ Pink), garis pembatas antar sesi, serta tata letak bersih tanpa card box yang meluber.
*   **Daftar Perintah di Awalan:** Menampilkan daftar cepat perintah utama langsung saat aplikasi pertama kali dibuka.
*   **Pilihan Model AI Generasi Terbaru:**
    *   `Lyra Orpheus 6` - Model penalaran canggih & kreasi kode tingkat tinggi.
    *   `Lyra Eurydice 6` - Model penalaran mendalam dengan tingkat presisi tinggi.
    *   `Lyra Nebula 4` - Paling mampu untuk pekerjaan kompleks & skala besar.
    *   `Lyra Luma 5.5 (instant)` - Tercepat & responsif untuk tugas instan sehari-hari.
*   **Pengaturan Tingkat Penalaran (Reasoning Effort):** Pilihan penalaran `Cepat (Low effort)` atau `Sedang (Medium effort)` via `/reasoning` atau `/model`.
*   **Auto-Update Otomatis:** Deteksi versi baru dari GitHub di latar belakang dan opsi perbarui aplikasi langsung dengan perintah `/update`.
*   **Render Tabel Grid Presisi:** Otomatis mengubah tabel Markdown dari respons AI menjadi tabel Unicode Box Grid (`┌───┬───┐`, `├───┼───┤`, `└───┴───┘`) yang rapi dan terukur.
*   **Konfirmasi Eksekusi Script Rapi:** Tampilan dialog izin eksekusi script multi-baris di-box dengan indentasi 4 spasi dan *syntax highlighting*.
*   **Agen AI Lokal (Tool Calling):** AI dapat mendaftar isi folder, membaca file, menulis file baru, scaffolding project (`/project`), dan mengeksekusi perintah terminal secara aman.
*   **API Key Persisten:** API Key disimpan secara lokal di `~/.amagi_cli_config.json`.

---

### Cara Instalasi

#### Metode 1: Instalasi Cepat Satu Baris (Rekomendasi)

**Untuk macOS / Linux (Terminal):**
```bash
curl -sSf https://raw.githubusercontent.com/mikumimiestu/lyra-ai-cli/main/install.sh | bash
```

**Untuk Windows (PowerShell):**
```powershell
iwr -useb https://raw.githubusercontent.com/mikumimiestu/lyra-ai-cli/main/install.ps1 | iex
```

#### Metode 2: Menggunakan Pip (Semua OS - Cross Platform)
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

### Perintah Utama CLI

| Perintah | Deskripsi |
| :--- | :--- |
| `/model` | Buka pilihan model AI (Orpheus 6, Eurydice 6, Nebula 4, Luma 5.5) |
| `/reasoning` | Atur tingkat penalaran (`cepat` / `sedang`) |
| `/update` | Cek & perbarui Lyra CLI ke versi terbaru dari GitHub secara otomatis |
| `/version` | Tampilkan versi Lyra CLI saat ini |
| `/project` | Wizard scaffolding project baru (React, Next.js, Laravel, FastAPI, Express, dll.) |
| `/clear` | Bersihkan riwayat chat |
| `/history` | Tampilkan ringkasan riwayat percakapan |
| `/cd <path>` | Ganti direktori kerja aktif |
| `/ls [path]` | Tampilkan isi direktori |
| `/run <cmd>` | Langsung jalankan perintah terminal |
| `/reset-key` | Atur ulang ASTBYTE_API_KEY |
| `/help` | Tampilkan daftar bantuan lengkap |
| `exit` / `quit` | Keluar dari aplikasi |

---

## ENGLISH (English Version)

Amagi CLI is a modern, interactive terminal chat client for **AstByte Lyra**. It features full-page aesthetics, unicode grid table rendering, next-gen AI models, customizable reasoning effort levels, persistent API key management, and local agentic capabilities to interact with your file system and run terminal commands safely.

### Key Features
*   **Full-Page Clean Layout:** True Color gradient logo (Blue ➔ Purple ➔ Pink), full-width section dividers, and clean borderless chat layout.
*   **Startup Command List:** Displays a quick cheat-sheet of primary commands upon launch.
*   **Next-Gen AI Models:**
    *   `Lyra Orpheus 6` - Advanced reasoning & high-level code creation.
    *   `Lyra Eurydice 6` - Deep reasoning with high precision.
    *   `Lyra Nebula 4` - Powerful model for complex tasks.
    *   `Lyra Luma 5.5 (instant)` - Ultra-fast & responsive for daily tasks.
*   **Reasoning Effort Controls:** Switch reasoning speed between `Fast (Low effort)` and `Medium (Medium effort)` via `/reasoning` or `/model`.
*   **Precision Grid Table Renderer:** Automatically parses Markdown tables from AI responses into crisp Unicode Box Grid tables (`┌───┬───┐`, `├───┼───┤`, `└───┴───┘`).
*   **Clean Multi-line Execution Dialogs:** Indented, syntax-highlighted execution approval boxes for multi-line scripts and commands.
*   **Local AI Agent (Tool Calling):** The AI can list directories, read files, write files, scaffold fullstack projects (`/project`), and execute shell commands safely.

---

### Installation

#### Method 1: Quick One-Liner Install (Recommended)

**For macOS / Linux (Terminal):**
```bash
curl -sSf https://raw.githubusercontent.com/mikumimiestu/lyra-ai-cli/main/install.sh | bash
```

**For Windows (PowerShell):**
```powershell
iwr -useb https://raw.githubusercontent.com/mikumimiestu/lyra-ai-cli/main/install.ps1 | iex
```

#### Method 2: Via Pip (Cross-Platform)
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

### Usage

Once installed, run the program globally from any terminal:
```bash
amagi
```
