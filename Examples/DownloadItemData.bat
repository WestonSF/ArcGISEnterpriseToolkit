:: ----- Download Item Data -----
:: Parameters:
:: 	GIS site URL
:: 	Admin username in GIS site
:: 	Admin password in GIS site
::	Item ID of the item in portal to download e.g. "2621136d1c6a4ee2ade145166e015477"
::	Location of the file where data will be saved e.g. "C:\Temp\Data.json"
"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" "C:\Development\Python for ArcGIS Tools\ArcGIS Enterprise Toolkit\DownloadItemData.py" ^
 "https://organisation.maps.arcgis.com" ^
 "sfweston" ^
 "*****" ^
 "b3d3ba2119c145c4af38eacf49080650" ^
 "C:\Temp\Data.json"