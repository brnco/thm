#sends email from thm gmail acct



def send_email(message,attachment_path,debug=False):
    '''
    sends an email using config from video-post-processing
    '''
    import os
    import smtplib
    from email.message import EmailMessage
    import configparser
    '''
    init config info from video-post-processing-config
    '''
    scriptRepo = os.path.dirname(os.path.abspath(__file__))
    config = configparser.ConfigParser()
    config.read(os.path.join(scriptRepo,"video-post-process-config.txt"))
    if not debug:
        _recipients = config.get('email','recipientlist')
    else:
        _recipients = config.get('email','debug')
    sender_email = config.get('email','senderaddress')
    sender_pwd = config.get('email','senderpwd')
    email_server = config.get('email','server')
    recipients = _recipients.split(",")
    '''
    init the email message
    '''
    msg = EmailMessage()
    msg['From'] = sender_email
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = "ingest notification"

    '''
    attachment handler
    '''
    if attachment_path:
        if os.path.getsize(attachment_path) < 9961472:
            with open(attachment_path,"rb") as file:
                    file_data = file.read()
            msg.add_attachment(file_data, maintype='text', subtype='plain')
        else:
            txt = txt + "\n\n attachment too big to include. Find it at the following location: " + attachment
    '''
    actually send the email

    with smtplib.SMTP(email_server) as server:
        server.send_message(msg)
    '''
    smtp = smtplib.SMTP(email_server)
    smtp.starttls()
    print(sender_email)
    print(sender_pwd)
    smtp.login(sender_email,sender_pwd)
    smtp.sendmail(sender_email,recipients,msg.as_string())
    smtp.close()
