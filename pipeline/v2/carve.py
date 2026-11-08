import sys, numpy as np
from scipy import ndimage
SP=sys.argv[1]
K0=np.fromfile(f'{SP}/kbase0.f32','<f4').reshape(1039,1024).astype(float)
inc=np.fromfile(f'{SP}/inc.f32','<f4').reshape(1039,1024).astype(float)
v = np.maximum(ndimage.grey_dilation(inc, size=5)*0.8, inc)
v = np.maximum(v, ndimage.gaussian_filter(ndimage.grey_dilation(inc, size=11), 6)*0.9)
v = ndimage.gaussian_filter(v, 1.5)
(K0 - v).astype('<f4').tofile(f'{SP}/kbase1.f32'); print('max valley', v.max())
