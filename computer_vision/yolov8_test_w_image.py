from IPython import *

#!/usr/bin/env python
# coding: utf-8

# In[5]:


#cd ..


# In[6]:


#get_ipython().run_line_magic('cd', 'Users\\blhco\\paradigm_cvision\\datasets\\runs\\segment\\train6\\weights')
#Change this to the location of the 'weights' folder on your computer


# In[27]:


get_ipython().system('yolo task=segment mode=predict model=best.pt conf=0.25 source=test_images save=true')


# In[ ]:




