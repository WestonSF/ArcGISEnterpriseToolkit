#-------------------------------------------------------------
# Name:                 Start or Stop Service
# Purpose:              Starts or stops a service or services in an
#                       ArcGIS Enterprise site.
# Author:               Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:         05/11/2018
# Last Updated:         05/11/2018
# ArcGIS Version:       ArcGIS API for Python 1.4.2+
# Python Version:       3.6.5+ (Anaconda Distribution)
#--------------------------------

# Import main modules
import os
import sys
import logging
import smtplib
import time
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

# Set global variables
# Logging
enableLogging = "true" # Use within code to print and log messages - printMessage("xxx","info"), printMessage("xxx","warning"), printMessage("xxx","error")
logFile = os.path.join(os.path.dirname(__file__), "StartStopService.log") # e.g. os.path.join(os.path.dirname(__file__), "Example.log")
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
def mainFunction(siteURL,adminUser,adminPassword,servicesFolder,serviceName,serviceAction): # Add parameters sent to the script here e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)
    try:
        # --------------------------------------- Start of code --------------------------------------- #
        # Connect to GIS site
        printMessage("Connecting to GIS site - " + siteURL + "...","info")
        gis = arcgis.GIS(url=siteURL, username=adminUser, password=adminPassword, verify_cert=False)

        # Get a list of servers in the site
        gisServers = gis.admin.servers.list()

        # If a service name is set
        if (serviceName):
            # Set GIS service found to false
            gisServiceFound = False
        else:
            # Set GIS service found to true
            gisServiceFound = True

        # For each server
        for gisServer in gisServers:
            # If a folder is set
            if (servicesFolder):
                # If the folder does not exist
                if servicesFolder not in gisServer.services.folders:
                    printMessage("Services folder does not exist: " + servicesFolder, "error")

            # For each service in the root directory
            for gisService in gisServer.services.list():
                # If no services folder set (Start/stop services in the root directory)
                if (servicesFolder is None) or (servicesFolder == ""):
                    # If no service name set (Start/stop all services)
                    if (serviceName is None) or (serviceName == ""):
                        # Function - Start or stop the service
                        startStopService(gisService, serviceAction)
                    # Service name set (Just start/stop that service)
                    else:
                        # If the service name and type is equal to the one specified
                        if (serviceName.lower() == gisService.properties.serviceName.lower() + "." + gisService.properties.type.lower()):
                            # Function - Start or stop the service
                            startStopService(gisService, serviceAction)
                            # Set GIS service found to true
                            gisServiceFound = True
            # For each folder
            for gisFolder in gisServer.services.folders:
                # If the services folder is equal to the one specified
                if (servicesFolder.lower() == gisFolder.lower()):
                    # For each service in the folder
                    for gisService in gisServer.services.list(folder=gisFolder):
                        # If no service name set (Start/stop all services)
                        if (serviceName is None) or (serviceName == ""):
                            # Function - Start or stop the service
                            startStopService(gisService, serviceAction)
                        # Service name set (Just start/stop that service)
                        else:
                            # If the service name and type is equal to the one specified
                            if (serviceName.lower() == gisService.properties.serviceName.lower() + "." + gisService.properties.type.lower()):
                                # Function - Start or stop the service
                                startStopService(gisService, serviceAction)
                                # Set GIS service found to true
                                gisServiceFound = True

        # If a service name was set but not found
        if (gisServiceFound == False):
            printMessage("Service does not exist: " + serviceName, "error")
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


# Start of start or stop service function
def startStopService(gisService,serviceAction):
    if (serviceAction.lower() == "start"):
        printMessage("Starting service: " + gisService.properties.serviceName + "." + gisService.properties.type + "...", "info")
        gisService.start()
        printMessage(gisService.properties.serviceName + "." + gisService.properties.type + " is now " + gisService.status["realTimeState"].lower() + "...","info")
    elif (serviceAction.lower() == "stop"):
        printMessage("Stopping service: " + gisService.properties.serviceName + "." + gisService.properties.type + "...", "info")
        gisService.stop()
        printMessage(gisService.properties.serviceName + "." + gisService.properties.type + " is now " + gisService.status["realTimeState"].lower() + "...","info")
    else:
        printMessage("Neither start or stop has been set in the parameters...", "warning")
        printMessage(gisService.properties.serviceName + "." + gisService.properties.type + " remains " + gisService.status["realTimeState"].lower() + "...","info")
# End of start or stop service function


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
