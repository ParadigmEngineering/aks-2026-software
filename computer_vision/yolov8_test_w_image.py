from IPython import *
#IMPORTANT: When running files which use IPython in the terminal, first enter 'ipython' to start the thing,
#then enter '%run yolov8_test_w_image.py' to run this script.


#!/usr/bin/env python
# coding: utf-8

# In[5]:


#cd ..


# In[6]:


get_ipython().run_line_magic('cd', 'datasets//White-Line-Detection_v4//runs//segment//train2//weights')
#Change this to the location of the 'weights' folder on your computer


# In[27]:


get_ipython().system('yolo task=segment mode=predict model=best.pt conf=0.25 source=test_images save=true')


# In[ ]:




