:: ----- Create Portal Content -----
:: Parameters:
:: 	GIS site URL
:: 	Admin username in GIS site
:: 	Admin password in GIS site
::	Location of CSV file with content to create
::	Item type in CSV to create e.g. "Group" will only create the groups listed and ignore all other types
"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" "%~dp0..\CreatePortalContent.py" ^
 "https://organisation.maps.arcgis.com" ^
 "shaun_svcs" ^
 "*****" ^
 "%~dp0..\Configuration\PortalContent.csv" ^
 ""