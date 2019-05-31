:: ----- Check ArcGIS Server and services are running -----
:: Parameters:
::	ArcGIS Server site URL to query
::	ArcGIS Server site URL with admin access enabled to query for service status (Use same as above if admin access is enabled), if not provided, service status will not be queried 
::	Portal site URL that the server site is federated with to query for token to access secured services
::	Admin username in GIS site
::	Admin password in GIS site
::	Service in ArcGIS Server site to query e.g. "Gas/GasDesign.MapServer" or leave blank to query all services on the site
::	If a map or feature service, query the data - "true" or "false"
::	If a map service, query the map - "true" or "false"
::	If a GP service, submit a job - "true" or "false"
::	GP service parameters - e.g. "{ \"task\":\"Export Web Map\", \"parameter1\":\"a\", \"parameter2\":\"b\" }" 
::	Log error messages for stopped services - "true" or "false"
C:\Python27\ArcGIS10.7\python "C:\Development\Python for ArcGIS Tools\ArcGIS Enterprise Toolkit\ArcGISServerAvailability.py" ^
 "https://gis.mstn.govt.nz/arcgis" ^
 "" ^
 "" ^
 "" ^
 "" ^
 "Tools/ExportWebMapPublic.GPServer" ^
 "false" ^
 "false" ^
 "true" ^
 "{ \"task\":\"Export Web Map\", \"Web_Map_as_JSON\":\"test\" }" ^
 "false"