#!/usr/bin/python
#the history makers ingest.py
#processes videos for The History Makers

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
    else:
        accession_path = kwargs.config.raw_captures
        raw_captures = [path for path in accession_path.glob('**/*.*') \
            if not any(part.startswith('.') for part in path.parts) \
            and not any(part.startswith('Thumbs.db') for part in path.parts)
            and path.suffix in kwargs.config.filetypes.input]
        for file in raw_captures:
            grandcestors = str(file.parents[1])
            accession_number = str(file).replace(grandcestors,"").replace(str(file.name),"").replace("/","")
            try:
                ingests[accession_number].append(str(file))
            except:
                ingests[accession_number] = []
                ingests[accession_number].append(str(file))
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
    '''
    for file in files:
    subprocess.run(robocopy Z:\source D:\destination file.mov)
    '''
    return True

def hash_files(files, kwargs):
    '''
    creates portable SHA -1 hash for file
    '''
    logging.info("hashing files")
    hashes = {}
    cmd = "certutil -hashfile '" + file + "'"
    output = subprocess.run(cmd, capture_output=True)
    if output.returncode == 0:
        lines = output.stdout.split(b"\r\n")
        hash = str(lines[1].strip())
        hashes[file] = hash
    else:
        return False
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
        mezzanine mxf
        mezz.mxf
        '''
        logging.info("creating mxf mezzanine")
        mxf_mezz_ok = transcodes.make_mxf_mezz(accession, file, kwargs)
        if not mxf_mezz_ok:
            logging.error("creation of mxf mezzanine failed")
            return False
    return [mp4_with_tc_ok, mp4_with_logo_ok, mpeg_dvd_ok, mxf_mezz_ok]

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
    #files = [accession + "_pres.mov"]
    with util.cd(str(accession_fullpath)):
        files = make_derivatives(accession, files, kwargs)
    if not files:
        logging.error("derivative creation failed")
        return False
    return files

def make_test_files(kwargs):
    '''
    creates test video files conforming to output standards, using ffmpeg
    '''
    print("make test videos")

def verify_startup(kwargs):
    '''
    manages startup of script
    '''
    already_running = startup.verify_already_running(kwargs)
    if already_running:
        logging.error("makevideos is already running")
        return False
    files_done_copying = startup.verify_file_copying(kwargs)
    drives_ok = startup.verify_config_drivepaths(kwargs)
    if not drives_ok:
        logging.error("drives not found")
        return False
    timecode_and_watermark_files_ok = startup.verify_config_filepaths(kwargs)
    if not timecode_and_watermark_files_ok:
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
    kwargs.config.timecode_fontfile = pathlib.Path(config.get('transcode','timecodefont'))
    kwargs.config.raw_captures = pathlib.Path(config.get('transcode','rawCaptureDir'))
    kwargs.config.sunnascopyto = pathlib.Path(config.get('fileDestinations','sunnascopyto'))
    kwargs.config.sunnas = pathlib.Path(config.get('fileDestinations','sunnas'))
    kwargs.config.xendata = pathlib.Path(config.get('fileDestinations','xendata'))
    kwargs.config.xendatacopyto = pathlib.Path(config.get('fileDestinations','xendatacopyto'))
    kwargs.config.xcluster = pathlib.Path(config.get('fileDestinations','xcluster'))
    kwargs.config.mediaconchas = pathlib.Path(config.get('mediaconch','folder'))
    kwargs.config.filetypes = util.d({"input":config.get('filetypes','input')})
    kwargs.config.fm_username = config.get('filemaker','user')
    kwargs.config.fm_pwd = config.get('filemaker','pwd')
    return kwargs

def init_kwargs():
    '''
    initialize variables and arguments from command line

    "kwargs" = KeyWordArguments - this is a single object/ dictionary that stores msot of our variables
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
    parser.add_argument('--no_input_validation', action='store_true',\
            default=False, help="disable mediaconch file validation on input files")
    parser.add_argument('--no_output_validation', action='store_true', default=False,\
            help="disable mediaconch file validation on output files")
    parser.add_argument('--make_test_files', action='store_true', default=False,\
            help="create test output files using ffmpeg")
    args = parser.parse_args()
    kwargs = util.d({})
    kwargs.script_dir = pathlib.Path(__file__).parent.absolute()
    kwargs.input = args.input
    kwargs.mtf = args.make_test_files
    #next two lines flip the boolean values for concatenation and input/output validation
    #makes the code more readable in main()
    kwargs.input_validation = operator.not_(args.no_input_validation)
    kwargs.output_validation = operator.not_(args.no_output_validation)
    kwargs.input_concatenation = operator.not_(args.no_concat)
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
        if kwargs.mtf:
            make_test_files(kwargs)
            logging.info("script started in test mode, exiting...")
            kwargs.config.lockfile.unlink()
            quit()
        '''
        create ingest list
        technically ingests dictionary with list of full filepaths for each accession folder
        A2022_012_001_001:['file1.mov','file2.mov']
        '''
        ingests = get_files_for_ingest(kwargs)
        '''
        loop through ingest list
        '''
        for accession in sorted(ingests.keys()):
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
                        kwargs.config.lockfile.unlink()
                        quit()
                    else:
                        kwargs.accession_mediaconch_policy = accession_mediaconch_policy
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
                do output validation on each file, if requested
                '''
                if kwargs.output_validation:
                    outputs_ok = file_validation.validate_output(accession, files, kwargs)
                '''
                create checksums for each derivative
                hashes is dictionary of full_filepath:hash pairs
                '''
                hashes = hash_files(files, kwargs)
                if not hashes:
                    logging.error("file hashing failed")
                    return False
                '''
                send checksums to filemaker
                file transfers are validated post-ingest by Mark Strecker's Java app
                '''
                kwargs.id = accession
                for filetype in hashes.keys():
                    kwargs.hash = hashes[file]
                    kwargs.filename = file.name
                    fm_updates_ok = fm.update_hash(accession, cursor, filemaker_connection, kwargs)
                    if not fm_updates_ok:
                        logging.error("FileMaker update for hashes failed")
                        return False
                '''
                send file data to various places
                '''
                files_moved_ok = move_files(accession, files, kwargs)
                if not files_moved_ok:
                    logging.error("file transfer to preservation storage failed")
                    return False
                else:
                    logging.info("accession %s processed successfully", accession)
                    #send_email("processing successful for " + accession, \
                            #logging.getLoggerClass().root.handlers[0].baseFilename)
    except Exception as e:
        logging.error("processing of accession %s unsuccessful", accession)
        logging.error("ingest.py encountered an error:")
        logging.error(str(e))
        logging.error(traceback.format_exc())
        #send_email("processing unsuccessful for " + accession, \
                #logging.getLoggerClass().root.handlers[0].baseFilename)
    kwargs.config.lockfile.unlink() #delete lockfile so script knows it's not already running

if __name__ == "__main__":
    main()
