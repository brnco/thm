'''
startup functions for thm makevideos script
'''
from makevideos import log

def verify_raw_captures(kwargs):
    '''
    checks that there are raw captures in the folder we specified
    '''
    log(kwargs.log,"verifying there are raw captures to be processed")
    raw_captures = [path for path in kwargs.config.raw_captures.glob('**/*') \
            if not any(part.startswith('.') for part in path.parts) \
            and not any(part.startswith('Thumbs.db') for part in path.parts)]
    if not raw_captures:
        log(kwargs.log,"ERROR: no files found in raw captures folder")
        return False
    else:
        log(kwargs.log,"raw captures ok")
        return raw_captures

def verify_config_filepaths(kwargs):
    '''
    checks that files defined in config file exist
    '''
    log(kwargs.log,"verifying that there are files in raw_captures directory")
    if not kwargs.config.watermark_white.is_file():
        msg = "The white-watermark file cannot be found." \
            "Please put the white watermark file at " + str(kwargs.config.watermark_white)
        #with open(logfile,"r+") as l:
            #thelog = l.read()
        #subprocess.call(["python","send-email.py","-txt",msg + "\n" + str(thelog)])
        log(kwargs.log,msg)
        return False
    if not kwargs.config.timecode_fontfile.is_file():
        msg = "The fontfile cannot be found." \
            "Please put the fontfile at " + str(kwargs.config.timecode_fontfile)
            #with open(logfile,"r+") as l:
                #thelog = l.read()
            #subprocess.call(["python","send-email.py","-txt",msg + "\n" + str(thelog)])
        log(kwargs.log,msg)
        return False
    log(kwargs.log,"file verification ok")
    return True

def verify_config_drivepaths(kwargs):
    '''
    verifies that drives defined in config file exist
    '''
    log(kwargs.log,"verifying that drives are mounted")
    if not kwargs.config.sunnas.is_dir():
        msg = "The video script is unable to run because SUNNAS is not mounted as expected." \
        "Please mount SUNNAS on XCluster at " + str(kwargs.config.sunnas)
        #with open(logfile,"r+") as l:
            #thelog = l.read()
        #subprocess.call(["python","send-email.py","-txt",msg + "\n" + str(thelog)])
        log(kwargs.log,msg)
        return False
    if not kwargs.config.sunnascopyto.is_dir():
        msg = "The video script is unable to run because the 'copy to' folder on Sunnas cannot be found." \
        "Please mount SUNNAS on XCluster and ensure this directory exists " + str(kwargs.config.sunnascopyto)
        #with open(logfile,"r+") as l:
            #thelog = l.read()
        #subprocess.call(["python","send-email.py","-txt",msg + "\n" + str(thelog)])
        log(kwargs.log,msg)
        return False
    if not kwargs.config.xendata.is_dir():
        msg = "The video script is unable to run because Xendata is not mounted as expected." \
        "Please mount Xendata on XCluster at " + str(kwargs.config.xendata)
        #with open(logfile,"r+") as l:
            #thelog = l.read()
        #subprocess.call(["python","send-email.py","-txt",msg + "\n" + str(thelog)])
        log(kwargs.log,msg)
        return False
    if not kwargs.config.xendatacopyto.is_dir():
        msg = "The video script is unable to run because the 'copy to' folder on Xendata cannot be found." \
        "Please mount Xendata on XCluster and ensure this directory exists " + str(kwargs.config.xendatacopyto)
        #with open(logfile,"r+") as l:
            #thelog = l.read()
        #subprocess.call(["python","send-email.py","-txt",msg + "\n" + str(thelog)])
        log(kwargs.log,msg)
        return False
    log(kwargs.log,"drives mounted ok")
    return True 

def verify_not_copying_now(kwargs):
    '''
    verifies that nothing is being copied right now
    '''
    #check that nothing is being copied currently
    donezo = False
    while donezo is False:
        fs = walk(rawCaptures)
        #print fs
        time.sleep(240)
        fsagain = walk(rawCaptures)
        #print fsagain
        donezo = compare(fs, fsagain)
        #print donezo

def verify_filemaker_records(kwargs):
    '''
    verifies that filemaker record exists for each accession
    '''
    #check that a filemaker record exists for each accession
    for dirs,subdirs,files in os.walk(rawCaptures):
        for s in subdirs:
            output = subprocess.Popen(["python","fm-stuff.py","-qExist","-id",s],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out,err = output.communicate()
            if not out:
                msg = "The video script is unable to run because there is not an accession record for " + s + " in FileMaker"
                subprocess.call(["python","send-email.py","-txt",msg,'-att',logfile])
                log(logfile,msg)
                sys.exit()
