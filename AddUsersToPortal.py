#-------------------------------------------------------------
# Name:       Add Users to Portal
# Purpose:    Imports a list of users provided in a CSV file to Portal for ArcGIS, assigning to roles and setting default password. Can be
#             built-in or enteprise users.    
# Author:     Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:    16/05/2014
# Last Updated:    29/08/2014
# Copyright:   (c) Eagle Technology
# ArcGIS Version:   Portal for ArcGIS 10.2+
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
import json
import Queue

# Enable data to be overwritten
arcpy.env.overwriteOutput = True

# Set global variables
enableLogging = "false" # Use logger.info("Example..."), logger.warning("Example..."), logger.error("Example...")
logFile = "" # os.path.join(os.path.dirname(__file__), "Example.log")
sendErrorEmail = "false"
emailTo = ""
emailUser = ""
emailPassword = ""
emailSubject = ""
emailMessage = ""
output = None

# Start of main function
def mainFunction(portalUrl, portalAdminName, portalAdminPassword, typeUsers, usersCSVFile): # Get parameters from ArcGIS Desktop tool by seperating by comma e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)  
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
        
        arcpy.AddMessage("Adding users to Portal...")

        # Get user data from file and load users to be added into queue
        usersData = getUserDataFromFile(usersCSVFile,typeUsers)

        # Go through each of the users in the queue
        usersLeftInQueue = True
        while usersLeftInQueue:
            try:
                # Set the provider names
                if typeUsers.lower() == "enterprise":
                    provider = "webadaptor"
                else:
                    provider = "arcgis"
                    
                userDict = usersData.get(False)
                userDict['f'] = 'json'
                userDict['token'] = token
                userDict['provider'] = provider
                params = urllib.urlencode(userDict)

                request = urllib2.Request(portalUrl + "/portaladmin/security/users/createUser?",params)

                # POST the create request
                response = urllib2.urlopen(request).read()
                responseJSON = json.loads(response)

                # Log results
                if responseJSON.has_key('error'):
                    errDict = responseJSON['error']
                    if int(errDict['code'])==498:
                        message = "Token Expired. Getting new token... Username: " + userDict['username'] + " will be added later..."
                        token = generateToken(username,password, portalUrl)
                        usersData.put(userDict)
                    else:
                        message =  "Error Code: %s \n Message: %s" % (errDict['code'],
                        errDict['message'])
                    arcpy.AddError(message)
                else:
                    # Success
                    if responseJSON.has_key('status'):
                        resultStatus = responseJSON['status']
                        arcpy.AddMessage("User: %s account created" % (userDict['username']))
            except Queue.Empty:
                  usersLeftInQueue = False
        
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


# Start of function that loads all the user data in the input text file into a Python Queue.
def getUserDataFromFile(inUserFile,provider):
    usersQ = Queue.Queue()
    keyParams = ['username', 'password', 'email', 'fullname','role','description']

    inFileHandle = open(inUserFile, 'r')
    userCount = 0
    arcpy.AddMessage("Processing input users file at " + inUserFile + "...")
    entryCount = 1;
    for line in inFileHandle.readlines():
        userParams = line.split('|')
        userParamDict = {}
        # If enterprise users
        if provider.lower() == "enterprise":
            if len(userParams) == 5:
                for i in range (0,5):
                    userParamDict[keyParams[0]] = userParams[0]  # Enterprise login
                    userParamDict[keyParams[1]] = ""
                    userParamDict[keyParams[2]] = userParams[1]  # Email
                    userParamDict[keyParams[3]] = userParams[2]  # Name
                    userParamDict[keyParams[4]] = userParams[3]  # Role
                    userParamDict[keyParams[5]] = userParams[4].replace('\n','')  # Description
                usersQ.put (userParamDict)
                userCount = userCount + 1
            else:
                arcpy.AddError("The format for entry %s is invalid.  The format for enterprise accounts should be <login>|<email address>|<name>|<role>|<description>. \n "% (entryCount))
        # If built-in users
        elif provider.lower() == "built-in":
            if len(userParams) == 6:
                for i in range (0,6):
                    userParamDict[keyParams[0]] = userParams[0]  # Account
                    userParamDict[keyParams[1]] = userParams[1]  # Password
                    userParamDict[keyParams[2]] = userParams[2]  # Email
                    userParamDict[keyParams[3]] = userParams[3]  # Name
                    userParamDict[keyParams[4]] = userParams[4]  # Role
                    userParamDict[keyParams[5]] = userParams[5].replace('\n','')  # Description
                usersQ.put (userParamDict)
                userCount = userCount + 1
            else:
                arcpy.AddError("The format for entry %s is invalid.  The format for built-in portal accounts should be <account>|<password>|<email address>|<name>|<role>|<description>.  \n "% (entryCount))
        # Else provider not specified correctly
        else:
            arcpy.AddError("The provider is incorrect...")
        entryCount = entryCount +1
        # If the user roles are not specified correctly
        if not ((userParamDict[keyParams[4]].lower()== "org_user") or (userParamDict[keyParams[4]].lower()=="org_publisher") or (userParamDict[keyParams[4]].lower()== "org_admin")):
            arcpy.AddError("The value for the user role %s in users text file is invalid.  Accepted values are org_user or org_publisher or org_admin. " % (userParamDict[keyParams[4]]))
    inFileHandle.close()
    # Create users and report results
    arcpy.AddMessage("Total members to be added: " + str(userCount))

    return usersQ
# End of function that loads all the user data in the input text file into a Python Queue.


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
        response = urllib.urlopen(portalUrl + '/sharing/rest/generateToken?',
                              parameters).read()
    except Exception as e:
        arcpy.AddError( 'Unable to open the url %s/sharing/rest/generateToken' % (portalUrl))
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
    mainFunction(*argv)
    
