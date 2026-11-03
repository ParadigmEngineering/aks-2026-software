
Grass and Lane Detection - v1 2026-10-27 7:46pm
==============================

This dataset was exported via roboflow.com on October 27, 2026 at 10:18 PM GMT

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

The dataset includes 806 images.
Grass-and-Lane-Detection are annotated in YOLOv8 format.

The following pre-processing was applied to each image:
* Auto-orientation of pixel data (with EXIF-orientation stripping)
* Resize to 432x432 (Fit within)

The following augmentation was applied to create 3 versions of each source image:
* Randomly crop between 0 and 29 percent of the image
* Random rotation of between -10 and +10 degrees
* Random brigthness adjustment of between -23 and +23 percent
* Random Gaussian blur of between 0 and 1.3 pixels


