#-------------------------------------------------------------
# Name:       Download Feature Layer
# Purpose:    Downloads a feature service (As file geodatabase, shapefile or CSV) from a portal site and optionally updates an existing dataset. Two update options:
#             Existing Mode - Will delete and append records, so field names need to be the same.
#             New Mode - Copies data over. Requires no locks on geodatabase datasets being overwritten.
# Author:     Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:    30/09/2014
# Last Updated:    01/03/2016
# Copyright:   (c) Eagle Technology
# ArcGIS Version:   ArcMap 10.3+ or ArcGIS Pro 1.1+ (Need to be signed into a portal site)
# Python Version:   2.7 or 3.4
#--------------------------------

# Import main modules
import os
import sys
import logging
import smtplib

# Set global variables
# Logging
enableLogging = "false" # Use within code - logger.info("Example..."), logger.warning("Example..."), logger.error("Example...") and to print messages - printMessage("xxx","info"), printMessage("xxx","warning"), printMessage("xxx","error")
logFile = os.path.join(os.path.dirname(__file__), "DownloadFeatureLayer.log") # os.path.join(os.path.dirname(__file__), "Example.log")
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
# ArcGIS desktop installed
arcgisDesktop = "false"

# If ArcGIS desktop installed
if (arcgisDesktop == "true"):
    # Import extra modules
    import arcpy
    # Enable data to be overwritten
    arcpy.env.overwriteOutput = True
# Python version check
if sys.version_info[0] >= 3:
    # Python 3.x
    import urllib.request as urllib2
else:
    # Python 2.x
    import urllib2
import urllib
import zipfile
import json
import glob
import time
import shutil
import tempfile


# Start of main function
def mainFunction(portalUrl,portalAdminName,portalAdminPassword,itemIDs,workspace,outputFormat,updateMode): # Get parameters from ArcGIS Desktop tool by seperating by comma e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)
    try:
        # --------------------------------------- Start of code --------------------------------------- #
        # If ArcGIS desktop installed
        if (arcgisDesktop == "true"):
            # Set temp folder
            tempFolder = arcpy.env.scratchFolder
        # ArcGIS desktop not installed
        else:
            # Set temp folder
            tempFolder = tempfile.mkdtemp()

        printMessage("Connecting to Portal - " + portalUrl + "...","info")
        # Generate token for portal
        token = generateToken(portalAdminName, portalAdminPassword, portalUrl)

        # Get the item IDs
        itemIDs = itemIDs.split(",")

        # For each item ID specified
        for itemID in itemIDs:
            printMessage("Exporting feature layer to " + outputFormat + ". Item ID - " + itemID + "...","info")

            # Setup parameters for export
            dict = {}
            dict['f'] = 'json'
            dict['token'] = token
            dict['itemId'] = itemID
            dict['exportFormat'] = outputFormat
            # Python version check
            if sys.version_info[0] >= 3:
                # Python 3.x
                # Encode parameters
                params = urllib.parse.urlencode(dict)
            else:
                # Python 2.x
                # Encode parameters
                params = urllib.urlencode(dict)
            params = params.encode('utf-8')

            # POST the request - Creates a new item in the ArcGIS online site
            requestURL = urllib2.Request(portalUrl + "/sharing/rest/content/users/" + portalAdminName + "/export",params)
            response = urllib2.urlopen(requestURL)
            # Python version check
            if sys.version_info[0] >= 3:
                # Python 3.x
                # Read json response
                responseJSON = json.loads(response.read().decode('utf8'))
            else:
                # Python 2.x
                # Read json response
                responseJSON = json.loads(response.read())

            # Log results
            if "error" in responseJSON:
                errDict = responseJSON['error']
                message =  "Error Code: %s \n Message: %s" % (errDict['code'],
                errDict['message'])
                printMessage(message,"error")
            else:
                jobId = responseJSON.get('jobId')
                exportItemId = responseJSON.get('exportItemId')

                # Setup parameters for status check
                dict = {}
                dict['f'] = 'json'
                dict['token'] = token
                dict['jobType'] = "export"
                dict['jobId'] = jobId
                # Python version check
                if sys.version_info[0] >= 3:
                    # Python 3.x
                    # Encode parameters
                    params = urllib.parse.urlencode(dict)
                else:
                    # Python 2.x
                    # Encode parameters
                    params = urllib.urlencode(dict)
                params = params.encode('utf-8')

                # POST the request - Get job info
                requestURL = urllib2.Request(portalUrl + "/sharing/rest/content/users/" + portalAdminName + "/items/" + exportItemId + "/status",params)
                response = urllib2.urlopen(requestURL)
                # Python version check
                if sys.version_info[0] >= 3:
                    # Python 3.x
                    # Read json response
                    responseJSON = json.loads(response.read().decode('utf8'))
                else:
                    # Python 2.x
                    # Read json response
                    responseJSON = json.loads(response.read())
                jobStatus = responseJSON.get('status')

                # While the request is still processing or if it has already completed
                while (jobStatus.lower() == "processing"):
                    # Pause every 10 seconds
                    time.sleep(10)

                    requestURL = urllib2.Request(portalUrl + "/sharing/rest/content/users/" + portalAdminName + "/items/" + exportItemId + "/status",params)
                    # POST the request - Get job info
                    response = urllib2.urlopen(requestURL)
                    # Python version check
                    if sys.version_info[0] >= 3:
                        # Python 3.x
                        # Read json response
                        responseJSON = json.loads(response.read().decode('utf8'))
                    else:
                        # Python 2.x
                        # Read json response
                        responseJSON = json.loads(response.read())

                    jobStatus = responseJSON['status']

                    # Once processing has finished
                    if (jobStatus.lower() == "completed"):
                        printMessage("Downloading data zip file to temporary directory...","info")

                        dataURL = portalUrl + "/sharing/rest/content/items/" + exportItemId + "/data" + "?token=" + token

                        # Download the file from the link
                        file = urllib2.urlopen(dataURL)

                        # Download in chunks
                        fileChunk = 16 * 1024
                        with open(os.path.join(tempFolder, "Data.zip"), 'wb') as output:
                            while True:
                                chunk = file.read(fileChunk)
                                if not chunk:
                                    break
                                # Write chunk to output file
                                output.write(chunk)
                        output.close()

                        # Setup parameters for deleting the item that was created
                        dict = {}
                        dict['f'] = 'json'
                        dict['token'] = token
                        # Python version check
                        if sys.version_info[0] >= 3:
                            # Python 3.x
                            # Encode parameters
                            params = urllib.parse.urlencode(dict)
                        else:
                            # Python 2.x
                            # Encode parameters
                            params = urllib.urlencode(dict)
                        params = params.encode('utf-8')

                        # Set the request to export
                        requestURL = urllib2.Request(portalUrl + "/sharing/rest/content/users/" + portalAdminName + "/items/" + exportItemId + "/delete",params)

                        # POST the request - Deletes the item that was created
                        response = urllib2.urlopen(requestURL)
                        # Python version check
                        if sys.version_info[0] >= 3:
                            # Python 3.x
                            # Read json response
                            responseJSON = json.loads(response.read().decode('utf8'))
                        else:
                            # Python 2.x
                            # Read json response
                            responseJSON = json.loads(response.read())

                        # Unzip the file to the scratch folder
                        printMessage("Extracting zip file...","info")
                        zip = zipfile.ZipFile(os.path.join(tempFolder, "Data.zip"), mode="r")
                        zip.extractall(tempFolder)

                        # If file geodatabase
                        if (outputFormat.lower() == "file geodatabase"):
                            # Get the newest unzipped database from the scratch folder
                            database = max(glob.iglob(tempFolder + r"\*.gdb"), key=os.path.getmtime)

                            # Assign the geodatabase workspace and load in the datasets to the lists
                            arcpy.env.workspace = database
                            featureclassList = arcpy.ListFeatureClasses()
                            tableList = arcpy.ListTables()

                            printMessage("Copying dataset(s) into geodatabase " + workspace + "...","info")
                            # Load the feature classes into the geodatabase if at least one is in the geodatabase provided
                            if (len(featureclassList) > 0):
                                # Loop through the feature classes
                                for eachFeatureclass in featureclassList:
                                   # Create a Describe object from the dataset
                                   describeDataset = arcpy.Describe(eachFeatureclass)

                                   # If update mode is then copy, otherwise delete and appending records
                                   if (updateMode == "New"):
                                       # Copy feature class into geodatabase using the same dataset name
                                       arcpy.CopyFeatures_management(eachFeatureclass, os.path.join(workspace, describeDataset.name), "", "0", "0", "0")
                                   else:
                                        # If dataset exists in geodatabase, delete features and load in new data
                                        if arcpy.Exists(os.path.join(workspace, eachFeatureclass)):
                                            arcpy.DeleteFeatures_management(os.path.join(workspace, eachFeatureclass))
                                            arcpy.Append_management(os.path.join(arcpy.env.workspace, eachFeatureclass), os.path.join(workspace, eachFeatureclass), "NO_TEST", "", "")
                                        else:
                                            # Log warning
                                            printMessage("Warning: " + os.path.join(workspace, eachFeatureclass) + " does not exist and won't be updated","warning")
                                            # Logging
                                            if (enableLogging == "true"):
                                                logger.warning(os.path.join(workspace, eachFeatureclass) + " does not exist and won't be updated")

                            if (len(tableList) > 0):
                                # Loop through of the tables
                                for eachTable in tableList:
                                   # Create a Describe object from the dataset
                                   describeDataset = arcpy.Describe(eachTable)
                                   # If update mode is then copy, otherwise delete and appending records
                                   if (updateMode == "New"):
                                       # Copy feature class into geodatabase using the same dataset name
                                       arcpy.TableSelect_analysis(eachTable, os.path.join(workspace, describeDataset.name), "")
                                   else:
                                        # If dataset exists in geodatabase, delete features and load in new data
                                        if arcpy.Exists(os.path.join(workspace, eachTable)):
                                            arcpy.DeleteRows_management(os.path.join(workspace, eachTable))
                                            arcpy.Append_management(os.path.join(arcpy.env.workspace, eachTable), os.path.join(workspace, eachTable), "NO_TEST", "", "")
                                        else:
                                            # Log warning
                                            printMessage("Warning: " + os.path.join(workspace, eachTable) + " does not exist and won't be updated","warning")
                                            # Logging
                                            if (enableLogging == "true"):
                                                logger.warning(os.path.join(workspace, eachTable) + " does not exist and won't be updated")
                        # CSV file
                        elif (outputFormat.lower() == "csv"):
                            # Get the newest csv file from the scratch folder
                            csvFile = max(glob.iglob(tempFolder + r"\*.csv"), key=os.path.getmtime)
                            csvFileSplit = os.path.split(csvFile)

                            printMessage("Copying CSV into folder " + workspace + "...","info")
                            shutil.copyfile(csvFile, os.path.join(workspace, csvFileSplit[-1]))
                        # If shapefile
                        else:
                            # If ArcGIS desktop installed
                            if (arcgisDesktop == "true"):
                                # Get the newest unzipped shapefile from the scratch folder
                                shapefile = max(glob.iglob(tempFolder + r"\*.shp"), key=os.path.getmtime)

                                printMessage("Copying dataset(s) into geodatabase " + workspace + "...","info")

                                # Create a Describe object from the dataset
                                describeDataset = arcpy.Describe(shapefile)
                                # Copy shapefile into geodatabase using the same dataset name
                                arcpy.CopyFeatures_management(shapefile, os.path.join(workspace, (describeDataset.name).replace(".shp", "").replace(" ", "_")), "", "0", "0", "0")
                            # ArcGIS desktop not installed
                            else:
                                # Unzip the file direct to the workspace folder
                                zip = zipfile.ZipFile(os.path.join(tempFolder, "Data.zip"), mode="r")
                                zip.extractall(workspace)
        # --------------------------------------- End of code --------------------------------------- #
        # If called from gp tool return the arcpy parameter
        if __name__ == '__main__':
            # Return the output if there is any
            if output:
                # If ArcGIS desktop installed
                if (arcgisDesktop == "true"):
                    arcpy.SetParameterAsText(1, output)
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
    # If arcpy error
    except arcpy.ExecuteError:
        # Build and show the error message
        errorMessage = arcpy.GetMessages(2)
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
    # If python error
    except Exception as e:
        errorMessage = ""
        # Build and show the error message
        # If many arguments
        if (e.args):
            for i in range(len(e.args)):
                if (i == 0):
                    # Python version check
                    if sys.version_info[0] >= 3:
                        # Python 3.x
                        errorMessage = str(e.args[i]).encode('utf-8').decode('utf-8')
                    else:
                        # Python 2.x
                        errorMessage = unicode(e.args[i]).encode('utf-8')
                else:
                    # Python version check
                    if sys.version_info[0] >= 3:
                        # Python 3.x
                        errorMessage = errorMessage + " " + str(e.args[i]).encode('utf-8').decode('utf-8')
                    else:
                        # Python 2.x
                        errorMessage = errorMessage + " " + unicode(e.args[i]).encode('utf-8')
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


# Start of get token function
def generateToken(username, password, portalUrl):
    # Python version check
    if sys.version_info[0] >= 3:
        # Python 3.x
        # Encode parameters
        parameters = urllib.parse.urlencode({'username' : username,
                        'password' : password,
                        'client' : 'referer',
                        'referer': portalUrl,
                        'expiration': 60,
                        'f' : 'json'})
    else:
        # Python 2.x
        # Encode parameters
        parameters = urllib.urlencode({'username' : username,
                        'password' : password,
                        'client' : 'referer',
                        'referer': portalUrl,
                        'expiration': 60,
                        'f' : 'json'})
    parameters = parameters.encode('utf-8')
    try:
        urllib2.urlopen(portalUrl + '/sharing/rest/generateToken?',parameters)
        response = urllib2.urlopen(portalUrl + '/sharing/rest/generateToken?',parameters)
    except Exception as e:
        printMessage( 'Unable to open the url %s/sharing/rest/generateToken' % (portalUrl),'error')
        printMessage(e,'error')

    # Python version check
    if sys.version_info[0] >= 3:
        # Python 3.x
        # Read json response
        responseJSON = json.loads(response.read().decode('utf8'))
    else:
        # Python 2.x
        # Read json response
        responseJSON = json.loads(response.read())

    # Log results
    if "error" in responseJSON:
        errDict = responseJSON['error']
        if int(errDict['code'])==498:
            message = 'Token Expired. Getting new token... '
            token = generateToken(username,password, portalUrl)
        else:
            message =  'Error Code: %s \n Message: %s' % (errDict['code'],
            errDict['message'])
            printMessage(message,'error')
    token = responseJSON.get('token')
    return token
# End of get token function


# Start of print message function
def printMessage(message,type):
    # If ArcGIS desktop installed
    if (arcgisDesktop == "true"):
        if (type.lower() == "warning"):
            arcpy.AddWarning(message)
        elif (type.lower() == "error"):
            arcpy.AddError(message)
        else:
            arcpy.AddMessage(message)
    # ArcGIS desktop not installed
    else:
        print(message)
# End of print message function


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
    # Test to see if ArcGIS desktop installed
    if ((os.path.basename(sys.executable).lower() == "arcgispro.exe") or (os.path.basename(sys.executable).lower() == "arcmap.exe") or (os.path.basename(sys.executable).lower() == "arccatalog.exe")):
        arcgisDesktop = "true"

    # If ArcGIS desktop installed
    if (arcgisDesktop == "true"):
        argv = tuple(arcpy.GetParameterAsText(i)
            for i in range(arcpy.GetArgumentCount()))
    # ArcGIS desktop not installed
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
