export const repository = 'https://github.com/mikumimiestu/lyra-ai-cli';
export const version = __AMAGI_CLI_VERSION__;
export const installers = [
  { label: 'macOS / Linux', shell: 'Terminal', command: 'curl -sSf https://amagi-cli.astbyte.com/install | bash' },
  { label: 'Windows', shell: 'PowerShell', command: 'iwr -useb https://amagi-cli.astbyte.com/install.ps1 | iex' },
  { label: 'pip', shell: 'Python', command: `pip install https://amagi-cli.astbyte.com/packages/amagi_cli-${version}.tar.gz` },
];
export const models = [
  { name: 'Lyra Luma 5.5', id: 'lyra-luma-flash', reasoning: false, default: false },
  { name: 'Lyra Nebula 4', id: 'lyra-nebula-4', reasoning: true, default: false },
  { name: 'Lyra Orpheus 6', id: 'lyra-orpheus-6', reasoning: true, default: true },
  { name: 'Lyra Eurydice 6', id: 'lyra-eurydice-6', reasoning: true, default: false },
];
export const commands = [
  { name: '/details', group: 'Sesi & model', description: 'Lihat lima aktivitas tool terakhir dari riwayat maksimal 20 aktivitas di memori.', example: '/details' },
  { name: '/model', group: 'Sesi & model', description: 'Buka pilihan model Lyra. Pilihan disimpan untuk sesi berikutnya.', example: '/model' },
  { name: '/reasoning', group: 'Sesi & model', description: 'Pilih tingkat penalaran low atau medium.', example: '/reasoning' },
  { name: '/clear', group: 'Sesi & model', description: 'Bersihkan riwayat percakapan pada sesi aktif.', example: '/clear' },
  { name: '/history', group: 'Sesi & model', description: 'Lihat ringkasan 10 pesan terakhir dari percakapan aktif.', example: '/history' },
  { name: '/memory', group: 'Memori & waktu', description: 'Buka menu untuk membaca, menambah, atau menghapus memori lokal.', example: '/memory' },
  { name: '/time', group: 'Memori & waktu', description: 'Tampilkan tanggal, waktu, dan zona waktu komputer.', example: '/time' },
  { name: '/reminder', group: 'Memori & waktu', description: 'Buka menu pengingat: buat, lihat, batalkan, atau cek daemon.', example: '/reminder' },
  { name: '/project', group: 'File & project', description: 'Buka wizard untuk memilih tipe, nama, dan direktori project baru.', example: '/project' },
  { name: '/cd', group: 'File & project', description: 'Pindah direktori kerja aktif. Sertakan path direktori tujuan.', example: '/cd ~/projects' },
  { name: '/ls', group: 'File & project', description: 'Lihat isi folder. Path opsional; default ke direktori aktif.', example: '/ls .' },
  { name: '/run', group: 'File & project', description: 'Jalankan perintah terminal dari direktori aktif, melalui konfirmasi eksekusi.', example: '/run git status' },
  { name: '/update', group: 'Aplikasi', description: 'Cek versi di GitHub dan pilih apakah ingin memperbarui aplikasi.', example: '/update' },
  { name: '/version', group: 'Aplikasi', description: 'Tampilkan versi CLI yang terpasang.', example: '/version' },
  { name: '/reset-key', group: 'Aplikasi', description: 'Hapus key dari konfigurasi dan masukkan API key pengganti.', example: '/reset-key' },
  { name: '/help', group: 'Aplikasi', description: 'Tampilkan bantuan dan daftar perintah di terminal.', example: '/help' },
  { name: 'exit', group: 'Aplikasi', description: 'Keluar dari Amagi. Bisa juga menggunakan quit.', example: 'exit' },
];

export const shortcuts = [
  { keys: 'Enter', action: 'Kirim pesan' },
  { keys: 'Alt+Enter / Ctrl+J', action: 'Tambah baris' },
  { keys: 'Tab / ↑ ↓', action: 'Pilih saran perintah atau file' },
  { keys: 'Ctrl+C', action: 'Batalkan draft atau proses aktif' },
  { keys: 'Ctrl+D', action: 'Keluar saat input kosong' },
];

export const releases = [
  { version: '2.5.0', title: 'Thinking yang ringkas.', changes: [
    'Indikator satu baris dengan durasi nyata dan metadata model. Penalaran panjang disembunyikan dari percakapan.',
    'Spinner dibersihkan sebelum jawaban ditampilkan, saat error, atau ketika proses dibatalkan.',
    'Ringkasan selesai memakai durasi seluruh tugas dan jumlah file unik yang berhasil dibaca lewat tool.',
  ], commit: '648b0d384c808e236068e7ded6c676661e502974' },
  { version: '2.4.1', title: 'Perbaikan ukuran bingkai.', changes: [
    'Memperbaiki pesan “Window too small” yang muncul keliru di terminal besar.',
    'Ruang autocomplete ikut dihitung. Bingkai dan status disembunyikan sementara saat terminal sangat kecil.',
  ], commit: '5477433d2972556f2b463b246d531d7112c64a9d' },
  { version: '2.4.0', title: 'Lyra Console.', changes: [
    'Bingkai input adaptif, status direktori dan branch Git, serta referensi file lewat @.',
    'Kelompok aktivitas, /details, dan preview diff sebelum konfirmasi penulisan file.',
    'Fallback ASCII, palet terang, dan mode tanpa warna.',
  ], commit: '38a1553' },
  { version: '2.3.1', title: 'Logo Lyra kembali.', changes: [
    'Logo ASCII gradasi biru–ungu–pink dipertahankan. Terminal sempit memakai wordmark sederhana.',
  ], commit: '32faa1f' },
  { version: '2.3.0', title: 'Editor interaktif.', changes: [
    'Autocomplete perintah, input beberapa baris, dan paste kode sebagai satu pesan.',
    'Riwayat input selama sesi, pembatalan draft dengan Ctrl+C, dan keluar lewat Ctrl+D.',
  ], commit: 'b8688010e70f6978e4a3def238434572ea568276' },
];
