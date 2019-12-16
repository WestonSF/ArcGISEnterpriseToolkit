#-------------------------------------------------------------
# Name:                 Download Item Data
# Purpose:              Downloads data from specified items in portal or downloads all
#                       items in a portal site to a specified folder. Downloads web map/web
#                       application as JSON and hosted feature service as FGDB. Can download attachments data
#                       based on configuration parameters. Configuration file parameters:
#                       * dataID - Unique ID for each item listed (Required)
#                       * itemID - ID of the item in the portal site to download (Required)
#                       * layerID - If downloading attachments, the layer ID in the service to download (Optional)
#                       * createFolder - If downloading attachments, create a folder (using the name parameter) for attachments
#                       to be downloaded to e.g. "true" or "false" (Optional)
#                       * createFeatureFolder - If downloading attachments, create a folder (using the ID field) for each attachment
#                       that is downloaded to e.g. "true" or "false" (Optional)
#                       * subFolders - If downloading attachments, names of blank sub folders to create for each feature that
#                       is downloaded e.g. "Folder1,Folder2,Folder3" (Optional)
#                       * name - If downloading attachments, name of the layer to download, which will be the name of the folder
#                       that is created e.g. "Features1" (Optional)
#                       * idField - If downloading attachments, the name of the field in the layer to use as the ID when
#                       creating a folder for each feature where attachments will be downloaded e.g. "GlobalID" (Optional)
#                       * parentDataID - If downloading attachments, the ID of the item to join to if needing to needing to
#                       create a folder structure where the layer attachments will be downloaded under the folder for the parent
#                       data ID layer e.g. "2" (Optional)
#                       * joinField - If downloading attachments, the name of the field in the layer to use as the ID when
#                       needing to create a folder structure where the layer attachments will be downloaded under the folder
#                       for the parent data ID layer e.g. "ParentGlobalID" (Optional) 
# Author:               Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:         09/04/2019
# Last Updated:         17/12/2019
# ArcGIS Version:       ArcGIS API for Python 1.6.1+
# Python Version:       3.6.5+ (Anaconda 5.2+)
#--------------------------------

# Import main modules
import os
import sys
import logging
import smtplib
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
import time
import shutil
import csv
import json
import multiprocessing.pool
import itertools

# Set global variables
# Logging
enableLogging = "true" # Use within code to print and log messages - printMessage("xxx","info"), printMessage("xxx","warning"), printMessage("xxx","error")
logFile = os.path.join(os.path.dirname(__file__), "DownloadItemData.log") # e.g. os.path.join(os.path.dirname(__file__), "Example.log")
archiveLogFiles = "true"
# Email logging
sendErrorEmail = "false"
emailServerName = "" # e.g. smtp.gmail.com
emailServerPort = 0 # e.g. 25
emailTo = ""
emailUser = ""
emailPassword = ""
emailSubject = ""
emailMessage = ""
# Proxy
enableProxy = "false"
requestProtocol = "http" # http or https
proxyURL = ""
# Output
output = None
featureFolderLocations = []


# Start of main function
def mainFunction(portalURL,portalUser,portalPassword,configFile,createFolder,downloadLocation,parallelProcessing): # Add parameters sent to the script here e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)
    try:
        # --------------------------------------- Start of code --------------------------------------- #
        # Connect to GIS portal
        printMessage("Connecting to GIS Portal - {}...".format(portalURL),"info")
        
        gisPortal = arcgis.GIS(url=portalURL, username=portalUser, password=portalPassword, verify_cert=False)

        # If config file is provided
        itemDicts = []
        configData = None
        if (configFile):
            # If config file is valid
            if (os.path.isfile(configFile)):
                # Open the JSON file
                with open(configFile) as jsonFile:
                    configData = json.load(jsonFile)
                    if "items" in configData:
                        # For each item
                        for itemConfig in configData["items"]:
                            if "itemID" in itemConfig:
                                # Get the item
                                item = gisPortal.content.get(itemConfig["itemID"])
                                itemDict = {}
                                itemDict["item"] = item
                                itemDict["itemConfig"] = itemConfig
                                itemDicts.append(itemDict)
                            else:
                                printMessage("Configuration file is not valid, item ID parameter is not present - " + configFile + "...","error")                                
                    else:
                        printMessage("Configuration file is not valid, items list is not present - " + configFile + "...","error")                         
            else:
                printMessage("Configuration file is not valid - " + configFile + "...","error")                
        # Else get all items
        else:
            # Query all items in the portal
            items = gisPortal.content.search(query="",max_items=10000)
            for item in items:
                itemDict = {}
                itemDict["item"] = item
                itemDict["itemConfig"] = ""
                itemDicts.append(itemDict)                

        # If there are items
        if len(itemDicts) > 0:
            # Setup a folder if necessary
            if (createFolder.lower() == "true"):
                if not os.path.exists(os.path.join(downloadLocation,"AGSBackup-" + time.strftime("%Y%m%d"))):
                    # Create the folder
                    printMessage("Creating folder - " + os.path.join(downloadLocation,"AGSBackup-" + time.strftime("%Y%m%d")) + "...","info")
                    os.makedirs(os.path.join(downloadLocation,"AGSBackup-" + time.strftime("%Y%m%d")))
                downloadLocation = os.path.join(downloadLocation,"AGSBackup-" + time.strftime("%Y%m%d"))

            # If using parallel processing to download the items
            if (parallelProcessing.lower() == "true"):            
                # Download data for items - Pool items for processing   
                multiprocessing.pool.ThreadPool().starmap(downloadItem,zip(itemDicts,itertools.repeat(configData),itertools.repeat(downloadLocation)))
            else:
                # For each item
                for itemDict in itemDicts:
                    # Download data for item
                    downloadItem(itemDict,configData,downloadLocation)                
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
            sendEmail(errorMessage)
# End of main function


# Start of download item function
def downloadItem(itemDict,configData,downloadLocation):
    exportData = True
    result = None

    # If item is a hosted feature service 
    if (isHostedFeatureService(itemDict["item"])):
        # If config data
        if configData:
            # If there is config for the item
            if (itemDict["itemConfig"]):
                # If all the required parameters are in the object - Will export all attachments
                if (("layerID" in itemDict["itemConfig"]) and ("createFolder" in itemDict["itemConfig"]) and ("name" in itemDict["itemConfig"]) and ("idField" in itemDict["itemConfig"])):
                    # Export attachments and add folder locations to an array
                    exportAttachments(itemDict["item"],itemDict["itemConfig"],downloadLocation)
                    exportData = False
                # Set to export data
                else:
                    exportData = True
                    
        # If exporting data               
        if (exportData == True):
            printMessage("Exporting data for feature service - " + itemDict["item"].id + " (Title - " + itemDict["item"].title + ")...","info")
            fgdbItem = itemDict["item"].export(itemDict["item"].title, "File Geodatabase")
            result = fgdbItem.download(downloadLocation)
            fgdbItem.delete()

    # If item is a feature service
    if (itemDict["item"].type.lower() == "feature service"):
        # If a hosted service
        if "Hosted Service" not in itemDict["item"].typeKeywords:
            # Download the JSON data
            printMessage("Downloading data from item - " + itemDict["item"].id + " (Title - " + itemDict["item"].title + ")...","info")         
            result = itemDict["item"].download(downloadLocation)                    
    elif (itemDict["item"].type.lower() == "code attachment"):
        printMessage("Not downloading data for code attachment - " + itemDict["item"].id + " (Title - " + itemDict["item"].title + ")...","warning")
        exportData = False
    else:
        # Download the JSON data
        printMessage("Downloading data from item - " + itemDict["item"].id + " (Title - " + itemDict["item"].title + ")...","info")         
        result = itemDict["item"].download(downloadLocation)

    # If exporting data  
    if (exportData == True):
        # If data is downloaded
        if result:
            # If there is no file extension
            filePath = result
            fileExtension = os.path.splitext(result)[1]
            if not fileExtension:
                # If the file aready exists
                if os.path.isfile(result + ".json"):
                    # Delete file
                    os.remove(result + ".json")
                os.rename(result, result + ".json")
                filePath = result + ".json"       
            printMessage("Downloaded data to " + filePath,"info")
        else:
            printMessage("There was an error downloading the data for item " + itemDict["item"].id,"error")      
# End of download item function


# Start of export attachments function
def exportAttachments(item,configItem,downloadLocation):
    printMessage("Exporting attachments for feature service - {} (Title - {}), layer ID - {} ({})...".format(item.id,item.title,configItem["layerID"],configItem["name"]),"info")
    # Get the feature layer
    featureLayer = getFeatureLayer(item,configItem["layerID"])    
    if (featureLayer):
        # Get the ID fields
        objectIDField,idField,idJoin = getIDFields(featureLayer,configItem)

        # Get the features
        printMessage("Querying feature service...","info")
        featureSet = featureLayer.query(return_geometry=False)

        # Get a list of features to download attachments for - Pool features for processing       
        featureFolders = multiprocessing.pool.ThreadPool().starmap(processFeature,zip(featureSet.features,itertools.repeat(configItem),itertools.repeat(featureLayer),itertools.repeat(objectIDField),itertools.repeat(idField),itertools.repeat(idJoin),itertools.repeat(downloadLocation)))                      
        # For each feature returned
        for featureFolder in featureFolders:
            # Check base folder location exists
            if not os.path.exists(featureFolder["baseLocation"]):
                # Create the folder
                printMessage("Creating folder - {}...".format(featureFolder["baseLocation"]),"info")
                os.mkdir(featureFolder["baseLocation"])            
            # Check folder location exists
            if not os.path.exists(featureFolder["location"]):
                # Create the folder
                printMessage("Creating folder - {}...".format(featureFolder["location"]),"info")
                os.mkdir(featureFolder["location"])

            # For each sub folder
            for subFolder in featureFolder["subFolders"]:
                if not os.path.exists(os.path.join(featureFolder["location"],subFolder)):
                    # Create the folder
                    printMessage("Creating folder - {}...".format(os.path.join(featureFolder["location"],subFolder)),"info")
                    os.mkdir(os.path.join(featureFolder["location"],subFolder))
                
            # If there are attachments
            if (len(featureFolder["featureAttachments"]) > 0):
                # Download attachments - Pool downloads for processing
                printMessage("Querying attachments for {}...".format(featureFolder["featureID"]),"info")
                multiprocessing.pool.ThreadPool().starmap(downloadAttachments,zip(featureFolder["featureAttachments"],itertools.repeat(featureLayer),itertools.repeat(featureFolder["objectid"]),itertools.repeat(featureFolder["location"])))                                           
    else:
        printMessage("No layer or table name found in item - " + configItem["name"] + "...","warning")
# End of export attachments function
        

# Start of process feature function
def processFeature(feature,configItem,featureLayer,objectIDField,idField,idJoin,downloadLocation):
    # Get the ID values and set a default
    idValue = "Other"
    joinValue = "Other"
    if (idField):
        if (feature.attributes[idField]):
            idValue = str(feature.attributes[idField])
    if (idJoin):
        if (feature.attributes[idJoin]):
            joinValue = str(feature.attributes[idJoin])
    printMessage("Querying data for " + idValue + "...","info")
        
    # Check if parent data ID provided
    if (configItem["parentDataID"]):
        # Get the base folder path for the parent item
        printMessage("Querying parent data for {}...".format(idValue),"info")
        baseDownloadLocation = getFeatureFolderPath(configItem["parentDataID"],joinValue)
        # If there is no matching feature, set to base location
        if baseDownloadLocation is None:
            baseDownloadLocation = downloadLocation
    else:
        baseDownloadLocation = downloadLocation
        
    # Setup the base folder if necessary
    if (configItem["createFolder"].lower() == "true"):
        # Update folder location
        baseDownloadLocation = os.path.join(baseDownloadLocation,str(configItem["name"]))                

    # Setup the feature folder if necessary
    downloadFeatureLocation = baseDownloadLocation
    if (configItem["createFeatureFolder"].lower() == "true"):               
        # Setup the feature folder location
        downloadFeatureLocation = os.path.join(baseDownloadLocation,idValue)

    # Setup the sub folders if necessary
    subFolders = configItem["subFolders"].split(",")            

    # Get a list of attachments for the feature
    featureAttachments = featureLayer.attachments.get_list(oid=feature.attributes[objectIDField])
    
    # Load location into global array
    featureFolderLocation = {}
    featureFolderLocation["dataID"] = configItem["dataID"]            
    featureFolderLocation["featureID"] = idValue
    featureFolderLocation["baseLocation"] = baseDownloadLocation   
    featureFolderLocation["location"] = downloadFeatureLocation
    featureFolderLocation["objectid"] = feature.attributes[objectIDField] 
    featureFolderLocation["featureAttachments"] = featureAttachments
    featureFolderLocation["subFolders"] = subFolders   
    featureFolderLocations.append(featureFolderLocation)
    # Return the location
    return featureFolderLocation                    
# End of process feature function


# Start of download attachments function
def downloadAttachments(featureAttachment,featureLayer,objectID,downloadFeatureLocation):
    # Check if file has already been downloaded
    downloadAttachment = False
    if not os.path.exists(os.path.join(downloadFeatureLocation,featureAttachment["name"])):
        downloadAttachment = True
        printMessage("Downloading {}...".format(featureAttachment["name"]),"info")
    else:
        printMessage("Attachment already exists - {}...".format(os.path.join(downloadFeatureLocation,featureAttachment["name"])),"info")
        # Compare attachment file size to the one that is already downloaded
        if (featureAttachment["size"] != os.path.getsize(os.path.join(downloadFeatureLocation,featureAttachment["name"]))):
            downloadAttachment = True
            printMessage("Attachment has been updated, downloading {}...".format(featureAttachment["name"]),"info")   
    # If downloading the attachment
    if (downloadAttachment == True):
        featureLayer.attachments.download(oid=objectID,attachment_id=featureAttachment["id"],save_path=downloadFeatureLocation)      
# End of download attachments function


# Start of get item folder path function
def getFeatureFolderPath(dataID,joinValue):
    dataIDFound = False
    path = None
    # For each feature location
    for featureFolderLocation in featureFolderLocations:
        # If there is a data ID Matching
        if (featureFolderLocation["dataID"].lower() == dataID.lower()):  
            dataIDFound = True
        # If there is a feature matching
        if (featureFolderLocation["dataID"].lower() == dataID.lower()) and (featureFolderLocation["featureID"].lower() == joinValue.lower()):
            path = featureFolderLocation["location"]
    # If data ID is not found
    if (dataIDFound == False):
        printMessage("Item with data ID of " + str(dataID) +  " was not found in the configuration file...","warning")
        
    return path
# End of get item folder path function


# Start of get ID fields function
def getIDFields(featureLayer,configItem):
    # Get the field names
    fieldNames = []
    # Get the object ID field
    objectIDField = "OBJECTID"
    for field in featureLayer.properties.fields:
        if (field['name'].lower() == "objectid"):
            objectIDField = field['name']
        fieldNames.append(field['name'].lower())

    # Get the ID field
    idField = objectIDField
    if configItem["idField"].lower() in fieldNames: 
        idField = configItem["idField"]
    else:
        printMessage(configItem["idField"] + " field not in data...","warning")        
    printMessage("ID field set to " + idField + "...","info")     

    # Get the join ID field
    idJoin = configItem["joinField"]
    if configItem["joinField"].lower() in fieldNames:
        printMessage("Join field set to " + idJoin + "...","info")
    else:
        printMessage("Join field not provided or not present in layer/table...","warning")
        idJoin = None

    return objectIDField,idField,idJoin
# End of get ID fields function


# Start of get feature layer function
def getFeatureLayer(item,layerID):
    layer = None
    # Get the layers in the items
    featureLayers = item.layers + item.tables

    for featureLayer in featureLayers:
        # If layer ID matches layer ID in config
        if (str(featureLayer.properties.id) == str(layerID)): 
            layer = featureLayer
    return layer         
# End of get feature layer function
    

# Start of is hosted feature service function
def isHostedFeatureService(item):
    isFeatureService = False    
    # If item is a feature service
    if (item.type.lower() == "feature service"):
        # If a hosted service
        if "Hosted Service" in item.typeKeywords:
            isFeatureService = True
    return isFeatureService    
# End of is hosted feature service function


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
def sendEmail(message):
    # Send an email
    printMessage("Sending email...","info")
    # Server and port information
    smtpServer = smtplib.SMTP(emailServerName,emailServerPort)
    smtpServer.ehlo()
    smtpServer.starttls()
    smtpServer.ehlo
    # Login with sender email address and password
    smtpServer.login(emailUser, emailPassword)
    # Email content
    header = 'To:' + emailTo + '\n' + 'From: ' + emailUser + '\n' + 'Subject:' + emailSubject + '\n'
    body = header + '\n' + emailMessage + '\n' + '\n' + message
    # Send the email and close the connection
    smtpServer.sendmail(emailUser, emailTo, body)
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
        # Archive log file
        if (archiveLogFiles == "true"):
            # If file exists
            if (os.path.isfile(logFile)):
                # If file is larger than 10MB
                if ((os.path.getsize(logFile) / 1048576) > 10):
                    # Archive file
                    shutil.move(logFile, os.path.basename(os.path.splitext(logFile)[0]) + "-" + time.strftime("%d%m%Y") + ".log")         
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
