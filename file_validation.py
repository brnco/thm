#!/usr/bin/env python
'''
handles mediaconch file validation
'''
import pathlib
import util
import subprocess
import logging

logger = logging.getLogger(__name__)

def detect_valid_mp4(file, kwargs):
    '''
    uses MediaConch to detect if mp4 contains pcm audio
    '''
    mediaconch_mp4_pcm_policy = kwargs.config.mediaconch.mp4_pcm_policy
    logger.info("checking for non-standard PCM audio in MP4")
    logger.info("%s",file)
    logger.debug("mediaconch -p " + str(mediaconch_mp4_pcm_policy) + " " + str(file))
    output = subprocess.run(['mediaconch','-p',str(mediaconch_mp4_pcm_policy),str(file)],capture_output=True,shell=True)
    logger.debug(output.stdout.decode('utf-8'))
    stdout = output.stdout.decode('utf-8')
    if stdout.startswith('pass'):
        logger.info("invalid MP4 detected with PCM audio")
        logger.info("this file or set of files will be re-wrapped in MOV")
        return False
    else:
        logger.info("MP4 contains valid audio codec")
        return True

def load_mediaconch_policies(kwargs):
    '''
    loads policies from folder in config file
    '''
    true_parent = pathlib.Path(kwargs.config.mediaconch.input_policies)
    childs = true_parent.glob('**/*.xml')
    mediaconch_policies = []
    for child in childs:
        if str(child.parent) == str(true_parent):
            mediaconch_policies.append(child)
    if not mediaconch_policies:
        logger.error("no mediaconch policies found at config path: %s", str(kwargs.config.mediaconch.input_policies))
        return False
    return mediaconch_policies

def validate_output(accession, files, kwargs):
    '''
    validates output video files

    logger.info("validating derivative files for %s", accession)
    for file in files:
        if "_pres" in str(file) and not kwargs.input_validation:
            #skip _pres file if input file(s) not validated
            #continue in this context means (move to next iteration of containing loop)
            continue
        if file.suffix == ".mov":
            logger.info("validating %s against mediaconch policy %s", (file, kwargs.accession_mediaconch_policy))
        #elif file.suffix == "_mezz.mxf":
            #logger.info("validating %s against mediaconch policy %s", (file, kwargs.config.mediaconch.mezz_policy))
        elif file.suffix == ".mp4":
            if "_wm" in str(file):
                logger.info("validating %s against mediaconch policy %s", (file, kwargs.config.mediaconch.wm_policy))
            elif "_tc" in str(file):
                logger.info("validating %s against mediaconch policy %s", (file, kwargs.config.mediaconch.tc_policy))
        elif file.suffix == ".mpg":
            logger.info("validating %s against mediaconch policy %s", (file, kwargs.config.mediaconch.dvd_policy))
    '''
    logger.debug("output validation not yet implemented")
    return True

def validate_input(accession, files, kwargs):
    '''
    validates input video files
    '''
    if not kwargs.accession_mediaconch_policy or kwargs.reset_mediaconch_policy == True:
        mediaconch_policies = load_mediaconch_policies(kwargs)
    else:
        mediaconch_policies = [kwargs.accession_mediaconch_policy]
    policy_passes = []
    for file in files:
        for policy in mediaconch_policies:
            logger.info("testing %s against %s", str(file), str(policy))
            output = subprocess.run(['mediaconch','-p',policy,file], capture_output=True)
            logger.debug(output.returncode)
            logger.debug(output.stdout.decode('utf-8'))
            logger.debug(output.stderr.decode('utf-8'))
            if not output.stdout.decode('utf-8').startswith("pass"):
                logger.debug("mediaconch input validation failed for: %s", str(file))
                logger.debug(str(output.stdout.decode('utf-8')))
            else:
                logger.info("mediaconch input validation passed for: %s", str(file))
                logger.debug(str(output.stdout.decode('utf-8')))
                policy_passes.append(file)
                break
    if len(policy_passes) == len(files):
        logger.info("mediaconch input validation passed for %s", str(accession))
        logger.info("input/output mediaconch policy is %s", str(policy))
        accession_mediaconch_policy = policy
        return accession_mediaconch_policy
    else:
        logger.error("mediaconch unable to pass input validation for accession %s", str(accession))
        return False

def main():
    '''
    do the thing
    '''

if __name__ == "__main__":
    main()
