#!/usr/bin/env python
'''
handles aspects of starting script
verifies drives are attached
verifies there's not a file copying into D:/incoming
'''
import logging
import pathlib
import time
import traceback
import sys
logger = logging.getLogger(__name__)

def verify_venv():
    '''
    verifies if the virutal environment (venv) has been enabled
    '''
    logger.debug("sys.base_prefix = %s", sys.base_prefix)
    logger.debug("sys.prefix = %s", sys.prefix)
    is_venv = sys.base_prefix != sys.prefix
    if not is_venv:
        logger.error("the script could not be started because the virtual environment has not been enabled")
        logger.info("to enable the virtual environment for this script," \
            + " run the below code in cmd.exe, while in the code repo directory (C:\\Users\\archadmin\\code\\thm)")
        logger.info("venv/Scripts/activate.bat")
        return False
    return True

def verify_file_copying(kwargs):
    '''
    checks if something is copying into the raw capture dir

    does so by renaming the file to a temporary filename, then naming back
    on Windows, files can only be used by 1 IO process at a time
    so, if a file is copying, renaming raises OSError, script tries again 120seconds later
    '''
    logging.info("verifying that no files are being copied into raw_captures")
    for file in kwargs.config.raw_captures.glob('**/*'):
        if file.is_file() and not file.name.startswith(".") \
        and not file.name.startswith('$') and not "Thumbs.db" in file.name:
            logger.debug("testing file %s", file)
            while True:
                try:
                    real_file = file
                    tmp_file = pathlib.Path(str(file) + "_")
                    file.rename(tmp_file)
                    time.sleep(1)
                    tmp_file.rename(real_file)
                    break
                except OSError:
                    logger.debug(traceback.format_exc())
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
