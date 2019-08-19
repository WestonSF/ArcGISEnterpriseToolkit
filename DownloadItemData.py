#-------------------------------------------------------------
# Name:                 Download Item Data
# Purpose:              Downloads data as a JSON file from a specified item in portal or downloads
#                       all items in a portal site and zips these up.
# Author:               Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:         09/04/2019
# Last Updated:         19/08/2019
# ArcGIS Version:       ArcGIS API for Python 1.5.1+
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
import csv
import shutil

# Set global variables
# Logging
enableLogging = "true" # Use within code to print and log messages - printMessage("xxx","info"), printMessage("xxx","warning"), printMessage("xxx","error")
logFile = os.path.join(os.path.dirname(__file__), "DownloadItemData.log") # e.g. os.path.join(os.path.dirname(__file__), "Example.log")
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


# Start of main function
def mainFunction(portalURL,portalUser,portalPassword,itemID,downloadLocation): # Add parameters sent to the script here e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)
    try:
        # --------------------------------------- Start of code --------------------------------------- #
        # Connect to GIS portal
        printMessage("Connecting to GIS Portal - " + portalURL + "...","info")
        gisPortal = arcgis.GIS(url=portalURL, username=portalUser, password=portalPassword, verify_cert=False)

        # If item ID is provided
        if (itemID):
            item = gisPortal.content.get(itemID)
            items = []
            items.append(item)
        # Else get all items
        else:
            # Query all items in the portal
            items = gisPortal.content.search(query="",max_items=10000)

            # Create a new folder if it does not exist already
            if not os.path.exists(os.path.join(downloadLocation,"AGSBackup-" + time.strftime("%Y%m%d"))):
                os.makedirs(os.path.join(downloadLocation,"AGSBackup-" + time.strftime("%Y%m%d")))
            downloadLocation = os.path.join(downloadLocation,"AGSBackup-" + time.strftime("%Y%m%d"))

        # For each item
        for item in items:
            # If item is a feature service
            if (item.type.lower() == "feature service"):
                # If a hosted service
                if "Hosted Service" in item.typeKeywords:
                    printMessage("Exporting data for feature service - " + item.id + " (Title - " + item.title + ")...","info")
                    fgdbItem = item.export(item.title, "File Geodatabase")
                    printMessage("Downloading data...","info")
                    result = fgdbItem.download(downloadLocation)
                    fgdbItem.delete()
                else:
                    # Download the JSON data
                    printMessage("Downloading data from item - " + item.id + " (Title - " + item.title + ")...","info")         
                    result = item.download(downloadLocation)                    
            elif (item.type.lower() == "code attachment"):
                printMessage("Not downloading data for code attachment - " + item.id + " (Title - " + item.title + ")...","warning")
                result = None
            else:
                # Download the JSON data
                printMessage("Downloading data from item - " + item.id + " (Title - " + item.title + ")...","info")         
                result = item.download(downloadLocation)

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
                printMessage("There was an error downloading the data for item " + item.id,"error")      
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
