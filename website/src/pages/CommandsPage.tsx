import { useEffect, useRef, useState } from 'react';
import { Search, ArrowUpRight } from 'lucide-react';
import { commands } from '../data';
import { CopyCode, PageHeading } from '../components/Workbench';
export function CommandsPage() {
  const [query, setQuery] = useState('');
  const [group, setGroup] = useState('Semua');
  const searchRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const focusSearch = (event: KeyboardEvent) => {
      const target = event.target;
      if (event.key === '/' && !event.ctrlKey && !event.metaKey && !(target instanceof HTMLElement && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)))) {
        event.preventDefault();
        searchRef.current?.focus();
      }
    };
    document.addEventListener('keydown', focusSearch);
    return () => document.removeEventListener('keydown', focusSearch);
  }, []);
  const filtered = commands.filter(item => (group === 'Semua' || item.group === group) && `${item.name} ${item.description}`.toLowerCase().includes(query.toLowerCase()));
  return <div className="container inner-page"><PageHeading number="02" label="REFERENSI PERINTAH" title="Sedikit ketikan. Banyak jalan." description="Ketik / di Lyra Console untuk membuka saran. Cari kegunaannya di sini, lalu buka baris perintah untuk melihat contoh." /><div className="command-context-note"><span className="eyebrow">REFERENSI FILE</span><p>Tulis <code>@app.py</code> atau <code>@"catatan project.md"</code> dalam pesan biasa. Referensi file memakai konteks pesan, tanpa slash command tambahan.</p></div><div className="command-controls"><label className="search-field"><Search size={18} /><input ref={searchRef} type="search" placeholder="Cari perintah atau kegunaan…" value={query} onChange={event => setQuery(event.target.value)} aria-label="Cari perintah" /><kbd>/</kbd></label><div className="filter-tabs" role="group" aria-label="Kategori perintah">{['Semua', 'Sesi & model', 'Memori & waktu', 'File & project', 'Aplikasi'].map(item => <button key={item} aria-pressed={item === group} onClick={() => setGroup(item)}>{item}</button>)}</div></div><div className="list-heading"><span>PERINTAH / KEGUNAAN</span><span>{filtered.length} ditemukan</span></div><div className="command-list">{filtered.map(item => <details key={item.name}><summary><code>{item.name}</code><span>{item.description}</span><span className="detail-plus">+</span></summary><div className="command-detail"><p className="eyebrow">CONTOH DI DALAM AMAGI</p><CopyCode code={item.example} />{['/model', '/reasoning', '/memory', '/reminder', '/project'].includes(item.name) && <p>Perintah ini membuka menu interaktif. Ikuti pilihan yang muncul di terminal.</p>}</div></details>)}{filtered.length === 0 && <div className="empty-state"><h2>Belum ketemu.</h2><p>Coba kata seperti “folder”, “model”, atau “memori”.</p><button className="text-link" onClick={() => { setQuery(''); setGroup('Semua'); }}>Tampilkan semua perintah <ArrowUpRight size={16} /></button></div>}</div><p className="page-note">Ctrl+C membatalkan draft atau proses aktif; Ctrl+D pada input kosong untuk keluar. Butuh bantuan di terminal? Ketik <code>/help</code>. Gunakan <code>exit</code> atau <code>quit</code> untuk keluar.</p></div>;
}
