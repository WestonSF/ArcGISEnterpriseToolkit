:: ----- Create Vector Tile Package -----
:: Parameters:
:: 	ArcGIS Pro map file to be tiled
:: 	Tiling scheme to be used for the vector tile package
:: 	File system location of where the vector tile package will be saved
:: 	GIS site URL
:: 	Admin username in GIS site
:: 	Admin password in GIS site
:: 	ID in portal of the vector tile package
:: 	Title to be used in portal
:: 	Description to be used in portal
:: 	Tags to be used in portal
:: 	Share with everyone in portal - "True" or "False"
:: 	Share with organisation in portal - "True" or "False"
:: 	List of group IDs to share with in portal
:: 	Thumbnail to be used in portal
:: 	Publish as service - "True" or "False"
"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" "\\GISDATA\Data\Tools & Scripts\ArcGIS Admin Toolkit\CreateVectorTilePackage.py" ^
 "\\GISDATA\Data\Services\Streets.mapx" ^
 "\\GISDATA\Data\Tools & Scripts\ArcGIS Admin Toolkit\Data\NZTMTileScheme.xml" ^
 "\\GISDATA\Data\Services\Streets.vtpk" ^
 "https://organisation/arcgis" ^
 "User" ^
 "*****" ^
 "377fe5a6ef814baeaf2e6e921daefa75" ^
 "Streets" ^
 "Streets basemap for the Wairarapa region of New Zealand." ^
 "Streets, Service, Basemap, Wairarapa" ^
 "true" ^
 "true" ^
 "60794d6eae524b99ad5ea4ee01f5d9aa" ^
 "\\GISDATA\Data\Tools & Scripts\ArcGIS Admin Toolkit\Data\StreetsThumbnail.jpg" ^
 "true"