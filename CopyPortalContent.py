#-------------------------------------------------------------
# Name:                 Copy Portal Content
# Purpose:              Copy all content from one portal/ArcGIS Online site
#                       to another portal/ArcGIS Online site.
# Author:               Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:         17/07/2018
# Last Updated:         17/07/2018
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
import tempfile
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
enableLogging = "false" # Use within code to print and log messages - printMessage("xxx","info"), printMessage("xxx","warning"), printMessage("xxx","error")
logFile = os.path.join(os.path.dirname(__file__), "CopyPortalContent.log") # e.g. os.path.join(os.path.dirname(__file__), "Example.log")
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
def mainFunction(sourcePortalURL,sourcePortalUser,sourcePortalPassword,targetPortalURL,targetPortalUser,targetPortalPassword): # Add parameters sent to the script here e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)
    try:
        # --------------------------------------- Start of code --------------------------------------- #
        # Connect to GIS portals
        printMessage("Connecting to Source GIS Portal - " + sourcePortalURL + "...","info")
        sourceGISPortal = arcgis.GIS(url=sourcePortalURL, username=sourcePortalUser, password=sourcePortalPassword)
        printMessage("Connecting to Target GIS Portal - " + targetPortalURL + "...","info")
        targetGISPortal = arcgis.GIS(url=targetPortalURL, username=targetPortalUser, password=targetPortalPassword)

        # Create a list of system accounts that should not be modified
        systemUsers = ['system_publisher', 'esri_nav', 'esri_livingatlas','esri_boundaries', 'esri_demographics']

        # Get a list of all users
        sourceUsers = sourceGISPortal.users.search(query=None, sort_field='username', sort_order='asc', max_users=1000000, outside_org=False)
        targetUsers = targetGISPortal.users.search(query=None, sort_field='username', sort_order='asc', max_users=1000000, outside_org=False)

        # Create a list of groups to not copy
        groupsIgnore = []
        # Get a list of all groups
        sourceGroups = sourceGISPortal.groups.search(query='', sort_field='title', sort_order='asc', max_groups=1000000, outside_org=False, categories=None)
        targetGroups = targetGISPortal.groups.search(query='', sort_field='title', sort_order='asc', max_groups=1000000, outside_org=False, categories=None)

        # Check if groups are already present in target portal
        for sourceGroup in sourceGroups:
            for targetGroup in targetGroups:
                if sourceGroup.title == targetGroup.title:
                    printMessage("Group already exists in target portal - " + targetGroup.title + "...","warning")
                    groupsIgnore.append(targetGroup.title)

        # Copy all the groups from source to target
        for group in sourceGroups:
            # If not ignoring the group
            if group.title not in groupsIgnore:
                if not group.owner in systemUsers:
                    printMessage("Copying group - " + group.title + "...","info")
                    newGroup = copyGroup(sourceGISPortal,targetGISPortal,targetPortalUser,targetUsers,group)
                    printMessage("New group created - " + newGroup.groupid + "...","info")

        # Get a list of all items in the portal
        sourceItems = {}
        for user in sourceUsers:
            num_items = 0
            num_folders = 0
            user_content = user.items()

            # Get item ids from root folder first
            for item in user_content:
                num_items += 1
                sourceItems[item.itemid] = item

            # Get item ids from each of the folders next
            folders = user.folders
            for folder in folders:
                num_folders += 1
                folder_items = user.items(folder=folder['title'])
                for item in folder_items:
                    num_items += 1
                    sourceItems[item.itemid] = item

        # Get the group sharing information for each of the items
        for group in sourceGroups:
            # Iterate through each item shared to the source group
            for group_item in group.content():
                # Get the item
                item = sourceItems[group_item.itemid]
                if item is not None:
                    if not 'groups'in item:
                        item['groups'] = []

                    # Assign the target portal's corresponding group's name
                    item['groups'].append(group['title'])

        # Copy all content from source to target
        sourceTargetItems  = {}
        for key in sourceItems.keys():
            sourceItem = sourceItems[key]

            printMessage("Copying {} \tfor\t {}".format(sourceItem.title, sourceItem.owner),"info")
            # Copy the item
            targetItem = copyItem(targetGISPortal, sourceItem)
            if targetItem:
                sourceTargetItems[key] = targetItem.itemid
            else:
                sourceTargetItems[key] = None
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
            sendEmail(errorMessage)
# End of main function


# Start of copy group function
def copyGroup(sourceGISPortal,targetGISPortal,targetPortalUser,targetUsers,group):
    with tempfile.TemporaryDirectory() as tempDirectory:
        groupCopyProperties = ['title','description','tags','snippet','phone','access','isInvitationOnly']
        targetGroup = {}

        # For each property
        for property in groupCopyProperties:
            targetGroup[property] = group[property]

        # Setup the access for the group
        if targetGroup['access'] == 'org' and targetGISPortal.properties['portalMode'] == 'singletenant':
            targetGroup['access'] = 'public'
        elif targetGroup['access'] == 'public'\
             and sourceGISPortal.properties['portalMode'] == 'singletenant'\
             and targetGISPortal.properties['portalMode'] == 'multitenant'\
             and 'id' in targetGISPortal.properties: # is org
            targetGroup['access'] = 'org'

        # Handle the thumbnail (if one exists)
        thumbnailFile = None
        if 'thumbnail' in group:
            targetGroup['thumbnail'] = group.download_thumbnail(tempDirectory)

        # Create the group in the target portal
        copiedGroup = targetGISPortal.groups.create_from_dict(targetGroup)

        # Create a list of user names in the target portal
        users = []
        for targetUser in targetUsers:
            users.append(targetUser.username)

        # Reassign all groups to correct owners, add users, and find shared items
        members = group.get_members()
        if not members['owner'] == targetPortalUser:
            # If the member exists in the target portal
            if members['owner'] in users:
                # Change owner of group
                copiedGroup.reassign_to(members['owner'])
        if members['users']:
            # For each member
            for member in members['users']:
                # If the member exists in the target portal
                if member in users:
                    copiedGroup.add_users(member)

        return copiedGroup
# End of copy group function


# Start of copy item function
def copyItem(targetGISPortal, sourceItem):
    with tempfile.TemporaryDirectory() as tempDirectory:
        textBasedItemTypes = frozenset(['Web Map', 'Feature Service', 'Map Service','Web Scene',
                                   'Image Service', 'Feature Collection',
                                   'Feature Collection Template',
                                   'Web Mapping Application', 'Mobile Application',
                                   'Symbol Set', 'Color Set',
                                   'Windows Viewer Configuration'])
        fileBasedItemTypes = frozenset(['File Geodatabase','CSV', 'Image', 'KML', 'Locator Package',
                                  'Map Document', 'Shapefile', 'Microsoft Word', 'PDF',
                                  'Microsoft Powerpoint', 'Microsoft Excel', 'Layer Package',
                                  'Mobile Map Package', 'Geoprocessing Package', 'Scene Package',
                                  'Tile Package', 'Vector Tile Package'])
        itemCopyProperties = ['title', 'type', 'typeKeywords', 'description', 'tags','snippet', 'extent', 'spatialReference', 'name','accessInformation', 'licenseInfo', 'culture', 'url']
        itemProperties = {}
        for property in itemCopyProperties:
            itemProperties[property] = sourceItem[property]

        dataFile = None

        if sourceItem.type in textBasedItemTypes:
            # If its a text-based item, then read the text and add it to the request.
            text = sourceItem.get_data(False)
            itemProperties['text'] = text

        elif sourceItem.type in fileBasedItemTypes:
            # Download data and add to the request as a file
            dataFile = sourceItem.download(tempDirectory)

        thumbnail_file = sourceItem.download_thumbnail(tempDirectory)
        metadata_file = sourceItem.download_metadata(tempDirectory)

        # Find items owner
        sourceItem_owner = source.users.search(sourceItem.owner)[0]

        # Find items folder
        item_folder_titles = [f['title'] for f in sourceItem_owner.folders
                              if f['id'] == sourceItem.ownerFolder]
        folder_name = None
        if len(item_folder_titles) > 0:
            folder_name = item_folder_titles[0]

        # If folder does not exist for target user, create it
        if folder_name:
            target_user = targetGISPortal.users.search(sourceItem.owner)[0]
            target_user_folders = [f['title'] for f in target_user.folders
                                   if f['title'] == folder_name]
            if len(target_user_folders) == 0:
                # Create the folder
                targetGISPortal.content.create_folder(folder_name, sourceItem.owner)

        # Add the item to the target portal, assign owner and folder
        copiedItem = targetGISPortal.content.add(itemProperties, dataFile, thumbnail_file,
                                         metadata_file, sourceItem.owner, folder_name)

        # Set sharing information
        share_everyone = sourceItem.access == 'public'
        share_org = sourceItem.access in ['org', 'public']
        share_groups = []
        if sourceItem.access == 'shared':
            share_groups = sourceItem.groups

        copiedItem.share(share_everyone, share_org, share_groups)

        return copiedItem
# End of copy item function


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
