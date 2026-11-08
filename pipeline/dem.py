import sys, math, json, numpy as np, rasterio
from scipy import ndimage
W = sys.argv[1]; N = int(sys.argv[2])
latc, lonc, size = 46.825, 17.4925, 13300.0            # Badacsony, Gulács, Tóti, Szent György, Csobánc and the shore
mlon = 111320 * math.cos(math.radians(latc)); mlat = 111132; cell = size / (N - 1)
idx = np.arange(N) - (N - 1) / 2
lon = lonc + idx * cell / mlon; lat = latc - idx * cell / mlat
src = rasterio.open(f'{W}/raw/glo_E017.tif')
win = rasterio.windows.from_bounds(lon.min() - .01, lat.min() - .01, lon.max() + .01, lat.max() + .01, src.transform)
a = src.read(1, window=win).astype(np.float64); tr = src.window_transform(win)
LON, LAT = np.meshgrid(lon, lat)
D = ndimage.map_coordinates(a, [(LAT - tr.f) / tr.e - .5, (LON - tr.c) / tr.a - .5], order=3, mode='nearest')
np.save(f'{W}/D{N}.npy', D.astype(np.float32))
json.dump(dict(N=N, cell=cell, lonc=lonc, latc=latc, mlon=mlon, mlat=mlat, lon_min=float(lon.min()), lon_max=float(lon.max()), lat_min=float(lat.min()), lat_max=float(lat.max())), open(f'{W}/grid{N}.json', 'w'))
print('N', N, 'cell', round(cell, 2), 'D', D.min(), D.max())
