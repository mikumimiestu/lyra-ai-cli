import { useEffect, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { ArrowUpRight, Menu, Moon, Sun, X } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { repository } from '../data';

export function Navbar() {
  const [open, setOpen] = useState(false);
  const { resolvedTheme, setTheme } = useTheme();
  const { pathname } = useLocation();
  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpen(false); };
    document.addEventListener('keydown', close);
    return () => document.removeEventListener('keydown', close);
  }, [open]);
  return <header className="site-header"><div className="container nav-inner">
    <Link to="/" className="wordmark" aria-label="Amagi CLI beranda"><span className="brand-mark">a<span>_</span></span><span>amagi<span className="brand-cli"> / cli</span></span></Link>
    <nav id="main-navigation" className={open ? 'main-nav open' : 'main-nav'} aria-label="Navigasi utama">{[['/docs', 'Panduan'], ['/commands', 'Perintah'], ['/models', 'Model'], ['/changelog', 'Catatan versi']].map(([path, label]) => <NavLink key={path} to={path}>{label}</NavLink>)}<a className="mobile-github" href={repository} target="_blank" rel="noreferrer">GitHub <ArrowUpRight size={14} /></a></nav>
    <div className="nav-actions"><button className="icon-button" onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')} aria-label={resolvedTheme === 'dark' ? 'Gunakan tema terang' : 'Gunakan tema gelap'}>{resolvedTheme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}</button><a className="github-link" href={repository} target="_blank" rel="noreferrer">GitHub <ArrowUpRight size={15} /></a><button className="icon-button menu-toggle" aria-label={open ? 'Tutup menu' : 'Buka menu'} aria-expanded={open} aria-controls="main-navigation" onClick={() => setOpen(!open)}>{open ? <X size={20} /> : <Menu size={20} />}</button></div>
  </div></header>;
}
