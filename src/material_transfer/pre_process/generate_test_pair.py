"""
generate test pair, use selected image and shape.
"""
import sys
sys.path.append('/home/code/TMT/src')
import cv2
import json
import math
import numpy as np
import os
import random
import shutil
import skimage
import skimage.io
import thirdparty.toolbox.toolbox.images
from PIL import Image
from pathlib import Path
from skimage.color import rgb2gray
from skimage.segmentation import slic
from tqdm import tqdm


def bright_pixel_mask(image, percentile=80):
    image = rgb2gray(image)
    perc = np.percentile(np.unique(image), percentile)
    mask = image < perc
    return mask


def get_seg(camera_pose, shape_id, shape_root):
    os.system(f'blender -noaudio -b -P ./material_transfer/pre_process/generate_seg_map.py -- \
            {shape_root + str(shape_id)}/models/uvmapped_v2.obj \
            {str(camera_pose[0])} \
            {str(camera_pose[1])} \
            {str(camera_pose[2])}')


def main():
    test_id = '1'
    # Basic settings.
    totalPair = 1  # total number of test pairs.
    shapesEachEx = 1  # shape numbers of each exemplar.
    realImageRoot = './material_transfer/exemplar/wild_photo/target/' 
    shapeRoot = './material_transfer/exemplar/shapes/'
    # Shape
    fixShapeIDS = [44940]
    # Exemplar
    realImages = os.listdir(realImageRoot)
    selReals = [img for img in realImages if 'jpg' in img]
    
    saveRoot_txt = './material_transfer/exemplar/'
    saveRoot = './material_transfer/exemplar/validation/'   
    if not os.path.exists(saveRoot): os.makedirs(saveRoot)
    
    refTxt = []
    for index, selReal in enumerate(tqdm(selReals)):
        with open(Path(realImageRoot.replace('target', 'campose') + selReal.replace('jpg', 'json')), 'r') as f1:
            camJson = json.load(f1)
            x, y, z = camJson['cam_loc_est']
        camEst = [x, y, z]
        print(camEst)
        # get shapeID.
        selShapeIDs = fixShapeIDS
        for shapeIdx, shapeID in enumerate(selShapeIDs):
            savePre = 'render_val_' + str(index * shapesEachEx + shapeIdx + 1).zfill(8)
            # get segmentation
            get_seg(camEst, shapeID, shapeRoot)
            os.rename('/home/code/TMT/src/material_transfer/exemplar/validation/shape_rend_segments_500x500.map0001.png', saveRoot + savePre + '.png')
            shutil.copyfile(realImageRoot + selReal, saveRoot + savePre + '.jpg')
            
            saveOth = 'render_val_' + str(index * shapesEachEx + shapeIdx + 1 + len(selReals) * shapesEachEx).zfill(8)
            shutil.copyfile(realImageRoot + selReal, saveRoot + saveOth + '.jpg')
            realImage = skimage.io.imread(realImageRoot + selReal)

            foreGround = bright_pixel_mask(realImage, percentile=85).astype(np.uint8)
            superPix = slic(realImage, n_segments=5, mask=foreGround)
            cv2.imwrite(saveRoot + saveOth + '.png', superPix)

            refTxt.append(savePre + '.jpg,' + saveOth + '.jpg,' + saveOth + '.jpg,'+ \
                                            saveOth + '.jpg,' + saveOth + '.jpg,' + saveOth + '.jpg,' + \
                                            saveOth + '.jpg,' + saveOth + '.jpg,' + saveOth + '.jpg,' + \
                                            saveOth + '.jpg,' + saveOth + '.jpg\n')

            with open(saveRoot + savePre + '.json', 'w') as f1:
                json.dump({
                    'exemplar': selReal,
                    'shape': int(shapeID),
                    'camera': camEst
                },f1,indent=2)

    with open(saveRoot_txt + 'ref_test.txt', 'w') as f2:
        f2.writelines(refTxt) 


if __name__ == '__main__':
    main()