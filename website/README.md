# Amagi CLI website

Website panduan dan pengenalan Amagi CLI. Dibangun dengan React, TypeScript, Tailwind CSS, Three.js, dan Vite. Semua perubahan tampilan berada di direktori ini; aplikasi Python di root tidak diubah.

## Jalankan lokal

```sh
npm install
npm run dev
```

## Build

```sh
npm run build
npm run preview
```

Output produksi tersedia di `dist/`. Hosting harus mengarahkan URL aplikasi seperti `/docs` dan `/commands` ke `index.html` agar navigasi langsung dapat berjalan.

Build website membutuhkan Node.js dan Python 3. Python hanya dipakai untuk membuat paket source pip; bisa memilih executable lain melalui variabel `PYTHON`.

Tiga file instalasi tersedia saat development, preview, dan di hasil build:

- `/install`: script asli `../install.sh`.
- `/install.ps1`: script asli `../install.ps1`.
- `/packages/amagi_cli-2.4.0.tar.gz`: paket source pip dari versi CLI di `version.txt` dan modul yang terdaftar di `setup.py`. Nama paket mengikuti versi secara otomatis. Paket hanya berisi modul aplikasi, setup, README, dan versi.

Perintah instalasi:

```sh
curl -sSf https://amagi-cli.astbyte.com/install | bash
```

```powershell
iwr -useb https://amagi-cli.astbyte.com/install.ps1 | iex
```

```sh
pip install https://amagi-cli.astbyte.com/packages/amagi_cli-2.4.0.tar.gz
```

Domain perlu mengarah ke deployment website ini agar URL publik berfungsi. Layani ketiga file sebelum aturan fallback SPA, tanpa autentikasi atau redirect. Gunakan `Content-Type: text/plain; charset=utf-8` untuk script dan `application/gzip` untuk paket bila hosting mendukung pengaturan header. Script Bash dan PowerShell tetap mengambil file aplikasi dari GitHub. Pip mengunduh paket aplikasi dari domain ini dan dependensi melalui index pip yang dikonfigurasi pengguna.

## Halaman

- `/`: pengenalan, contoh terminal, model, dan instalasi.
- `/docs`: instalasi, API key, memori, reminder, scaffolding, dan bantuan.
- `/commands`: pencarian, kategori, dan contoh perintah.
- `/models`: nama model, ID API, dan dukungan penalaran.
- `/changelog`: ringkasan versi source dan tautan riwayat commit.

Data perintah, model, installer, dan versi ada di `src/data.ts`; cocokkan dengan `app.py`, `config.py`, dan installer di root ketika sistem CLI berubah. Preview terminal bersifat ilustratif, tidak terhubung ke CLI atau mengeksekusi perintah.

Website menyediakan tema terang/gelap, navigasi mobile, akses keyboard, dan tombol salin. Di halaman perintah, tekan `/` untuk fokus ke pencarian.

## Visual dan animasi

Hero memakai scene Three.js yang dimuat terpisah: terminal, memori, dan pengingat di atas papan sirkuit. Gerak mengikuti pointer dan dapat dijeda. Renderer berhenti ketika scene keluar layar atau tab tersembunyi; resource dibersihkan saat komponen dilepas. Jika WebGL tidak tersedia, tampil ilustrasi pengganti.

Tailwind CSS dimuat melalui plugin Vite dengan layer theme dan utilities; CSS desain lokal mempertahankan palet dan tata letak situs. Animasi masuk saat scroll, transisi konten terminal, hover, dan indikator posisi baca berlaku tanpa mengubah sistem CLI. Preferensi `prefers-reduced-motion` menonaktifkan gerakan dekoratif.
