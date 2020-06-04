# datasets of Medical report generation 

Code to download and preprocess the datasets  using in medical reports generation. 

This is based on  [[bio_image_caption](https://github.com/nlpaueb/bio_image_caption)] and [roco-dataset](https://github.com/razorx89/roco-dataset) repository. The modifications is:

- continue to download the dataset if an interruption occurs

## Dependencies ##
To use this code you will need to install python 3.6 and the packages from the requirements.txt file. To install them run 
```shell
pip install -r requirements.txt.
```
## Datasets ##

you can use the following code to download IU X-ray,  Peir_Gross and roco datasets. 


```shell
# IU X-ray:
python get_iu_xray.py
# Peir Gross:
python get_peir_gross.py
# ROCO:
python get_roco.py
```

or directly download the data I have processed from this link: [IU-xray](https://drive.google.com/file/d/1oMIsXww4zvlg82PB8sKlfXvL-WKCiZpJ/view?usp=sharing)   [peir_gross](https://drive.google.com/file/d/1QRVmzftguZ7tnjgBynYq54-IYqBenUFH/view?usp=sharing)