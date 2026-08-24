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
import util
logger = logging.getLogger(__name__)


def get_files_for_ingest(kwvars):
    '''
    parses hm_interviews and special_collections directories
    gets files to work on
    '''
    ingests = util.d({})
    if kwvars.input:
        '''
        ingest one or more single accessions
        could be either HM interview(s) or special collection(s)
        '''
        for accession in kwvars.input:
            files_to_process = []
            spec_coll_dir = kwvars.config.special_colls_dir / accession
            hm_intv_dir = kwvars.config.hm_interviews_dir / accession
            if spec_coll_dir.is_dir():
                '''
                parse special collections directory for files
                '''
                if not kwvars.special_collections:
                    logger.error(f"accession directory {spec_coll_dir} found but --special_collections flag not specified")
                    logger.error("please use the --special_collections flag when running this script to process this accession")
                    raise RuntimeError("missing input option --special_collections")
                lockfile = detect_lockfile(spec_coll_dir)
                if lockfile:
                    continue
                files_to_process = detect_files_at_path(spec_coll_dir, kwvars)
                return {accession: files_to_process}
            elif hm_intv_dir.is_dir() and kwvars.special_collections:
                logger.error(f"--special_collections flag provided for accession {accession}"
                            + " however accession directory exists in hm_interviews folder {hm_intv_dir}")
                logger.error("Please move the accession directory to special collections folder"
                            + " or remove --special_collections flag")
                raise RuntimeError("Input options incompatible with accession folder location")
            elif hm_intv_dir.is_dir():
                '''
                parse hm interviews directory for files
                '''
                lockfile = detect_lockfile(hm_intv_dir, True)
                if lockfile:
                    continue
                files_to_process = detect_files_at_path(hm_intv_dir, kwvars)
                return {accession: files_to_process}
            else:
                logger.error("accession folder does not exist at either expected location:")
                logger.error(f"{spec_coll_dir}")
                logger.error(f"{hm_intv_dir}")
                raise RuntimeError("could not find accession directory location")
        if not files_to_process:
            raise RuntimeError(f"Accession folder could not be found or is processing already")
    else:
        if kwvars.special_collections:
            '''
            ok go through special collections directory from config
            '''
            accessions_path = kwvars.config.special_colls_dir
        else:
            '''
            go through the hm_interviews directory from config
            '''
            accessions_path = kwvars.config.hm_interviews_dir
        '''
        return list of files to work on
        from the first accession found without a lockfile
        '''
        accessions = [x for x in accessions_path.iterdir() if x.is_dir()]
        logger.debug(accessions)
        if not accessions:
            logger.warning(f"Accessions directory {accessions_path} is empty")
            exit()
        for accession in accessions:
            files_to_process = []
            lockfile = [path for path in accession.glob('processing.lock')]
            if lockfile:
                continue
            files_to_process = detect_files_at_path(accession, kwvars)
            return {accession.stem: files_to_process}
        if not files_to_process:
            logger.warning("All accessions are being processed")
            exit()


def detect_lockfile(dir_path, give_warning=False):
    '''
    detects lockfile at path
    displays warning if we think the user expects there not to be a lockfile there
    '''
    lockfile = [path for path in dir_path.glob('processing.lock')]
    if lockfile:
        if give_warning:
            logger.warning(f"processing.lock file found in {dir_path}")
            logger.warning(f"accesison {dir_path.stem} is already being processed, "
            + "or did not complete its last processing attempt.")
            logger.warning("please check the directory and other terminal windows")
        return True
    return False


def detect_files_at_path(accession_path, kwvars):
    '''
    actually detects if there's files to be processed in a given accession directory
    '''
    raw_captures = [path for path in accession_path.glob('*.*') \
        if not any(part.startswith('.') for part in path.parts) \
        and not any(part.startswith('Thumbs.db') for part in path.parts) \
        and not any(part.startswith('$') for part in path.parts) \
        and path.suffix in kwvars.config.filetypes.input]
    return raw_captures


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
        logger.debug(f"testing file: {file}")
        try:
            real_file = file
            tmp_file = pathlib.Path(str(file) + "_")
            file.rename(tmp_file)
            time.sleep(1)
            tmp_file.rename(real_file)
        except OSError:
            return False
    return True


def verify_incoming_dirs_exist(kwvars):
    '''
    verifies that the directories containing incoming footage
    as defined int he config files video-post-processing-config.txt
    exists
    '''
    if not kwvars.config.hm_interviews_dir.is_dir() \
        or not kwvars.config.special_colls_dir.is_dir():
        return False
    return True


def verify_config_drivepaths(kwvars):
    '''
    verifies that drives defined in config file exist
    '''
    logger.info("verifying that drives are mounted")
    if not kwvars.config.thmfs01.is_dir():
        logger.error("The video script is unable to run because thm-fs01 is not mounted as expected. " \
        "Please mount thm-fs01 at %s", str(kwvars.config.sunnas))
        return False
    if not kwvars.config.thmfs01copyto.is_dir():
        logger.error("The video script is unable to run because the 'copy to' folder on thm-fs01 cannot be found." \
        "Please mount thm-fs01 and ensure this directory exists ", str(kwvars.config.sunnascopyto))
        return False
    if not kwvars.config.xendata.is_dir():
        logger.error("The video script is unable to run because Xendata is not mounted as expected. " \
        "Please mount Xendata at %s", str(kwvars.config.xendata))
        return False
    if not kwvars.config.xendatacopyto.is_dir():
        logger.error("The video script is unable to run because \
            the 'copy to' folder on Xendata cannot be found." \
            "Please mount Xendata and ensure this directory exists %s", \
            str(kwvars.config.xendatacopyto))
        return False
    logger.info("drives mounted ok")
    return True
