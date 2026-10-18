import { useEffect, useRef, useState } from 'react';
import { ArrowRight, Check, Copy, Pause, Play } from 'lucide-react';
import { installers, version } from '../data';
import cliLogo from '../assets/lyra-logo.txt?raw';

export function CopyCode({ code, label = 'Salin perintah' }: { code: string; label?: string }) {
  return <CopyCodeContent key={code} code={code} label={label} />;
}

function CopyCodeContent({ code, label }: { code: string; label: string }) {
  const [status, setStatus] = useState<'idle' | 'copied' | 'error'>('idle');
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setStatus('copied');
    } catch { setStatus('error'); }
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setStatus('idle'), 2500);
  }
  return <div className="code-block"><code>{code}</code><button onClick={copy} aria-label={label} title={label}>{status === 'copied' ? <Check size={16} /> : <Copy size={16} />}<span aria-live="polite">{status === 'copied' ? 'Tersalin' : status === 'error' ? 'Salin manual' : 'Salin'}</span></button></div>;
}

export function Installation({ compact = false }: { compact?: boolean }) {
  const [active, setActive] = useState(0);
  return <div className={`installation ${compact ? 'compact' : ''}`}>
    <div className="install-top"><div className="platforms" role="group" aria-label="Pilih metode instalasi">{installers.map((item, index) => <button key={item.label} aria-pressed={active === index} onClick={() => setActive(index)}>{item.label}</button>)}</div><span className="mono shell-label">{installers[active].shell}</span></div>
    <CopyCode code={installers[active].command} />
    <p className="install-note">Butuh Python 3{active === 2 ? '.7+ dan pip' : ''}. Setelah terpasang, ketik <code>amagi</code> di terminal.</p>
  </div>;
}

type DemoPhase = 'waiting' | 'processing' | 'done';
const sessions = [
  { label: 'Thinking', command: 'jelaskan alur @app.py', note: 'Indikator ✻ berhenti saat jawaban tampil. Tiap tool muncul sebagai langkah; ringkasan menghitung durasi tugas dan file unik yang dibaca.' },
  { label: '@file', command: 'baca @app.py dan @"catatan project.md"', note: 'Referensi file teks UTF-8 dibaca saat pesan dikirim. Nama file dengan spasi bisa ditulis dalam tanda kutip.' },
  { label: 'Preview diff', command: 'ubah pesan pembuka di @app.py', note: 'Preview berisi nomor baris dan bar merah/hijau, lalu dialog izin menampilkan detail penulisan. File ditulis setelah pengguna menyetujuinya.' },
];

export function TerminalPreview() {
  const [active, setActive] = useState(0);
  const [phase, setPhase] = useState<DemoPhase>('done');
  const [elapsed, setElapsed] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | undefined>(undefined);
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => { setReducedMotion(query.matches); if (query.matches) { clearInterval(timer.current); setPlaying(false); } };
    update();
    query.addEventListener('change', update);
    return () => { query.removeEventListener('change', update); clearInterval(timer.current); };
  }, []);
  const stop = () => { clearInterval(timer.current); setPlaying(false); };
  const select = (index: number) => { stop(); setActive(index); setPhase('done'); setElapsed(0); };
  const replay = () => {
    clearInterval(timer.current);
    setElapsed(0);
    setPhase('waiting');
    if (reducedMotion) { setPlaying(false); return; }
    setPlaying(true);
    const started = performance.now();
    timer.current = setInterval(() => {
      const seconds = Math.floor((performance.now() - started) / 1000);
      setElapsed(seconds);
      if (seconds >= 3) { setPhase('done'); setPlaying(false); clearInterval(timer.current); }
      else if (seconds >= 1) setPhase('processing');
    }, 100);
  };
  const next = () => { stop(); setPhase(phase === 'waiting' ? 'processing' : 'done'); setElapsed(0); };
  const session = sessions[active];
  return <div className="terminal-wrap console-preview">
    <div className="terminal">
      <div className="terminal-bar"><span className="terminal-dots"><i /><i /><i /></span><span>Lyra Console — ~/amagi-cli</span><span>v{version}</span></div>
      <div className="terminal-body">
        <pre className="terminal-logo" aria-label="Logo ASCII Lyra CLI">{cliLogo}</pre>
        <div className="console-welcome" aria-label="Kartu sambutan Lyra CLI">
          <p className="console-welcome-title"><span>✦ Lyra CLI</span> v{version}</p>
          <p>Mau ngerjain apa hari ini?</p>
          <p className="console-context">Lyra Orpheus 6 · reasoning medium</p>
          <p className="console-context">~/amagi-cli</p>
        </div>
        <div className="console-composer console-sent"><span>›</span><span>{session.command}</span></div>
        <div className="console-output" key={`${active}-${phase}`}>
          {phase !== 'done' ? <>
            <div className="console-thinking"><span className={playing && !reducedMotion ? 'thinking-glyph spinning' : 'thinking-glyph'} aria-hidden="true">✻</span><span>{phase === 'waiting' ? 'Menunggu respons...' : 'Memproses permintaan...'}</span><time>({elapsed}s · Ctrl+C batal)</time></div>
            <p className="console-hint">{playing ? 'Simulasi sedang diputar' : 'Langkah contoh · lanjutkan untuk melihat hasil'}</p>
          </> : active === 2 ? <>
            <p className="console-tool"><i>●</i> <b>Baca</b><span>(app.py)</span></p><p className="console-result">⎿ Membaca 42 baris</p>
            <p className="console-tool"><i>●</i> <b>Tulis</b><span>(app.py)</span></p><p className="console-result">⎿ Perubahan · <em className="diff-add-text">+1</em> <em className="diff-remove-text">-1</em></p>
            <div className="console-diff"><span className="diff-line diff-remove"><u>12</u>-print("Halo")</span><span className="diff-line diff-add"><u>12</u>+print("Mau bikin apa hari ini?")</span></div>
            <div className="console-permission-box"><p>⚠ Konfirmasi Tulis File</p><p><em>Path</em> app.py</p></div>
            <p className="console-permission">Izinkan? (y/n) ❯</p>
          </> : <>
            <p className="console-tool"><i>●</i> <b>Baca</b><span>(app.py)</span></p><p className="console-result">⎿ Membaca 42 baris</p>
            {active === 1 && <><p className="console-tool"><i>●</i> <b>Baca</b><span>(catatan project.md)</span></p><p className="console-result">⎿ Membaca 8 baris</p></>}
            <p className="console-answer"><i>●</i> {active === 0 ? 'app.py mengatur sesi, model, dan pemanggilan tool.' : 'Kedua file dipakai sebagai konteks percakapan.'}</p>
            <p className="console-summary">✻ Selesai · {elapsed || 3}s · {active === 1 ? '2 file' : '1 file'} dibaca</p>
          </>}
        </div>
        <div className="console-composer"><span>› <i /></span></div>
        <div className="console-context console-shortcuts">Orpheus 6 · medium | ~/amagi-cli / main <span>/ perintah · @ file · Alt+Enter baris baru</span></div>
      </div>
      <div className="terminal-status"><span><i /> Orpheus 6 · medium</span><span>amagi-cli / main</span></div>
    </div>
    <div className="demo-tabs" role="group" aria-label="Contoh Lyra Console">{sessions.map((item, index) => <button key={item.label} aria-pressed={active === index} onClick={() => select(index)}><span>0{index + 1}</span>{item.label}</button>)}</div>
    <div className="demo-playback"><span>Simulasi browser · tanpa eksekusi CLI</span>{playing ? <button onClick={() => { stop(); setPhase('done'); }}>Hentikan contoh <Pause size={11} /></button> : phase !== 'done' ? <button onClick={next}>Langkah berikutnya <ArrowRight size={11} /></button> : <button onClick={replay}>Putar contoh <Play size={11} /></button>}</div>
    <p className="demo-caption">{session.note}</p>
  </div>;
}

export function PageHeading({ number, label, title, description }: { number: string; label: string; title: string; description: string }) {
  return <header className="page-heading"><p className="eyebrow">{number} / {label}</p><h1>{title}</h1><p className="lead">{description}</p></header>;
}
