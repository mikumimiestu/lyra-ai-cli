import { useEffect } from 'react';
import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { Navbar } from './components/Navbar';
import { SiteMotion } from './components/SiteMotion';
import { Footer } from './components/Footer';
import { HomePage } from './pages/HomePage';
import { DocsPage } from './pages/DocsPage';
import { ModelsPage } from './pages/ModelsPage';
import { CommandsPage } from './pages/CommandsPage';
import { ChangelogPage } from './pages/ChangelogPage';
function NavigationEffects() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    const names: Record<string, string> = { '/': 'Asisten di terminal kamu', '/docs': 'Panduan', '/commands': 'Perintah', '/models': 'Model', '/changelog': 'Catatan versi' };
    document.title = `${names[pathname] || 'Halaman tidak ditemukan'} — Amagi CLI`;
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView();
    else window.scrollTo(0, 0);
  }, [pathname, hash]);
  return null;
}
function App() {
  return <ThemeProvider><BrowserRouter><NavigationEffects /><SiteMotion /><a className="skip-link" href="#main">Langsung ke konten</a><Navbar /><main id="main"><Routes><Route path="/" element={<HomePage />} /><Route path="/docs" element={<DocsPage />} /><Route path="/models" element={<ModelsPage />} /><Route path="/commands" element={<CommandsPage />} /><Route path="/changelog" element={<ChangelogPage />} /><Route path="*" element={<div className="container page-heading"><p className="eyebrow">404</p><h1>Halaman ini belum ada.</h1><Link className="button primary" to="/">Kembali ke beranda</Link></div>} /></Routes></main><Footer /></BrowserRouter></ThemeProvider>;
}
export default App;
