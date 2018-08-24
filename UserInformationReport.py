#-------------------------------------------------------------
# Name:                 User Information Report
# Purpose:              Produces a number of reports (CSV format) for all users
#                       in the portal. Reports are:
#                       - Users that have not logged in over a year.
#                       - Groups a user is a member of.
#                       - Number/size of content a user owns.
# Author:               Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:         02/07/2018
# Last Updated:         16/08/2018
# ArcGIS Version:       ArcGIS API for Python 1.4.2+
# Python Version:       3.6.5+ (Anaconda 5.2+)
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
logFile = os.path.join(os.path.dirname(__file__), "UserInformationReport.log") # e.g. os.path.join(os.path.dirname(__file__), "Example.log")
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
def mainFunction(portalURL,portalUser,portalPassword,inactiveUsersCSV,inactiveUsersID,userPermissionsCSV,userPermissionsID,userContentCSV,userContentID): # Add parameters sent to the script here e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)
    try:
        # --------------------------------------- Start of code --------------------------------------- #
        # Connect to GIS portal
        printMessage("Connecting to GIS Portal - " + portalURL + "...","info")
        gisPortal = arcgis.GIS(url=portalURL, username=portalUser, password=portalPassword, verify_cert=False)

        # Get a list of all users
        users = gisPortal.users.search(query=None, sort_field='username', sort_order='asc', max_users=1000000, outside_org=False)

        # Get a list of all groups
        groups = gisPortal.groups.search(query='', sort_field='title', sort_order='asc', max_groups=1000000, outside_org=False, categories=None)

        # Create inactive users report
        inactiveUsersReport(inactiveUsersCSV,users)
        # If portal ID provided
        if (inactiveUsersID):
            printMessage("Updating report in portal - " + inactiveUsersID + "...","info")
            # Get the portal item
            inactiveUsersItem = gisPortal.content.get(inactiveUsersID)
            # Update the CSV in portal
            inactiveUsersItem.update(None,inactiveUsersCSV)

        # Create user permissions report
        userPermissionsReport(userPermissionsCSV,users,groups)
        # If portal ID provided
        if (userPermissionsID):
            printMessage("Updating report in portal - " + userPermissionsID + "...","info")
            # Get the portal item
            userPermissionsItem = gisPortal.content.get(userPermissionsID)
            # Update the CSV in portal
            userPermissionsItem.update(None,userPermissionsCSV)

        # Create user content report
        userContentReport(userContentCSV,users)
        # If portal ID provided
        if (userContentID):
            printMessage("Updating report in portal - " + userContentID + "...","info")
            # Get the portal item
            userContentItem = gisPortal.content.get(userContentID)
            # Update the CSV in portal
            userContentItem.update(None,userContentCSV)

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


# Start of inactive users report function
def inactiveUsersReport(inactiveUsersCSV,users):
    printMessage("Creating inactive users report - " + inactiveUsersCSV + "...","info")

    # Create a CSV writer and setup header
    file = open(inactiveUsersCSV, 'w', newline='')
    writer = csv.writer(file, delimiter=",")

    # Add in header information for CSV
    fieldNames = ["Name","Email","Level","Role","Date Created","Last Login","Days Since Last Login"]
    writer.writerow(fieldNames)

    # For each user
    data = []
    for user in users:
        userData = []
        username = user.username
        fullName = user.fullName
        email = user.email
        level = user.level
        role = user.role
        # Get the date the account was created
        dateCreated = time.strftime("%d/%m/%Y %H:%M:%S",time.localtime(user.created/1000))
        # If user has last login
        if (user.lastLogin != -1):
            # Get the last login date and days since last active
            lastLogin = time.strftime("%d/%m/%Y %H:%M:%S",time.localtime(user.lastLogin/1000))
            daysSinceActive = int((time.time() - (user.lastLogin/1000))/86400)
        # User has not logged in
        else:
            # Get number of days since account was created
            daysSinceActive = int((time.time() - (user.created/1000))/86400)
            lastLogin = "Not logged in"

        # If last login was over a year ago or not logged in at all
        if (daysSinceActive > 365):
            # If not a system/general user
            if (username.lower() != "system_publisher") and (username.lower() != "esri_boundaries") and (username.lower() != "esri_demographics") and (username.lower() != "esri_livingatlas") and (username.lower() != "esri_nav"):
            # Add in user details to list
                userData.append(fullName)
                userData.append(email)
                userData.append(level)
                userData.append(role)
                userData.append(dateCreated)
                userData.append(lastLogin)
                userData.append(daysSinceActive)
                # Add to data list
                data.append(userData)

    # Sort data by column 7 (Days since last login)
    sortedData = sorted(data, key=lambda data: data[6], reverse=True)

    # Write data to csv
    for row in sortedData:
        writer.writerow(row)

    # Close file
    file.close()
# End of inactive users report function


# Start of user permissions report function
def userPermissionsReport(userPermissionsCSV,users,groups):
    printMessage("Creating user permissions report - " + userPermissionsCSV + "...","info")

    # Create a CSV writer and setup header
    file = open(userPermissionsCSV, 'w', newline='')
    writer = csv.writer(file, delimiter=",")

    # Add in header information for CSV
    fieldNames = ["Name","Email","Level","Role"]

    # For each group
    groupTitles = []
    for group in groups:
        # Add group name to header
        fieldNames.append(group.title)
        # Add group title to array
        groupTitles.append(group.title.lower())
    writer.writerow(fieldNames)

    # For each user
    data = []
    for user in users:
        userData = []
        username = user.username
        fullName = user.fullName
        email = user.email
        level = user.level
        role = user.role
        userGroups = user.groups
        userGroupTitles = []
        for userGroup in userGroups:
            # Add group title to array
            userGroupTitles.append(userGroup.title.lower())

        # If not a system/general user
        if (username.lower() != "system_publisher") and (username.lower() != "esri_boundaries") and (username.lower() != "esri_demographics") and (username.lower() != "esri_livingatlas") and (username.lower() != "esri_nav"):
            # Add in user details to list
            userData.append(fullName)
            userData.append(email)
            userData.append(level)
            userData.append(role)
            # For each group
            for groupTitle in groupTitles:
                # Add whether user is a member of the group
                if groupTitle in userGroupTitles:
                    userData.append("Yes")
                else:
                    userData.append("")
            # Add to data list
            data.append(userData)

    # Sort data by column 1 (name)
    sortedData = sorted(data, key=lambda data: data[0], reverse=False)

    # Write data to csv
    for row in sortedData:
        writer.writerow(row)

    # Close file
    file.close()
# End of user permissions report function


# Start of user content report function
def userContentReport(userContentCSV,users):
    printMessage("Creating user content report - " + userContentCSV + "...","info")

    # Create a CSV writer and setup header
    file = open(userContentCSV, 'w', newline='')
    writer = csv.writer(file, delimiter=",")

    # Add in header information for CSV
    fieldNames = ["Name","Email","Level","Role","Number of Items","Data Usage (MB)"]
    writer.writerow(fieldNames)

    # For each user
    data = []
    for user in users:
        userData = []
        username = user.username
        fullName = user.fullName
        email = user.email
        level = user.level
        role = user.role

        # If not a system/general user
        if (username.lower() != "system_publisher") and (username.lower() != "esri_boundaries") and (username.lower() != "esri_demographics") and (username.lower() != "esri_livingatlas") and (username.lower() != "esri_nav"):
            # Add in user details to list
            userData.append(fullName)
            userData.append(email)
            userData.append(level)
            userData.append(role)

            # Get the number of items owner by the user
            folders = user.folders
            items = user.items()
            # For each folder
            count = 0
            for folder in folders:
                # Get the items in the folder
                folderItems = user.items(folder = folders[count])
                # Add folder items to items
                items = items + folderItems
                count = count + 1

            # For each item
            dataUsage = 0
            for item in items:
                # Get the item size and add to total size
                dataUsage = dataUsage + item.size

            numberItems = str(len(items))
            userData.append(numberItems)
            # Append the size of data in MB rounded to two decimal places
            userData.append(round(dataUsage/(1024*1024),2))
            # Add to data list
            data.append(userData)

    # Sort data by column 6 (data usage)
    sortedData = sorted(data, key=lambda data: data[5], reverse=True)

    # Write data to csv
    for row in sortedData:
        writer.writerow(row)

    # Close file
    file.close()
# End of user content report function


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
