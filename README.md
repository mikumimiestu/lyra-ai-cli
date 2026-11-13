# Amagi CLI - AI Terminal Client & Agent

[![CI](https://github.com/mikumimiestu/lyra-ai-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/mikumimiestu/lyra-ai-cli/actions/workflows/ci.yml)

```text
  [kepala kucing Nexara, pixel art]    Lyra CLI  v2.12.9
                               Mau ngerjain apa hari ini?
                               Orpheus 6 · medium · ~/projects/amagi-cli
                               / perintah · @ file · /help

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

### Baru di v2.11.0 — Login dengan akun AstByte

- **Dua cara masuk:** saat pertama dijalankan, pilih *Login dengan akun AstByte* atau *Pakai API key*. API key tetap bekerja seperti biasa dan ditagih dari saldo developer.
- **Login akun:** CLI menampilkan kode dan membuka browser. Setujui kode itu di halaman AstByte, lalu kembali ke terminal. Tidak ada password yang diketik di CLI.
- **Kuota token per tier:** jendela 5 jam (dimulai saat pesan pertama, lalu menunggu sampai genap 5 jam kalau habis) dan batas mingguan. Free 50K, Student 100K, Pro 300K, Plus 600K, Ultra 1,2M, Ultimate 2,5M token per 5 jam; batas mingguannya 9x angka itu. Semua tier bisa memakai semua model yang ada di CLI.
- **Perintah baru:** `/login`, `/logout`, dan `/kuota` (sisa token dan waktu reset). `/status` menampilkan cara masuk yang aktif.
- **Kelola perangkat:** buka halaman `/cli-login` di akun AstByte untuk melihat kuota, daftar perangkat, dan mencabut akses.

### Perbaikan v2.12.9 — Server rilis sendiri dan verifikasi checksum

- **Sumber unduhan baru:** installer (`install.sh`, `install.ps1`) dan `/update` kini mengambil file dari `https://astbyte.my.id`. GitHub tetap menjadi cadangan otomatis bila server itu tidak terjangkau. Untuk mirror lain, atur `LYRA_UPDATE_URL` (update) atau `AMAGI_BASE_URL` (installer).
- **Verifikasi `SHA256SUMS`:** setiap file diperiksa dengan checksum dari server utama. File yang tidak cocok atau tidak terdaftar ditolak, lalu Lyra mencoba GitHub. Tanpa checksum yang valid, server utama tidak dipercaya begitu saja.
- **Update atomik:** semua file diunduh dan diperiksa dulu di memori, baru ditulis. Kegagalan di tengah jalan tidak lagi meninggalkan campuran file lama dan baru.
- **Untuk yang merilis:** `deploy/setup-vps.sh` menyiapkan nginx dan SSL di VPS, `deploy/publish.sh` mengunggah rilis beserta `SHA256SUMS`. Instalasi lama masih memantau GitHub, jadi rilis tetap di-push ke GitHub juga.

### Perbaikan v2.12.8 — Kuota 5 jam dan mingguan

- **Dua jendela kuota:** kuota harian diganti jendela 5 jam (dimulai saat pesan pertama, lalu menunggu genap 5 jam kalau habis) dan batas mingguan. Per 5 jam: Free 50K, Student 100K, Pro 300K, Plus 600K, Ultra 1,2M, Ultimate 2,5M token; batas mingguan 9x angka itu.
- **`/kuota`** menampilkan kedua jendela beserta sisa, persen terpakai, dan waktu reset (bisa dalam hari). Footer "sisa kuota" memakai jendela yang paling ketat.
- Tetap aman bila backend masih mengirim format lama: bagian mingguan disembunyikan, tidak error.

### Perbaikan v2.12.7 — Tailwind, tampilan lebih rapi, dan Python otomatis

- **Tailwind CSS di `/project`:** Lyra menanyakan "Pasang Tailwind CSS?" lalu mengatur konfigurasinya sendiri. Vite (React, Vue, Svelte): memasang `tailwindcss` dan `@tailwindcss/vite`, menambah plugin ke `vite.config` dan `@import "tailwindcss";` ke CSS utama. Next.js: lewat flag `--tailwind`. Django, Flask, dan PHP: Tailwind CLI, template dasar, dan skrip `build:css`/`watch:css`. Laravel sudah membawa Tailwind. Kalau `vite.config` berbentuk tak dikenal, Lyra memberi tahu langkah manualnya, bukan gagal.
- **`/memory` rapi:** catatan bernomor dengan tanggal redup dan teks terbungkus, tampil di dalam menu dan hilang saat ditutup. `/status`, `/todos`, `/time`, `/kuota`, `/instruksi`, dan `/reminder` juga menghilang dari layar saat ditutup dengan Enter atau Esc.
- **Dialog izin ringkas:** perintah yang menulis file lewat `cat <<EOF` hanya menampilkan 3 baris isi lalu "… +N baris isi file"; perintah dan sisa setelahnya tetap terlihat. Ketik `v` untuk melihat semuanya. Baris aktivitas menjadi "Tulis (shell) · src/App.tsx".
- **Python dipasang otomatis:** kalau installer tidak menemukan Python 3.7+ (dengan venv dan pip), ia menawarkan memasangnya: apt/dnf/yum/pacman/zypper/apk di Linux, Homebrew lalu installer python.org di Mac, winget lalu installer python.org per-pengguna di Windows. Selalu bertanya dulu; untuk instalasi tanpa terminal gunakan `AMAGI_ASSUME_YES=1`.

### Perbaikan v2.12.6 — Pembuatan project (`/project`)

- **Aman dari injeksi:** perintah framework dijalankan tanpa shell, dan nama project divalidasi dulu (huruf, angka, `.`, `-`, `_`). Nama seperti `a; rm -rf ~` ditolak sebelum apa pun berjalan.
- **Satu konfirmasi yang jujur:** dialog menampilkan perintah persis yang akan dijalankan. Sebelumnya ada dua konfirmasi dan sebagian perintah tersembunyi.
- **Flag yang benar:** Next.js memakai `--disable-git` dan `--yes` (flag lama `--no-git` tidak valid), Vite tidak lagi menjalankan `npm install` ganda, Django dibuat di folder project dengan virtualenv sendiri.
- **Tidak menggantung:** input ditutup supaya installer tidak menunggu tombol, Esc atau Ctrl+C menghentikan langkah yang berjalan, ada batas waktu.
- **Gagal ya gagal:** langkah yang error dilaporkan beserta ujung lognya, dan hasil diperiksa (mis. `package.json`, `manage.py`, `artisan`) sebelum menyatakan berhasil.
- **Cek alat:** kalau Node, Python, PHP, Composer, atau Flutter belum terpasang, Lyra memberi tahu dan menautkan halaman pemasangannya. Folder tujuan yang sudah berisi file tidak ditimpa.
- **Tipe baru:** Svelte, Flask, dan Flutter (varian: `react-js`, `next-js`, `vue-js`, `svelte-ts`, `express-ts`).

### Perbaikan v2.12.5 — Windows dan editor yang hilang

- **Kepala kucing saja:** maskot di awal kini hanya kepala Nexara (10 baris, sebelumnya 12), tanpa badan, kerah, dan kaki. Terminal minimal 20 baris tingginya agar gambarnya tampil.
- **Maskot di Windows:** terminal Windows tidak mengisi `COLORTERM` atau `TERM`, jadi Lyra mengira terminal tanpa warna dan hanya menampilkan teks. Kini Windows Terminal, VS Code, ConEmu, dan konsol Windows 10 build 14931 ke atas dikenali sebagai warna penuh.
- **Tanpa `prompt_toolkit`:** input tidak lagi tampil sebagai garis putus-putus dengan kata "pesan". Lyra menampilkan satu keterangan beserta perintah pip yang tepat, menawarkan untuk memasangnya sekali saat dibuka (jawaban "n" diingat dan tidak ditanyakan lagi), dan `/update` sekarang ikut memasang paket yang hilang. Sebelumnya `/update` hanya menyalin file, sehingga instalasi lama yang diperbarui kehilangan menu panah, autocomplete, dan input beberapa baris.
- Kalau `prompt_toolkit` belum terpasang dan kamu tidak ingin menunggu penawaran: `python -m pip install prompt_toolkit` (pada instalasi lewat installer, gunakan Python di folder `.amagi-cli/venv`).

### Baru di v2.12.4 — Panduan project, markdown lebih lengkap, dan CI

**`LYRA.md`: panduan untuk project kamu**
- Taruh `LYRA.md` di folder project berisi hal yang ingin Lyra ingat: tujuan project, perintah tes dan build, konvensi kode, serta hal yang tidak boleh diubah. Lyra membacanya otomatis pada setiap pesan, jadi kamu tidak perlu mengulang konteks tiap sesi.
- **`/init`** meminta Lyra mempelajari project (struktur folder, README, file manifest) lalu menulis `LYRA.md` untukmu. Kalau file sudah ada, Lyra memeriksa dan memperbaruinya. Penulisan tetap lewat diff dan izin seperti biasa.
- **`/instruksi`** menampilkan file yang sedang dimuat beserta ukurannya. Saat sebuah `LYRA.md` dimuat atau berubah, muncul satu baris pemberitahuan.
- `LYRA.md` dicari dari folder kerja naik ke atas sampai root repositori (folder yang berisi `.git`), atau sampai folder home bila tidak ada repositori. File yang paling dekat diutamakan. `~/LYRA.md` bisa dipakai untuk preferensi pribadi.
- **Batas dan keamanan:** maksimal 20 KB per file, 40 KB total, dan 4 file. File biner dan symlink yang mengarah keluar dari project diabaikan, dan folder di luar repositori atau home tidak pernah dibaca. Isinya ikut dikirim ke API Lyra, jadi jangan menaruh rahasia di dalamnya. Aturan konfirmasi dan pengaman perintah berbahaya tetap berlaku di atas instruksi apa pun.

**Markdown lebih lengkap**
- Tautan `[teks](url)` tampil sebagai teks bergaris bawah diikuti `(url)`, gambar sebagai `[gambar: alt]`, dan tautan di dalam tabel ikut dirender.
- `~~coret~~` benar-benar tercoret, `- [ ]` dan `- [x]` menjadi kotak centang ☐ dan ☒ tanpa butir, kutipan bersarang (`> >`) memakai satu garis per tingkat, dan daftar yang menjorok dalam tetap dikenali sebagai daftar.

**CI di GitHub**
- Workflow `.github/workflows/ci.yml` menjalankan semua tes di macOS, Linux, dan Windows (Python 3.9, 3.11, dan 3.13), memeriksa sintaksis Python 3.7, dan menguji `install.sh`, `install.ps1`, serta paket pip dari awal sampai perintah `amagi --version` berjalan. Hasil Windows ditampilkan tetapi belum membuat CI gagal sampai beberapa putaran pertama menunjukkan apa yang perlu dirapikan.

### Perbaikan v2.12.3

Judul markdown level 4 sampai 6 (`####`, `#####`, `######`) kini dirender sebagai judul, bukan tercetak dengan tanda pagarnya. Tiap level punya gaya sendiri, tanda pagar penutup (`## Judul ##`) dan penanda tebal di dalam judul dibersihkan, dan teks seperti `#hashtag` atau komentar di dalam blok kode tidak tersentuh.

### Baru di v2.12.2 — Maskot Nexara, teks yang rapi, dan dialog izin ringkas

- **Maskot di awal:** logo ASCII "LYRA CLI" diganti kucing peliharaan Nexara, maskot AstByte, dalam pixel art (12 baris) di samping empat baris info: versi, sapaan, model + reasoning + folder, dan petunjuk singkat. Kartu sambutan lama ikut digantikan.
- **Cadangan otomatis:** tanpa warna (`NO_COLOR`), tanpa unicode (`LYRA_ASCII=1`), terminal lebih sempit dari 66 kolom, atau lebih pendek dari 22 baris, header tampil sebagai empat baris teks tanpa gambar. Terminal 256 warna (misalnya Terminal.app macOS) memakai palet 256 warna; terminal truecolor memakai warna penuh.
- **Jawaban dibungkus per kata:** teks panjang tidak lagi terpotong di tengah kata dan jatuh ke kolom pertama. Baris lanjutan mengikuti indentasi paragraf, daftar bernomor, butir, dan kutipan, dan gaya tebal/miring/kode tetap terjaga setelah baris dipatahkan. Blok kode dan tabel tidak diubah susunannya, dan keluaran yang di-pipe tidak dibungkus.
- **Dialog izin ringkas:** tanpa kotak. Judul satu baris, perintah ditampilkan **utuh** di samping garis, lalu satu baris info (`di ~/folder · batas 120 dtk`). Operasi file cukup dua baris, misalnya `Mengubah File · ~/proj/app.py · 1 penggantian`.

### Baru di v2.12.1 — Bantuan per perintah, mode satu kali tanya, dan footer lebih informatif

- **`/help <perintah>`:** penjelasan satu perintah lengkap dengan pemakaian, alias, contoh, dan catatan, misalnya `/help mode`. Nama dan alias boleh ditulis dengan atau tanpa `/`. Salah ketik memunculkan saran (`/help modl` menjawab "Maksudmu /model, /mode?"). Setelah `/help `, Tab melengkapi nama perintah.
- **`amagi --version` (`-V`) dan `--help` (`-h`):** menampilkan versi atau bantuan tanpa membuka sesi, tanpa menyentuh konfigurasi. Opsi yang tidak dikenal (atau kata lepas seperti `amagi halo`) kini ditolak dengan kode keluar 2, bukan membuka sesi.
- **`amagi -p "pertanyaan"`:** satu kali tanya lalu keluar. Jawaban dicetak sebagai teks biasa ke stdout (tanpa warna atau hiasan, aman di-pipe), pesan kesalahan ke stderr. Isi stdin ikut sebagai konteks, misalnya `cat error.log | amagi -p "apa penyebabnya?"`. Kode keluar: `0` berhasil, `1` gagal (API atau kuota), `2` salah pakai atau belum masuk. Di mode ini Lyra hanya boleh membaca (`list_directory`, `read_file`, `search`, dan sejenisnya); menulis file dan menjalankan perintah ditolak. Percakapan tidak disimpan.
- **Footer:** untuk login akun, tampil `sisa kuota 62%` di sebelah `ctx` (kuning di 25%, merah di 10%, atau `saldo developer` saat kuota habis dan saldo dipakai). Saat kamu mengetik sementara Lyra bekerja, footer menghitung `2 pesan antre`.

### Baru di v2.12.0 — Edit presisi, urungkan, ringkas, dan lanjutkan

**Mengubah dan mencari**
- **`edit_file`:** Lyra mengganti hanya potongan teks yang tepat di file yang sudah ada, bukan menulis ulang seluruh file. Jika potongan itu muncul lebih dari sekali, atau spasi dan indentasinya berbeda, perubahan ditolak dengan petunjuk, bukan ditebak. Akhir baris Windows (`\r\n`) dipertahankan. Preview diff dan izin tetap berlaku, dan mode `auto-setuju edit file` berlaku juga.
- **`search`:** mencari teks dengan regex di banyak file (atau mendaftar file lewat `glob`), dengan hasil `path:baris: isi`. Folder sampah (`.git`, `node_modules`, `__pycache__`, `venv`, `dist`, dan sejenisnya), folder tersembunyi, dan file biner dilewati. Langkahnya dilipat menjadi satu baris seperti `Mencari 3 kali`.

**`/undo`**
- Lyra mengingat isi file sebelum setiap perubahan (20 terakhir, file sampai 2 MB). `/undo` mengembalikan yang terbaru setelah menampilkan diff dan meminta izin; `/undo list` menampilkan daftarnya.
- File yang dibuat Lyra dihapus saat diurungkan. Jika file sudah kamu ubah sendiri sesudahnya, ada peringatan sebelum isi terkini ditimpa.
- Yang tidak bisa diurungkan: perubahan lewat perintah terminal (misalnya `sed` atau `git`).

**`/compact`**
- Meringkas semua percakapan sebelum permintaan terakhir menjadi satu ringkasan pendek, lalu melanjutkan dengan konteks yang jauh lebih kecil. Permintaan terakhir dan tool yang sedang berjalan tetap utuh. `/compact fokus ke tes` mengarahkan ringkasan. Hasilnya menampilkan perkiraan token sebelum dan sesudah. Peringatan konteks di 90% kini menyarankan perintah ini.

**`/resume` dan `--continue`**
- Setiap percakapan disimpan otomatis setelah satu giliran selesai di `~/.amagi_sessions` (30 terbaru). `/resume` menampilkan menu panah untuk memilih yang dilanjutkan, `amagi --continue` (atau `-c`) langsung melanjutkan yang terakhir, dan `/resume hapus` menghapus semuanya.
- **Privasi:** percakapan disimpan sebagai teks biasa, termasuk isi file yang kamu sertakan lewat `@` dan hasil tool. Folder dan file berizin hanya untuk pengguna (`0700` / `0600`). `LYRA_NO_HISTORY=1` mematikan penyimpanan, dan `LYRA_SESSIONS_DIR` memindahkan lokasinya.
- `/status` menampilkan jumlah perubahan yang bisa diurungkan dan status riwayat.

### Perbaikan v2.10.2

Memperbaiki crash `'ascii' codec can't encode character` pada terminal tanpa dukungan UTF-8 (misalnya locale `C` di Linux, SSH, atau container). Konsol live kini mengikuti encoding terminal yang sebenarnya, sehingga tampilan otomatis beralih ke karakter ASCII sederhana. Karakter yang tetap tidak bisa ditampilkan diganti `?`, bukan membuat aplikasi berhenti.

### Baru di v2.10.1 — Keluar dengan layar bersih

- Ketik `exit` atau `quit` (atau tekan Ctrl+D pada input kosong): layar terminal dibersihkan, lalu muncul satu baris pamit. Percakapan tidak tertinggal di layar.
- Hanya layar yang terlihat yang dibersihkan. Riwayat scrollback terminal tidak dihapus, dan di luar terminal interaktif (pipe, `TERM=dumb`) tidak ada yang dibersihkan.

### Baru di v2.10.0 — Input tetap di bawah, seperti Claude Code

- **Area hidup di bawah layar:** kotak input, footer, status, dan baris jawaban yang sedang mengalir tetap berada di bawah. Baris yang sudah selesai dicetak ke atas dan masuk ke scrollback terminal, jadi riwayat chat tetap bisa di-scroll dan disalin.
- **Status selalu tampil:** `✢ Menulis jawaban... (12s · ↓ 1,1k token · Esc batal)` tetap terlihat selama Lyra menjawab, lengkap dengan baris tips.
- **Ketik saat Lyra bekerja:** pesan yang kamu kirim sementara Lyra masih bekerja masuk antrean dan dijalankan berurutan.
- **Esc atau Ctrl+C langsung membatalkan** jawaban yang sedang mengalir, tanpa menunggu. Pesan antrean berikutnya tetap berjalan.
- **Izin dan menu tetap berfungsi:** konfirmasi `y/n` dan menu panah menjeda area hidup sebentar, lalu mengembalikannya.
- **Saat sesi baru dibuka**, kotak input berada tepat di bawah kartu sambutan dan turun ke dasar layar begitu percakapan memenuhi terminal.
- Mode ini aktif di macOS dan Linux pada terminal interaktif. Windows, pipe, dan `TERM=dumb` memakai prompt klasik seperti sebelumnya; `LYRA_CLASSIC=1` memaksa prompt klasik di mana saja.
- Pengguna versi lama tidak perlu langkah ekstra: fitur ini ikut terunduh lewat `/update` lalu `/restart`.

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
curl -fsSL https://astbyte.my.id/install.sh | bash
```

> Installer dan `/update` mengambil file dari `astbyte.my.id` dan memverifikasinya dengan `SHA256SUMS`. Kalau server itu tidak terjangkau, otomatis memakai GitHub (`raw.githubusercontent.com`, branch `main`) sebagai cadangan. Alamat cadangan manual: `curl -sSf https://raw.githubusercontent.com/mikumimiestu/lyra-ai-cli/main/install.sh | bash`.

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
curl -fsSL https://astbyte.my.id/install.sh | bash
```

**Untuk Windows (PowerShell):**
```powershell
iwr -useb https://astbyte.my.id/install.ps1 | iex
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
| `/init` | Minta Lyra mempelajari project dan menulis atau memperbarui `LYRA.md` |
| `/instruksi` | Lihat `LYRA.md` yang sedang dimuat |
| `/undo [list]` | Urungkan perubahan file terakhir dari Lyra, atau lihat daftarnya |
| `/compact [fokus]` | Ringkas percakapan agar konteks longgar |
| `/resume [hapus]` | Lanjutkan percakapan tersimpan, atau hapus semuanya |
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
| `/login` | Masuk dengan akun AstByte |
| `/logout` | Keluar dari akun AstByte |
| `/kuota` | Lihat sisa token (jendela 5 jam dan mingguan) |
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
curl -fsSL https://astbyte.my.id/install.sh | bash
```

**For Windows (PowerShell):**
```powershell
iwr -useb https://astbyte.my.id/install.ps1 | iex
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
