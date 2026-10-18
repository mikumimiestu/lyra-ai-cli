import { ArrowUpRight } from 'lucide-react';
import { releases, repository, version } from '../data';
import { CopyCode, PageHeading } from '../components/Workbench';

export function ChangelogPage() {
  return <div className="container inner-page">
    <PageHeading number="04" label="CATATAN VERSI" title="Perubahan yang sudah sampai ke CLI." description="Dari editor interaktif sampai thinking yang lebih ringkas. Catatan ini mengikuti perubahan yang sudah di-commit pada source Amagi." />
    <div className="release-layout">
      <aside><span className="version-display">v{version}</span><p className="mono"><span className="status-dot" /> Versi pada source</p><a className="text-link" href={`${repository}/commits/main/`} target="_blank" rel="noreferrer">Riwayat commit <ArrowUpRight size={15} /></a><div className="release-upgrade"><p className="eyebrow">UPDATE DI DALAM AMAGI</p><CopyCode code="/update" /><p>Konfirmasi, lalu keluar dan buka ulang aplikasi.</p></div></aside>
      <div className="release-history">{releases.map(release => <article key={release.version} id={`v${release.version}`} className="release-entry"><div className="release-entry-heading"><span className="mono">v{release.version}</span>{release.version === version && <span className="release-current"><span className="status-dot" /> Versi saat ini</span>}</div><h2>{release.title}</h2><ul>{release.changes.map(change => <li key={change}>{change}</li>)}</ul><a href={`${repository}/commit/${release.commit}`} target="_blank" rel="noreferrer" className="text-link">Lihat perubahan source <ArrowUpRight size={14} /></a></article>)}<p className="page-note">Memori Markdown, pengingat desktop, dan empat model Lyra tetap tersedia. Riwayat sebelum v2.3 dapat dilihat di repositori.</p></div>
    </div>
  </div>;
}
