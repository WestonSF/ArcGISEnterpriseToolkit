:: ----- Change User Role -----
:: Parameters:
:: 	GIS site URL
:: 	Admin username in GIS site
:: 	Admin password in GIS site
::	Current user role name - Will find all users in this role e.g. "Administrator", "Publisher", "User", or the name of a custom role.
::	Current user level - Will change the level of the user before changing the role e.g. "1"
::	New user role name - Will change all users in the role above to this role e.g. "Administrator", "Publisher", "User", or the name of a custom role.
::	New user level - Will change the level of the user before changing the role e.g. "2"
"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" "C:\Development\Python for ArcGIS Tools\ArcGIS Enterprise Toolkit\ChangeUserRole.py" ^
 "https://organisation/portal" ^
 "portaladmin" ^
 "*****" ^
 "Viewer" ^
 "1" ^
 "User" ^
 "2"