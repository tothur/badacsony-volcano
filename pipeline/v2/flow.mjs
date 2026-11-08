import fs from 'fs';
const [,, inp, out, W, H, CELL] = process.argv;
const w = +W, h = +H, cell = +CELL, N = w * h;
const z = new Float32Array(fs.readFileSync(inp).buffer.slice(0));
// priority-flood (with epsilon) so every cell drains to the edge
const filled = new Float64Array(z), done = new Uint8Array(N);
const heap = [], push = (v, i) => { heap.push([v, i]); let k = heap.length - 1; while (k > 0) { const p = (k - 1) >> 1; if (heap[p][0] <= heap[k][0]) break; [heap[p], heap[k]] = [heap[k], heap[p]]; k = p; } };
const pop = () => { const top = heap[0], last = heap.pop(); if (heap.length) { heap[0] = last; let k = 0; for (;;) { const l = 2 * k + 1, r = l + 1; let m = k; if (l < heap.length && heap[l][0] < heap[m][0]) m = l; if (r < heap.length && heap[r][0] < heap[m][0]) m = r; if (m === k) break; [heap[m], heap[k]] = [heap[k], heap[m]]; k = m; } } return top; };
for (let x = 0; x < w; x++) for (const y of [0, h - 1]) { const i = y * w + x; done[i] = 1; push(filled[i], i); }
for (let y = 1; y < h - 1; y++) for (const x of [0, w - 1]) { const i = y * w + x; done[i] = 1; push(filled[i], i); }
const order = []; const NB = [[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]];
const rec = new Int32Array(N).fill(-1);
while (heap.length) {
  const [v, i] = pop(); order.push(i); const x = i % w, y = (i / w) | 0;
  for (const [dx, dy] of NB) { const xx = x + dx, yy = y + dy; if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
    const j = yy * w + xx; if (done[j]) continue; done[j] = 1;
    if (filled[j] <= v) filled[j] = v + 1e-4; rec[j] = i; push(filled[j], j); }
}
// steepest descent receiver on filled surface
for (let i = 0; i < N; i++) { const x = i % w, y = (i / w) | 0; let best = -1, bs = 0;
  for (const [dx, dy] of NB) { const xx = x + dx, yy = y + dy; if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
    const j = yy * w + xx, s = (filled[i] - filled[j]) / Math.hypot(dx, dy); if (s > bs) { bs = s; best = j; } }
  if (best >= 0) rec[i] = best; }
const A = new Float64Array(N).fill(cell * cell);
for (let k = order.length - 1; k >= 0; k--) { const i = order[k]; if (rec[i] >= 0) A[rec[i]] += A[i]; }
const inc = new Float32Array(N);
for (let i = 0; i < N; i++) inc[i] = A[i] < 4e4 ? 0 : Math.min(32, 0.028 * Math.sqrt(A[i] - 4e4));
console.log('max A km2', (A.reduce((m, v) => Math.max(m, v), 0) / 1e6).toFixed(1));
fs.writeFileSync(out, Buffer.from(inc.buffer));
