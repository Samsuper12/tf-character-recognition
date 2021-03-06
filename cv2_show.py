#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
from numba import jit

import log

"""Utility functions for showing images from model."""

DESIRED_HEIGHT = 500  # convenient size of the image to be shown
DEFAULT_BACKGROUND_COLOR = 0.3 * 255

_logger = log.getLogger('cv2_show')


def visualize_grayscale_negative_values(image):
    """Changes grayscale image to RGB that shows negative values using different color"""
    assert image.dtype in [np.float32, np.float64], 'Image is not floating point'
    # prepare image
    if image.ndim == 2:
        image = image[:, :, None]
    assert image.shape[2] == 1, 'Image is already 3-channel'
    blue = np.where(image < 0, -image, 0)  # negative values as positive blue
    green = np.zeros_like(blue)
    red = np.where(image < 0, 0, image)  # negative values as zero, positive are red
    image = np.stack([blue[:,:,0], green[:,:,0], red[:,:,0]], axis=-1)
    return image

def show_image(image, wait=True, resize_to_fit=False, normalize=False, visualize_negative=True):
    """Shows given image using OpenCV.

    'image' - image with float values from 0 to 255 (as Model operates on such)
    'wait' - if True waits forever, if False waits 1ms, else waits 'wait' ms
    return - True if ESCAPE or 'q' key was pressed else False
    """
    image = np.asarray(image)
    assert image.dtype in [np.float32, np.float64], 'Image is not floating point'
    if normalize:
        eps = 1e-15
        image = image / (np.max(image) + eps) * 255
    if resize_to_fit:
        height_scaling = DESIRED_HEIGHT / image.shape[0]
        image = cv2.resize(image, None, fx=height_scaling, fy=height_scaling, interpolation=cv2.INTER_NEAREST)
    if visualize_negative and len(image[image < 0]) > 0:
        _logger.debug('Visualizing negative values as BLUE (positive as RED)')
        image = visualize_grayscale_negative_values(image)
    cv2.imshow('image', image / 255)  # openCV wants floats in [0, 1]
    wait_ms = (0 if wait else 1) if isinstance(wait, bool) else wait
    return not cv2.waitKey(wait_ms) in [27, ord('q')] # 'ESCAPE' or 'q'

# convenience function - finds best layaout of elements ina agrid
def best_grid(N):
    rows = np.floor(np.sqrt(N)) # floor => take less rows than columns
    cols = np.ceil(N / rows)    # take so many cols to fit all elements
    return int(rows), int(cols)

def show_images_grid(images, wait=True, padding=1, resize_to_fit=True, normalize=False, visualize_negative=True):
    """
    'images' - 3D array of shape [n_images, width, height]; float values [0, 255]
    'wait' - if True waits forever, if False waits 1ms, else waits 'wait' ms
    return - True if ESCAPE or 'q' key was pressed else False
    """
    images = np.asarray(images)
    assert images.ndim in [3, 4], 'Images - wrong ndim (shape = %s)' % images.shape
    images = images.squeeze(axis=-1)  # remove channels axis
    n_images = images.shape[0]
    # create one big image from filter outputs
    n_rows, n_cols = best_grid(n_images)
    img_height, img_width = images.shape[1:]
    # find the final size
    total_row_padding = (n_rows + 1) * padding
    total_col_padding = (n_cols + 1) * padding
    total_images_height = n_rows * img_height
    total_images_width = n_cols * img_width
    height_scaling = (DESIRED_HEIGHT - total_row_padding) / total_images_height
    width_scaling = height_scaling  # keep aspect ratio
    # define resizing of the images
    if resize_to_fit:
        resize = lambda img: \
            cv2.resize(img, None, fx=width_scaling, fy=height_scaling, interpolation=cv2.INTER_NEAREST)
        new_height = round(height_scaling * img_height)
        new_width = round(width_scaling * img_width)
    else:
        resize = lambda img: img
        new_height, new_width = img_height, img_width
    # create the final grid-image
    grid_image = np.ones([n_rows * new_height + total_row_padding,
        n_cols * new_width + total_col_padding]) * DEFAULT_BACKGROUND_COLOR
    # assemble final image
    for row in range(n_rows):
        for col in range(n_cols):
            n = row * n_cols + col
            if n >= n_images:
                continue
            image = resize(images[n, :, :])
            # find the right index ranges in the 'grid_image' matrix
            base_height = (row+1) * padding + row * new_height
            base_width = (col+1) * padding + col * new_width
            slice_h = slice(base_height, base_height + new_height)
            slice_w = slice(base_width, base_width + new_width)
            # normalize image if desired
            if normalize:
                eps = 1e-15
                image = image / (np.max(np.abs(image)) + eps) * 255
            # insert image at its position
            grid_image[slice_h, slice_w] = image
    return show_image(grid_image, wait=wait, visualize_negative=visualize_negative)


if __name__ == '__main__':
    import os
    this_dir = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
    dirnames = [
        'database/chars74k/hand/test/H',
        'database/chars74k/hand/train/H',
        'database/chars74k/img_good/test/H',
        'database/chars74k/img_bad/test/H',
    ]
    for dirname in dirnames:
        dirname = os.path.join(this_dir, dirname)
        images = []
        for filename in os.listdir(dirname):
            image = cv2.imread(os.path.join(dirname, filename))
            image = image.astype(np.float32)[:, :, 0] # as grayscale
            image = cv2.resize(image, (100, 100))
            images.append(image)
        images = np.stack(images)
        show_images_grid(images, padding=2, resize_to_fit=True)
