#!/usr/bin/env python
'''
main script for ingesting materials for The HIstory Makers
'''
'''
import official python libraries
'''
import os
import sys
import subprocess
import glob
import re
import time
import logging
import random
import pathlib
import traceback
import operator
import argparse
import configparser

'''
import microservice scripts
(located in thm folder)
'''
import util
import transcodes
import filemaker_handler as fm
import file_validation
from send_email import send_email
import startup

'''
function definitions
'''
def get_files_for_ingest(kwargs):
    '''
    parses raw_captures directory for files to work on
    '''
    ingests = util.d({})
    if kwargs.input:
        for accession in kwargs.input:
            ingests[accession] = []
            accession_path = kwargs.config.raw_captures / accession
            raw_captures = [path for path in accession_path.glob('*.*') \
                    if not any(part.startswith('.') for part in path.parts) \
                    and not any(part.startswith('Thumbs.db') for part in path.parts)
                    and path.suffix in kwargs.config.filetypes.input]
            ingests[accession] = raw_captures
            for file in accession_path.iterdir():
                if not file.suffix in kwargs.config.filetypes.input:
                    logging.warning("the file " + str(file) + " does not have appropriate extension")
                    logging.warning("this file will not be processed")
    else:
        accession_path = kwargs.config.raw_captures
        raw_captures = [path for path in accession_path.glob('**/*.*') \
            if not any(part.startswith('.') for part in path.parts) \
            and not any(part.startswith('Thumbs.db') for part in path.parts)
            and path.suffix in kwargs.config.filetypes.input]
        for file in raw_captures:
            grandcestors = file.parents[1]
            accession_number = str(file.parent).replace(str(file.parent.parent),"").replace("\\","")
            try:
                ingests[accession_number].append(file)
            except:
                ingests[accession_number] = []
                ingests[accession_number].append(file)
    logging.debug("%s",str(ingests))
    return ingests

def updateFM(hashlist,scriptRepo,logfile):
    logging.info("sending hashes to filemaker")
    for fh in hashlist:
        fname,ext = os.path.splitext(fh)
        fdigi = ext.replace(".","")
        output = subprocess.Popen(["python",os.path.join(scriptRepo,"fm-stuff.py"),"-uSha","-id",fname,"-hash",hashlist[fh],"-fdigi",fdigi],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return

def verifyFM(hashlist,scriptRepo,logfile):
    logging.info("verifying hashes in filemaker")
    verifiedwrong = []
    for fh in hashlist:
        fname,ext=os.path.splitext(fh)
        fdigi = ext.replace(".","")
        sys.stdout.flush()
        output = subprocess.Popen(["python",os.path.join(scriptRepo,"fm-stuff.py"),"-qSha","-id",fname,"-fdigi",fdigi],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        fmhash = output.communicate()
        if any(hashlist[fh] in foo for foo in fmhash):
            logging.info("hash of %s verified correctly as: %s", str(fh), str(fmhash))
        else:
            logging.error("hash of %s verified incorrectly", str(fh))
            logging.error("makevideos calculated hash of: %s", hashlist[fh])
            logging.error("filemaker hash stored is: %s", str(fmhash))
            verifiedwrong.append(str(fh))
    if verifiedwrong:
        moveyn = False
    else:
        moveyn = True
    return moveyn

def move_files(accession, files, kwargs):
    '''
    moves files from processing directory to preservation server
    '''
    logging.info("moving files from processing dir to preservation")
    accession_fullpath = kwargs.config.raw_captures / accession
    try:
        for file in files:
            if "_pres" in str(file.name) or "dvd.mpg" in str(file.name):
                #xendata
                file = pathlib.Path(file)
                cmd = "robocopy " + str(accession_fullpath) + " " + \
                    str(kwargs.config.xendatacopyto) + " " + str(file.name)
            if "wm.mp4" in str(file.name) or "tc.mp4" in str(file.name):
                #sunnas
                file = pathlib.Path(file)
                cmd = "robocopy " + str(accession_fullpath) + " " + \
                    str(kwargs.config.sunnascopyto) + " " + str(file.name)
            logger.info("copying %s", str(file))
            logger.debug(cmd)
            output = subprocess.run(cmd, capture_output=True)
            if output.returncode < 2 and not "pres" in str(file.name):
                if not "pres" in str(file.name):
                    #move files up to their anchor X:\ or whatever
                    file.replace(file.parents[-1] / file.name)
                continue
            else:
                logger.error(output.returncode)
                logger.error(output.stderr)
                logger.error(output.stdout)
                logger.error("there was an error moving a file %s", file)
                return False
    except Exception as e:
        logger.error("there was an error moving a file %s", file)
        logger.error(e)
        return False
    return True

def hash_files(files, kwargs):
    '''
    creates portable SHA -1 hash for file
    '''
    logging.info("hashing files")
    hashes = {}
    for file in files:
        file = str(file)
        logger.info("hashing " + file)
        cmd = 'certutil -hashfile "' + file + '"'
        logger.debug(cmd)
        output = subprocess.run(cmd, capture_output=True)
        if output.returncode == 0:
            lines = output.stdout.split(b"\r\n")
            hash = lines[1].strip().decode("utf-8")
            hashes[file] = hash
        else:
            logging.error(output.stderr)
            return False
    logging.info("hashing files completed successfully")
    return hashes

def make_derivatives(accession, input_files, kwargs):
    '''
    manages derivative creation
    '''
    for file in input_files:
        '''
        mp4 with timecode
        accession_tc.mp4
        '''
        logging.info("creating mp4 with burned-in timecode")
        mp4_with_tc_ok = transcodes.make_mp4_with_tc(accession, file, kwargs)
        if not mp4_with_tc_ok:
            logging.error("creation of mp4 with burned-in timecode failed")
            return False
        '''
        mp4 with watermark
        accession_wm.mp4
        '''
        logging.info("creating mp4 with burned-in watermark")
        mp4_with_logo_ok = transcodes.make_mp4_with_logo(accession, file, kwargs)
        if not mp4_with_logo_ok:
            logging.error("creation of mp4 with watermark failed")
            return False
        '''
        mpeg file for DVD
        accession_dvd.mpeg
        '''
        logging.info("creating mpeg DVD file")
        mpeg_dvd_ok = transcodes.make_mpg_dvd(accession, file, kwargs)
        if not mpeg_dvd_ok:
            logging.error("creation of mpeg DVD file failed")
            return False
        '''
        NOT IMPLEMENTED
        mezzanine mxf
        mezz.mxf

        logging.info("creating mxf mezzanine")
        mxf_mezz_ok = transcodes.make_mxf_mezz(accession, file, kwargs)
        if not mxf_mezz_ok:
            logging.error("creation of mxf mezzanine failed")
            return False
        return [mp4_with_tc_ok, mp4_with_logo_ok, mpeg_dvd_ok, mxf_mezz_ok]
        '''
    return [mp4_with_tc_ok, mp4_with_logo_ok, mpeg_dvd_ok]

def process_accession(accession, files, kwargs):
    '''
    manages processing of single accession
    '''
    logging.info("Processing accession %s", accession)
    '''
    concatenates files by default
    flag for --no_concatenation evaluated here
    files variable changes value based on output from transcodes:
    input is list of raw files in accession directory
    input files have their full paths
    output is list of single concatenated file, named for accession_pres.mov
    output is also full path
    '''
    accession_fullpath = kwargs.config.raw_captures / accession
    if kwargs.input_concatenation and len(files) > 1:
        with util.cd(str(accession_fullpath)):
            logging.info("concatenating raw files in accession dir: %s", str(accession_fullpath))
            files = transcodes.concatenate_raw_captures(accession, files, kwargs)
            if not files:
                logging.error("concatenation failed")
                return False
    '''
    make derivatives in transcode script
    '''
    with util.cd(str(accession_fullpath)):
        files = make_derivatives(accession, files, kwargs)
    if not files:
        logging.error("derivative creation failed")
        return False
    return files

def test(kwargs):
    '''
    here you can define functions/ flows for testing the script
    '''
    logging.info("testing")
    '''
    create ingest list
    technically ingests dictionary with list of full filepaths (as pathlib objects) for each accession folder
    {A2022_012_001_001:['D:\file1.mov','D:\file2.mov'],A2022_034_001_001:['D:\file3.mov', 'D\:file4.mov']}
    '''
    ingests = get_files_for_ingest(kwargs)
    '''
    loop through ingest list
    accession here is string of form A2022_001_001_001
    '''
    for accession in sorted(ingests.keys()):
        accession_fullpath = kwargs.config.raw_captures / accession
        '''
        check filemaker records for each accession
        '''
        filemaker_connection, cursor = fm.init_connection(kwargs)
        filemaker_ok = fm.verify_record_exists(accession, cursor, kwargs)
        if not filemaker_ok:
            logging.error("FileMaker record not found for %s", accession)
            kwargs.config.lockfile.unlink()
            quit()
        else:
            '''
            do input validation on each file, if requested
            '''
            if kwargs.input_validation:
                logging.info("running mediaconch policies against input files to determine valid inputs")
                accession_mediaconch_policy = file_validation.validate_input(accession, \
                        ingests[accession], kwargs)
                if not accession_mediaconch_policy:
                    logging.error("mediainfo input validation failed for accession %s", \
                            str(accession))
                    logging.info("for specific errors, please open file %s " \
                            "in MediaConch GUI and evaluate against policies located at "\
                            "%s", ingests[accession][0], kwargs.config.mediaconch.input_policies)
                    logging.info("alternatively, try running this script with " + \
                            "--no_input_validation flag")
                    kwargs.config.lockfile.unlink()
                    quit()
                else:
                    kwargs.accession_mediaconch_policy = accession_mediaconch_policy
        kwargs = transcodes.detect_interlaced_video(ingests[accession][0], kwargs)
        if not kwargs:
            logger.error("interlace detection failed for accession %s", accession)
            return
        return


def verify_startup(kwargs):
    '''
    manages startup of script
    '''
    already_running = startup.verify_already_running(kwargs)
    if already_running:
        logging.error("makevideos is already running")
        return False
    #files_done_copying = startup.verify_file_copying(kwargs)
    #drives_ok = startup.verify_config_drivepaths(kwargs)
    drives_ok = True
    if not drives_ok:
        logging.error("drives not found")
        return False
    watermark_file_ok = startup.verify_config_filepaths(kwargs)
    if not watermark_file_ok:
        logging.error("timecode and/or watermark files not found")
        return False
    if not kwargs.mtf:
        raw_captures_files_ok = startup.verify_raw_captures(kwargs)
        if not raw_captures_files_ok:
            logging.error("files not found in raw capture directory")
            return False
    return True

def init_log(kwargs):
    '''
    initalizes log actions
    '''
    log_filename = pathlib.Path("log-" + time.strftime("%Y-%m-%d %H-%M-%S", time.localtime()) + ".txt")
    log_filepath = str(kwargs.config.logs_path / log_filename)
    message_format = logging.Formatter('%(asctime)s %(levelname)s: %(message)s',\
            datefmt='%Y-%m-%d %H:%M:%S')
    global logger
    logger = logging.getLogger()
    '''
    make a handler for log file, add to logger
    '''
    log_handler = logging.FileHandler(log_filepath)
    log_handler.setFormatter(message_format)
    log_handler.setLevel(logging.DEBUG)
    logger.addHandler(log_handler)
    '''
    make a handler for printing to terminal screen, add to logger
    '''
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(message_format)
    stream_handler.setLevel(kwargs.print_loglevel)
    logger.addHandler(stream_handler)
    logger.setLevel(logging.DEBUG)
    '''
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',\
            datefmt='%Y-%m-%d %H:%M:%S', filename=log_filepath, \
            stream=sys.stdout, encoding='utf-8', level=logging.DEBUG)
    '''
    logger.info("initializing script and log")
    logger.debug("kwargs object: %s", str(kwargs))

def init_config(kwargs):
    '''
    initialize variables and arguments from config file
    '''
    kwargs.config = util.d({})
    config = configparser.ConfigParser()
    config.read(kwargs.script_dir / "video-post-process-config.txt")
    kwargs.config.logs_path = pathlib.Path(config.get('logs','logs_path'))
    kwargs.config.lockfile = pathlib.Path(config.get('logs','lockfile'))
    kwargs.config.watermark_white = pathlib.Path(config.get('transcode','whitewatermark'))
    #kwargs.config.timecode_fontfile = pathlib.Path(config.get('transcode','timecodefont'))
    kwargs.config.raw_captures = pathlib.Path(config.get('transcode','rawCaptureDir'))
    kwargs.config.sunnascopyto = pathlib.Path(config.get('fileDestinations','sunnascopyto'))
    kwargs.config.sunnas = pathlib.Path(config.get('fileDestinations','sunnas'))
    kwargs.config.xendata = pathlib.Path(config.get('fileDestinations','xendata'))
    kwargs.config.xendatacopyto = pathlib.Path(config.get('fileDestinations','xendatacopyto'))
    kwargs.config.xcluster = pathlib.Path(config.get('fileDestinations','xcluster'))
    kwargs.config.filetypes = util.d({"input":config.get('filetypes','input')})
    kwargs.config.filemaker_user = config.get('filemaker','user')
    kwargs.config.filemaker_pwd = config.get('filemaker','pwd')
    kwargs.config.mediaconch = util.d( \
        {"input_policies":config.get('mediaconch','input_policies_dir'), \
        "wm_policy":config.get('mediaconch','watermark_mp4'), \
        "tc_policy":config.get('mediaconch','timecode_mp4'), \
        "dvd_policy":config.get('mediaconch','dvd_mpg')})
    return kwargs

def init_kwargs():
    '''
    initialize variables and arguments from command line

    "kwargs" = KeyWordArguments - this is a single object/ dictionary that stores most of our variables
    '''
    parser = argparse.ArgumentParser(description='Process videos for ingest')
    parser.add_argument('-v','--verbose', action='store_true',default=False,\
            help="verbose mode, print debug messages to terminal screen")
    parser.add_argument('-q','--quiet',action='store_true',default=False,\
            help="quiet mode, only report errors to terminal screen")
    parser.add_argument('input', nargs='*',\
            help='the input folder(s)')
    parser.add_argument('--no_concat', action='store_true', default=False,\
            help="disable concatenation of input files")
    parser.add_argument('--continue_on_error', action='store_true', default=False,\
            help="continue processing accessions even if 1 fails")
    parser.add_argument('--mediaconch_policy', default="",\
            help="run input/output validation against specified mediaconch policy at path")
    parser.add_argument('--no_input_validation', action='store_true', default=False, \
        help="disable mediaconch file validation on input files and _pres output file")
    parser.add_argument('--no_copy', action='store_true', default=False, \
        help="disable file copying to sunnas / xendata, useful for testing")
    parser.add_argument('--test', action='store_true', default=False,\
            help="runs script in test mode")
    args = parser.parse_args()
    kwargs = util.d({})
    kwargs.script_dir = pathlib.Path(__file__).parent.absolute()
    kwargs.input = args.input
    kwargs.test = args.test
    #next lines flip the boolean values for concatenation and input/output validation
    #makes the code more readable in main()
    kwargs.input_validation = operator.not_(args.no_input_validation)
    kwargs.input_concatenation = operator.not_(args.no_concat)
    kwargs.copy_files = operator.not_(args.no_copy)
    #sets mediaconch location
    kwargs.mediaconch_policy = pathlib.Path(args.mediaconch_policy)
    '''
    next lines set console output verbosity
    running script with both -qv is possible, but the -v will override the -q
    log file unaffected by either choice, logs debug and up
    '''
    if args.verbose:
        kwargs.print_loglevel = logging.DEBUG
    elif args.quiet:
        kwargs.print_loglevel = logging.WARNING
    else:
        kwargs.print_loglevel = logging.INFO
    return kwargs

def main():
    '''
    manages the running of the script
    '''
    try:
        '''
        initialization
        '''
        kwargs = init_kwargs()
        kwargs = init_config(kwargs)
        init_log(kwargs)
        startup_ok = verify_startup(kwargs)
        if not startup_ok:
            logging.error("startup failed")
            kwargs.config.lockfile.unlink()
            quit()
        '''
        determine if script is running in test mode
        '''
        if kwargs.test:
            accession = "test"
            test(kwargs)
            logging.info("script started in test mode, exiting...")
            kwargs.config.lockfile.unlink()
            quit()
        '''
        create ingest list
        technically ingests dictionary with list of full filepaths (as pathlib objects) for each accession folder
        {A2022_012_001_001:['D:\file1.mov','D:\file2.mov'],A2022_034_001_001:['D:\file3.mov', 'D\:file4.mov']}
        '''
        ingests = get_files_for_ingest(kwargs)
        '''
        loop through ingest list
        accession here is string of form A2022_001_001_001
        '''
        for accession in sorted(ingests.keys()):
            accession_fullpath = kwargs.config.raw_captures / accession
            '''
            check filemaker records for each accession
            '''
            filemaker_connection, cursor = fm.init_connection(kwargs)
            filemaker_ok = fm.verify_record_exists(accession, cursor, kwargs)
            if not filemaker_ok:
                logging.error("FileMaker record not found for %s", accession)
                kwargs.config.lockfile.unlink()
                quit()
            else:
                '''
                do input validation on each file, if requested
                '''
                if kwargs.input_validation:
                    logging.info("running mediaconch policies against input files to determine valid inputs")
                    accession_mediaconch_policy = file_validation.validate_input(accession, \
                            ingests[accession], kwargs)
                    if not accession_mediaconch_policy:
                        logging.error("mediainfo input validation failed for accession %s, quitting", \
                                str(accession))
                        logging.info("to process this accession, try running this script with" + \
                                "--no_input_validation flag")
                        kwargs.config.lockfile.unlink()
                        quit()
                    else:
                        kwargs.accession_mediaconch_policy = accession_mediaconch_policy
                '''
                detect interlacing / progressive frame format for input accession
                '''
                kwargs = transcodes.detect_interlaced_video(ingests[accession][0], kwargs)
                if not kwargs:
                    logger.error("interlace detection failed for accession %s, quitting", accession)
                    quit()
                '''
                actually process/ transcode the files
                processing_ok variable is list of full paths to derivative files
                '''
                files = processing_ok = process_accession(accession, \
                        ingests[accession], kwargs)
                if not processing_ok:
                    logging.error("processing for accession %s failed. See log for details",str(accession))
                    if kwargs.continue_on_error:
                        pass
                    else:
                        logging.info("script instructed to quit on processing error. Exiting...")
                        break
                '''
                do output validation on preservation file, if requested
                '''
                if kwargs.input_validation:
                    output_pres_ok = file_validation.validate_output(accession, files, kwargs)
                    if not output_pres_ok:
                        logging.error("preservation file did not pass validation, quitting...")
                        kwargs.config.lockfile.unlink()
                        quit()
                '''
                create checksums for each derivative
                hashes is dictionary of full_filepath:hash pairs
                '''
                hashes = hash_files(files, kwargs)
                if not hashes:
                    logging.error("file hashing failed")
                    return False
                logging.debug(hashes)
                '''
                send checksums to filemaker
                file transfers are validated post-ingest by Mark Strecker's Java app
                '''
                kwargs.id = accession
                for file in hashes.keys():
                    file = pathlib.Path(file)
                    kwargs.hash = hashes[str(file)]
                    kwargs.filename = str(file.name)
                    fm_updates_ok = fm.update_hash(accession, cursor, filemaker_connection, kwargs)
                    if not fm_updates_ok:
                        logging.error("FileMaker update for hashes failed")
                        raise RuntimeError("the script failed due to an error at runtime")
                '''
                send file data to various places
                '''
                if kwargs.copy_files:
                    files_moved_ok = move_files(accession, files, kwargs)
                    if not files_moved_ok:
                        logging.error("file transfer to preservation storage failed")
                        raise RuntimeError("the script failed due to an error at runtime")
                    else:
                        logging.info("files moved successfully")
                        #for file in accession_fullpath.iterdir():
                            #file.unlink()
                        time.sleep(1)
                        #accession_fullpath.rmdir() #deletes accession dir we just processed
                logging.info("accession %s processed successfully", accession)
                '''send_email("processing successful for " + accession, \
                        logging.getLoggerClass().root.handlers[0].baseFilename)'''
    except Exception as e:
        logging.error("processing of accession %s unsuccessful", accession)
        logging.error("ingest.py encountered an error:")
        logging.error(str(e))
        logging.error(traceback.format_exc())
        '''send_email("processing unsuccessful for " + accession, \
                logging.getLoggerClass().root.handlers[0].baseFilename)'''
    kwargs.config.lockfile.unlink() #delete lockfile so script knows it's not already running

if __name__ == "__main__":
    main()
