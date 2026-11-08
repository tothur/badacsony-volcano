# Badacsony data pipeline (v3, Börzsöny engine)

Builds `../data/` for the viewer. Needs Python (numpy, scipy, rasterio, pillow) and Node.
Area: 13.3 km square centred on 46.825 N 17.4925 E (Badacsony, Gulács, Szent György-hegy, Csobánc, the shore).

```
W=/some/work/dir; OUT=../data
curl -o $W/raw/glo_E017.tif https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N46_00_E017_00_DEM/Copernicus_DSM_COG_10_N46_00_E017_00_DEM.tif
for n in 1024 2048 4096; do python dem.py $W $n; done
python sat.py $W x 0 list | xargs -P 8 -n 2 sh -c 'curl -s -o "$1" "$0"'; python sat.py $W $OUT/sat.jpg 4096
python recon_b.py $W base                                   # Pannonian plain + older volcanoes
node flowacc.mjs $W/K0.f32 $W/A_K0.f32 4096 4096 3.25
python recon_b.py $W carve                                  # stream valleys
node erode.mjs $W/K1.f32 $W/K2.f32 4096 4096 3.25 4000000 50 2
python recon_b.py $W final                                  # Badacsony maar / tuff ring / cone shapes, lake level
python -c "import numpy as np; np.load('$W/D1024.npy').astype('<f4').tofile('$W/D1024.f32')"
node flowacc.mjs $W/D1024.f32 $W/A_D1024.f32 1024 1024 13.0
python recon_b.py $W pack $OUT
python hi1m_b.py $W prep
node flowacc.mjs $W/m1_flow.f32 $W/m1_A.f32 6144 6144 1.0
python hi1m_b.py $W geo
node erode.mjs $W/m1_geo.f32 $W/m1_ero.f32 6144 6144 1.0 12000000 50 2
python hi1m_b.py $W pack
```

The viewer (`../index.html`) was generated from `borzsony/index.html` with `port.py`; since then it has been edited directly.
`v2/` holds the scripts of the previous (single-mesh) version.
