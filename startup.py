'''
startup functions for thm makevideos script
'''
import logging
import pathlib
import time
logger = logging.getLogger(__name__)

def verify_already_running(kwargs):
    '''
    returns True if logs/makevideos.lock exists
    '''
    if kwargs.config.lockfile.is_file():
        logger.error("ingest.py may already be running")
        print("Ensure that ingest.py isn't already running")
        print("This error may be caused by improper shutdown of ingest.py")
        print("Check the most recent log file located at:")
        print(kwargs.config.logs_path)
        print("If ingest.py isn't already running, you can re-run it now as normal")
        return True
    else:
        logger.info("creating lock file %s", str(kwargs.config.lockfile))
        kwargs.config.lockfile.touch()
        return False

def verify_file_copying(kwargs):
    '''
    checks if something is copying into the raw capture dir

    does so by renaming the file to a temporary filename, then naming back
    on Windows, files can only be used by 1 IO process at a time
    so, if a file is copying, renaming raises OSError, script tries again 120seconds later
    '''
    logging.info("verifying that no files are being copied into raw_captures")
    for file in kwargs.config.raw_captures.iterdir():
        if file.is_file():
            while True:
                try:
                    _tmp_file = str(kwargs.config.raw_captures) + file + "_"
                    tmp_file = pathlib.Path(_tmp_file)
                    file.rename(tmp_file)
                    tmp_file.rename(file)
                    time.sleep(0.05)
                    break
                except OSError:
                    time.sleep(120)
    return True

def verify_raw_captures(kwargs):
    '''
    checks that there are raw captures in the folder we specified
    '''
    logger.info("verifying there are raw captures to be processed")
    raw_captures = []
    if kwargs.input:
        for accession in kwargs.input:
            accession_path = kwargs.config.raw_captures / accession
            raw_captures = [path for path in accession_path.glob('*.*') \
                if not any(part.startswith('.') for part in path.parts) \
                and not any(part.startswith('Thumbs.db') for part in path.parts)]
    else:
        accession_path = kwargs.config.raw_captures
        raw_captures = [path for path in accession_path.glob('**/*.*') \
            if not any(part.startswith('.') for part in path.parts) \
            and not any(part.startswith('Thumbs.db') for part in path.parts)]
    if not raw_captures:
        logger.error("no files found in raw captures folder: %s", str(accession_path))
        return False
    else:
        logger.info("raw captures ok")
        return raw_captures

def verify_config_filepaths(kwargs):
    '''
    checks that files defined in config file exist
    '''
    logger.info("verifying watermark and timecode font files exist")
    if not kwargs.config.watermark_white.is_file():
        logger.error("The white-watermark file cannot be found." \
            "Please put the white watermark file at %s", str(kwargs.config.watermark_white))
        return False
    if not kwargs.config.timecode_fontfile.is_file():
        logger.error("The fontfile cannot be found." \
            "Please put the fontfile at %s", str(kwargs.config.timecode_fontfile))
        return False
    logger.info("timecode font and watermark file verification ok")
    return True

def verify_config_drivepaths(kwargs):
    '''
    verifies that drives defined in config file exist
    '''
    logger.info("verifying that drives are mounted")
    if not kwargs.config.sunnas.is_dir():
        logger.error("The video script is unable to run because SUNNAS is not mounted as expected. " \
        "Please mount SUNNAS on XCluster at %s", str(kwargs.config.sunnas))
        return False
    if not kwargs.config.sunnascopyto.is_dir():
        logger.error("The video script is unable to run because the 'copy to' folder on Sunnas cannot be found." \
        "Please mount SUNNAS on XCluster and ensure this directory exists ", str(kwargs.config.sunnascopyto))
        return False
    if not kwargs.config.xendata.is_dir():
        logger.error("The video script is unable to run because Xendata is not mounted as expected. " \
        "Please mount Xendata on XCluster at ", str(kwargs.config.xendata))
        return False
    if not kwargs.config.xendatacopyto.is_dir():
        logger.error("The video script is unable to run because \
            the 'copy to' folder on Xendata cannot be found." \
            "Please mount Xendata on XCluster and ensure this directory exists %s", \
            str(kwargs.config.xendatacopyto))
        return False
    logger.info("drives mounted ok")
    return True

def verify_filemaker_records(kwargs):
    '''
    verifies that filemaker record exists for each accession
    '''
    for dirs,subdirs,files in os.walk(rawCaptures):
        for s in subdirs:
            output = subprocess.Popen(["python","fm-stuff.py","-qExist","-id",s],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out,err = output.communicate()
            if not out:
                msg = "The video script is unable to run because there is not an accession record for " + s + " in FileMaker"
                subprocess.call(["python","send-email.py","-txt",msg,'-att',logfile])
                log(logfile,msg)
                sys.exit()
