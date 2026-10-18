import { useEffect, useRef, useState } from 'react';
import { BoxGeometry, CanvasTexture, Color, CylinderGeometry, DirectionalLight, EdgesGeometry, Group, HemisphereLight, LineBasicMaterial, LineSegments, Mesh, MeshStandardMaterial, PerspectiveCamera, PlaneGeometry, Scene, SRGBColorSpace, TorusGeometry, Vector2, WebGLRenderer } from 'three';
import { Pause, Play } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

function screenTexture(title: string, subtitle: string, accent: string) {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 320;
  const context = canvas.getContext('2d')!;
  context.fillStyle = '#242b27';
  context.fillRect(0, 0, 512, 320);
  context.fillStyle = accent;
  context.fillRect(36, 35, 30, 5);
  context.font = 'bold 100px monospace';
  context.fillText(title, 36, 175);
  context.fillStyle = '#aab99e';
  context.font = '22px monospace';
  context.fillText(subtitle, 36, 260);
  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  return texture;
}

export default function WorkspaceScene() {
  const hostRef = useRef<HTMLDivElement>(null);
  const playingRef = useRef(true);
  const [playing, setPlaying] = useState(true);
  const [available, setAvailable] = useState(true);
  const { resolvedTheme } = useTheme();
  useEffect(() => { playingRef.current = playing; }, [playing]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    let renderer: WebGLRenderer;
    try { renderer = new WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' }); }
    catch { setAvailable(false); return; }
    setAvailable(true);
    const dark = resolvedTheme === 'dark';
    const scene = new Scene();
    const camera = new PerspectiveCamera(32, 1, 0.1, 100);
    camera.position.set(6.2, 5.1, 7.8);
    camera.lookAt(0, 0.2, 0);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
    renderer.outputColorSpace = SRGBColorSpace;
    host.appendChild(renderer.domElement);
    scene.add(new HemisphereLight(0xfff9e9, 0x596856, 3.2));
    const key = new DirectionalLight(0xffedcf, 5);
    key.position.set(3, 8, 4);
    scene.add(key);
    const rim = new DirectionalLight(0xb5cfa6, 2.2);
    rim.position.set(-5, 2, -4);
    scene.add(rim);
    const assembly = new Group();
    scene.add(assembly);
    const cream = new MeshStandardMaterial({ color: dark ? '#a4ad97' : '#dedcc9', roughness: 0.5, metalness: 0.15 });
    const graphite = new MeshStandardMaterial({ color: '#303c31', roughness: 0.4, metalness: 0.5 });
    const copper = new MeshStandardMaterial({ color: '#bf694b', roughness: 0.35, metalness: 0.55 });
    const green = new MeshStandardMaterial({ color: '#8a9d70', roughness: 0.45, metalness: 0.3 });
    const base = new Mesh(new CylinderGeometry(3.15, 3.15, 0.14, 80), graphite);
    base.position.y = -0.75;
    assembly.add(base);
    const inset = new Mesh(new CylinderGeometry(2.97, 2.97, 0.025, 80), cream);
    inset.position.y = -0.66;
    assembly.add(inset);
    // Traces connect the terminal, memory, and scheduler modules on the board.
    for (let index = 0; index < 6; index++) {
      const trace = new Mesh(new TorusGeometry(1.2 + index * 0.25, 0.009, 5, 80, Math.PI * 1.45), copper);
      trace.rotation.x = -Math.PI / 2;
      trace.rotation.z = index * 0.4;
      trace.position.y = -0.62;
      assembly.add(trace);
    }
    const modules: Group[] = [];
    const textures: CanvasTexture[] = [];
    const positions = [[0, 0.75, 0, 1.7, '>_', 'AMAGI / CLI'], [-2, 0.2, 0.65, 0.85, 'md', 'MEMORY'], [1.65, 0.15, -1.15, 0.85, '10m', 'REMINDER']] as const;
    positions.forEach(([x, y, z, size, title, subtitle], index) => {
      const module = new Group();
      module.position.set(x, y, z);
      module.rotation.y = index === 1 ? 0.3 : -0.2;
      const housing = new Mesh(new BoxGeometry(size, size * 0.8, 0.28), cream);
      module.add(housing);
      const texture = screenTexture(title, subtitle, index === 0 ? '#df9674' : '#b4c999');
      textures.push(texture);
      const screen = new Mesh(new PlaneGeometry(size * 0.86, size * 0.59), new MeshStandardMaterial({ map: texture, roughness: 0.7, emissive: new Color('#ffffff'), emissiveMap: texture, emissiveIntensity: 0.35 }));
      screen.position.z = 0.145;
      module.add(screen);
      const outline = new LineSegments(new EdgesGeometry(housing.geometry), new LineBasicMaterial({ color: '#8b9580', transparent: true, opacity: 0.25 }));
      module.add(outline);
      const stem = new Mesh(new BoxGeometry(size * 0.24, 0.35, 0.18), graphite);
      stem.position.y = -size * 0.4 - 0.16;
      module.add(stem);
      assembly.add(module);
      modules.push(module);
    });
    for (let index = 0; index < 8; index++) {
      const chip = new Mesh(new BoxGeometry(0.18, 0.1, 0.28), index % 2 ? green : copper);
      const angle = index / 8 * Math.PI * 2;
      chip.position.set(Math.cos(angle) * 2.65, -0.55, Math.sin(angle) * 2.65);
      chip.rotation.y = angle;
      assembly.add(chip);
    }
    const pointer = new Vector2();
    const onPointerMove = (event: PointerEvent) => {
      const bounds = host.getBoundingClientRect();
      pointer.set((event.clientX - bounds.left) / bounds.width - 0.5, (event.clientY - bounds.top) / bounds.height - 0.5);
    };
    const resetPointer = () => pointer.set(0, 0);
    host.addEventListener('pointermove', onPointerMove);
    host.addEventListener('pointerleave', resetPointer);
    const resize = new ResizeObserver(() => {
      renderer.setSize(host.clientWidth, host.clientHeight);
      camera.aspect = host.clientWidth / Math.max(host.clientHeight, 1);
      camera.updateProjectionMatrix();
    });
    resize.observe(host);
    let visible = true;
    let frame = 0;
    let lastTime = 0;
    let elapsed = 0;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const render = (time: number) => {
      frame = 0;
      if (!visible || document.hidden) { lastTime = 0; return; }
      const delta = lastTime ? Math.min(time - lastTime, 50) : 0;
      lastTime = time;
      if (playingRef.current && !reducedMotion.matches) elapsed += delta / 1000;
      modules.forEach((module, index) => { module.position.y = positions[index][1] + Math.sin(elapsed * 1.1 + index) * 0.075; });
      const interactive = !reducedMotion.matches && playingRef.current;
      assembly.rotation.y += ((interactive ? pointer.x * 0.28 + Math.sin(elapsed * 0.3) * 0.04 : 0) - assembly.rotation.y) * 0.06;
      assembly.rotation.x += ((interactive ? pointer.y * 0.09 : 0) - assembly.rotation.x) * 0.06;
      renderer.render(scene, camera);
      if (!reducedMotion.matches && playingRef.current) frame = requestAnimationFrame(render);
    };
    const start = () => { if (!frame) frame = requestAnimationFrame(render); };
    const visibility = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; if (visible) start(); });
    visibility.observe(host);
    document.addEventListener('visibilitychange', start);
    reducedMotion.addEventListener('change', start);
    host.addEventListener('amagi-playback', start);
    start();
    return () => {
      cancelAnimationFrame(frame);
      resize.disconnect();
      visibility.disconnect();
      document.removeEventListener('visibilitychange', start);
      reducedMotion.removeEventListener('change', start);
      host.removeEventListener('pointermove', onPointerMove);
      host.removeEventListener('pointerleave', resetPointer);
      host.removeEventListener('amagi-playback', start);
      scene.traverse(object => {
        if (object instanceof Mesh || object instanceof LineSegments) {
          object.geometry.dispose();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach(material => material.dispose());
        }
      });
      textures.forEach(texture => texture.dispose());
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [resolvedTheme]);

  return <div className="workspace-scene relative overflow-hidden rounded-t-lg">
    <div className="scene-grid" aria-hidden="true" />
    <div className="scene-corner mono"><span className="status-dot" /> AMAGI WORKSPACE <span>FIG. 01</span></div>
    <div ref={hostRef} className="scene-canvas" role="img" aria-label="Ilustrasi 3D terminal Amagi, memori Markdown, dan pengingat yang terhubung di satu papan." />
    {!available && <div className="scene-fallback" aria-hidden="true"><span>md</span><strong>❯_</strong><span>10m</span></div>}
    <div className="scene-bottom mono"><span>TERMINAL · MEMORY · REMINDER</span>{available && <button className="scene-pause inline-flex items-center gap-2 transition-colors hover:text-[var(--accent)]" onClick={() => { const next = !playing; playingRef.current = next; setPlaying(next); hostRef.current?.dispatchEvent(new Event('amagi-playback')); }} aria-label={playing ? 'Jeda animasi 3D' : 'Putar animasi 3D'} aria-pressed={!playing}>{playing ? <Pause size={12} /> : <Play size={12} />}<span>{playing ? 'Jeda' : 'Putar'}</span></button>}</div>
  </div>;
}
