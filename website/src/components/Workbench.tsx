import { useEffect, useRef, useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { installers } from '../data';

export function CopyCode({ code, label = 'Salin perintah' }: { code: string; label?: string }) {
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

const sessions = [
  { label: 'Jelajahi file', command: '/ls .', lines: ['📂 ~/projects/catatan', '├── src/', '│   ├── app.py', '│   └── config.py', '├── README.md', '└── requirements.txt'], note: 'Lihat struktur folder dari direktori aktif.' },
  { label: 'Memori', command: '/memory', lines: ['Memori Jangka Panjang', '(Memori masih kosong)', '', '1. Tambah Catatan Baru', '2. Reset / Bersihkan Memori', '3. Kembali'], note: 'Catatan tersimpan di ~/.amagi_memory.md.' },
  { label: 'Project baru', command: '/project', lines: ['Buat Project Baru', '', 'Tipe project ❯ react', 'Nama project ❯ catatan', 'Direktori tujuan ❯ ~/projects', '', 'Memulai scaffolding react project…'], note: 'Wizard meminta tipe, nama, dan direktori project.' },
];
export function TerminalPreview() {
  const [active, setActive] = useState(0);
  const session = sessions[active];
  return <div className="terminal-wrap"><div className="terminal">
    <div className="terminal-bar"><span className="terminal-dots"><i /><i /><i /></span><span>amagi — ~/projects/catatan</span><span>01</span></div>
    <div className="terminal-body"><div className="terminal-brand">AMAGI<span>CLI / 2.4.0</span></div><p className="terminal-muted">AstByte Lyra · Orpheus 6 · medium</p><div className="terminal-divider" /><p className="terminal-prompt"><span>❯</span> {session.command}</p><pre key={active}>{session.lines.join('\n')}</pre><div className="terminal-cursor">❯ <span /></div></div>
    <div className="terminal-status"><span><i /> Direktori lokal</span><span>Contoh tampilan</span></div>
  </div><div className="demo-tabs" role="group" aria-label="Contoh penggunaan">{sessions.map((item, index) => <button key={item.label} aria-pressed={index === active} onClick={() => setActive(index)}><span>0{index + 1}</span>{item.label}</button>)}</div><p className="demo-caption" aria-live="polite">{session.note}</p></div>;
}

export function PageHeading({ number, label, title, description }: { number: string; label: string; title: string; description: string }) {
  return <header className="page-heading"><p className="eyebrow">{number} / {label}</p><h1>{title}</h1><p className="lead">{description}</p></header>;
}
