import fs from 'fs';
const [,, inp, out, W, H, CELL, NDROP] = process.argv;
const w = +W, h = +H, cell = +CELL;
const src = new Float32Array(fs.readFileSync(inp).buffer.slice(0));
const map = new Float32Array(src.length);
for (let i = 0; i < map.length; i++) map[i] = src[i] / cell; // dimensionless (cell = 1)
// Lague-style droplet erosion
const P = { inertia: .05, cap: 6, minCap: .002, erode: .35, deposit: .3, evap: .015, grav: 4, life: 60, radius: 4 };
const brushIdx = [], brushW = [];
for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { /* built lazily per cell below */ }
const R = P.radius, offs = [], wts = []; let ws = 0;
for (let dy = -R; dy <= R; dy++) for (let dx = -R; dx <= R; dx++) { const d = Math.hypot(dx, dy); if (d <= R) { offs.push([dx, dy]); wts.push(1 - d / R); ws += 1 - d / R; } }
for (let k = 0; k < wts.length; k++) wts[k] /= ws;
let seed = 12345; const rnd = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
function hg(x, y) {
  const cx = x | 0, cy = y | 0, u = x - cx, v = y - cy, i = cy * w + cx;
  const a = map[i], b = map[i + 1], c = map[i + w], d = map[i + w + 1];
  return [(b - a) * (1 - v) + (d - c) * v, (c - a) * (1 - u) + (d - b) * u, a * (1 - u) * (1 - v) + b * u * (1 - v) + c * (1 - u) * v + d * u * v];
}
const N = +NDROP;
for (let n = 0; n < N; n++) {
  let x = rnd() * (w - 2), y = rnd() * (h - 2), dx = 0, dy = 0, speed = 1, water = 1, sed = 0;
  for (let s = 0; s < P.life; s++) {
    const cx = x | 0, cy = y | 0, u = x - cx, v = y - cy, i = cy * w + cx;
    const [gx, gy, hh] = hg(x, y);
    dx = dx * P.inertia - gx * (1 - P.inertia); dy = dy * P.inertia - gy * (1 - P.inertia);
    const len = Math.hypot(dx, dy); if (len === 0) break; dx /= len; dy /= len;
    x += dx; y += dy;
    if (x < 1 || y < 1 || x >= w - 2 || y >= h - 2) break;
    const nh = hg(x, y)[2], dh = nh - hh;
    const capacity = Math.max(-dh, P.minCap) * speed * water * P.cap;
    if (sed > capacity || dh > 0) {
      const amt = dh > 0 ? Math.min(dh, sed) : (sed - capacity) * P.deposit; sed -= amt;
      map[i] += amt * (1 - u) * (1 - v); map[i + 1] += amt * u * (1 - v); map[i + w] += amt * (1 - u) * v; map[i + w + 1] += amt * u * v;
    } else {
      const amt = Math.min((capacity - sed) * P.erode, -dh);
      for (let k = 0; k < offs.length; k++) {
        const bx = cx + offs[k][0], by = cy + offs[k][1]; if (bx < 0 || by < 0 || bx >= w || by >= h) continue;
        const j = by * w + bx, e = amt * wts[k], de = map[j] < e ? map[j] : e;
        map[j] -= de; sed += de;
      }
    }
    speed = Math.sqrt(Math.max(0, speed * speed + dh * P.grav)); water *= 1 - P.evap;
  }
}
const res = new Float32Array(map.length); let maxCut = 0, maxFill = 0;
for (let i = 0; i < map.length; i++) { res[i] = map[i] * cell; const d = res[i] - src[i]; if (d < maxCut) maxCut = d; if (d > maxFill) maxFill = d; }
console.log('max cut', maxCut.toFixed(1), 'max fill', maxFill.toFixed(1));
fs.writeFileSync(out, Buffer.from(res.buffer));
