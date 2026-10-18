# Amagi CLI - AI Terminal Client & Agent

```text
  ✦ Lyra CLI  v2.3.1

  Lyra Orpheus 6 · reasoning medium
  ~/projects/amagi-cli

  Mau ngerjain apa hari ini?
  Jelaskan tugasnya, atau ketik / untuk lihat perintah.

  ›
```

### Perbaikan v2.3.1

Logo ASCII Lyra CLI dengan gradasi biru–ungu–pink dikembalikan pada tampilan awal. Terminal sempit memakai wordmark sederhana agar logo tidak terpotong. Input interaktif dan header ringkas dari v2.3.0 tetap tersedia.

### Baru di v2.3.0

- Header Lyra yang ringkas, warna terminal adaptif, dan versi yang mengikuti konfigurasi aplikasi.
- Menu perintah saat mengetik `/`, dengan pilihan Tab dan tombol panah.
- Enter untuk mengirim; Alt+Enter atau Ctrl+J untuk baris baru. Paste kode beberapa baris tetap menjadi satu pesan.
- Status model, reasoning, dan direktori aktif di bawah editor. Riwayat input hanya disimpan selama proses berjalan, tanpa file history baru.
- Ctrl+C membatalkan input atau proses aktif; Ctrl+D pada input kosong atau `exit` menutup aplikasi.
- Label aktivitas file dan terminal yang singkat. Operasi yang membutuhkan izin tetap meminta konfirmasi.

Editor interaktif memakai `prompt_toolkit`. Instalasi baru memasang dependensinya secara otomatis. Jika dependency belum tersedia atau input diarahkan melalui pipe, Lyra memakai input teks sederhana; jalankan installer terbaru untuk mendapat editor penuh.

```sh
curl -sSf https://amagi-cli.astbyte.com/install | bash
```

> Domain `/install` perlu dideploy dari folder `website` agar memakai installer v2.3.0 yang memasang dependency editor baru. Push GitHub sendiri tidak menjamin deployment domain berubah. Installer tetap mengunduh source aplikasi dari branch `main` GitHub.

[Bahasa Indonesia](#indonesian-versi-bahasa-indonesia) | [English](#english-version)

---

## INDONESIAN (Versi Bahasa Indonesia)

Amagi CLI adalah klien chat AI berbasis terminal yang modern dan interaktif untuk asisten AI **AstByte Lyra**. Aplikasi ini menyediakan input interaktif dengan autocomplete perintah, model Lyra, pengaturan penalaran, memori lokal, dan pengingat desktop. Operasi file dan perintah terminal yang membutuhkan izin tetap meminta konfirmasi.

### Fitur Utama
*   **Memori Jangka Panjang (.md):** Menyimpan fakta dan catatan penting pengguna di `~/.amagi_memory.md` yang otomatis dibaca AI pada setiap percakapan.
*   **Waktu & Tanggal Laptop:** Amagi dapat membaca waktu, tanggal, dan timezone terkini secara akurat langsung dari komputer pengguna.
*   **Pengingat & Notifikasi Laptop ("Bangun Sendiri"):** Amagi memiliki daemon background yang dapat berjalan otomatis di latar belakang. Saat waktu pengingat tiba, Amagi akan bangun sendiri dan memunculkan notifikasi popup desktop (dengan suara) di laptop pengguna tanpa perlu mengetik `amagi`.
*   **Tampilan Ringkas:** Identitas Lyra kecil, percakapan tanpa kotak besar, dan status konteks di bawah editor.
*   **Menu Perintah:** Ketik `/` untuk melihat perintah; pilih dengan Tab atau panah.
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
curl -sSf https://amagi-cli.astbyte.com/install | bash
```

**Untuk Windows (PowerShell):**
```powershell
iwr -useb https://amagi-cli.astbyte.com/install.ps1 | iex
```

#### Metode 2: Menggunakan Pip (Semua OS - Cross Platform)
```bash
pip install https://amagi-cli.astbyte.com/packages/amagi_cli-2.3.1.tar.gz
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
| `/memory` | Kelola memori jangka panjang (`~/.amagi_memory.md`) |
| `/time` | Lihat tanggal, waktu, dan timezone laptop pengguna |
| `/reminder` | Kelola pengingat & notifikasi desktop laptop (daemon background) |
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
*   **Compact Layout:** Small Lyra identity, borderless conversation, and a live model and directory toolbar.
*   **Command Menu:** Type `/` to discover commands and select them with Tab or arrow keys.
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
curl -sSf https://amagi-cli.astbyte.com/install | bash
```

**For Windows (PowerShell):**
```powershell
iwr -useb https://amagi-cli.astbyte.com/install.ps1 | iex
```

#### Method 2: Via Pip (Cross-Platform)
```bash
pip install https://amagi-cli.astbyte.com/packages/amagi_cli-2.3.1.tar.gz
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
