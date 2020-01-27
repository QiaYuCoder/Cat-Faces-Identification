import math
import cv2.cv2 as cv
import numpy as np
from matplotlib import pyplot as plt
import os
from PIL import Image

SF = 1.05  # play around with it (i.e. 1.05, 1.3 etc) Good ones: 1.04 (haar), 1.05
N = 2  # play around with it (3,4,5,6) Good ones: 2 (haar)
cascade_models_dir = '../models/detection/'
cat_cascades = ['haarcascade_frontalcatface.xml', 'haarcascade_frontalcatface_extended.xml',
                'lbpcascade_frontalcatface.xml']
eye_cascade_model = cascade_models_dir + 'haarcascade_eye.xml'


def detect_cat_face(file, classifier, show=False, scaleFactor=SF, minNeighbors=N,
                    eyes_ScaleFactor=1.1, eyes_minNeighbors=3, eyes_minSize=(0, 0)):
    """
    Cat face detection utility.

    :param file : str
        The name of the image file to detect the face from.
    :param classifier : int
        Integer used to select the type of detector model to be used:
        0 = haarcascade_frontalcatface.xml
        1 = haarcascade_frontalcatface_extended.xml
        2 = lbpcascade_frontalcatface.xml
    :param show: bool
        set to True to see an output image
    :param scaleFactor: float
        Scale factor value the detector should use
    :param minNeighbors : int
        Min neighbors value the detector should use
    :param eyes_ScaleFactor: float
        scaleFactor value the eyes detector should use
    :param eyes_minNeighbors:
        minNeighbors value the eyes detector should use
    :param eyes_minSize:
        minSize value the eyes detector should use
    :return a list of rectangles containing the detected features
    """

    cat_cascade = cv.CascadeClassifier(cascade_models_dir + cat_cascades[classifier])
    eye_cascade = cv.CascadeClassifier(eye_cascade_model)

    if cat_cascade.empty():
        raise RuntimeError('The face classifier was not loaded correctly!')

    if eye_cascade.empty():
        raise RuntimeError('The eye classifier was not loaded correctly!')

    img = cv.imread(file)
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

    face = cat_cascade.detectMultiScale(gray, scaleFactor=SF, minNeighbors=N)

    for (x, y, w, h) in face:  # blue
        img = cv.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
        roi_gray = gray[y:y + h, x:x + w]
        roi_color = img[y:y + h, x:x + w]
        eyes = eye_cascade.detectMultiScale(roi_gray,
                                            scaleFactor=eyes_ScaleFactor,
                                            minNeighbors=eyes_minNeighbors,
                                            minSize=eyes_minSize)
        if len(eyes) == 0:
            print("No eyes detected")
        elif len(eyes) == 1:
            print("Only 1 eye (possibly) detected")
        elif len(eyes) > 2:
            print("More than 2 eyes (?) detected")

        for (ex, ey, ew, eh) in eyes:
            cv.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (255, 255, 0), 2)

    if show:
        cv.namedWindow('win', cv.WINDOW_NORMAL)
        # cv.resizeWindow('win', 1980, 1800)

        cv.imshow('win', img)
        cv.waitKey(0)
        cv.destroyAllWindows()

    return face


def resize_image(image, width=None, height=None, inter=cv.INTER_AREA):
    """
    Resizes an image according to the specified parameters.

    :param image: image
        image to resize
    :param width: int
        output width
    :param height: int
        output height
    :param inter: interpolation
        interpolation to use
    :return: resized image
    """
    # initialize the dimensions of the image to be resized and
    # grab the image size
    dim = None
    (h, w) = image.shape[:2]

    # if both the width and height are None, then return the
    # original image
    if width is None and height is None:
        return image

    # check to see if the width is None
    if width is None:
        # calculate the ratio of the height and construct the
        # dimensions
        r = height / float(h)
        dim = (int(w * r), height)

    # otherwise, the height is None
    else:
        # calculate the ratio of the width and construct the
        # dimensions
        r = width / float(w)
        dim = (width, int(h * r))

    # resize the image
    resized = cv.resize(image, dim, interpolation=inter)

    # return the resized image
    return resized


def Distance(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)


def ScaleRotateTranslate(image, angle, center=None, new_center=None, scale=None, resample=Image.BICUBIC):
    if (scale is None) and (center is None):
        return image.rotate(angle=angle, resample=resample)
    nx, ny = x, y = center
    sx = sy = 1.0
    if new_center:
        (nx, ny) = new_center
    if scale:
        (sx, sy) = (scale, scale)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    a = cosine / sx
    b = sine / sx
    c = x - nx * a - ny * b
    d = -sine / sy
    e = cosine / sy
    f = y - nx * d - ny * e
    return image.transform(image.size, Image.AFFINE, (a, b, c, d, e, f), resample=resample)


def CropFace(image, eye_left=(0, 0), eye_right=(0, 0), offset_pct=(0.2, 0.2), dest_sz=(70, 70)):
    # calculate offsets in original image
    offset_h = math.floor(float(offset_pct[0]) * dest_sz[0])
    offset_v = math.floor(float(offset_pct[1]) * dest_sz[1])
    # get the direction
    eye_direction = (eye_right[0] - eye_left[0], eye_right[1] - eye_left[1])
    # calc rotation angle in radians
    rotation = -math.atan2(float(eye_direction[1]), float(eye_direction[0]))
    # distance between them
    dist = Distance(eye_left, eye_right)
    # calculate the reference eye-width
    reference = dest_sz[0] - 2.0 * offset_h
    # scale factor
    scale = float(dist) / float(reference)
    # rotate original around the left eye
    image = ScaleRotateTranslate(image, center=eye_left, angle=rotation)
    # crop the rotated image
    crop_xy = (eye_left[0] - scale * offset_h, eye_left[1] - scale * offset_v)
    crop_size = (dest_sz[0] * scale, dest_sz[1] * scale)
    image = image.crop(
        (int(crop_xy[0]), int(crop_xy[1]), int(crop_xy[0] + crop_size[0]), int(crop_xy[1] + crop_size[1])))
    # resize it
    image = image.resize(dest_sz, Image.ANTIALIAS)
    return image


if __name__ == '__main__':
    """Main for testing purposes"""
    imdir = ''

    images = [os.path.join(imdir, f) for f in os.listdir(imdir) if
              os.path.isfile(os.path.join(imdir, f))]

    for im in images:
        detect_cat_face(im, 0, show=True)