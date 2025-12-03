from IPython import *

#!/usr/bin/env python
# coding: utf-8

# In[1]:


#get_ipython().run_line_magic('cd', "C:\\Users\\blhco\\paradigm_cvision\\datasets")
#Change this to where the 'datasets' folder is located in your computer"


# In[2]:


#dataset_location = 'C:\\Users\\blhco\\paradigm_cvision\\datasets\\White-Line-Detection(instance-segmentation)-3'
#Sets to location of the dataset, change this to where the 'datasets' folder is located in your computer 


# In[19]:


#print(dataset_location) #Use to confirm the location of the dataset


# In[ ]:


get_ipython().system('pip install roboflow ')
#Installs a version of this yolo model on your computer

from roboflow import Roboflow
rf = Roboflow(api_key="VmIXHUMJcfpIBX5uALxj")
project = rf.workspace("paradigmcomputervision").project("white-line-detection-instance-segmentation-qwdzf")
version = project.version(3)
dataset = version.download("yolov8")


# In[21]:


get_ipython().system('yolo task=segment mode=train model=yolov8s-seg.pt  data="data.yaml" epochs=10 imgsz=640')
#Trains the model, this should take about 20 minutes 


# In[ ]:




