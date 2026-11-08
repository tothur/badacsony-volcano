// Priority-flood + D8 flow accumulation. Usage: node flowacc.mjs in.f32 out.f32 W H cell
import fs from 'fs';
const [,, inp, out, W, H, CELL] = process.argv;
const w = +W, h = +H, cell = +CELL, N = w * h;
const z = new Float32Array(fs.readFileSync(inp).buffer.slice(0));
const f = new Float64Array(z), done = new Uint8Array(N);
let hk = new Float64Array(1 << 20), hi = new Int32Array(1 << 20), hn = 0;
function push(v, i) {
  if (hn === hk.length) { const k2 = new Float64Array(hn * 2); k2.set(hk); hk = k2; const i2 = new Int32Array(hn * 2); i2.set(hi); hi = i2; }
  let k = hn++; while (k > 0) { const p = (k - 1) >> 1; if (hk[p] <= v) break; hk[k] = hk[p]; hi[k] = hi[p]; k = p; } hk[k] = v; hi[k] = i;
}
function pop() {
  const top = hi[0], lv = hk[--hn], li = hi[hn]; let k = 0;
  for (;;) { const l = 2 * k + 1, r = l + 1; if (l >= hn) break; let m = l; if (r < hn && hk[r] < hk[l]) m = r; if (hk[m] >= lv) break; hk[k] = hk[m]; hi[k] = hi[m]; k = m; }
  hk[k] = lv; hi[k] = li; return top;
}
for (let x = 0; x < w; x++) for (const y of [0, h - 1]) { const i = y * w + x; if (!done[i]) { done[i] = 1; push(f[i], i); } }
for (let y = 1; y < h - 1; y++) for (const x of [0, w - 1]) { const i = y * w + x; done[i] = 1; push(f[i], i); }
const order = new Int32Array(N); let on = 0;
const DX = [1, -1, 0, 0, 1, 1, -1, -1], DY = [0, 0, 1, -1, 1, -1, 1, -1];
while (hn) {
  const i = pop(); order[on++] = i; const x = i % w, y = (i / w) | 0, v = f[i];
  for (let k = 0; k < 8; k++) { const xx = x + DX[k], yy = y + DY[k]; if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
    const j = yy * w + xx; if (done[j]) continue; done[j] = 1; if (f[j] <= v) f[j] = v + 1e-3; push(f[j], j); }
}
const rec = new Int32Array(N).fill(-1);
for (let i = 0; i < N; i++) { const x = i % w, y = (i / w) | 0; let best = -1, bs = 0;
  for (let k = 0; k < 8; k++) { const xx = x + DX[k], yy = y + DY[k]; if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
    const j = yy * w + xx, s = (f[i] - f[j]) / (k < 4 ? 1 : 1.41421); if (s > bs) { bs = s; best = j; } }
  rec[i] = best; }
const A = new Float32Array(N).fill(cell * cell);
for (let k = N - 1; k >= 0; k--) { const i = order[k]; if (rec[i] >= 0) A[rec[i]] += A[i]; }
fs.writeFileSync(out, Buffer.from(A.buffer));
console.log('flowacc done, max km2', (A.reduce((m, v) => v > m ? v : m, 0) / 1e6).toFixed(1));
