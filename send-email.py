#this script sends an email
#the txt of the message is provided by makevideos.py

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from random import randint
import SimpleHTTPServer
import argparse
import ConfigParser

#grab args fromCLI
parser = argparse.ArgumentParser(description="sends an email")
parser.add_argument("-txt","--text",dest="txt",help="the message body") #remember to enclose in quotes
args = vars(parser.parse_args())
txt = args['txt'] #this is the message body

scriptRepo = os.path.dirname(os.path.abspath(__file__))
config = ConfigParser.ConfigParser()
config.read(os.path.join(scriptRepo,"video-post-process-config.txt"))
#the following need to be added to the config file
to = config.get('email','recipientlist') #comma delimited list of email addresses for recipients MUST BE A LIST NOT JUST 1
senderaddy = config.get('email','senderaddress') #email address of sender
senderpwd = config.get('email','senderpwd') #pwd for email acct of sender
emailserver = config.get('email','server') #the server and port for the sender, e.g. smtp.gmail.com:587
#emailport = config.get('email','port')

commaspace = ', ' #helpful later
msg = MIMEMultipart() #init the message

msg = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (senderaddy, ", ".join(to), "makevideos script error", txt)
	
s = smtplib.SMTP(emailserver)
s.starttls()
s.login(senderaddy,senderpwd)
s.sendmail(senderaddy, to, msg)
s.quit

