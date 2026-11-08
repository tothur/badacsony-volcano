"""1 m layer around Badacsony, as residual on top of the viewer's eruption-time surface. Stages: prep -> (node flowacc) -> geo -> (node erode) -> pack"""
import sys, json, math, os, numpy as np
from scipy import ndimage
W, stage = sys.argv[1], sys.argv[2]
OUTD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
meta = json.load(open(f'{OUTD}/meta.json')); g = meta['grid']; NK = 4096; cell = g['cell']
BX, BZ = meta['bad']['x'], meta['bad']['z']
N1 = 6144; X0, Z0 = BX - (N1 - 1) / 2, BZ - (N1 - 1) / 2
f32 = np.float32
def smoothstep(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def noise(scale, seed, n=N1):
    gsz = n // scale + 3; gr = np.random.default_rng(seed).random((gsz, gsz)).astype(f32)
    return ndimage.zoom(gr, scale, order=3)[:n, :n]
xs = X0 + np.arange(N1, dtype=np.float64); zs = Z0 + np.arange(N1, dtype=np.float64)
def kcoords(r0, r1):
    R, C = np.meshgrid(zs[r0:r1], xs, indexing='ij'); return R / cell + (NK - 1) / 2, C / cell + (NK - 1) / 2
if stage == 'prep':
    Pf = np.load(f'{W}/Pfinal.npy'); out = np.empty((N1, N1), f32)
    for r0 in range(0, N1, 1024):
        R, C = kcoords(r0, r0 + 1024); out[r0:r0 + 1024] = ndimage.map_coordinates(Pf, [R, C], order=3)
    out.tofile(f'{W}/m1_base.f32')
    (out + 1.2 * (noise(24, 71) - .5) + 0.4 * (noise(6, 72) - .5)).astype('<f4').tofile(f'{W}/m1_flow.f32')
    print('prep ok', out.min(), out.max())
elif stage == 'geo':
    h = np.fromfile(f'{W}/m1_base.f32', '<f4').reshape(N1, N1); A = np.fromfile(f'{W}/m1_A.f32', '<f4').reshape(N1, N1)
    X, Z = np.meshgrid(xs, zs); r = np.hypot(X - BX, Z - BZ).astype(f32); del X, Z
    lakeL = meta['bad']['L']
    lake = (np.abs(h - lakeL) < 0.6) & (r < meta['bad']['Rc'])            # the flat lava-lake surface stays untouched
    gy0, gx0 = np.gradient(ndimage.gaussian_filter(h, 6.0)); s0 = np.hypot(gx0, gy0); del gy0, gx0
    inc = np.where(A > 250, np.minimum(2.5, 0.012 * np.sqrt(np.maximum(A - 250, 0))), 0).astype(f32) * smoothstep(0.07, 0.15, s0) * (~lake)
    h = h - ndimage.gaussian_filter(np.maximum(ndimage.grey_dilation(inc, size=3) * 0.7, inc), 0.7)
    gy, gx = np.gradient(ndimage.gaussian_filter(h, 2.0)); slope = np.hypot(gx, gy).astype(f32); del gx, gy
    steep = smoothstep(0.42, 0.8, slope + 0.15 * (noise(40, 5) - 0.5)) * (~lake)
    # bedded tuff and scoria: thin layers that dip away from the vent
    warp = 2.5 * (noise(150, 7) - .5) + 1 * (noise(25, 8) - .5) + r * 0.02
    sp = 1.6 + 2.4 * noise(220, 9)
    q = (h + warp) / sp; fr = q - np.floor(q)
    terr = (np.floor(q) + smoothstep(0.62, 0.95, fr)) * sp - warp
    h = h + (terr - h) * steep * 0.7
    below = ndimage.gaussian_filter(steep, 5) * (1 - steep)
    scree = smoothstep(0.08, 0.35, below).astype(f32)
    h = h + scree * 0.7 * (0.6 + 0.8 * noise(6, 11))
    h.astype('<f4').tofile(f'{W}/m1_geo.f32')
    np.save(f'{W}/m1_rock.npy', steep.astype(f32)); np.save(f'{W}/m1_scree.npy', scree); np.save(f'{W}/m1_lake.npy', lake)
    print('geo ok', float((steep > .5).mean()), float((scree > .5).mean()))
elif stage == 'pack':
    from PIL import Image
    geo = np.fromfile(f'{W}/m1_geo.f32', '<f4').reshape(N1, N1); ero = np.fromfile(f'{W}/m1_ero.f32', '<f4').reshape(N1, N1)
    gy, gx = np.gradient(ndimage.gaussian_filter(geo, 4)); slp = np.hypot(gx, gy); del gy, gx
    lake = np.load(f'{W}/m1_lake.npy')
    h = geo + (ero - geo) * np.clip((slp - 0.035) / 0.055, 0, 1) * (~lake)
    # what the viewer draws for the finished eruption: quantised K + quantised shape layers, bilinear
    def png16(path): a = np.array(Image.open(path)).astype(np.uint32); return a[..., 0] * 256 + a[..., 1]
    K = np.zeros((NK, NK), np.float64)
    for ty in range(2):
        for tx in range(2): K[ty * 2048:(ty + 1) * 2048, tx * 2048:(tx + 1) * 2048] = png16(f'{OUTD}/k4096_{ty}{tx}.png') / 40 + 50
    sh = png16(f'{OUTD}/shape2048.png').reshape(8, 2048, 2048).astype(np.float64)
    nm = meta['shapeNames']; rg = meta['shapeRanges']
    Sch = {nm[k]: rg[k][0] + sh[k] / 65535 * (rg[k][1] - rg[k][0]) for k in range(8)}
    res = np.empty((N1, N1), f32); L = meta['bad']['L']
    for r0 in range(0, N1, 1024):
        R, C = kcoords(r0, r0 + 1024)
        base = ndimage.map_coordinates(K, [R, C], order=1)
        s2r, s2c = R / (NK - 1) * 2047, C / (NK - 1) * 2047
        ring, bowl, cone, crater = [ndimage.map_coordinates(Sch[n], [s2r, s2c], order=1) for n in ('ringB', 'bowlB', 'cone', 'craterB')]
        f = base + ring - bowl; f = np.where((crater > 0.5) & (f <= L), L, f) + cone
        res[r0:r0 + 1024] = h[r0:r0 + 1024] - f
    a = np.abs(res); print('residual p99', np.percentile(a, 99), 'max', a.max())
    SCALE = 0.1
    q = np.clip(np.round(res / SCALE) + 128, 0, 255).astype(np.uint8)
    G = np.clip(np.load(f'{W}/m1_rock.npy') * 255, 0, 255).astype(np.uint8); B = np.clip(np.load(f'{W}/m1_scree.npy') * 255, 0, 255).astype(np.uint8)
    os.makedirs(f'{OUTD}/m1', exist_ok=True); T = 512; nt = N1 // T; tot = 0
    for ty in range(nt):
        for tx in range(nt):
            sl = (slice(ty * T, (ty + 1) * T), slice(tx * T, (tx + 1) * T)); p = f'{OUTD}/m1/{tx}_{ty}.png'
            Image.fromarray(np.dstack([q[sl], G[sl], B[sl]])).save(p, optimize=True); tot += os.path.getsize(p)
    print('tiles', nt * nt, 'MB', round(tot / 1e6, 1))
    meta['hi1'] = dict(N=N1, x0=X0, z0=Z0, tile=T, tiles=nt, scale=SCALE, offset=128)
    json.dump(meta, open(f'{OUTD}/meta.json', 'w')); print('meta ok')
