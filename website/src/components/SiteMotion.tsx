import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';

export function SiteMotion() {
  const { pathname } = useLocation();
  const progressRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let frame = 0;
    const update = () => {
      const range = document.documentElement.scrollHeight - window.innerHeight;
      if (progressRef.current) progressRef.current.style.transform = `scaleX(${range > 0 ? window.scrollY / range : 0})`;
      frame = 0;
    };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(update); };
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    update();
    return () => { cancelAnimationFrame(frame); window.removeEventListener('scroll', onScroll); window.removeEventListener('resize', onScroll); };
  }, [pathname]);
  useEffect(() => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (reducedMotion.matches) return;
    const targets = document.querySelectorAll('.section, .index-strip, .model-table-row, .two-column-notes > section, .docs-content > section, .release-items > li');
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.setAttribute('data-visible', 'true');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -20px 0px' });
    targets.forEach(target => { target.setAttribute('data-reveal', 'true'); observer.observe(target); });
    return () => {
      observer.disconnect();
      targets.forEach(target => { target.removeAttribute('data-reveal'); target.removeAttribute('data-visible'); });
    };
  }, [pathname]);
  return <div className="reading-progress" ref={progressRef} aria-hidden="true" />;
}
