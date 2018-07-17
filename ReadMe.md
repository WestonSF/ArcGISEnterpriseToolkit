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

#### Portal Services Report
Queries an ArcGIS Online/Portal for ArcGIS site to find all services that are being used in web maps then aggregates these in a CSV file. This tool needs to be run as an ArcGIS Online/Portal administrator.

#### User Information Report
Produces a number of reports (CSV format) for all users in the portal. Reports are:
* Users that have not logged in over a year.
* Groups a user is a member of.
* Number/size of content a user owns.


## Issues

Find a bug or want to request a new feature?  Please let me know by submitting an issue.


## Contributing

Anyone and everyone is welcome to contribute. 


## Licensing

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.