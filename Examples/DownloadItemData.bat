:: ----- Download Item Data -----
:: Parameters:
:: 	GIS site URL
:: 	Admin username in GIS site
:: 	Admin password in GIS site
::	Item ID of the item in portal to download. If no item ID is specified all items in the site will be downloaded e.g. "2621136d1c6a4ee2ade145166e015477" or ""
::	Folder where data will be saved. If downloading all items, a new folder will be created e.g. "C:\Temp"
"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" "C:\Development\Python for ArcGIS Tools\ArcGIS Enterprise Toolkit\DownloadItemData.py" ^
 "https://organisation.maps.arcgis.com" ^
 "user" ^
 "*****" ^
 "" ^
 "C:\Temp"