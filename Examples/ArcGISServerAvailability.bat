:: ----- Check ArcGIS Server and services are running -----
:: Parameters:
::	ArcGIS Server site URL to query
::	ArcGIS Server site URL with admin access enabled to query for service status (Use same as above if admin access is enabled) 
::	Portal site URL that the server site is federated with to query for token to access secured services
::	Admin username in GIS site
::	Admin password in GIS site
::	Service in ArcGIS Server site to query e.g. "Gas/GasDesign.MapServer" or leave blank to query all services on the site
::	Log error messages for stopped services - "true" or "false"
C:\Python27\ArcGIS10.6\python "C:\Development\Python for ArcGIS Tools\ArcGIS Enterprise Toolkit\ArcGISServerAvailability.py" ^
 "https://gisportal/arcgis" ^
 "https://gisportal/arcgisadmin" ^
 "https://gisportal/portal" ^
 "portaladmin" ^
 "*****" ^
 "Gas/GasDesign.MapServer" ^
 "false"