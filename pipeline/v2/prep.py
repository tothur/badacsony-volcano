import sys, math, os, urllib.request
import numpy as np, rasterio
from rasterio.windows import from_bounds
from scipy import ndimage
from PIL import Image
SP, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True); os.makedirs(f'{SP}/raw/sat', exist_ok=True)
lat0, lat1, lon0, lon1 = 46.765, 46.845, 17.435, 17.550
latc = (lat0 + lat1) / 2
mlon = 111320 * math.cos(math.radians(latc)); mlat = 111132
NC = 1024; cell = (lon1 - lon0) * mlon / (NC - 1); NR = int(round((lat1 - lat0) * mlat / cell)) + 1
lat1e = lat1; lat0e = lat1 - (NR - 1) * cell / mlat
cols = np.arange(NC); rows = np.arange(NR)
lon = lon0 + cols * cell / mlon; lat = lat1 - rows * cell / mlat
with rasterio.open(f'{SP}/raw/glo30.tif') as ds:
    win = from_bounds(lon0 - .01, lat0 - .01, lon1 + .01, lat1 + .01, ds.transform)
    a = ds.read(1, window=win).astype(np.float64); tr = ds.window_transform(win)
LON, LAT = np.meshgrid(lon, lat)
D = ndimage.map_coordinates(a, [(LAT - tr.f) / tr.e - .5, (LON - tr.c) / tr.a - .5], order=3, mode='nearest')
print('grid', NC, NR, 'cell', round(cell, 2), 'D', D.min(), D.max())
lowvals = D[D < 110]; print('low hist', np.percentile(lowvals, [1, 10, 50, 90]) if lowvals.size else None)

# --- satellite mosaic (EOX Sentinel-2 cloudless 2020), z14
z = 14; n = 2 ** z
mx = lambda lo: (lo + 180) / 360 * n * 256
def my(la):
    r = math.radians(la); return (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * n * 256
x0, x1 = int(mx(lon0) // 256), int(mx(lon1) // 256); y0, y1 = int(my(lat1) // 256), int(my(lat0e) // 256)
mos = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256, 3), np.uint8)
for tx in range(x0, x1 + 1):
    for ty in range(y0, y1 + 1):
        p = f'{SP}/raw/sat/{z}_{tx}_{ty}.jpg'
        if not os.path.exists(p):
            urllib.request.urlretrieve(f'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2020_3857/default/g/{z}/{ty}/{tx}.jpg', p)
        mos[(ty - y0) * 256:(ty - y0 + 1) * 256, (tx - x0) * 256:(tx - x0 + 1) * 256] = np.asarray(Image.open(p).convert('RGB'))
SW = 2048; SH = int(round(SW * (NR - 1) / (NC - 1))) + 1
slon = lon0 + np.arange(SW) / (SW - 1) * (lon1 - lon0); slat = lat1 - np.arange(SH) / (SH - 1) * (lat1 - lat0e)
PX, PY = np.meshgrid(np.array([mx(v) for v in slon]) - x0 * 256 - .5, np.array([my(v) for v in slat]) - y0 * 256 - .5)
img = np.stack([ndimage.map_coordinates(mos[:, :, c].astype(float), [PY, PX], order=1) for c in range(3)], -1)
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(f'{OUT}/sat.jpg', quality=86, optimize=True)
print('sat', SW, SH)

# --- volcano geometry
X = (cols - (NC - 1) / 2) * cell; Zc = (rows - (NR - 1) / 2) * cell
XX, ZZ = np.meshgrid(X, Zc)
def gridpos(la, lo): return (lat1 - la) * mlat / cell, (lo - lon0) * mlon / cell
def peak(la, lo, rad=70):
    r, c = map(int, map(round, gridpos(la, lo)))
    sub = D[r - rad:r + rad, c - rad:c + rad]; k = np.unravel_index(np.argmax(sub), sub.shape)
    return r - rad + k[0], c - rad + k[1]
rng = np.random.default_rng(7)
def noise(scale_cells, seed):
    g = np.random.default_rng(seed).random((NR // scale_cells + 3, NC // scale_cells + 3))
    return ndimage.zoom(g, scale_cells, order=3)[:NR, :NC]
def fbm(base, oct, seed):
    s, amp, tot = base, 1, 0
    acc = np.zeros((NR, NC))
    for k in range(oct):
        acc += amp * (noise(max(2, s), seed + k) - .5); tot += amp; s //= 2; amp *= .5
    return acc / tot
def smoothstep(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

def volcano(la, lo, thr, name):
    pr, pc = peak(la, lo)
    lab, _ = ndimage.label(D > thr); cap = lab == lab[pr, pc]
    soft = ndimage.gaussian_filter(cap.astype(float), 60 / cell) > .5
    area = soft.sum() * cell * cell; Rcap = math.sqrt(area / math.pi)
    sd = ndimage.distance_transform_edt(~soft) * cell - ndimage.distance_transform_edt(soft) * cell
    r = np.maximum(0, Rcap + sd)
    Rc = Rcap * 1.12
    L = float(np.percentile(D[cap], 85))
    cy, cx = ndimage.center_of_mass(cap)
    print(name, 'peak', D[pr, pc], 'Rcap', round(Rcap), 'L', round(L), 'cells', cap.sum())
    return dict(name=name, r=r, Rc=Rc, L=L, cap=cap, pr=pr, pc=pc, cy=cy, cx=cx,
                x=float((cx - (NC - 1) / 2) * cell), z=float((cy - (NR - 1) / 2) * cell),
                px=float(X[pc]), pz=float(Zc[pr]), peak=float(D[pr, pc]))
bad = volcano(46.801, 17.4911, 340, 'Badacsony')
gul = volcano(46.8292, 17.5013, 300, 'Gulacs')

# --- old plain
north = 1 - rows / (NR - 1)
B = 376 + 22 * north[:, None] + 26 * fbm(160, 4, 1) + 5 * fbm(24, 3, 20)
near = np.zeros_like(D, bool)
for v in (bad, gul): near |= v['r'] < 1.5 * v['Rc']
K = np.maximum(B, np.where(near, 0, D))
def shapes(v, ringnoise_seed):
    r, Rc = v['r'], v['Rc']; Bv = float(B[int(v['cy']), int(v['cx'])])
    depth = 110 + 40 * min(1, Rc / 1200); hr = max(v['L'] + 24, Bv + 38) - Bv
    hrn = hr * (1 + .28 * fbm(40, 3, ringnoise_seed))
    ring = np.where(r < Rc, hrn * smoothstep(.68 * Rc, Rc, r), hrn * np.exp(-(r - Rc) / (.85 * Rc)))
    bowl = np.where(r < Rc, depth * np.power(np.clip(1 - (r / Rc) ** 2, 0, 1), .8), 0)
    crater = smoothstep(.99 * Rc, .93 * Rc, r)
    v.update(Bv=Bv, depth=depth, hr=hr)
    return ring, bowl, crater
ringG, bowlG, craterG = shapes(gul, 31)
K = K + ringG - bowlG
oldLake = (craterG > .5) & (K < gul['L'])
K = np.where(oldLake, gul['L'], K)
ringB, bowlB, craterB = shapes(bad, 41)
d = np.hypot(XX - bad['x'], ZZ - bad['z'])
cone = 58 * np.power(np.clip(1 - d / 500, 0, 1), 1.15) * (1 + .15 * fbm(12, 2, 55)) - 22 * np.clip(1 - d / 140, 0, 1)
ash = np.where(bad['r'] < bad['Rc'], 1.0, np.exp(-(bad['r'] - bad['Rc']) / (1.8 * bad['Rc'])))
np.savez(f'{SP}/fields.npz', D=D, B=B, ringB=ringB, bowlB=bowlB, craterB=craterB, cone=cone, ash=ash,
         ringG=ringG, oldLake=oldLake.astype(float), capB=bad['cap'].astype(float))
K.astype('<f4').tofile(f'{SP}/kbase0.f32')
import json
meta = dict(NC=NC, NR=NR, cell=cell, lon0=lon0, lon1=lon1, lat0=lat0e, lat1=lat1, mlon=mlon, mlat=mlat, SW=SW, SH=SH,
            bad={k: bad[k] for k in ('x', 'z', 'px', 'pz', 'Rc', 'L', 'Bv', 'depth', 'peak')},
            gul={k: gul[k] for k in ('x', 'z', 'px', 'pz', 'Rc', 'L', 'peak')})
json.dump(meta, open(f'{SP}/meta0.json', 'w'), indent=1)
print(json.dumps(meta['bad']), json.dumps(meta['gul']))
