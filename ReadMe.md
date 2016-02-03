# ArcGIS Online & Portal Toolkit

The ArcGIS Online & Portal toolkit contains a number of tools and scripts to administer Portal for ArcGIS and ArcGIS Online.

#### Create ArcGIS Online/Portal Group
Creates a ArcGIS Online or Portal for ArcGIS group. Sets up description, logo and members of the group.

#### Add Users to Portal for ArcGIS Site 
Imports a list of users provided in a CSV file to Portal for ArcGIS, assigning to roles and setting default password. Can be
built-in or enteprise users.  

#### Download Feature Layer
Downloads a feature service (As file geodatabase, Shapefile or CSV) from a portal site and optionally updates an existing dataset. Two update options:
        
* Existing Mode - Will delete and append records, so field names need to be the same.
             
* New Mode - Copies data over. Requires no locks on geodatabase datasets being overwritten.  

#### Register Service
Registers a service with an ArcGIS Online site.  


## Features

* Add a number of users to a site at once.
* Setup a number of groups.


## Requirements

* ArcGIS Online
	* Create ArcGIS Online/Portal Group

* Portal for ArcGIS 10.2+ 
	* Add Users to Portal for ArcGIS Site 
	* Create ArcGIS Online/Portal Group


## Installation Instructions

* Setup a script to run as a scheduled task
	* Fork and then clone the repository or download the .zip file. 
	* Edit the [batch file](/Examples) to be automated and change the parameters to suit your environment.
	* Open Windows Task Scheduler and setup a new basic task.
	* Set the task to execute the batch file at a specified time.


## Resources

* [LinkedIn](http://www.linkedin.com/in/sfweston)
* [GitHub](https://github.com/WestonSF)
* [Twitter](https://twitter.com/Westonelli)
* [Blog](http://westonelli.wordpress.com)
* [ArcGIS Blog](http://blogs.esri.com/esri/arcgis)
* [Python for ArcGIS](http://resources.arcgis.com/en/communities/python)


## Issues

Find a bug or want to request a new feature?  Please let me know by submitting an issue.


## Contributing

Anyone and everyone is welcome to contribute. 


## Licensing
Copyright 2014 - Shaun Weston

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.