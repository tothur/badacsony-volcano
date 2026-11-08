# Badacsony data pipeline

Builds `../data/` (heights.png, shape.png, sat.jpg, meta.json) for the viewer.
Needs Python with numpy, scipy, rasterio, pillow, and Node.

```
WORK=/some/work/dir; OUT=../data
mkdir -p $WORK/raw
curl -o $WORK/raw/glo30.tif https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N46_00_E017_00_DEM/Copernicus_DSM_COG_10_N46_00_E017_00_DEM.tif
python prep.py $WORK $OUT            # DEM grid, satellite mosaic, crater shapes, ancient plain
node flow.mjs $WORK/kbase0.f32 $WORK/inc.f32 1024 1039 8.57   # drainage network
python carve.py $WORK                # cut valleys
node erode.mjs $WORK/kbase1.f32 $WORK/kbase.f32 1024 1039 8.57 1200000   # droplet erosion detail
python pack.py $WORK $OUT            # 16-bit values packed into RGB PNGs (high byte R, low byte G)
```
