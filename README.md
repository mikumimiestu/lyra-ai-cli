# Amagi CLI - AI Terminal Client & Agent

```text
  [Logo ASCII LYRA CLI asli]

  ╭─ ✦ Lyra CLI v2.9.1 ──────────────────────────────────╮
  │ Mau ngerjain apa hari ini?                           │
  │ Lyra Orpheus 6 · reasoning medium                    │
  │ ~/projects/amagi-cli                                 │
  ╰──────────────────────────────────────────────────────╯
  / perintah · @ file · Alt+Enter baris baru · /help

   › jelaskan @app.py                                      ← pita abu penuh lebar

  Membaca 1 file                                           ← langkah baca-saja dilipat jadi satu baris
● app.py mengatur sesi, model, dan pemanggilan tool.

✻ Selesai · 4s · 1 file dibaca · 00:22

  ───────────────────────────────────────────────────────
   ›
  ───────────────────────────────────────────────────────
  Orpheus 6 · medium · ctx ~3% | ~/projects/amagi-cli / main
  ▸▸ tanya dulu (Shift+Tab ganti) · / perintah · @ file     ✔ Update terpasang · /restart
```

### Baru di v2.9.1 — Menu dengan tombol panah

- `/model`, `/reasoning`, `/memory`, `/reminder`, dan `/project` kini berupa menu: gerakkan dengan **↑ ↓** (atau `j` / `k`), konfirmasi dengan **Enter**, tekan **angka** untuk langsung memilih, dan **Esc** (atau `q`) untuk membatalkan. Menu mulai dari pilihan yang sedang dipakai.
- Di terminal tanpa mode interaktif (pipe, `TERM=dumb`, atau `prompt_toolkit` belum terpasang), menu otomatis kembali ke input angka seperti sebelumnya.

### Baru di v2.9.0 — Tampilan ala Claude Code dan mode persetujuan

**Tampilan**

- Pesan yang kamu kirim muncul sebagai pita abu penuh lebar. Composer berada di antara dua garis (bukan kotak), dan hilang setelah kirim.
- Footer dua baris: model, reasoning, perkiraan konteks, direktori, branch; lalu mode persetujuan dan petunjuk tombol. Notifikasi update tampil rata kanan, menggantikan baris kuning lama.
- `/update` lalu `/restart` memulai ulang Lyra dengan versi baru tanpa mengetik `amagi` lagi.
- Status saat menunggu: `✢ Memproses permintaan... (23s · ↓ 1,1k token · Esc batal)` dengan baris tips yang berganti di bawahnya. Jumlah token adalah perkiraan dari panjang teks (sekitar 4 karakter per token).
- Langkah tool yang hanya membaca (baca file, lihat folder, cek waktu atau memori) dilipat menjadi satu baris, misalnya `Membaca 3 file, melihat 2 folder`. Penulisan file dan perintah terminal tetap tampil lengkap. Detail penuh ada di `/details`.
- Ringkasan akhir menampilkan jam: `✻ Selesai · 4s · 1 file dibaca · 00:22`. Perubahan lewat `/model` dan `/reasoning` dikonfirmasi dengan baris `⎿`.

**Mode persetujuan** (Shift+Tab atau `/mode`)

| Mode | Perilaku |
| :--- | :--- |
| `tanya dulu` (bawaan) | Setiap penulisan file dan perintah meminta izin, seperti sebelumnya. |
| `auto-setuju edit file` (`/mode edit`) | Penulisan file dan pembuatan folder berjalan tanpa tanya, preview diff tetap tampil. Perintah terminal tetap meminta izin. |
| `AUTO SEMUA` (`/mode all`) | File ditulis dan perintah dijalankan tanpa tanya. Footer berwarna merah tebal. |

- Mode hanya berlaku untuk sesi berjalan, tidak pernah disimpan, dan setiap sesi baru dimulai dari `tanya dulu`.
- `/mode all` meminta konfirmasi `y/n`, lalu menampilkan kotak peringatan merah. Peringatan muncul lagi pada pesan berikutnya bila mode dipindah lewat Shift+Tab.
- Di mode `AUTO SEMUA`, perintah berbahaya **tetap meminta izin**: `rm -rf`, `sudo`, `git push --force`, `git reset --hard`, `git clean -f`, `curl ... | sh`, penulisan ke `/dev/sd*`, `chmod -R`, `shutdown`, `DROP TABLE`, `npm publish`, serta perintah yang menyentuh `~/.ssh` atau `.env`. Daftar ini adalah pengaman tambahan, bukan jaminan; gunakan mode ini hanya di folder yang kamu percaya.
- Tindakan yang disetujui otomatis ditandai `✔ Disetujui otomatis (mode ...)` agar tetap terlihat di riwayat.

### Baru di v2.8.0 — Daftar model diperbarui

- Lima model: `Lyra Orpheus 6`, `Lyra Eurydice 6`, `Lyra Luma 6.1`, `Lyra Luma 4 mini`, dan `Lyra Luma Flash`. Model bawaan tetap Orpheus 6.
- `Lyra Luma 5.5` digantikan `Lyra Luma 6.1`, dan `Lyra Nebula 4` digantikan `Lyra Luma 4 mini`. Pilihan model yang sudah tersimpan dialihkan otomatis; id lama tidak pernah dikirim ke server.
- Perbaikan installer Windows: koma ganda di `install.ps1` yang membuat instalasi gagal dengan error `Cannot convert 'System.Object[]'`.

### Baru di v2.7.0 — Streaming halus, Esc, dan daftar tugas

- **Streaming per token:** teks jawaban muncul seketika saat diterima, lengkap dengan gaya `**tebal**`, `*miring*`, dan `kode`. Heading, blok kode, garis, dan tabel tetap dirender rapi per baris.
- **Esc untuk berhenti:** tekan Esc saat Lyra menjawab untuk membatalkan, sama seperti Ctrl+C. Terminal hanya dialihkan selama jawaban mengalir, jadi prompt izin dan editor tidak terpengaruh. `LYRA_NO_ESC=1` mematikan fitur ini.
- **Daftar tugas:** untuk pekerjaan multi-langkah Lyra menampilkan checklist (`☐` menunggu, `◼` dikerjakan, `☒` selesai) dan memperbaruinya per langkah. Lihat kapan saja dengan `/todos`.
- **`/status`:** ringkasan versi, model, reasoning, direktori, branch, sumber API key (tanpa menampilkan key), ukuran percakapan, tugas, memori, daemon, dan terminal.
- **Footer konteks:** `ctx ~12%` memperkirakan ukuran percakapan (sekitar 4 karakter per token) terhadap jendela konteks 128.000 token. Ubah dengan `LYRA_CONTEXT_TOKENS`. Footer menguning di 80% dan memerah di 95%, dan Lyra memberi peringatan sekali di 90%. `/clear` mengosongkan konteks.

### Baru di v2.6.0 — Tampilan ala agent CLI

- Logo Lyra CLI tetap sama. Di bawahnya ada kartu sambutan berbingkai bulat berisi versi, model, reasoning, dan direktori kerja.
- Composer berbingkai bulat; footer satu baris menampilkan model, reasoning, direktori, branch Git, dan petunjuk tombol.
- Jawaban dibuka dengan penanda `●`. Heading, daftar bersarang, kutipan, dan blok kode dirapikan.
- Aktivitas tool tampil per langkah: `● Baca(app.py)` lalu `⎿ Membaca 120 baris`. Perintah terminal menampilkan status exit dan beberapa baris output; sisanya lewat `/details`.
- Preview perubahan file memakai nomor baris dan bar merah/hijau, dengan ringkasan `+N -M`.
- Dialog izin berbingkai bulat dan menampilkan seluruh perintah sebelum disetujui. Jawaban `y`, `ya`, atau `yes` dianggap setuju.
- Indikator proses memakai simbol `✻` berdenyut dengan jam dan petunjuk `Ctrl+C batal`. `LYRA_ASCII=1`, `NO_COLOR=1`, dan `LYRA_NO_ANIMATION=1` tetap berlaku.

### Baru di v2.5.0 — Thinking yang ringkas

- Indikator satu baris memakai waktu nyata: menunggu respons, memproses permintaan saat model mengirim penalaran, atau menyiapkan aksi ketika tool call diterima.
- Metadata model dan effort terlihat tanpa mencetak penalaran panjang. Penalaran tidak disimpan di detail aktivitas atau riwayat percakapan baru; jawaban dan tool call tetap diproses.
- Indikator dibersihkan sebelum jawaban ditampilkan. Selesai satu tugas, ringkasan menampilkan durasi seluruh tugas dan jumlah file unik yang berhasil dibaca lewat tool.
- Ctrl+C, error koneksi, dan timeout membersihkan indikator serta menutup koneksi streaming. Indikator scaffolding dihentikan sebelum konfirmasi atau eksekusi perintah berikutnya.
- Terminal sederhana memakai status teks; `LYRA_ASCII=1` memakai karakter sederhana dan `LYRA_NO_ANIMATION=1` menonaktifkan animasi indikator.

### Perbaikan v2.4.1

Memperbaiki pesan `Window too small` yang keliru muncul di terminal besar: tinggi bingkai kini memperhitungkan ruang minimum autocomplete dan kedua garis bingkai. Saat terminal sangat kecil, bingkai dan status disembunyikan sementara agar input tetap bisa digunakan. Ukuran status mengikuti ukuran output editor saat terminal di-resize.

### Baru di v2.4.0 — Lyra Console

- Logo ASCII gradasi asli dipertahankan. Composer memakai bingkai tipis yang mengikuti panjang pesan, dengan status model, reasoning, direktori, dan branch Git bila tersedia.
- Ketik `@nama-file` atau `@"nama file.md"` untuk menyertakan file teks UTF-8 ke pesan. Ada autocomplete file/folder. Maksimal 8 file, 128 KB per file, dan 256 KB total; file dibaca hanya saat pesan dikirim.
- Aktivitas tool dikelompokkan menjadi Eksplorasi, Perubahan, Pengujian, Terminal, atau Konteks. `/details` menampilkan detail lima aktivitas terakhir dari riwayat maksimal 20 aktivitas di memori.
- Sebelum tool menulis file, tampilkan preview diff merah/hijau. Izin penulisan tetap diminta; preview panjang dibatasi 60 baris dan lebar terminal.
- `LYRA_ASCII=1` memaksa karakter sederhana. `NO_COLOR=1` mematikan warna; `LYRA_LIGHT_THEME=1` memilih palet untuk background terang. Terminal tanpa editor interaktif tetap memakai input sederhana.

Contoh: `jelaskan @app.py dan @"catatan project.md"`. Isi file yang disebutkan ikut dikirim ke API Lyra; hindari menyertakan file rahasia yang tidak ingin dibagikan ke layanan tersebut.

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
curl -sSf https://raw.githubusercontent.com/mikumimiestu/lyra-ai-cli/main/install.sh | bash
```

> Installer mengambil script dan source aplikasi langsung dari GitHub (`raw.githubusercontent.com`, branch `main`), jadi tidak bergantung pada domain atau firewall server sendiri.

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
    *   `Lyra Luma 4 mini` - Ringkas dan hemat untuk pekerjaan sehari-hari.
    *   `Lyra Luma 6.1 (instant)` - Tercepat & responsif untuk tugas instan sehari-hari.
    *   `Lyra Luma Flash` - Super cepat tanpa penalaran, cocok untuk pertanyaan singkat.
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
| `/status` | Ringkasan sesi: versi, model, direktori, konteks, persetujuan, daemon |
| `/mode [ask\|edit\|all]` | Atur persetujuan otomatis (Shift+Tab juga berganti mode) |
| `/restart` | Mulai ulang Lyra, misalnya setelah `/update` |
| `/todos` | Lihat daftar tugas yang sedang dikerjakan Lyra |
| `/model` | Buka pilihan model AI (Orpheus 6, Eurydice 6, Luma 4 mini, Luma 6.1, Luma Flash) |
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
    *   `Lyra Luma 4 mini` - Compact and economical for everyday work.
    *   `Lyra Luma 6.1 (instant)` - Ultra-fast & responsive for daily tasks.
    *   `Lyra Luma Flash` - Very fast, no reasoning, ideal for quick questions.
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
