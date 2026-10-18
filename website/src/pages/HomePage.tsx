import { lazy, Suspense } from 'react';
import { ArrowDown, ArrowRight, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { CopyCode, Installation, TerminalPreview } from '../components/Workbench';
import { models, shortcuts, version } from '../data';

const WorkspaceScene = lazy(() => import('../components/WorkspaceScene'));

export function HomePage() {
  return <div className="container home">
    <section className="hero">
      <div className="hero-copy">
        <Link to="/changelog" className="release-link"><span className="status-dot" /> v{version}<span className="release-divider">/</span>Tampilan ala agent CLI <ArrowUpRight size={13} /></Link>
        <p className="eyebrow hero-eyebrow">AMAGI / LYRA CONSOLE</p>
        <h1>Ide, file,<br />dan pekerjaan.<br /><span>Satu terminal.</span></h1>
        <p className="hero-description">Sebut file dengan @, ikuti prosesnya, lalu tinjau perubahan sebelum ditulis. Lyra tetap bekerja dari folder project kamu.</p>
        <div className="hero-actions"><a className="button primary" href="#install">Pasang Amagi <ArrowDown size={16} /></a><Link className="text-link" to="/docs#console">Kenali Console <ArrowRight size={16} /></Link></div>
        <p className="hero-footnote">Python 3.7+ · macOS, Linux & Windows</p>
      </div>
      <div className="hero-workspace relative min-w-0"><Suspense fallback={<div className="scene-loading workspace-scene" aria-label="Memuat ilustrasi workspace" />}><WorkspaceScene /></Suspense><TerminalPreview /></div>
    </section>
    <div className="index-strip"><span className="mono">KENALI AMAGI</span><a href="#workflow">01 / Console <ArrowDown size={13} /></a><a href="#models">02 / Model <ArrowDown size={13} /></a><a href="#install">03 / Instalasi <ArrowDown size={13} /></a></div>
    <section className="workflow section" id="workflow">
      <div className="section-heading"><p className="eyebrow">01 / LYRA CONSOLE</p><h2>Konteks jelas.<br />Perubahan bisa ditinjau.</h2><p>Logo Lyra yang sama, dengan kartu sambutan, composer berbingkai bulat, dan aktivitas yang tampil langkah demi langkah.</p><Link className="text-link console-guide-link" to="/docs#console">Lihat panduan Console <ArrowRight size={16} /></Link></div>
      <div className="workflow-rows">{[
        ['01', 'Sebut file yang perlu dibaca.', 'Ketik @app.py atau pilih file lewat autocomplete. Isi file teks disertakan saat pesan dikirim ke API Lyra.', '@app.py'],
        ['02', 'Tinjau edit sebelum ditulis.', 'Tool penulisan menampilkan preview diff bernomor baris, lalu dialog izin yang memuat seluruh perintah. Detail aktivitas bisa dibuka kembali.', '/details'],
        ['03', 'Ikuti prosesnya, tetap fokus.', 'Indikator ✻ menampilkan durasi nyata, dan tiap tool tampil sebagai ● Baca(file) dengan hasil di bawahnya. Setelah selesai, lihat durasi tugas dan jumlah file yang dibaca.', 'Ctrl+C untuk membatalkan'],
      ].map(([number, title, description, command]) => <div className="workflow-row group transition-colors duration-300 hover:bg-[var(--soft)]" key={number}><span className="row-number">{number}</span><div><h3>{title}</h3><p>{description}</p></div><code>{command}</code></div>)}</div>
      <Link to="/commands" className="text-link section-end">Lihat semua perintah <ArrowRight size={16} /></Link>
    </section>
    <section className="console-keyboard section"><div className="section-heading"><p className="eyebrow">TETAP NYAMAN DI KEYBOARD</p><h2>Tulis beberapa baris.<br />Lanjutkan tanpa pindah jendela.</h2><p>Paste kode sebagai satu pesan. Input, autocomplete, dan status menyesuaikan ruang terminal yang tersedia.</p></div><dl className="shortcut-list">{shortcuts.map(item => <div key={item.keys}><dt><kbd>{item.keys}</kbd></dt><dd>{item.action}</dd></div>)}</dl></section>
    <section className="model-overview section relative" id="models"><div className="section-heading inline-heading"><div><p className="eyebrow">02 / MODEL LYRA</p><h2>Ganti model.<br />Tetap di sesi yang sama.</h2></div><div><p>Empat model lewat <code>/model</code>. Pilih effort low atau medium pada model yang mendukung penalaran. Model dan effort terlihat di footer editor.</p><Link to="/models" className="text-link">Lihat pengaturan model <ArrowRight size={16} /></Link></div></div><div className="model-list">{models.map((model, index) => <Link to="/models" className="group transition-colors duration-300 hover:bg-[var(--soft)]" key={model.id}><span className="mono muted">0{index + 1}</span><h3>{model.name}</h3><span className="model-type">{model.default ? 'Model bawaan' : model.reasoning ? 'Dengan penalaran' : 'Tanpa penalaran'}</span><ArrowUpRight size={19} /></Link>)}</div></section>
    <section className="local-tools section"><p className="eyebrow">KONTEKS YANG BISA DIBAWA KEMBALI</p><div><article><h3>Catatan dalam Markdown.</h3><p>Simpan preferensi lewat <code>/memory</code>. Catatan lokal dibaca kembali saat mengirim pesan berikutnya.</p><Link to="/docs#memory" className="text-link">Kelola memori <ArrowRight size={15} /></Link></article><article><h3>Pengingat di komputer.</h3><p>Buat pengingat lewat <code>/reminder</code>. Daemon mengirim notifikasi saat komputer aktif.</p><Link to="/docs#reminders" className="text-link">Atur pengingat <ArrowRight size={15} /></Link></article></div></section>
    <section className="install-section section" id="install"><div className="section-heading"><p className="eyebrow">03 / MULAI PAKAI</p><h2>Buka terminal.<br />Pasang Amagi.</h2><p>Pilih metode instalasi sesuai sistem operasi. Installer memasang aplikasi dan dependency editor. Siapkan API key AstByte untuk mengobrol.</p><Link to="/docs#install" className="text-link">Panduan instalasi lengkap <ArrowRight size={16} /></Link></div><div className="install-methods"><Installation /><div className="upgrade-inline"><div><span className="eyebrow">SUDAH PAKAI AMAGI?</span><Link to="/docs#update" className="text-link">Panduan update <ArrowRight size={14} /></Link></div><CopyCode code="/update" /><p>Jalankan di dalam Amagi, konfirmasi, lalu buka ulang aplikasinya.</p></div></div></section>
  </div>;
}
