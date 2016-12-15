''' Use built-in backend AGG to prevent X server error.
    This error happens when work in remote server through ssh '''
import matplotlib;    matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os, glob
import numpy as np
from multiprocessing import Pool
from sar2ice import convert2gray, get_texture_features
from scipy.ndimage import maximum_filter

# find input files
idir = '/Volumes/ExFAT2TB/Sentinel1A/odata_FramStrait_corrected/'
odir = ( os.path.abspath(os.getcwd()+'/../shared/test_data/sentinel1a_l1')
         +'/odata_FramStrait_TFs/' )
ifiles = sorted(glob.glob(idir + 'S1A_EW_GRDM_1SDH*_s0.npz'))

# dynamic range of sigma0
# run 'Extras_getDynamicRange.py' to get optimal values
sigma0_max = {'HH':   0.0, 'HV': -12.0}
sigma0_min = {'HH': -24.5, 'HV': -30.0}

# set up parameters for Haralick texture features computation
stp = 25    # step size
ws  = 25    # 1km pixel spacing (40m * 25 = 1000m)
l   = 64    # gray-level. 32 or 64.
threads = 4
alg = 3
''' alg: TF computation algorithm flag
        0 for conventional single-distance using mahotas
        1 for multi-distance using mahotas (averaged TFs)
        2 for multi-distance using scikit-image (averaged TFs)
        3 for multi-distance using scikit-image (averaged GLCM) '''


for ifile in ifiles:
    
    ifilename = os.path.split(ifile)[1]
    ofile = os.path.join(odir, ifilename.replace('_s0','_har'))
    if os.path.exists(ofile):
        continue
        
    print ifilename
    pol = ifilename[68:70]
    wm = np.load(ifile)['wm']
    sigma0 = np.load(ifile)['sigma0']
    sigma0 = convert2gray(sigma0, sigma0_min[pol], sigma0_max[pol], l)
    # apply land mask with buffer size of (ws*2).
    sigma0[maximum_filter(wm==2,ws*2)] = 0

    # get texture features
    print 'compute texture features'
    tfs = get_texture_features(sigma0, ws, stp, threads, alg)
    
    # save each texture feature in a PNG
    for i, tf in enumerate(tfs):
        vmin, vmax = np.percentile( tf[np.isfinite(tf)], (2.5, 97.5) )
        plt.imsave( ofile.replace('har.npz','har%02d.png' % i),
                    tf, vmin=vmin, vmax=vmax )
    
    # save texture features for further processing
    proc_params = { 'input_dimension':sigma0.shape, 'window_size':ws,
                    'step_size':stp, 'gray_level':l, 'glcm_algorithm':alg }
    np.savez_compressed(ofile, tfs=tfs, proc_params=proc_params)
