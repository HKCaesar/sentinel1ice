''' Use built-in backend AGG to prevent X server error.
    This error happens when work in remote server through ssh '''
import matplotlib;    matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os, glob, pickle
import numpy as np
from PIL import Image
from sklearn import svm
from sar2ice import apply_svm
from config import get_env


idir = get_env()['outputDirectory']
myZonesSuffix = get_env()['myZonesSuffix']
svmFile = get_env()['supportVectorMachineFile']
zoneColors = get_env()['zoneColors']     # set zone colors for each class
tfID = get_env()['textureFeatureID']
threads = get_env()['numberOfThreads']

ifiles = sorted(glob.glob(idir+'*/*'+myZonesSuffix))
allData = []
for ifile in ifiles:
    ifileHH = ifile.replace(myZonesSuffix,'_HH_har_norm.npz')
    ifileHV = ifile.replace(myZonesSuffix,'_HV_har_norm.npz')
    if not os.path.exists(ifileHH) and os.path.exists(ifileHV):
        continue
    hhTF = np.load(ifileHH)['tfsNorm'][tfID,:,:]
    hvTF = np.load(ifileHV)['tfsNorm'][tfID,:,:]
    # read the image with my classification
    myZonesImg = np.array(Image.open(ifile))
    # if myZones was processed in full resolution, resize back to original size
    if prod(myZonesImg.shape)/4 != (hhTF.shape[1]*hhTF.shape[2]):
        stp = get_env()['stepSize']
        myZonesImg = myZonesImg[stp-1::stp,stp-1::stp,:]
    myZones = np.zeros((myZonesImg.shape[0],myZonesImg.shape[1])) + np.nan
    for zc in zoneColors:
        # find non transparent pixels
        # with defined color (whiate, or gray, or black)
        gpi = ( (myZonesImg[:,:,0] == zc ) * (myZonesImg[:,:,1] == zc )
                * (myZonesImg[:,:,2] == zc ) * (myZonesImg[:,:,3] == 255) )
        myZones[gpi] = zc

    # stack HH/HV textures and zones
    imgData = np.vstack([hhTF,hvTF,myZones[None]])
    # reshape into stackable 2D matrix
    imgData = imgData.reshape(2*len(tfID)+1,hhTF.shape[1]*hhTF.shape[2])

    # append data from many images
    allData.append(imgData)

# stack data from all images into [nTF*2+1] x n_pixes array
allData = np.hstack(allData)

gpi = np.isfinite(allData.sum(axis=0))
allDataGood = allData[:, gpi]

# random indeces
randIndeces = np.random.permutation(allDataGood.shape[1])
print len(randIndeces)
# training and testing data
maxSize = 100000
trnIndeces = randIndeces[:maxSize]
tstIndeces = randIndeces[maxSize:maxSize+maxSize]

trnTF = allDataGood[:len(tfID)*2, trnIndeces]
trnZones = allDataGood[len(tfID)*2, trnIndeces]

tstTF = allDataGood[:len(tfID)*2, tstIndeces]
tstZones = allDataGood[len(tfID)*2, tstIndeces]

# train SVM
print 'Train SVM'
clf = svm.SVC(C=1.0, gamma=0.1)
clf.fit(trnTF.T, trnZones)

# save SVM into file
pickle.dump(clf, open(svmFile, "wb" ))

# test SVM on small independent subsample
print 'Test on independent sample'
svmZones = clf.predict(tstTF.T)

diff = tstZones - svmZones
print len(diff[diff != 0]) / float(len(diff))

# apply SVM to all data for testing (in threads)
ifilesHH = sorted(glob.glob(idir + '*/*_HH_har_norm.npz'))
for ifileHH in ifilesHH:
    ifileHV = ifileHH.replace('_HH_','_HV_')
    if not os.path.exists(ifileHV):
        continue
    hhTF = np.load(ifileHH)['tfsNorm'][tfID,:,:]
    hvTF = np.load(ifileHV)['tfsNorm'][tfID,:,:]
    # stack HH/HV textures and zones
    tfs = np.vstack([hhTF, hvTF])

    svmMap = apply_svm(tfs, svmFile, threads)
    ofileSVM = ifileHH.replace('_HH_har_norm.npz', '_svm_zones.png')
    plt.imsave(ofileSVM, svmMap)
