#-------------------------------------------------------------
# Name:                 Create Vector Tile Package
# Purpose:              Creates a vector tile package from and an ArcGIS Pro map file (.mapx)
#                       and uploads this to a portal site.
#                       NOTE: The data included in the vector tile package will be only data included
#                       in the display extent of the map file.
# Author:               Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:         2/10/2018
# Last Updated:         8/10/2018
# ArcGIS Version:       ArcGIS Pro (ArcPy) 2.2+
# Python Version:       3.6.5+ (Anaconda Distribution)
#--------------------------------

# Import main modules
import os
import sys
import logging
import smtplib
# Import ArcGIS modules
useArcPy = "true"
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
enableLogging = "false" # Use within code to print and log messages - printMessage("xxx","info"), printMessage("xxx","warning"), printMessage("xxx","error")
logFile = os.path.join(os.path.dirname(__file__), "CreateVectorTilePackage.log") # e.g. os.path.join(os.path.dirname(__file__), "Example.log")
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
def mainFunction(mapFile,tileSchemeFile,localOutputLocation,portalURL,portalUser,portalPassword,vectorTilePackageID,title,description,tags): # Add parameters sent to the script here e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)
    try:
        # --------------------------------------- Start of code --------------------------------------- #
        printMessage("Creating vector tile package - " + localOutputLocation + "...","info")
        arcpy.CreateVectorTilePackage_management(mapFile, # Map file
                                                 localOutputLocation, # Output vector tile package
                                                 "EXISTING", # Service type - ONLINE or EXISTING 
                                                 tileSchemeFile, # Tile scheme file
                                                 "INDEXED", # Tile structure - INDEXED or FLAT
                                                 18489297.737236, # Minimim cached scale
                                                 70.5310735, # Maximum cached scale
                                                 "", # Indexed polygons
                                                 description, # Summary
                                                 tags) # Tags

        # If uploading to portal
        if (portalURL and portalUser and portalPassword and title and description and tags):
            # Connect to GIS portal
            printMessage("Connecting to GIS Portal - " + portalURL + "...","info")
            gisPortal = arcgis.GIS(url=portalURL, username=portalUser, password=portalPassword, verify_cert=False)
        
            # If ID provided
            if (vectorTilePackageID):
                printMessage("Updating existing vector tile package in portal - " + vectorTilePackageID,"info")

                # Get the portal item
                userContentItem = gisPortal.content.get(vectorTilePackageID)
                # Update the vtpk in portal
                userContentItem.update(None,localOutputLocation)
            else:
                printMessage("Uploading vector tile package to portal...","info")

                # Get all items for the user
                user = gisPortal.users.get(portalUser)
                userItems = user.items()
                itemExists = False
                # For each item
                for userItem in userItems:
                    # If item already exists
                    if (title.lower() == userItem.title.lower()):
                        printMessage("Vector tile package already exists in portal - " + userItem.id + "...", "info")

                        # Get the portal item
                        userContentItem = gisPortal.content.get(userItem.id)
                        printMessage("Updating existing vector tile package...", "info")
                        # Update the vtpk in portal
                        userContentItem.update(None,localOutputLocation)
                        itemExists = True

                # If item doesn't exist in portal
                if (itemExists == False):
                    # Upload the vtpk to portal
                    item = gisPortal.content.add({"title":title},localOutputLocation)
                    printMessage("Vector Tile Package uploaded - " + item.id + "...", "info")
                    # Publish the item as a service
                    item.publish()


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
