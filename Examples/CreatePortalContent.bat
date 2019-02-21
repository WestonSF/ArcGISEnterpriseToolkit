:: ----- Create Portal Content -----
:: Parameters:
:: 	GIS site URL
:: 	Admin username in GIS site
:: 	Admin password in GIS site
::	Location of CSV file with content to create
::	Item type in CSV to create e.g. "Group" will only create the groups listed and ignore all other types
"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" "C:\Development\Python for ArcGIS Tools\ArcGIS Enterprise Toolkit\CreatePortalContent.py" ^
 "https://2108-sxw.etgnz.eagle.co.nz/portal" ^
 "portaladmin" ^
 "G1Sadm1n" ^
 "C:\Development\Python for ArcGIS Tools\ArcGIS Enterprise Toolkit\PortalContent.csv" ^
 ""