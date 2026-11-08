import sys, math, json, os, numpy as np
from scipy import ndimage
from PIL import Image
W, OUT, SW = sys.argv[1], sys.argv[2], int(sys.argv[3])
g = json.load(open(f'{W}/grid4096.json'))
z = 14; n = 2 ** z
mx = lambda lo: (lo + 180) / 360 * n * 256
def my(la): r = math.radians(la); return (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * n * 256
x0, x1 = int(mx(g['lon_min']) // 256), int(mx(g['lon_max']) // 256); y0, y1 = int(my(g['lat_max']) // 256), int(my(g['lat_min']) // 256)
if sys.argv[4:] == ['list']:
    for tx in range(x0, x1 + 1):
        for ty in range(y0, y1 + 1):
            if not os.path.exists(f'{W}/raw/sat/{tx}_{ty}.jpg'):
                print(f'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2020_3857/default/g/{z}/{ty}/{tx}.jpg {W}/raw/sat/{tx}_{ty}.jpg')
    sys.exit()
mos = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256, 3), np.uint8)
for tx in range(x0, x1 + 1):
    for ty in range(y0, y1 + 1):
        mos[(ty - y0) * 256:(ty - y0 + 1) * 256, (tx - x0) * 256:(tx - x0 + 1) * 256] = np.asarray(Image.open(f'{W}/raw/sat/{tx}_{ty}.jpg').convert('RGB'))
idx = np.arange(SW) / (SW - 1)
lon = g['lon_min'] + idx * (g['lon_max'] - g['lon_min']); lat = g['lat_max'] - idx * (g['lat_max'] - g['lat_min'])
PX, PY = np.meshgrid(np.array([mx(v) for v in lon]) - x0 * 256 - .5, np.array([my(v) for v in lat]) - y0 * 256 - .5)
img = np.stack([ndimage.map_coordinates(mos[:, :, c].astype(np.float32), [PY, PX], order=1) for c in range(3)], -1)
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(OUT, quality=84, optimize=True)
print('ok', os.path.getsize(OUT))
