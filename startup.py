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


def verify_file_copying(accession_to_process):
    '''
    checks if something is copying into the folder we're trying to process

    does so by renaming the file to a temporary filename, then naming back
    on Windows, files can only be used by 1 IO process at a time
    so, if a file is copying, renaming raises OSError
    returns False if that happens
    '''
    accession_number = next(iter(accession_to_process))
    accession_fullpath = accession_to_process[accession_number][0].parent
    logging.info(f"verifying that no files are being copied into accession dir {accession_fullpath}")
    for file in accession_to_process[accession_number]:
        logger.debug(f"testing {file}")
        try:
            real_file = file
            tmp_file = pathlib.Path(str(file) + "_")
            file.rename(tmp_file)
            time.sleep(1)
            tmp_file.rename(real_file)
        except OSError:
            return False
    return True


def verify_incoming_dirs_exist(kwargs):
    '''
    verifies that the directories containing incoming footage
    as defined int he config files video-post-processing-config.txt
    exists
    '''
    if not kwargs.config.hm_interviews_dir.is_dir() \
        or not kwargs.config.special_colls_dir.is_dir():
        return False
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
