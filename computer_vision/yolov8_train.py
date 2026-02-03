from IPython import *
#IMPORTANT: When running files which use IPython in the terminal, first enter 'ipython' to start the thing,
#then enter '%run yolov8_train.py' to run this script.

#!/usr/bin/env python
# coding: utf-8

# In[1]:


get_ipython().run_line_magic('cd', "datasets//White-Line-Detection_v4")
#Change this to where the dataset folder is located in your computer


# In[2]:


#dataset_location = 'C:\\Users\\blhco\\paradigm_cvision\\datasets\\White-Line-Detection(instance-segmentation)-3'
#Sets to location of the dataset, change this to where the 'datasets' folder is located in your computer 


# In[19]:


#print(dataset_location) #Use to confirm the location of the dataset


# In[ ]:


get_ipython().system('pip install roboflow ')
#Installs a version of this yolo model on your computer

########################################################################################################################
#
# The code below is taken from roboflow, you may have to change the parameters to correspond to the specifc dataset
# you want to train a model on. These parameters can be found on roboflow's website by clicking 'Download Dataset',
# turning 'Show download code' on and clicking 'continue'.
#
########################################################################################################################
from roboflow import Roboflow
rf = Roboflow(api_key="VmIXHUMJcfpIBX5uALxj")
project = rf.workspace("paradigmcomputervision").project("white-line-detection-instance-segmentation-qwdzf")
version = project.version(4)
dataset = version.download("yolov8")


# In[21]:


get_ipython().system('yolo task=segment mode=train model=yolov8s-seg.pt  data="data.yaml" epochs=10 imgsz=640')
#Trains the model, this should take about 20 minutes 


# In[ ]:

########################################################################################################################
#
# For this code to run you'll need to install IPython and Ultralytics and you may need to change the location of
# "datasets_dir" in Ultralytics' 'settings.json' file to the directory where your 'data.yaml' file is located.
# 'settings.json' should be located in C: -> Users -> Username -> AppData -> Roaming -> Ultralytics
#
########################################################################################################################

