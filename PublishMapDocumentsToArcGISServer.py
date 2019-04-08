#-------------------------------------------------------------
# Name:                 Publish Map Documents to ArcGIS Server
# Purpose:              Publish map documents to ArcGIS Server (Federated with Portal) from a CSV file. Will overwrite map services with same name.
#                       - Creates ArcGIS Server folder if does not exist.
#                       - Enables feature access (with operations) or KML if specified in CSV.
#                       - Tests each published map/feature service by sending query to get all features.
#                       - Shares service with organisation and/or groups if specified.
# Author:               Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:         24/01/2019
# Last Updated:         21/02/2019
# ArcGIS Version:       ArcMap (ArcPy) 10.6+
# Python Version:       2.7.11+
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
import xml.dom.minidom as DOM
import json
import urllib
import urllib2
import ssl
import re
# Import ArcGIS modules
useArcPy = "true"
useArcGISAPIPython = "false"
if (useArcPy == "true"):
    # Import arcpy module
    import arcpy
    # Enable data to be overwritten
    arcpy.env.overwriteOutput = True
if (useArcGISAPIPython == "true"):
    # Import arcgis module
    import arcgis

# Set global variables
# Logging
enableLogging = "true" # Use within code to print and log messages - printMessage("xxx","info"), printMessage("xxx","warning"), printMessage("xxx","error")
logFile = os.path.join(os.path.dirname(__file__), "PublishMapDocumentsToArcGISServer.log") # e.g. os.path.join(os.path.dirname(__file__), "Example.log")
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
def mainFunction(portalURL,portalUser,portalPassword,csvFileLocation): # Add parameters sent to the script here e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)
    try:
        # --------------------------------------- Start of code --------------------------------------- #
                          
        # Read the csv file
        with open(csvFileLocation) as csvFile:
            reader = csv.DictReader(csvFile)
            # For each row in the CSV
            for row in reader:
                # If map document exists
                if (os.path.isfile(row["Map Document"])):
                    # If service name and title
                    if (row["Service Name"] and row["Title"]):                    
                        printMessage("Publishing map document to ArcGIS Server - " + row["Map Document"] + "...","info")
                        # Create service definition draft file
                        printMessage("Creating service definition draft file - " + os.path.join(arcpy.env.scratchFolder,row["Service Name"].replace(" ", "")) + ".sddraft...","info")
                        mxd = arcpy.mapping.MapDocument(row["Map Document"])

                        # If the ArcGIS server connection file exists
                        if (os.path.isfile(row["ArcGIS Server Connection"])):   
                            arcpy.mapping.CreateMapSDDraft(mxd,
                                                           os.path.join(arcpy.env.scratchFolder,row["Service Name"].replace(" ", "") + ".sddraft"),
                                                           row["Service Name"].replace(" ", ""),
                                                           'ARCGIS_SERVER', 
                                                           row["ArcGIS Server Connection"],
                                                           False,
                                                           row["ArcGIS Server Folder"],
                                                           row["Description"],
                                                           row["Tags"])

                            # Get the ArcGIS Server site from the connection file
                            agsURL = getAGSURL(os.path.join(arcpy.env.scratchFolder,row["Service Name"].replace(" ", "") + ".sddraft"))
                            
                            # Get the service capabilities
                            serviceCapabilities = []
                            for serviceCapability in row["Service Capabilities"].split(","):
                                serviceCapabilities.append(serviceCapability.replace(" ", "").lower())

                            if "featureaccess" in  serviceCapabilities:
                                # Set as feature service
                                enableFeatureAccess(os.path.join(arcpy.env.scratchFolder,row["Service Name"].replace(" ", "") + ".sddraft"),row["Service Operations"],row["Ownership Feature Access"],row["Enable Geometry Updates"])
                            if "kml" not in  serviceCapabilities:
                                # Disable KML access
                                disableKMLAccess(os.path.join(arcpy.env.scratchFolder,row["Service Name"].replace(" ", "") + ".sddraft"),row["Service Operations"])

                            printMessage("Analysing service definition...","info")
                            analysisSD = arcpy.mapping.AnalyzeForSD(os.path.join(arcpy.env.scratchFolder,row["Service Name"].replace(" ", "") + ".sddraft"))

                            # If there are no errors
                            if (analysisSD['errors'] == {}):
                                # Get a portal token
                                token = getToken(portalURL,portalUser,portalPassword)

                                if (token):                               
                                    # Create the ArcGIS Server folder if it does not exist
                                    if (row["ArcGIS Server Folder"]):
                                        checkAGSFolder(token,agsURL + "/admin/services/",row["ArcGIS Server Folder"])
                                
                                # Create service definition file
                                printMessage("Creating service definition file - " + os.path.join(arcpy.env.scratchFolder,row["Service Name"].replace(" ", "")) + ".sd...","info")
                                arcpy.StageService_server(os.path.join(arcpy.env.scratchFolder,row["Service Name"].replace(" ", "") + ".sddraft"), os.path.join(arcpy.env.scratchFolder,row["Service Name"].replace(" ", "") + ".sd"))
                                # Publishing to ArcGIS Server
                                printMessage("Publishing service...","info")
                                arcpy.UploadServiceDefinition_server(in_sd_file=os.path.join(arcpy.env.scratchFolder,row["Service Name"].replace(" ", "") + ".sd"), in_server=row["ArcGIS Server Connection"], in_override="OVERRIDE_DEFINITION", in_organization="SHARE_ORGANIZATION")

                                # Print the service URL
                                folderURL = ""
                                if (row["ArcGIS Server Folder"]):
                                    folderURL = row["ArcGIS Server Folder"] + "/"
                                if "featureaccess" in  serviceCapabilities:
                                    printMessage("Service has been published - " + agsURL + "/rest/services/" + folderURL + row["Service Name"].replace(" ", "") + "/FeatureServer","info")
                                    # Test the service
                                    testService(agsURL + "/rest/services/" + folderURL + row["Service Name"].replace(" ", "") + "/FeatureServer",token)
                                else:
                                    printMessage("Service has been published - " + agsURL + "/rest/services/" + folderURL + row["Service Name"].replace(" ", "") + "/MapServer","info")
                                    # Test the service
                                    testService(agsURL + "/rest/services/" + folderURL + row["Service Name"].replace(" ", "") + "/MapServer",token)

                                if (token):
                                    # Get item IDs for service
                                    portalItems = getItemIDs(token,agsURL + "/admin/services/" + folderURL + row["Service Name"].replace(" ", "") + ".MapServer")

                                    # For each portal item
                                    for portalItem in portalItems:
                                        # Get the owner of the portal item
                                        itemOwner = getItemOwner(token,portalURL,portalItem)
                                                                      
                                        # Set the title and thumbnail of the item in portal
                                        updateItemDetails(token,portalURL,itemOwner,portalItem,row["Title"],row["Thumbnail"])
                                        
                                        # Get item IDs for groups
                                        itemIDs = getItemIDGroup(token,portalURL,row["Group Sharing"])
                    
                                        # Set sharing for item
                                        setSharing(token,portalURL,itemOwner,portalItem,row["Organisation Sharing"],itemIDs)                            
                            else:
                                printMessage("Service not published - There were errors found in the map document...","error")
                        # ArcGIS server connection file does not exist
                        else:
                            printMessage("Service not published - ArcGIS server connection file does not exist - " + row["ArcGIS Server Connection"] + "...","error")                        
                    # Title and/or service name not provided
                    else:
                        printMessage("Service not published - Title and/or service name not provided...","error")
                # Map document does not exist
                else:
                    printMessage("Service not published - Map document does not exist - " + row["Map Document"] + "...","error")
        
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

               
# Start of enable feature access function
def enableFeatureAccess(serviceDefinitionFile,serviceOperations,ownershipFeatureAccess,enableGeometryUpdates):
    printMessage("Enabling feature access with these operations - " + serviceOperations + "...","info")
    
    # Read the service definition draft xml
    document = DOM.parse(serviceDefinitionFile)

    # For all the type names
    typeNames = document.getElementsByTagName('TypeName')
    for typeName in typeNames:
        # Enable FeatureServer capability
        if typeName.firstChild.data == "FeatureServer":
            extension = typeName.parentNode
            for extElement in extension.childNodes:
                if extElement.tagName =='Enabled':
                    extElement.firstChild.data ='true'

    # For all the values
    values = document.getElementsByTagName('Value')               
    for value in values:
        if value.hasChildNodes():
            # Set the service operations
            if value.firstChild.data == 'Query,Create,Update,Delete,Uploads,Editing':
                value.firstChild.data = serviceOperations
    
    # For all the keys
    printMessage("Enabling geometry updates - " + enableGeometryUpdates + "...","info")  
    keys = document.getElementsByTagName('Key')
    for key in keys:
        if key.hasChildNodes():
            # Allow geometry updates
            if key.firstChild.data.lower() == "allowgeometryupdates":
                if enableGeometryUpdates.lower() == "yes":
                    key.nextSibling.firstChild.data = "true"
                else:
                    key.nextSibling.firstChild.data = "false" 

    # If ownership feature access is set
    if (ownershipFeatureAccess):
        printMessage("Enabling ownership-based access control on features - " + ownershipFeatureAccess + "...","info")           
        # For all the keys
        keys = document.getElementsByTagName('Key')
        for key in keys:
            if key.hasChildNodes():
                # Enable ownership based access control 
                if key.firstChild.data.lower() == "enableownershipbasedaccesscontrol":
                    key.nextSibling.firstChild.data = "true"

                # Allow others to query
                if key.firstChild.data.lower() == "allowotherstoquery":
                    if "query" in ownershipFeatureAccess.lower():
                        key.nextSibling.firstChild.data = "true"
                    else:
                        key.nextSibling.firstChild.data = "false"                        
                    
                # Allow others to update
                if key.firstChild.data.lower() == "allowotherstoupdate":
                    if "update" in ownershipFeatureAccess.lower():
                        key.nextSibling.firstChild.data = "true"
                    else:
                        key.nextSibling.firstChild.data = "false" 

                # Allow others to delete
                if key.firstChild.data.lower() == "allowotherstodelete":
                    if "delete" in ownershipFeatureAccess.lower():
                        key.nextSibling.firstChild.data = "true"
                    else:
                        key.nextSibling.firstChild.data = "false"                   
    
    f = open(serviceDefinitionFile, 'w')     
    document.writexml(f)     
    f.close()
# End of enable feature access function


# Start of disable KML access function
def disableKMLAccess(serviceDefinitionFile,serviceOperations):
    printMessage("Disabling KML access...","info")
    
    # Read the service definition draft xml
    document = DOM.parse(serviceDefinitionFile)

    # Disable KML capablility
    typeNames = document.getElementsByTagName('TypeName')
    for typeName in typeNames:
        # Get the TypeName we want to disable - KmlServer
        if typeName.firstChild.data == "KmlServer":
            extension = typeName.parentNode
            for extElement in extension.childNodes:
                if extElement.tagName == 'Enabled':
                    extElement.firstChild.data = 'false'

    f = open(serviceDefinitionFile, 'w')     
    document.writexml(f)     
    f.close()
# End of disable KML access function


# Start of get ArcGIS Server URL function
def getAGSURL(serviceDefinitionFile):
    printMessage("Getting the ArcGIS Server URL from connection file...","info")
    
    # Read the service definition draft xml
    document = DOM.parse(serviceDefinitionFile)

    agsURL = ""
    stagingSettings = document.getElementsByTagName('StagingSettings')[0]
    propArray = stagingSettings.firstChild
    propSets = propArray.childNodes
    for propSet in propSets:
        keyValues = propSet.childNodes
        for keyValue in keyValues:
            if keyValue.tagName == 'Key':
                if keyValue.firstChild.data == "ServerConnectionString":
                    # Load connection string into an array
                    connectionStringValues = keyValue.nextSibling.firstChild.data.split(";")
                    # For each connection string value
                    for connectionStringValue in connectionStringValues:
                        # Get the server URL
                        if (connectionStringValue.split("=")[0].replace(" ", "").lower() == "serverurl"):
                            agsURL = connectionStringValue.split("=")[-1].replace("/admin","")

    return agsURL                    
# End of get ArcGIS Server URL function


# Start of check ArcGIS Server folder function
def checkAGSFolder(token,serviceURL,folder):
    printMessage("Checking ArcGIS Server folder - " + folder,"info")
    
    # Setup the parameters
    parameters = urllib.urlencode({'token': token,
                  'folderName': folder,
                  'f': 'json'})
    queryString = parameters.encode('utf-8')

    # Request to check if folder exists
    try:
        context = ssl._create_unverified_context()
        request = urllib2.Request(serviceURL + "/exists",queryString)
        responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
        if "error" in responseJSON:
            printMessage(responseJSON,"error")
        else:
            # If folder does not exist
            if (str(responseJSON["exists"]).lower() == "false"):
                # Create folder
                createAGSFolder(token,serviceURL,folder)
            else:
                printMessage("ArcGIS Server folder already exists - " + folder,"info")                
    except urllib2.URLError, error:
        printMessage("Could not connect...","error")
        printMessage(error,"error")
# End of check ArcGIS Server folder function


# Start of create ArcGIS Server folder function
def createAGSFolder(token,serviceURL,folder):
    printMessage("Creating ArcGIS Server folder - " + folder,"info")
    
    # Setup the parameters
    parameters = urllib.urlencode({'token': token,
                  'folderName': folder,
                  'f': 'json'})
    queryString = parameters.encode('utf-8')

    # Request to create folder
    try:
        context = ssl._create_unverified_context()
        request = urllib2.Request(serviceURL + "/createFolder",queryString)
        responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
        if "error" in responseJSON:
            printMessage(responseJSON,"error")
        else:
            printMessage("ArcGIS Server folder created - " + folder,"info")                
    except urllib2.URLError, error:
        printMessage("Could not connect...","error")
        printMessage(error,"error")
# End of create ArcGIS Server folder function


# Start of test service function
def testService(serviceURL,token):
    printMessage("Testing service - " + serviceURL,"info")

    # Setup the parameters
    parameters = urllib.urlencode({'token': token,
                  'f': 'json'})
    queryString = parameters.encode('utf-8')

    # Request to get layer IDs
    try:
        context = ssl._create_unverified_context()
        request = urllib2.Request(serviceURL,queryString)
        responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
        if "error" in responseJSON:
            printMessage("Test failed...","error")
            printMessage(responseJSON,"error")
        else:
            # If there are layers
            if (len(responseJSON["layers"]) > 0):
                # Get the ID of the first layer
                id = responseJSON["layers"][0]["id"]
                # Query the service layer
                queryServiceLayer(serviceURL + "/" + str(id) + "/query",token)
            # No layers
            else:
                printMessage("Test failed...","error")
                printMessage("This is an issue with the layers in the service...","error")            
    except urllib2.URLError, error:
        printMessage("Could not connect...","error")
        printMessage(error,"error")
# End of test service function


# Start of query service layer function
def queryServiceLayer(serviceLayerURL,token):
    printMessage("Querying service layer - " + serviceLayerURL,"info")

    # Setup the parameters
    parameters = urllib.urlencode({'token': token,
                  'where': '1=1',
                  'outFields': '*',
                  'f': 'json'})
    queryString = parameters.encode('utf-8')

    # Request to query service layer
    try:
        context = ssl._create_unverified_context()
        request = urllib2.Request(serviceLayerURL,queryString)
        responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
        if "error" in responseJSON:
            printMessage("Test failed...","error")
            printMessage(responseJSON,"error")
        else:
            if "features" in responseJSON: 
                printMessage("Test succeeded...","info")       
    except urllib2.URLError, error:
        printMessage("Could not connect...","error")
        printMessage(error,"error") 
# End of query service layer function


# Start of get item IDs function
def getItemIDs(token,serviceURL):
    printMessage("Requesting item ID from service - " + serviceURL,"info")
        
    # Setup the parameters
    parameters = urllib.urlencode({'token': token,
                  'f': 'json'})
    queryString = parameters.encode('utf-8')

    # Request to get item
    try:
        context = ssl._create_unverified_context()
        request = urllib2.Request(serviceURL,queryString)
        responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
        if "error" in responseJSON:
            printMessage(responseJSON,"error")
            return None
        else:
            portalProperties = responseJSON.get('portalProperties')
            portalItems = portalProperties.get('portalItems')
            # Return result
            return portalItems
    except urllib2.URLError, error:
        printMessage("Could not connect...","error")
        printMessage(error,"error")
        return None
# End of get item IDs function


# Start of get item owner function
def getItemOwner(token,portalURL,portalItem):
    printMessage("Requesting item owner...","info")

    # Setup the parameters
    parameters = urllib.urlencode({'token': token,           
                  'f': 'json'})
    queryString = parameters.encode('utf-8')

    # Request to search for item
    try:
        context = ssl._create_unverified_context()
        request = urllib2.Request(portalURL + "/sharing/rest/content/items/" + portalItem["itemID"],queryString)
        responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
        if "error" in responseJSON:
            printMessage(responseJSON,"error")
            return None
        else:  
            # Return result
            return responseJSON["owner"]
    except urllib2.URLError, error:
        printMessage("Could not connect...","error")
        printMessage(error,"error")
        return None
# End of get item owner function


# Start of set sharing function
def setSharing(token,portalURL,portalUser,portalItem,organisationSharing,groupSharing):
    everyoneBoolean = "false"
    orgBoolean = "false"
    if (organisationSharing.replace(" ", "").lower() == "org"):
        orgBoolean = "true"
    elif (organisationSharing.replace(" ", "").lower() == "public"):
        everyoneBoolean = "true"

    printMessage("Sharing item - " + portalURL + "/sharing/rest/content/users/" + portalUser + "/items/" + portalItem["itemID"],"info")
    printMessage("Organisation sharing - " + organisationSharing,"info")
    printMessage("Sharing with the following groups - " + groupSharing,"info")
    
    # Setup the parameters
    parameters = urllib.urlencode({'token': token,
                  'everyone': everyoneBoolean,
                  'org': orgBoolean,
                  'groups': groupSharing,
                  'f': 'json'})
    queryString = parameters.encode('utf-8')

    # Request to share item
    try:
        context = ssl._create_unverified_context()
        request = urllib2.Request( portalURL + "/sharing/rest/content/users/" + portalUser + "/items/" + portalItem["itemID"] + "/share",queryString)
        responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
        if "error" in responseJSON:
            printMessage(responseJSON,"error")
        else:
            printMessage(responseJSON,"info")           
    except urllib2.URLError, error:
        printMessage("Could not connect...","error")
        printMessage(error,"error") 
# End of set sharing function


# Start of update item details function
def updateItemDetails(token,portalURL,portalUser,portalItem,title,thumbnail):
    printMessage("Updating item title and thumbnail - " + portalItem["itemID"],"info")
    
    # Setup the parameters
    parameters = urllib.urlencode({'token': token,
                  'title': title,
                  'thumbnail': thumbnail,                                   
                  'f': 'json'})
    queryString = parameters.encode('utf-8')

   # Request to update item
    try:
        context = ssl._create_unverified_context()
        request = urllib2.Request( portalURL + "/sharing/rest/content/users/" + portalUser + "/items/" + portalItem["itemID"] + "/update",queryString) 
        responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
        if "error" in responseJSON:
            printMessage(responseJSON,"error")
        else:
            printMessage(responseJSON,"info") 
    except urllib2.URLError, error:
        printMessage("Could not connect...","error")
        printMessage(error,"error")      
# End of update item details function

                                    
# Start of get item IDs for groups function
def getItemIDGroup(token,portalURL,groupTitles):
    groupIDs = []
    for groupTitle in groupTitles.split(","):
        printMessage("Requesting Item ID for " + groupTitle + "...","info")        

        # Setup the parameters
        parameters = urllib.urlencode({'token': token,
                      'q': 'title:' + groupTitle,
                      'sort_field': 'title',
                      'sort_order': 'asc',              
                      'f': 'json'})
        queryString = parameters.encode('utf-8')

        # Request to search for item
        try:
            context = ssl._create_unverified_context()
            request = urllib2.Request( portalURL + "/sharing/rest/community/groups",queryString)
            responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
            if "error" in responseJSON:
                printMessage(responseJSON,"error")
            else:
                # For each result
                for result in responseJSON["results"]:
                    # If search result matches
                    if (result["title"].lower() == groupTitle.lower()):
                        # Add ID to array
                        groupIDs.append(result["id"])     
        except urllib2.URLError, error:
            printMessage("Could not connect...","error")
            printMessage(error,"error")
            
    return ','.join(groupIDs)
# End of get item IDs for groups function


# Start of get token function
def getToken(portalURL,portalUser,portalPassword):
    printMessage("Getting portal token - " + portalURL + "/sharing/rest/generateToken","info")
        
    # Setup the parameters
    parameters = urllib.urlencode({'username': portalUser,
                  'password': portalPassword,
                  'client': 'referer',
                  'referer': portalURL,
                  'expiration': '60',
                  'f': 'json'})
    queryString = parameters.encode('utf-8')

    # Request to get token
    try:
        context = ssl._create_unverified_context()
        request = urllib2.Request(portalURL + "/sharing/rest/generateToken",queryString)
        responseJSON = json.loads(urllib2.urlopen(request, context=context).read())
        if "error" in responseJSON:
            printMessage(responseJSON,"error")
            return None
        else:
            token = responseJSON.get('token')
            return token
    except urllib2.URLError, error:
        printMessage("Could not connect...","error")
        printMessage(error,"error")
        return None
# End of get token function


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
