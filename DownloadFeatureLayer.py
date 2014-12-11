#-------------------------------------------------------------
# Name:       Download Feature Layer
# Purpose:    Downloads a feature layer from an ArcGIS Online site and optionally updates an existing dataset. Two update options:
#             Existing Mode - Will delete and append records, so field names need to be the same.
#             New Mode - Copies data over. Requires no locks on geodatabase datasets being overwritten.      
# Author:     Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:    30/09/2014
# Last Updated:    11/12/2014
# Copyright:   (c) Eagle Technology
# ArcGIS Version:   ArcGIS Online
# Python Version:   2.7
#--------------------------------

# Import modules
import os
import sys
import logging
import smtplib
import arcpy
import urllib
import urllib2
import zipfile
import json
import glob

# Enable data to be overwritten
arcpy.env.overwriteOutput = True

# Set global variables
enableLogging = "false" # Use logger.info("Example..."), logger.warning("Example..."), logger.error("Example...")
logFile = os.path.join(os.path.dirname(__file__), "Logs\DownloadFeatureLayer.log") # os.path.join(os.path.dirname(__file__), "Example.log")
sendErrorEmail = "false"
emailTo = ""
emailUser = ""
emailPassword = ""
emailSubject = ""
emailMessage = ""
enableProxy = "false"
requestProtocol = "https" # http or https
proxyURL = ""
output = None

# Start of main function
def mainFunction(portalUrl, portalAdminName, portalAdminPassword, itemID, geodatabase, updateMode): # Get parameters from ArcGIS Desktop tool by seperating by comma e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)  
    try:
        # Logging
        if (enableLogging == "true"):
            # Setup logging
            logger, logMessage = setLogging(logFile)
            # Log start of process
            logger.info("Process started.")
            
        # --------------------------------------- Start of code --------------------------------------- #
    
        arcpy.AddMessage("Connecting to Portal - " + portalUrl + "...")
        # Generate token for portal
        token = generateToken(portalAdminName, portalAdminPassword, portalUrl)

        arcpy.AddMessage("Exporting feature layer to geodatabase. Item ID - " + itemID + "...")

        # Setup parameters for export   
        dict = {}
        dict['f'] = 'json'
        dict['token'] = token
        dict['itemId'] = itemID
        dict['exportFormat'] = "File Geodatabase"
        params = urllib.urlencode(dict)

        # Set the request to export
        request = urllib2.Request(portalUrl + "/sharing/rest/content/users/" + portalAdminName + "/export",params)

        # POST the request - Creates a new item in the ArcGIS online site
        response = urllib2.urlopen(request).read()
        responseJSON = json.loads(response)

        # Log results
        if responseJSON.has_key('error'):
            errDict = responseJSON['error']
            message =  "Error Code: %s \n Message: %s" % (errDict['code'],
            errDict['message'])
            arcpy.AddError(message)
        else:
            jobId = responseJSON['jobId']
            exportItemId = responseJSON['exportItemId']

            # Setup parameters for status check   
            dict = {}
            dict['f'] = 'json'
            dict['token'] = token
            dict['jobType'] = "export"
            dict['jobId'] = jobId
            params = urllib.urlencode(dict)

            # Set the request for status
            request = urllib2.Request(portalUrl + "/sharing/rest/content/users/" + portalAdminName + "/items/" + exportItemId + "/status",params)

            # POST the request - Get job info
            response = urllib2.urlopen(request).read()
            responseJSON = json.loads(response)
            jobStatus = responseJSON['status']
            
            # While the request is still processing
            while (jobStatus == "processing"):
                request = urllib2.Request(portalUrl + "/sharing/rest/content/users/" + portalAdminName + "/items/" + exportItemId + "/status",params)
                # POST the request - Get job info
                response = urllib2.urlopen(request).read()
                responseJSON = json.loads(response)
                jobStatus = responseJSON['status']
                
                # Once processing has finished
                if (jobStatus == "completed"):
                    arcpy.AddMessage("Downloading geodatabase...")

                    dataURL = portalUrl + "/sharing/rest/content/items/" + exportItemId + "/data" + "?token=" + token
                    
                    # Download the file from the link
                    file = urllib2.urlopen(dataURL)

                    # Download in chunks
                    fileChunk = 16 * 1024
                    with open(os.path.join(arcpy.env.scratchFolder, "Data.zip"), 'wb') as output:
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
                    params = urllib.urlencode(dict)

                    # Set the request to export
                    request = urllib2.Request(portalUrl + "/sharing/rest/content/users/" + portalAdminName + "/items/" + exportItemId + "/delete",params)

                    # POST the request - Deletes the item that was created
                    response = urllib2.urlopen(request).read()
                    responseJSON = json.loads(response)
        
                    # Unzip the file to the scratch folder
                    arcpy.AddMessage("Extracting zip file...")  
                    zip = zipfile.ZipFile(os.path.join(arcpy.env.scratchFolder, "Data.zip"), mode="r")
                    zip.extractall(arcpy.env.scratchFolder)

                    # Get the newest unzipped database from the scratch folder
                    database = max(glob.iglob(arcpy.env.scratchFolder + r"\*.gdb"), key=os.path.getmtime)

                    # Assign the geodatabase workspace and load in the datasets to the lists
                    arcpy.env.workspace = database
                    featureclassList = arcpy.ListFeatureClasses()
                    tableList = arcpy.ListTables()

                    arcpy.AddMessage("Copying dataset(s) into geodatabase...")        
                    # Load the feature classes into the geodatabase if at least one is in the geodatabase provided
                    if (len(featureclassList) > 0):        
                        # Loop through the feature classes
                        for eachFeatureclass in featureclassList:
                           # Create a Describe object from the dataset
                           describeDataset = arcpy.Describe(eachFeatureclass)

                           # If update mode is then copy, otherwise delete and appending records                
                           if (updateMode == "New"):
                               # Copy feature class into geodatabase using the same dataset name
                               arcpy.AddMessage(os.path.join(geodatabase, describeDataset.name))
                               arcpy.CopyFeatures_management(eachFeatureclass, os.path.join(geodatabase, describeDataset.name), "", "0", "0", "0")
                           else:
                                # If dataset exists in geodatabase, delete features and load in new data
                                if arcpy.Exists(os.path.join(geodatabase, eachFeatureclass)):
                                    arcpy.DeleteFeatures_management(os.path.join(geodatabase, eachFeatureclass))
                                    arcpy.Append_management(os.path.join(arcpy.env.workspace, eachFeatureclass), os.path.join(geodatabase, eachFeatureclass), "NO_TEST", "", "")
                                else:
                                    # Log warning
                                    arcpy.AddWarning("Warning: " + os.path.join(geodatabase, eachFeatureclass) + " does not exist and won't be updated")
                                    # Logging
                                    if (enableLogging == "true"):
                                        logger.warning(os.path.join(geodatabase, eachFeatureclass) + " does not exist and won't be updated")
                                        
                    if (len(tableList) > 0):    
                        # Loop through of the tables
                        for eachTable in tableList:
                           # Create a Describe object from the dataset
                           describeDataset = arcpy.Describe(eachTable)
                           # If update mode is then copy, otherwise delete and appending records                
                           if (updateMode == "New"):               
                               # Copy feature class into geodatabase using the same dataset name
                               arcpy.TableSelect_analysis(eachTable, os.path.join(geodatabase, describeDataset.name), "")
                           else:
                                # If dataset exists in geodatabase, delete features and load in new data
                                if arcpy.Exists(os.path.join(geodatabase, eachTable)):
                                    arcpy.DeleteRows_management(os.path.join(geodatabase, eachTable))
                                    arcpy.Append_management(os.path.join(arcpy.env.workspace, eachTable), os.path.join(geodatabase, eachTable), "NO_TEST", "", "")
                                else:
                                    # Log warning
                                    arcpy.AddWarning("Warning: " + os.path.join(geodatabase, eachTable) + " does not exist and won't be updated")
                                    # Logging
                                    if (enableLogging == "true"):
                                        logger.warning(os.path.join(geodatabase, eachTable) + " does not exist and won't be updated")
        
        # --------------------------------------- End of code --------------------------------------- #  
            
        # If called from gp tool return the arcpy parameter   
        if __name__ == '__main__':
            # Return the output if there is any
            if output:
                arcpy.SetParameterAsText(1, output)
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
            logging.FileHandler.close(logMessage)
            logger.removeHandler(logMessage)
        pass
    # If arcpy error
    except arcpy.ExecuteError:           
        # Build and show the error message
        errorMessage = arcpy.GetMessages(2)   
        arcpy.AddError(errorMessage)           
        # Logging
        if (enableLogging == "true"):
            # Log error          
            logger.error(errorMessage)                 
            # Remove file handler and close log file
            logging.FileHandler.close(logMessage)
            logger.removeHandler(logMessage)
        if (sendErrorEmail == "true"):
            # Send email
            sendEmail(errorMessage)
    # If python error
    except Exception as e:
        errorMessage = ""
        # Build and show the error message
        for i in range(len(e.args)):
            if (i == 0):
                errorMessage = unicode(e.args[i]).encode('utf-8')
            else:
                errorMessage = errorMessage + " " + unicode(e.args[i]).encode('utf-8')
        arcpy.AddError(errorMessage)              
        # Logging
        if (enableLogging == "true"):
            # Log error            
            logger.error(errorMessage)               
            # Remove file handler and close log file
            logging.FileHandler.close(logMessage)
            logger.removeHandler(logMessage)
        if (sendErrorEmail == "true"):
            # Send email
            sendEmail(errorMessage)            
# End of main function


# Start of get token function
def generateToken(username, password, portalUrl):
    '''Retrieves a token to be used with API requests.'''
    parameters = urllib.urlencode({'username' : username,
                                   'password' : password,
                                   'client' : 'referer',
                                   'referer': portalUrl,
                                   'expiration': 60,
                                   'f' : 'json'})
    try:
        response = urllib2.urlopen(portalUrl + '/sharing/rest/generateToken?',
                              parameters).read()     
    except Exception as e:
        arcpy.AddError( 'Unable to open the url %s/sharing/rest/generateToken' % (portalUrl))
        arcpy.AddError(e)
    responseJSON =  json.loads(response.strip(' \t\n\r'))
    # Log results
    if responseJSON.has_key('error'):
        errDict = responseJSON['error']
        if int(errDict['code'])==498:
            message = 'Token Expired. Getting new token... '
            token = generateToken(username,password, portalUrl)
        else:
            message =  'Error Code: %s \n Message: %s' % (errDict['code'],
            errDict['message'])
            arcpy.AddError(message)
    token = responseJSON.get('token')
    return token
# End of get token function


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
    arcpy.AddMessage("Sending email...")
    # Server and port information
    smtpServer = smtplib.SMTP("smtp.gmail.com",587) 
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
    # Arguments are optional - If running from ArcGIS Desktop tool, parameters will be loaded into *argv
    argv = tuple(arcpy.GetParameterAsText(i)
        for i in range(arcpy.GetArgumentCount()))

    # Setup the use of a proxy for requests
    if (enableProxy == "true"):
        # Setup the proxy
        proxy = urllib2.ProxyHandler({requestProtocol : proxyURL})
        openURL = urllib2.build_opener(proxy)
        # Install the proxy
        urllib2.install_opener(openURL)
            
    mainFunction(*argv)
    
