"""Badacsony paleo reconstruction. Stages: base -> (node flowacc) -> carve -> (node erode) -> final -> pack"""
import sys, json, math, os, numpy as np
from scipy import ndimage
W, stage = sys.argv[1], sys.argv[2]
g = json.load(open(f'{W}/grid4096.json')); N = 4096; cell = g['cell']
f32 = np.float32
def smoothstep(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def noise(scale, seed, n=N):
    gsz = n // scale + 3; gr = np.random.default_rng(seed).random((gsz, gsz)).astype(f32)
    return ndimage.zoom(gr, scale, order=3)[:n, :n]
def fbm(base, octs, seed):
    acc = np.zeros((N, N), f32); amp, tot, s = 1.0, 0.0, base
    for k in range(octs): acc += amp * (noise(max(2, s), seed + k) - .5); tot += amp; s //= 2; amp *= .5
    return acc / tot
def rc_of(la, lo): return (g['latc'] - la) * g['mlat'] / cell + (N - 1) / 2, (lo - g['lonc']) * g['mlon'] / cell + (N - 1) / 2
D = np.load(f'{W}/D4096.npy')
VOLC = [('Badacsony', 46.801, 17.4911, 340), ('Szent György-hegy', 46.8416, 17.4484, 320), ('Gulács', 46.8292, 17.5013, 300), ('Csobánc', 46.8714, 17.5045, 300)]
def volcano(name, la, lo, thr):
    r0, c0 = map(int, rc_of(la, lo)); w = int(500 / cell)
    sub = D[r0 - w:r0 + w, c0 - w:c0 + w]; k = np.unravel_index(np.argmax(sub), sub.shape); pr, pc = r0 - w + k[0], c0 - w + k[1]
    lab, _ = ndimage.label(D > thr); cap = lab == lab[pr, pc]
    soft = ndimage.gaussian_filter(cap.astype(f32), 60 / cell) > .5
    Rcap = math.sqrt(soft.sum() * cell * cell / math.pi)
    sd = ndimage.distance_transform_edt(~soft) * cell - ndimage.distance_transform_edt(soft) * cell
    cy, cx = ndimage.center_of_mass(cap)
    return dict(name=name, r=np.maximum(0, Rcap + sd).astype(f32), Rc=Rcap * 1.12, L=float(np.percentile(D[cap], 85)), cy=cy, cx=cx,
                x=float((cx - (N - 1) / 2) * cell), z=float((cy - (N - 1) / 2) * cell), px=float((pc - (N - 1) / 2) * cell), pz=float((pr - (N - 1) / 2) * cell), peak=float(D[pr, pc]))
if stage in ('base', 'final'):
    vs = [volcano(*v) for v in VOLC]
    for v in vs: print(v['name'], 'peak', round(v['peak']), 'Rc', round(v['Rc']), 'L', round(v['L']))
    rows = np.arange(N); north = (1 - rows / (N - 1)).astype(f32)
    B = 376 + 22 * north[:, None] + 26 * fbm(512, 4, 1) + 5 * fbm(96, 3, 20)
    def shapes(v, seed):
        r, Rc = v['r'], v['Rc']; Bv = float(B[int(v['cy']), int(v['cx'])])
        depth = 110 + 40 * min(1, Rc / 1200); hr = max(v['L'] + 24, Bv + 38) - Bv
        hrn = hr * (1 + .28 * fbm(160, 3, seed))
        ring = np.where(r < Rc, hrn * smoothstep(.68 * Rc, Rc, r), hrn * np.exp(-(r - Rc) / (.85 * Rc)))
        bowl = np.where(r < Rc, depth * np.power(np.clip(1 - (r / Rc) ** 2, 0, 1), .8), 0)
        crater = smoothstep(.99 * Rc, .93 * Rc, r)
        v.update(Bv=Bv, depth=depth, hr=hr); return ring.astype(f32), bowl.astype(f32), crater.astype(f32)
if stage == 'base':
    near = np.zeros_like(D, bool)
    for v in vs: near |= v['r'] < 1.5 * v['Rc']
    K = np.maximum(B, np.where(near, 0, D))
    ringO = np.zeros_like(D); oldLake = np.zeros_like(D)
    for k, v in enumerate(vs[1:]):
        ring, bowl, crater = shapes(v, 31 + k)
        K = K + ring - bowl; ringO += ring
        m = (crater > .5) & (K < v['L']); K = np.where(m, v['L'], K); oldLake = np.maximum(oldLake, m.astype(f32))
    np.save(f'{W}/ringO.npy', ringO.astype(f32)); np.save(f'{W}/oldLake.npy', oldLake.astype(f32))
    K.astype('<f4').tofile(f'{W}/K0.f32')
    print('base ok', K.min(), K.max())
elif stage == 'carve':
    K0 = np.fromfile(f'{W}/K0.f32', '<f4').reshape(N, N)
    A = np.fromfile(f'{W}/A_K0.f32', '<f4').reshape(N, N)
    inc = np.where(A > 4e4, np.minimum(32, 0.028 * np.sqrt(np.maximum(A - 4e4, 0))), 0).astype(f32)
    v = np.maximum(ndimage.grey_dilation(inc, size=9) * 0.8, inc)
    v = np.maximum(v, ndimage.gaussian_filter(ndimage.grey_dilation(inc, size=21), 10) * 0.9)
    v = ndimage.gaussian_filter(v, 2.5)
    (K0 - v).astype('<f4').tofile(f'{W}/K1.f32'); np.save(f'{W}/valley.npy', v.astype(f32)); print('carve ok', v.max())
elif stage == 'final':
    K2 = np.fromfile(f'{W}/K2.f32', '<f4').reshape(N, N); K0 = np.fromfile(f'{W}/K0.f32', '<f4').reshape(N, N)
    K = K2
    bad = vs[0]
    ringB, bowlB, craterB = shapes(bad, 41)
    yy, xx = np.mgrid[0:N, 0:N].astype(f32); d = np.hypot((xx - bad['cx']) * cell, (yy - bad['cy']) * cell)
    cone = (58 * np.power(np.clip(1 - d / 500, 0, 1), 1.15) * (1 + .15 * fbm(48, 2, 55)) - 22 * np.clip(1 - d / 140, 0, 1)).astype(f32)
    ash = np.where(bad['r'] < bad['Rc'], 1.0, np.exp(-(bad['r'] - bad['Rc']) / (1.8 * bad['Rc']))).astype(f32)
    valley = np.clip(K0 - K2, 0, None).astype(f32)
    np.save(f'{W}/K.npy', K); np.savez(f'{W}/shapes.npz', ringB=ringB, bowlB=bowlB, cone=cone, ringO=np.load(f'{W}/ringO.npy'), craterB=craterB, ash=ash, oldLake=np.load(f'{W}/oldLake.npy'), valley=valley)
    floor = bad['Bv'] - bad['depth'] * 0.95
    final = K + ringB - bowlB; final = np.where((craterB > .5) & (final < bad['L']), bad['L'], final) + cone
    np.save(f'{W}/Pfinal.npy', final.astype(f32))
    lab = [dict(text=v['name'], x=v['px'], z=v['pz'], kind='peak') for v in vs]
    def xz(la, lo): return dict(x=(lo - g['lonc']) * g['mlon'], z=(g['latc'] - la) * g['mlat'])
    lab += [dict(text='Lake Balaton', kind='water', **xz(46.778, 17.51)), dict(text='Badacsonytomaj', kind='town', **xz(46.8065, 17.5115)),
            dict(text='Badacsonytördemic', kind='town', **xz(46.8085, 17.4685)), dict(text='Tapolca', kind='town', **xz(46.882, 17.441))]
    json.dump(dict(bad={k: bad[k] for k in ('x', 'z', 'px', 'pz', 'Rc', 'L', 'Bv', 'depth', 'peak')}, floor=floor, labels=lab), open(f'{W}/volc.json', 'w'))
    print('final ok', 'lake', bad['L'], 'floor', floor)
elif stage == 'pack':
    from PIL import Image
    OUT = sys.argv[3]
    q = lambda a: np.clip(np.round((a - 50) * 40), 0, 65535).astype(np.uint32)
    def png16(u, path):
        rgb = np.stack([(u >> 8).astype(np.uint8), (u & 255).astype(np.uint8), np.zeros(u.shape, np.uint8)], -1)
        Image.fromarray(rgb).save(path, optimize=True); return os.path.getsize(path)
    K = np.load(f'{W}/K.npy'); D2 = np.load(f'{W}/D2048.npy')
    print('D', png16(q(D2), f'{OUT}/d2048.png'))
    for ty in range(2):
        for tx in range(2): print('K', png16(q(K[ty * 2048:(ty + 1) * 2048, tx * 2048:(tx + 1) * 2048]), f'{OUT}/k4096_{ty}{tx}.png'))
    print('K2048', png16(q(K.reshape(2048, 2, 2048, 2).mean((1, 3))), f'{OUT}/k2048.png'))
    S = np.load(f'{W}/shapes.npz'); names = ['ringB', 'bowlB', 'cone', 'ringO', 'craterB', 'ash', 'oldLake', 'valley']
    ranges, blocks = [], []
    for nme in names:
        a = S[nme].reshape(2048, 2, 2048, 2).mean((1, 3)); lo, hi = float(a.min()), float(a.max()); hi = hi if hi > lo else lo + 1
        ranges.append([lo, hi]); blocks.append(np.round((a - lo) / (hi - lo) * 65535).astype(np.uint32))
    print('shape', png16(np.concatenate(blocks, 0), f'{OUT}/shape2048.png'))
    # erosion timing (today's drainage + how much rock had to go) at 1024
    D1 = np.load(f'{W}/D1024.npy'); A = np.fromfile(f'{W}/A_D1024.f32', '<f4').reshape(1024, 1024)
    Pf = np.load(f'{W}/Pfinal.npy').reshape(1024, 4, 1024, 4).mean((1, 3))
    la = np.log10(A); la = np.clip((la - la.min()) / (np.percentile(la, 99.5) - la.min()), 0, 1)
    dep = np.clip((Pf - D1) / 300, 0, 1)
    ct = np.clip(0.12 + 0.68 * (0.55 * la + 0.45 * dep), 0.1, 0.8)
    ct = np.where(D1 < 112, np.maximum(ct, 0.6), ct)           # the Balaton basin is the regional low: it is lowered early, not last
    ct = ndimage.gaussian_filter(ct, 3.5)
    crater1 = np.load(f'{W}/shapes.npz')['craterB'].reshape(1024, 4, 1024, 4).mean((1, 3))
    chans = [np.zeros_like(ct), ct, np.zeros_like(ct), crater1]; auxR, blk = [], []
    for c_ in chans:
        lo, hi = float(c_.min()), float(c_.max()); hi = hi if hi > lo else lo + 1; auxR.append([lo, hi]); blk.append(np.round((c_ - lo) / (hi - lo) * 65535).astype(np.uint32))
    print('aux', png16(np.concatenate(blk, 0), f'{OUT}/aux1024.png'))
    vj = json.load(open(f'{W}/volc.json'))
    far = dict(x=1e6, z=1e6, ra=1.0, rb=1.0, rot=0.0, h=0.0)
    meta = dict(NC=4096, cell=cell, size=cell * (N - 1), grid=g, q=dict(offset=50, scale=40), shapeNames=names, shapeRanges=ranges, auxRanges=auxR,
                water=104.6, center=[vj['bad']['x'], vj['bad']['z']], summit=dict(lobes=[far] * 6, fumaroles=[[0, 0]]), **vj)
    json.dump(meta, open(f'{OUT}/meta.json', 'w')); print('meta ok')
