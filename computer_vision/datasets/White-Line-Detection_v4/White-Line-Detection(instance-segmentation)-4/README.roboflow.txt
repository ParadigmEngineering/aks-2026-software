
White Line Detection(instance segmentation) - v4 whiteline_instanceseg_v4
==============================

This dataset was exported via roboflow.com on January 22, 2026 at 10:20 PM GMT

Roboflow is an end-to-end computer vision platform that helps you
* collaborate with your team on computer vision projects
* collect & organize images
* understand and search unstructured image data
* annotate, and create datasets
* export, train, and deploy computer vision models
* use active learning to improve your dataset over time

For state of the art Computer Vision training notebooks you can use with this dataset,
visit https://github.com/roboflow/notebooks

To find over 100k other datasets and pre-trained models, visit https://universe.roboflow.com

The dataset includes 276 images.
White-line are annotated in YOLOv8 format.

The following pre-processing was applied to each image:
* Auto-orientation of pixel data (with EXIF-orientation stripping)
* Resize to 1920x1080 (Stretch)
* Grayscale (CRT phosphor)

The following augmentation was applied to create 3 versions of each source image:
* 50% probability of horizontal flip
* Randomly crop between 0 and 21 percent of the image
* Random rotation of between -9 and +9 degrees
* Random brigthness adjustment of between -25 and +25 percent
* Random exposure adjustment of between -12 and +12 percent
* Random Gaussian blur of between 0 and 2.5 pixels


