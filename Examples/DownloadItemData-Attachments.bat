:: ----- Download Item Data - Attachments -----
:: Parameters:
:: 	GIS site URL
:: 	Admin username in portal site
:: 	Admin password in portal site
::	Location of configuration file with Item IDs to download. If no item ID is specified all items in the site will be downloaded e.g "DownloadItemData-FeatureLayerItems.json" 
::		JSON objects in configuration file:
::                      * dataID - Unique ID for each item listed (Required)
::                      * itemID - ID of the item in the portal site to download (Required)
::                      * layerID - If downloading attachments, the layer ID in the service to download (Optional)
::                      * createFolder - If downloading attachments, create a folder (using the name parameter) for attachments
::                      to be downloaded to e.g. "true" or "false" (Optional)
::			* createFeatureFolder - If downloading attachments, create a folder (using the ID field) for each attachment
::                      that is downloaded to e.g. "true" or "false" (Optional)
::                      * subFolders - If downloading attachments, names of blank sub folders to create for each feature that
::                      is downloaded e.g. "Folder1,Folder2,Folder3" (Optional)
::                      * name - If downloading attachments, name of the layer to download, which will be the name of the folder
::                      that is created e.g. "Features1" (Optional)
::                      * idField - If downloading attachments, the name of the field in the layer to use as the ID when
::                      creating a folder for each feature where attachments will be downloaded e.g. "GlobalID" (Optional)
::                      * parentDataID - If downloading attachments, the ID of the item to join to if needing to needing to
::                      create a folder structure where the layer attachments will be downloaded under the folder for the parent
::                      data ID layer e.g. "2" (Optional)
::                      * joinField - If downloading attachments, the name of the field in the layer to use as the ID when
::                      needing to create a folder structure where the layer attachments will be downloaded under the folder
::                      for the parent data ID layer e.g. "ParentGlobalID" (Optional) 
::	Create folder and append date. If true a new folder will be created with date appended e.g. "true" or "false"
::	Folder where data will be saved e.g. "C:\Temp"
::	Will use parallel processing for downloading items e.g. "true" or "false"
"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" "%~dp0..\DownloadItemData.py" ^
 "https://organisation.maps.arcgis.com" ^
 "user" ^
 "*****" ^
 "%~dp0..\Configuration\DownloadItemData-Attachments.json" ^
 "false" ^
 "C:\Temp" ^
 "false"