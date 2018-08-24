#-------------------------------------------------------------
# Name:       Import ArcGIS Server Users
# Purpose:    Imports a list of users provided in a CSV file to ArcGIS server, assigning to
#             roles and setting default password.     
# Author:     Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:    15/05/2014
# Last Updated:    15/05/2014
# Copyright:   (c) Eagle Technology
# ArcGIS Version:   10.1/10.2
# Python Version:   2.7
#--------------------------------

# Import modules and enable data to be overwritten
import os
import sys
import logging
import smtplib
import httplib
import json
import urllib
import urlparse
import arcpy

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
def mainFunction(agsServerSite,username,password,usersCSV): # Get parameters from ArcGIS Desktop tool by seperating by comma e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)  
    try:
        # Logging
        if (enableLogging == "true"):
            # Setup logging
            logger, logMessage = setLogging(logFile)
            # Log start of process
            logger.info("Process started.")
            
        # --------------------------------------- Start of code --------------------------------------- #     

        # Get the server site details
        protocol, serverName, serverPort, context = splitSiteURL(agsServerSite)

        # If any of the variables are blank
        if (serverName == None or serverPort == None or protocol == None or context == None):
            return -1

        # Add on slash to context if necessary
        if not context.endswith('/'):
            context += '/'

        # Add on admin to context if necessary   
        if not context.endswith('admin/'):
            context += 'admin/'

        # Get token
        token = getToken(username, password, serverName, serverPort, protocol)

        # If token received
        if (token != -1):
            csvFile = open(usersCSV,'r')

            # Dictionaries to store user and role information
            roles = {}
            users = {}   
            addUserRole = {}

            # Read the next line 
            csvLine = csvFile.readline()

            # Counter to get through the column header of the input file
            count = 0
            while csvLine:
                if count == 0:
                    # CSV header
                    pass
                # Otherwise for every other line
                else:
                    # Split the current line into list
                    csvLineSplit = csvLine.split(",")
                    
                    # Build the Dictionary to add the roles
                    roles[csvLineSplit[1]] = {csvLineSplit[2]:csvLineSplit[len(csvLineSplit) -1].rstrip()}
                   
                    # Add the user information to a dictionary
                    users["user" + str(count)] = {"username":csvLineSplit[0],"password":csvLineSplit[3],"fullname":csvLineSplit[5],"email":csvLineSplit[4],"description":csvLineSplit[-1].rstrip()}

                    # Store the user and role type in a dictionary
                    if addUserRole.has_key(csvLineSplit[1]):
                        addUserRole[csvLineSplit[1]] =  addUserRole[csvLineSplit[1]] + "," + csvLineSplit[0]
                    else:
                        addUserRole[csvLineSplit[1]] = csvLineSplit[0]

                # Prepare to move to the next line        
                csvLine = csvFile.readline()
                count +=1

            # Call functions to add users and roles
            addRoles(roles,token,serverName,serverPort)
            addUsers(users,token,serverName,serverPort)
            addUserToRoles(addUserRole,token,serverName,serverPort)
            
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
                errorMessage = str(e.args[i])
            else:
                errorMessage = errorMessage + " " + str(e.args[i])
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


# Start of Add roles to ArcGIS Server function
def addRoles(roleDict, token, serverName, serverPort):  
    for item in roleDict.keys():
        # Build the dictionary with the role name and description
        roleToAdd = {"rolename":item}

        # Load the response
        jsRole = json.dumps(roleToAdd)
        
        # URL for adding a role
        addroleURL = "/arcgis/admin/security/roles/add"
        params = urllib.urlencode({'token':token,'f':'json','Role':jsRole})
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

        # Build the connection to add the roles to the server
        httpRoleConn = httplib.HTTPConnection(serverName, serverPort)
        httpRoleConn.request("POST",addroleURL,params,headers)

        response = httpRoleConn.getresponse()
        if (response.status != 200):
            httpRoleConn.close()
            arcpy.AddError("Could not add role...")
            return
        else:
            data = response.read()
            
            # Check that data returned is not an error object
            if not assertJsonSuccess(data):          
                arcpy.AddError("Error when adding role. " + str(data))
                return
            else:
                arcpy.AddMessage("Added role successfully...")

        httpRoleConn.close()

        # Assign a privilege to the recently added role 
        assignAdminUrl = "/arcgis/admin/security/roles/assignPrivilege"
        params = urllib.urlencode({'token':token,'f':'json',"rolename":item, "privilege":roleDict[item].keys()[0]})
            
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

        # Build the connection to assign the privilege
        httpRoleAdminConn = httplib.HTTPConnection(serverName, serverPort)
        httpRoleAdminConn.request("POST",assignAdminUrl,params,headers)

        response = httpRoleAdminConn.getresponse()
        if (response.status != 200):
            httpRoleAdminConn.close()
            arcpy.AddError("Could not assign privilege to role.")
            return
        else:
            data = response.read()
            
            # Check that data returned is not an error object
            if not assertJsonSuccess(data):          
                arcpy.AddError("Error when assigning privileges to role. " + str(data))
                return
            else:
                arcpy.AddMessage("Assigned privileges to role successfully...")

        httpRoleAdminConn.close()
# End of Add roles to ArcGIS Server function


# Start of Add users to ArcGIS Server function
def addUsers(userDict,token, serverName, serverPort):
    for userAdd in userDict:
        jsUser = json.dumps(userDict[userAdd])
        
        # URL for adding a user
        addUserURL = "/arcgis/admin/security/users/add"
        params = urllib.urlencode({'token':token,'f':'json','user':jsUser})
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

        # Build the connection to add the users
        httpRoleConn = httplib.HTTPConnection(serverName, serverPort)
        httpRoleConn.request("POST",addUserURL,params,headers)

        httpRoleConn.close()
# End of Add roles to ArcGIS Server function


# Start of Add user to roles function
def addUserToRoles(userRoleDict,token, serverName, serverPort):
    for userRole in userRoleDict.keys():

        # Using the current role build the URL to assign the right users to the role
        addUserURL = "/arcgis/admin/security/roles/addUsersToRole"
        params = urllib.urlencode({'token':token,'f':'json',"rolename":userRole,"users":userRoleDict[userRole]})
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
    
        # Build the connection
        httpRoleConn = httplib.HTTPConnection(serverName, serverPort)
        httpRoleConn.request("POST",addUserURL,params,headers)

        response = httpRoleConn.getresponse()
        if (response.status != 200):
            httpRoleConn.close()
            arcpy.AddError("Could not add user to role...")
            return
        else:
            data = response.read()
            
            # Check that data returned is not an error object
            if not assertJsonSuccess(data):          
                arcpy.AddError("Error when adding user to role. " + str(data))
                return
            else:
                arcpy.AddMessage("Added user to role successfully...")
                    
        httpRoleConn.close()
# End of Add user to roles function

        
# Start of get token function
def getToken(username, password, serverName, serverPort, protocol):
    params = urllib.urlencode({'username': username.decode(sys.stdin.encoding or sys.getdefaultencoding()).encode('utf-8'), 'password': password.decode(sys.stdin.encoding or sys.getdefaultencoding()).encode('utf-8'),'client': 'referer','referer':'backuputility','f': 'json'})
           
    # Construct URL to get a token
    url = "/arcgis/tokens/generateToken"
        
    try:
        response, data = postToServer(serverName, serverPort, protocol, url, params)
    except:
        arcpy.AddError("Unable to connect to the ArcGIS Server site on " + serverName + ". Please check if the server is running.")
        # Log error
        if (logging == "true") or (sendErrorEmail == "true"):       
            loggingFunction(logFile,"error","Unable to connect to the ArcGIS Server site on " + serverName + ". Please check if the server is running.")
            sys.exit()
        return -1    
    # If there is an error getting the token
    if (response.status != 200):
        arcpy.AddError("Error while generating the token.")
        arcpy.AddError(str(data))
        # Log error
        if (logging == "true") or (sendErrorEmail == "true"):       
            loggingFunction(logFile,"error","Error while generating the token.")
            sys.exit()
        return -1
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error while generating the token. Please check if the server is running and ensure that the username/password provided are correct.")
        # Log error
        if (logging == "true") or (sendErrorEmail == "true"):       
            loggingFunction(logFile,"error","Error while generating the token. Please check if the server is running and ensure that the username/password provided are correct.")
            sys.exit()
        return -1
    # Token returned
    else:
        # Extract the token from it
        dataObject = json.loads(data)

        # Return the token if available
        if "error" in dataObject:
            arcpy.AddError("Error retrieving token.")
            # Log error
            if (logging == "true") or (sendErrorEmail == "true"):       
                loggingFunction(logFile,"error","Error retrieving token.")
                sys.exit()
            return -1        
        else:
            return dataObject['token']
# End of get token function


# Start of HTTP POST request to the server function
def postToServer(serverName, serverPort, protocol, url, params):
    # If on standard port
    if (serverPort == -1 and protocol == 'http'):
        serverPort = 80

    # If on secure port
    if (serverPort == -1 and protocol == 'https'):
        serverPort = 443
        
    if (protocol == 'http'):
        httpConn = httplib.HTTPConnection(serverName, int(serverPort))

    if (protocol == 'https'):
        httpConn = httplib.HTTPSConnection(serverName, int(serverPort))
        
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",'referer':'backuputility','referrer':'backuputility'}
     
    # URL encode the resource URL
    url = urllib.quote(url.encode('utf-8'))

    # Build the connection to add the roles to the server
    httpConn.request("POST", url, params, headers) 

    response = httpConn.getresponse()
    data = response.read()

    httpConn.close()

    # Return response
    return (response, data)
# End of HTTP POST request to the server function


# Start of split URL function 
def splitSiteURL(siteURL):
    try:
        serverName = ''
        serverPort = -1
        protocol = 'http'
        context = '/arcgis'
        # Split up the URL provided
        urllist = urlparse.urlsplit(siteURL)
        # Put the URL list into a dictionary
        d = urllist._asdict()

        # Get the server name and port
        serverNameAndPort = d['netloc'].split(":")

        # User did not enter the port number, so we return -1
        if (len(serverNameAndPort) == 1):
            serverName = serverNameAndPort[0]
        else:
            if (len(serverNameAndPort) == 2):
                serverName = serverNameAndPort[0]
                serverPort = serverNameAndPort[1]

        # Get protocol
        if (d['scheme'] is not ''):
            protocol = d['scheme']

        # Get path
        if (d['path'] is not '/' and d['path'] is not ''):
            context = d['path']

        # Return variables
        return protocol, serverName, serverPort, context  
    except:
        arcpy.AddError("The ArcGIS Server site URL should be in the format http(s)://<host>:<port>/arcgis")
        # Log error
        if (logging == "true") or (sendErrorEmail == "true"):       
            loggingFunction(logFile,"error","The ArcGIS Server site URL should be in the format http(s)://<host>:<port>/arcgis")
            sys.exit()
        return None, None, None, None
# End of split URL function


# Start of status check JSON object function
def assertJsonSuccess(data):
    obj = json.loads(data)
    if 'status' in obj and obj['status'] == "error":
        if ('messages' in obj):
            errMsgs = obj['messages']
            for errMsg in errMsgs:
                arcpy.AddError(errMsg)
                # Log error
                if (logging == "true") or (sendErrorEmail == "true"):       
                    loggingFunction(logFile,"error",errMsg)
            sys.exit()
        return False
    else:
        return True
# End of status check JSON object function


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
    
