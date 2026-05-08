'use client';

import { useEffect, useRef } from 'react';

interface Node {
  label: string;
  x: number; // proportion of canvas width
  y: number; // proportion of canvas height
}

const NODES: Node[] = [
  { label: 'Upload',          x: 0.08, y: 0.35 },
  { label: 'Smart EDA',       x: 0.22, y: 0.22 },
  { label: 'Cleaning',        x: 0.36, y: 0.35 },
  { label: 'Insights',        x: 0.50, y: 0.22 },
  { label: 'BI Dashboard',    x: 0.62, y: 0.35 },
  { label: 'NL Query',        x: 0.74, y: 0.22 },
  { label: 'ML Recommender',  x: 0.85, y: 0.35 },
  { label: 'Report',          x: 0.93, y: 0.22 },
];

// Sequential edges: 0→1→2→3→4→5→6→7
const EDGES: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [4, 5], [5, 6], [6, 7],
];

const NODE_RADIUS = 18;
const PACKET_RADIUS = 3.5;
const NUM_PACKETS = 3;
const PACKET_SPEED = 0.004;
const CANVAS_OPACITY = 0.22;
const BLUE = '#3b82f6';
const BLUE_DIM = 'rgba(59,130,246,0.25)';
const BLUE_GLOW = 'rgba(59,130,246,0.08)';
const LABEL_COLOR = 'rgba(226,232,240,0.35)';

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

export default function PipelineGraph() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const packetsRef = useRef(
    Array.from({ length: NUM_PACKETS }, (_, i) => ({
      edgeIndex: Math.floor((i * EDGES.length) / NUM_PACKETS),
      t: (i / NUM_PACKETS),
    }))
  );
  const glowRef = useRef<number[]>(NODES.map(() => 0));
  const lastTimeRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const draw = (timestamp: number) => {
      animRef.current = requestAnimationFrame(draw);

      // Throttle to ~30 fps
      if (timestamp - lastTimeRef.current < 33) return;
      lastTimeRef.current = timestamp;

      const W = canvas.width;
      const H = canvas.height;
      ctx.clearRect(0, 0, W, H);

      // Resolve pixel positions
      const positions = NODES.map(n => ({ x: n.x * W, y: n.y * H }));

      // Decay node glows
      glowRef.current = glowRef.current.map(g => Math.max(0, g - 0.04));

      // Advance packets
      packetsRef.current = packetsRef.current.map(p => {
        let { edgeIndex, t } = p;
        t += PACKET_SPEED;
        if (t >= 1) {
          t = 0;
          edgeIndex = (edgeIndex + 1) % EDGES.length;
        }
        // Brighten the destination node
        const destNodeIdx = EDGES[edgeIndex][1];
        if (t > 0.85) {
          glowRef.current[destNodeIdx] = Math.min(1, glowRef.current[destNodeIdx] + 0.1);
        }
        return { edgeIndex, t };
      });

      // Draw edges
      EDGES.forEach(([a, b]) => {
        const p1 = positions[a];
        const p2 = positions[b];
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.strokeStyle = 'rgba(59,130,246,0.12)';
        ctx.lineWidth = 1;
        ctx.stroke();
      });

      // Draw nodes
      positions.forEach((pos, i) => {
        const glow = glowRef.current[i];
        const glowAlpha = 0.2 + glow * 0.6;
        const borderAlpha = 0.2 + glow * 0.7;

        // Outer glow ring
        if (glow > 0) {
          const grad = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, NODE_RADIUS * 2.5);
          grad.addColorStop(0, `rgba(59,130,246,${glow * 0.3})`);
          grad.addColorStop(1, 'transparent');
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, NODE_RADIUS * 2.5, 0, Math.PI * 2);
          ctx.fillStyle = grad;
          ctx.fill();
        }

        // Node fill
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, NODE_RADIUS, 0, Math.PI * 2);
        ctx.fillStyle = '#0f0f1a';
        ctx.fill();

        // Node border
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, NODE_RADIUS, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(59,130,246,${borderAlpha})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Center dot
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 3, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(59,130,246,${glowAlpha})`;
        ctx.fill();

        // Label
        ctx.font = '9px JetBrains Mono, monospace';
        ctx.textAlign = 'center';
        ctx.fillStyle = LABEL_COLOR;
        const label = NODES[i].label;
        // Wrap long labels
        const words = label.split(' ');
        if (words.length > 1) {
          ctx.fillText(words[0], pos.x, pos.y + NODE_RADIUS + 14);
          ctx.fillText(words.slice(1).join(' '), pos.x, pos.y + NODE_RADIUS + 24);
        } else {
          ctx.fillText(label, pos.x, pos.y + NODE_RADIUS + 14);
        }
      });

      // Draw packets
      packetsRef.current.forEach(p => {
        const [ai, bi] = EDGES[p.edgeIndex];
        const pa = positions[ai];
        const pb = positions[bi];
        const px = lerp(pa.x, pb.x, p.t);
        const py = lerp(pa.y, pb.y, p.t);

        // Glow
        const grad = ctx.createRadialGradient(px, py, 0, px, py, PACKET_RADIUS * 4);
        grad.addColorStop(0, 'rgba(59,130,246,0.7)');
        grad.addColorStop(1, 'transparent');
        ctx.beginPath();
        ctx.arc(px, py, PACKET_RADIUS * 4, 0, Math.PI * 2);
        ctx.fillStyle = grad;
        ctx.fill();

        // Core dot
        ctx.beginPath();
        ctx.arc(px, py, PACKET_RADIUS, 0, Math.PI * 2);
        ctx.fillStyle = '#93c5fd';
        ctx.fill();
      });
    };

    animRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 0, opacity: CANVAS_OPACITY }}
      aria-hidden="true"
    />
  );
}
