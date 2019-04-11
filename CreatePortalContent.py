#-------------------------------------------------------------
# Name:                 Create Portal Content
# Purpose:              Creates a list of portal content from a CSV file. Can set to only create a single
#                       item type from the CSV or everything in the CSV.
#                       - Creates groups,web maps, web mapping apps and dashboards listed in the CSV.
#                       - Shares item with organisation and/or groups if specified.
#                       - Adds users to group if specified.
#                       - Adds layers to web map if specified.
#                       - If web map/web application/dashboard already exists, will update the item details, but will not update the layers and basemap
#                       - If group already exists, will update the item details and add users to the group
# Author:               Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:         24/01/2019
# Last Updated:         10/04/2019
# ArcGIS Version:       ArcGIS API for Python 1.5.2+
# Python Version:       3.6.5+ (Anaconda Distribution)
#--------------------------------

# Import main modules
import os
import sys
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email.mime.application
import csv
# Import ArcGIS modules
useArcPy = "false"
useArcGISAPIPython = "true"
if (useArcPy == "true"):
    # Import arcpy module
    import arcpy
    # Enable data to be overwritten
    arcpy.env.overwriteOutput = True
if (useArcGISAPIPython == "true"):
    # Import arcgis module
    import arcgis
import json

# Set global variables
# Logging
enableLogging = "true" # Use within code to print and log messages - printMessage("xxx","info"), printMessage("xxx","warning"), printMessage("xxx","error")
logFile = os.path.join(os.path.dirname(__file__), "CreatePortalContent.log") # e.g. os.path.join(os.path.dirname(__file__), "Example.log")
# Email Use within code to send email - sendEmail(subject,message,attachment)
sendErrorEmail = "false"
emailServerName = "" # e.g. smtp.gmail.com
emailServerPort = None # e.g. 25
emailTo = "" # Address of email sent to
emailUser = "" # Address of email sent from
emailPassword = ""
# Proxy
enableProxy = "false"
requestProtocol = "http" # http or https
proxyURL = ""
# Output
output = None


# Start of main function
def mainFunction(portalURL,portalUser,portalPassword,csvFileLocation,setItemType): # Add parameters sent to the script here e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)
    try:
        # --------------------------------------- Start of code --------------------------------------- #
        # Connect to GIS portal
        printMessage("Connecting to GIS Portal - " + portalURL + "...","info")
        gisPortal = arcgis.GIS(url=portalURL, username=portalUser, password=portalPassword, verify_cert=False)

        # If item type 
        if (setItemType):
            printMessage("Only creating content of type " + setItemType + "...","info")
                    
        # Read the csv file
        with open(csvFileLocation) as csvFile:
            reader = csv.DictReader(csvFile)
            # For each row in the CSV
            for row in reader:
                processRow = True

                # Get the item type from the CSV
                itemType = row["Type"]
                
                # If item type 
                if (setItemType):
                    # If the row does not equal the item type set, do not process
                    if (setItemType.lower().replace(" ", "") != itemType.lower().replace(" ", "")):
                        processRow = False

                # If processing this row
                if (processRow == True):
                    # If a title is provided
                    if (row["Title"].replace(" ", "")):              
                        if (itemType.lower().replace(" ", "") == "group"):
                            # Create group
                            createGroup(gisPortal,row["Title"],row["Summary"],row["Description"],row["Tags"],row["Thumbnail"],row["Organisation Sharing"],row["Members"])                        
                        elif (itemType.lower().replace(" ", "") == "webmap"):
                            # Create web map
                            createWebMap(gisPortal,row["Title"],row["Summary"],row["Description"],row["Tags"],row["Thumbnail"],row["Web Map Basemap"],row["Web Map Layers"],row["Organisation Sharing"],row["Group Sharing"])
                        elif (itemType.lower().replace(" ", "") == "webmappingapplication"):
                            # Create web mapping application
                            createWebApplication(portalURL,gisPortal,row["Title"],row["Summary"],row["Description"],row["Tags"],row["Thumbnail"],row["Organisation Sharing"],row["Group Sharing"],row["Data"])
                        elif (itemType.lower().replace(" ", "") == "dashboard"):
                            # Create dashbaord
                            createDashboard(gisPortal,row["Title"],row["Summary"],row["Description"],row["Tags"],row["Thumbnail"],row["Organisation Sharing"],row["Group Sharing"],row["Data"])
                        else:
                            printMessage(row["Title"] + " item in CSV does not have a valid type set and will not be created...","warning")
                    else:
                        printMessage("Item in CSV does not have a title set and will not be created...","warning")
        # --------------------------------------- End of code --------------------------------------- #
        # If called from ArcGIS GP tool
        if __name__ == '__main__':
            # Return the output if there is any
            if output:
                # If using ArcPy
                if (useArcPy == "true"):
                    arcpy.SetParameter(1, output)
                # ArcGIS desktop not installed
                else:
                    return output
        # Otherwise return the result
        else:
            # Return the output if there is any
            if output:
                return output
        # Logging
        if (enableLogging == "true"):
            # Log end of process
            logger.info("Process ended.")
            # Remove file handler and close log file
            logMessage.flush()
            logMessage.close()
            logger.handlers = []
    # If error
    except Exception as e:
        # Build and show the error message
        # errorMessage = arcpy.GetMessages(2)

        errorMessage = ""
        # Build and show the error message
        # If many arguments
        if (e.args):
            for i in range(len(e.args)):
                if (i == 0):
                    errorMessage = str(e.args[i]).encode('utf-8').decode('utf-8')
                else:
                    errorMessage = errorMessage + " " + str(e.args[i]).encode('utf-8').decode('utf-8')
        # Else just one argument
        else:
            errorMessage = e
        printMessage(errorMessage,"error")
        # Logging
        if (enableLogging == "true"):
            # Log error
            logger.error(errorMessage)
            # Log end of process
            logger.info("Process ended.")
            # Remove file handler and close log file
            logMessage.flush()
            logMessage.close()
            logger.handlers = []
        if (sendErrorEmail == "true"):
            # Send email
            sendEmail("Python Script Error",errorMessage,None)
# End of main function


# Start of create group function
def createGroup(gisPortal,title,summary,description,tags,thumbnail,organisationSharing,members):
    printMessage("Creating group - " + title + "...","info")

    # FUNCTION - Search portal to see if group is already there
    groupExists = searchPortalForItem(gisPortal,title,"Group")

    # If group has not been created
    if (groupExists == False):       
        # Create the group
        group = gisPortal.groups.create(title=title,
                                        description=description,
                                        snippet=summary,
                                        tags=tags,
                                        access=organisationSharing.lower(), 
                                        thumbnail=thumbnail,
                                        is_invitation_only=True,
                                        sort_field = 'title',
                                        sort_order ='asc',
                                        is_view_only=False,
                                        users_update_items=False)
        printMessage(title + " group created - " + group.id + "...","info")        
    # Group already exists
    else:
        # Get the item ID
        itemID = getIDforPortalItem(gisPortal,title,"group")
        # Get the group
        group = gisPortal.groups.get(itemID)
        
        # Update the group
        group.update(title=title,
                     description=description,
                     snippet=summary,
                     tags=tags,
                     access=organisationSharing.lower(), 
                     thumbnail=thumbnail,
                     is_invitation_only=True,
                     sort_field = 'title',
                     sort_order ='asc',
                     is_view_only=False,
                     users_update_items=False)
        printMessage(title + " group updated - " + itemID + "...","info")

    # If users are provided
    if members:
        printMessage("Adding the following users to the group - " + members + "...","info")
        members = members.split(",")
        # Add users to the group
        group.add_users(members)        
# End of create group function


# Start of create web mapping application function
def createWebApplication(portalURL,gisPortal,title,summary,description,tags,thumbnail,organisationSharing,groupSharing,dataFile):
    printMessage("Creating web mapping application - " + title + "...","info")
            
    # FUNCTION - Search portal to see if web application is already there
    webApplicationExists = searchPortalForItem(gisPortal,title,"Web Mapping Application")

    # Create the web map properties
    itemProperties = {'title':title,
                      'type':"Web Mapping Application",
                      'typeKeywords':"JavaScript,Map,Mapping Site,Online Map,Ready To Use,WAB2D,Web AppBuilder,Web Map",
                      'description':description,
                      'snippet':summary,
                      'tags':tags,
                      'thumbnail':thumbnail,
                      'access':organisationSharing.lower()}
        
    # If the web application has not been created
    if (webApplicationExists == False):
        # Add the web application
        item = gisPortal.content.add(item_properties=itemProperties)

        # Get the JSON data from the file if provided
        jsonData = "{}"
        if (dataFile):
            # If the file exists
            if (os.path.exists(dataFile)):
                with open(dataFile) as jsonFile:
                    # Update the item ID
                    data = json.load(jsonFile)
                    data["appItemId"] = item.id
                    jsonData = json.dumps(data)
            else:
                printMessage(title + " web mapping application data does not exist - " + dataFile + "...","warning")
        # Update the URL and data properties 
        itemProperties = {'url':portalURL + "/apps/webappviewer/index.html?id=" + item.id,
                          'text':jsonData}
        item.update(itemProperties)
        printMessage(title + " web mapping application created - " + item.id + "...","info")
        
        # If sharing to group(s)
        if (groupSharing):
            printMessage("Sharing with the following groups - " + groupSharing + "...","info")
            groupSharing = groupSharing.split(",")
            item.share(groups=groupSharing)
    # Web application already exists
    else:
        # Get the item ID
        itemID = getIDforPortalItem(gisPortal,title,"web mapping application")
        # Get the web application
        item = gisPortal.content.get(itemID)

        # Update the web application
        item.update(itemProperties, thumbnail=thumbnail)
        printMessage(title + " web mapping application updated - " + itemID + "...","info")
# End of create web mapping application function


# Start of create dashboard function
def createDashboard(gisPortal,title,summary,description,tags,thumbnail,organisationSharing,groupSharing,dataFile):
    printMessage("Creating dashboard - " + title + "...","info")
            
    # FUNCTION - Search portal to see if web application is already there
    dashboardExists = searchPortalForItem(gisPortal,title,"Dashboard")

    # Create the web map properties
    itemProperties = {'title':title,
                      'type':"Dashboard",
                      'typeKeywords': "Dashboard,Operations Dashboard",
                      'description':description,
                      'snippet':summary,
                      'tags':tags,
                      'thumbnail':thumbnail,
                      'access':organisationSharing.lower()}
        
    # If the dashboard has not been created
    if (dashboardExists == False):
        # Add the dashboard
        item = gisPortal.content.add(item_properties=itemProperties)

        # Get the JSON data from the file if provided
        jsonData = "{}"
        if (dataFile):
            # If the file exists
            if (os.path.exists(dataFile)):
                with open(dataFile) as jsonFile:
                    data = json.load(jsonFile)
                    jsonData = json.dumps(data)
            else:
                printMessage(title + " dashboard data does not exist - " + dataFile + "...","warning")
        # Update the URL and data properties 
        itemProperties = {'text':jsonData}
        item.update(itemProperties)
        printMessage(title + " dashboard created - " + item.id + "...","info")
        
        # If sharing to group(s)
        if (groupSharing):
            printMessage("Sharing with the following groups - " + groupSharing + "...","info")
            groupSharing = groupSharing.split(",")
            item.share(groups=groupSharing)
    # Dashboard already exists
    else:
        # Get the item ID
        itemID = getIDforPortalItem(gisPortal,title,"dashboard")
        # Get the dashboard
        item = gisPortal.content.get(itemID)

        # Update the dashboard
        item.update(itemProperties, thumbnail=thumbnail)
        printMessage(title + " dashboard updated - " + itemID + "...","info")
# End of create dashboard function


# Start of create web map function
def createWebMap(gisPortal,title,summary,description,tags,thumbnail,webmapBasemap,webmapLayers,organisationSharing,groupSharing):
    printMessage("Creating web map - " + title + "...","info")
            
    # FUNCTION - Search portal to see if web map is already there
    webmapExists = searchPortalForItem(gisPortal,title,"Web Map")

    # Create the web map properties
    itemProperties = {'title':title,
                      'description':description,
                      'snippet':summary,
                      'tags':tags,
                      'thumbnail':thumbnail,
                      'access':organisationSharing.lower()}
        
    # If the web map has not been created
    if (webmapExists == False):
        # If basemap provided
        if (webmapBasemap):
            # Get the item ID for the basemap
            itemID = getIDforPortalItem(gisPortal,webmapBasemap,"Web Map")
            basemap = gisPortal.content.get(itemID)
            # Create a web map object
            webmap = arcgis.mapping.WebMap(basemap)
        else:
            # Create a web map object
            webmap = arcgis.mapping.WebMap()

        # If layers provided
        if (webmapLayers):
            # Add layers to web map
            addLayersToWebmap(gisPortal,webmap,webmapLayers)
                    
        # Save the web map
        item = webmap.save(itemProperties, thumbnail=thumbnail)
        printMessage(title + " web map created - " + item.id + "...","info")

        # If sharing to group(s)
        if (groupSharing):
            printMessage("Sharing with the following groups - " + groupSharing + "...","info")
            groupSharing = groupSharing.split(",")
            item.share(groups=groupSharing)
    # Web map already exists
    else:
        # Get the item ID
        itemID = getIDforPortalItem(gisPortal,title,"web map")
        # Get the web map
        item = gisPortal.content.get(itemID)
        webmap = arcgis.mapping.WebMap(item)
            
        # Update the web map
        webmap.update(itemProperties, thumbnail=thumbnail)
        printMessage(title + " web map updated - " + itemID + "...","info")
# End of create web map function

            
# Start of add layers to web map function
def addLayersToWebmap(gisPortal,webmap,webmapLayers):
    # For each of the web map layers
    for webmapLayer in webmapLayers.split(","):
        printMessage("Adding layer to web map - " + webmapLayer + "...","info")
        # Get the item ID
        itemID = getIDforPortalItem(gisPortal,webmapLayer.split(":")[0],webmapLayer.split(":")[-1])
        if (itemID):
            # Add layer to the web map
            layerItem = gisPortal.content.get(itemID)
            # For each layer in the item
            for layer in layerItem.layers:
                webmap.add_layer(layer, {'visibility':True})
            # For each table in the item
            for table in layerItem.tables:
                webmap.add_table(table, None)
        else:
            printMessage("Layer not found in portal - " + webmapLayer + "...","error")
# End of add layers to web map function


# Start of get ID for portal item function
def getIDforPortalItem(gisPortal,title,itemType):
    itemID = ""
    # If a group
    if (itemType.lower() == "group"):
        # Search portal to find item
        searchItems = gisPortal.groups.search(query="title:" + title, sort_field='title', sort_order='asc')  
    else:        
        # Search portal to find item
        searchItems = gisPortal.content.search(query="title:" + title, item_type=itemType, sort_field='title', sort_order='asc')
        
    for searchItem in searchItems:
        # If search result matches
        if (searchItem.title.lower().replace(" ", "") == title.lower().replace(" ", "")):
            # If a group
            if (itemType.lower() == "group"):
                itemID = searchItem.id
            else:
                # If item type matches
                if (searchItem.type.lower().replace(" ", "") == itemType.lower().replace(" ", "")):
                    itemID = searchItem.id

    # Return item ID
    return itemID
# End of get ID for portal item function

    
# Start of search portal for item function
def searchPortalForItem(gisPortal,title,itemType):
    itemExists = False
    # If a group
    if (itemType.lower() == "group"):
        # Search portal to see if group is already there
        searchItems = gisPortal.groups.search(query="title:" + title, sort_field='title', sort_order='asc')        
    else:
        # Search portal to see if item is already there
        searchItems = gisPortal.content.search(query="title:" + title, item_type=itemType, sort_field='title', sort_order='asc')        

    for searchItem in searchItems:
        # If search result matches
        if (searchItem.title.lower().replace(" ", "") == title.lower().replace(" ", "")):
            printMessage(title + " already exists - " + searchItem.id + "...","info")
            itemExists = True

    # Return item exists boolean
    return itemExists
# End of search portal for item function


# Start of print and logging message function
def printMessage(message,type):
    # If using ArcPy
    if (useArcPy == "true"):
        if (type.lower() == "warning"):
            arcpy.AddWarning(message)
            # Logging
            if (enableLogging == "true"):
                logger.warning(message)
        elif (type.lower() == "error"):
            arcpy.AddError(message)
            # Logging
            if (enableLogging == "true"):
                logger.error(message)
        else:
            arcpy.AddMessage(message)
            # Logging
            if (enableLogging == "true"):
                logger.info(message)
    else:
        print(message)
        # Logging
        if (enableLogging == "true"):
            logger.info(message)
# End of print and logging message function


# Start of set logging function
def setLogging(logFile):
    # Create a logger
    logger = logging.getLogger(os.path.basename(__file__))
    logger.setLevel(logging.DEBUG)
    # Setup log message handler
    logMessage = logging.FileHandler(logFile)
    # Setup the log formatting
    logFormat = logging.Formatter("%(asctime)s: %(levelname)s - %(message)s", "%d/%m/%Y - %H:%M:%S")
    # Add formatter to log message handler
    logMessage.setFormatter(logFormat)
    # Add log message handler to logger
    logger.addHandler(logMessage)

    return logger, logMessage
# End of set logging function


# Start of send email function
def sendEmail(message,attachment):
    # Send an email
    printMessage("Sending email...","info")
    # Server and port information
    smtpServer = smtplib.SMTP(emailServerName,emailServerPort)
    smtpServer.ehlo()
    smtpServer.starttls()
    smtpServer.ehlo
    # Setup content for email (In html format)
    emailMessage = MIMEMultipart('alternative')
    emailMessage['Subject'] = emailSubject
    emailMessage['From'] = emailUser
    emailMessage['To'] = emailTo
    emailText = MIMEText(message, 'html')
    emailMessage.attach(emailText)

    # If there is a file attachment
    if (attachment):
        fp = open(attachment,'rb')
        fileAttachment = email.mime.application.MIMEApplication(fp.read(),_subtype="pdf")
        fp.close()
        fileAttachment.add_header('Content-Disposition','attachment',filename=os.path.basename(attachment))
        emailMessage.attach(fileAttachment)

    # Login with sender email address and password
    if (emailUser and emailPassword):
        smtpServer.login(emailUser, emailPassword)
    # Send the email and close the connection
    smtpServer.sendmail(emailUser, emailTo, emailMessage.as_string())
# End of send email function


# This test allows the script to be used from the operating
# system command prompt (stand-alone), in a Python IDE,
# as a geoprocessing script tool, or as a module imported in
# another script
if __name__ == '__main__':
    # If using ArcPy
    if (useArcPy == "true"):
        argv = tuple(arcpy.GetParameterAsText(i)
            for i in range(arcpy.GetArgumentCount()))
    else:
        argv = sys.argv
        # Delete the first argument, which is the script
        del argv[0]
    # Logging
    if (enableLogging == "true"):
        # Setup logging
        logger, logMessage = setLogging(logFile)
        # Log start of process
        logger.info("Process started.")
    # Setup the use of a proxy for requests
    if (enableProxy == "true"):
        # Setup the proxy
        proxy = urllib2.ProxyHandler({requestProtocol : proxyURL})
        openURL = urllib2.build_opener(proxy)
        # Install the proxy
        urllib2.install_opener(openURL)
    mainFunction(*argv)
