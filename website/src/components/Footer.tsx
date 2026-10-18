import { Link } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import { repository, version } from '../data';
export function Footer() {
  return <footer className="site-footer"><div className="container"><div className="footer-main"><Link to="/" className="wordmark"><span className="brand-mark">a<span>_</span></span><span>amagi<span className="brand-cli"> / cli</span></span></Link><p>Tempat kerja tetap di terminal.</p><a href={repository} target="_blank" rel="noreferrer">Lihat source <ArrowUpRight size={16} /></a></div><div className="footer-bottom"><span>Amagi CLI · AstByte Lyra</span><span>macOS / Linux / Windows</span><Link to="/changelog">v{version} <span className="status-dot" /></Link></div></div></footer>;
}
