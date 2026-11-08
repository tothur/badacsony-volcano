import sys, json, gzip, numpy as np
from scipy import ndimage
SP, OUT = sys.argv[1], sys.argv[2]
meta = json.load(open(f'{SP}/meta0.json')); NC, NR = meta['NC'], meta['NR']
f = np.load(f'{SP}/fields.npz')
K = np.fromfile(f'{SP}/kbase.f32', '<f4').reshape(NR, NC).astype(float)
K0 = np.fromfile(f'{SP}/kbase0.f32', '<f4').reshape(NR, NC).astype(float)
valley = np.clip(K0 - K, 0, None)
q = lambda a: np.clip(np.round((a - 50) * 100), 0, 65535).astype('<u2')
hts = np.stack([q(f['D']), q(K)], -1)
from PIL import Image
def png16(blocks, path):
    u = np.concatenate(blocks, 0).astype(np.uint32)
    rgb = np.stack([(u >> 8).astype(np.uint8), (u & 255).astype(np.uint8), np.zeros_like(u, np.uint8)], -1)
    Image.fromarray(rgb, 'RGB').save(path, optimize=True)
png16([q(f['D']), q(K)], f'{OUT}/heights.png')
S = 512; SR = int(round(S * (NR - 1) / (NC - 1))) + 1
rr, cc = np.meshgrid(np.linspace(0, NR - 1, SR), np.linspace(0, NC - 1, S), indexing='ij')
smp = lambda a: ndimage.map_coordinates(a.astype(float), [rr, cc], order=1)
chans = [f['ringB'], f['bowlB'], f['cone'], f['ringG'], f['craterB'], f['ash'], f['oldLake'], valley]
ranges, blocks = [], []
for c in chans:
    a = smp(c); lo, hi = float(a.min()), float(a.max()); hi = hi if hi > lo else lo + 1
    ranges.append([lo, hi]); blocks.append(np.round((a - lo) / (hi - lo) * 65535))
png16(blocks, f'{OUT}/shape.png')
sh = np.zeros((SR, S, 8))
meta.update(SC=S, SR=SR, water=103.8, shapeRanges=ranges)
def xz(la, lo): return [ (lo - meta['lon0']) * meta['mlon'] - (NC - 1) / 2 * meta['cell'], (meta['lat1'] - la) * meta['mlat'] - (NR - 1) / 2 * meta['cell'] ]
meta['labels'] = [
  dict(text='Badacsony', x=meta['bad']['px'], z=meta['bad']['pz'], kind='peak'),
  dict(text='Gulács', x=meta['gul']['px'], z=meta['gul']['pz'], kind='peak'),
  dict(text='Lake Balaton', **dict(zip('xz', xz(46.778, 17.505))), kind='water'),
  dict(text='Badacsonytomaj', **dict(zip('xz', xz(46.8065, 17.5115))), kind='town'),
  dict(text='Badacsonytördemic', **dict(zip('xz', xz(46.8085, 17.4685))), kind='town'),
]
json.dump(meta, open(f'{OUT}/meta.json', 'w'))
print(SR, sh.shape)
