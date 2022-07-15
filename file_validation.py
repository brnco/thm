#!/usr/bin/env python
'''
handles mediaconch file validation
'''
import pathlib
import util
import subprocess
import logging

logger = logging.getLogger(__name__)

def load_mediaconch_policies(kwargs):
    '''
    loads policies from folder in config file
    '''
    true_parent = kwargs.config.mediaconchas
    childs = true_parent.glob('**/*.xml')
    mediaconch_policies = []
    for child in childs:
        if str(child.parent) == str(true_parent):
            mediaconch_policies.append(child)
    if not mediaconch_policies:
        logger.error("no mediaconch policies found at config path: %s", str(kwargs.config.mediaconchas))
        return False
    return mediaconch_policies

def validate_output(accession, files, kwargs):
    '''
    validates output video files
    '''
    logger.info("validating derivative files for %s", accession)
    for file in files:
        if file.endswith(".mov"):
            logger.info("validating %s against mediaconch policy %s", (file, kwargs.accession_mediaconch_policy))
        elif file.endswith("_mezz.mxf"):
            logger.info("validating %s against mediaconch policy %s", (file, kwargs.config.mezz_policy))
        elif file.endswith("_logo.mp4"):
            logger.info("validating %s against mediaconch policy %s", (file, kwargs.config.logo_policy))
        elif file.endswith("_burn.mp4"):
            logger.info("validating %s against mediaconch policy %s", (file, kwargs.config.burn_policy))
        elif file.endswith("_dvd.mpg"):
            logger.info("validating %s against mediaconch policy %s", (file, kwargs.config.dvd_policy))
    return True

def validate_input(accession, files, kwargs):
    '''
    validates input video files
    '''
    if not kwargs.accession_mediaconch_policy:
        mediaconch_policies = load_mediaconch_policies(kwargs)
    else:
        mediaconch_policies = [kwargs.accession_mediaconch_policy]
    policy_passes = []
    for policy in mediaconch_policies:
        for file in files:
            logger.info("testing %s against %s", str(file), str(policy))
            output = subprocess.run(['mediaconch','-p',policy,file], capture_output=True)
            logger.debug(output.returncode)
            logger.debug(output.stdout)
            logger.debug(output.stderr)
            if not str(output.stdout).startswith("pass"):
                logger.error("mediaconch input validation failed for: %s", str(file))
                logger.error(str(output.stdout))
                return False
            else:
                logger.info("mediaconch input validation passed for: %s", str(file))
                logs.append(str(output.stdout))
                policy_passes.append(file)
        if policy_passes:
            logger.info("mediaconch input validation passed for %s", str(accession))
            logger.info("input/output mediaconch policy is %s", str(policy))
            accession_mediaconch_policy = policy
            return accession_mediaconch_policy
        else:
            continue
    logger.error("mediaconch unable to pass input validation for accession %s", str(accession))
    return False

def main():
    '''
    do the thing
    '''

if __name__ == "__main__":
    main()
