:: ----- Start Service -----
:: Parameters:
:: 	GIS site URL
:: 	Admin username in GIS site
:: 	Admin password in GIS site
::	Folder in ArcGIS Server to perform action on e.g. "Property"
::	Name of service in ArcGIS Server to perform action on e.g. "Parcels.MapServer"
::	Action e.g. "Start" or "Stop"
"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" "C:\Development\Python for ArcGIS Tools\ArcGIS Enterprise Toolkit\StartStopService.py" ^
 "https://sxw-laptop.etgnz.eagle.co.nz/arcgis" ^
 "portaladmin" ^
 "*****" ^
 "" ^
 "Parcels.MapServer" ^
 "Start"