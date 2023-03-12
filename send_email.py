#sends email from thm gmail acct

def format_log_for_email(log_path):
    '''
    formats the log file for email
    '''
    import re
    try:
        import pathlib
        import time
        lines = []
        _tmp_log = pathlib.Path(log_path)
        tmp_log = _tmp_log.parent / "email_log.txt"
        with open(log_path) as log_file:
            for line in log_file:
                match = ''
                match = re.match(r"\d{4}-\d{2}-\d{2}",line)
                if match:
                    if not "DEBUG:" in line:
                        lines.append(line)
        tmp_log.touch(exist_ok=True)
        time.sleep(1)
        with open(str(tmp_log),"w+") as tlog:
            for line in lines:
                tlog.write(line)
        return str(tmp_log)
    except Exception as e:
        print(e)
        return False

def send_email(subject,message,attachment_path,debug=False):
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
    msg['Subject'] = subject

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
    smtp.login(sender_email,sender_pwd)
    smtp.sendmail(sender_email,recipients,msg.as_string())
    smtp.close()
