#!/usr/bin/env python
'''
main script for ingesting materials for The History Makers
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
from send_email import send_email, format_log_for_email
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
                    and not any(part.startswith('Thumbs.db') for part in path.parts) \
                    and not any(part.startswith('$') for part in path.parts) \
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
            and not any(part.startswith('Thumbs.db') for part in path.parts) \
            and not any(part.startswith('$') for part in path.parts) \
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
                copyto_parent = kwargs.config.xendata
                copyto_file = kwargs.config.xendatacopyto / file.name
            if "wm.mp4" in str(file.name) or "tc.mp4" in str(file.name):
                #sunnas
                file = pathlib.Path(file)
                cmd = "robocopy " + str(accession_fullpath) + " " + \
                    str(kwargs.config.sunnascopyto) + " " + str(file.name)
                copyto_parent = kwargs.config.sunnas
                copyto_file = kwargs.config.sunnascopyto / file.name
            logger.info("copying %s", str(file))
            logger.debug(cmd)
            output = subprocess.run(cmd, capture_output=True)
            if output.returncode < 2:
                if not "pres" in str(file.name):
                    #move files up to their anchor X:\ or whatever
                    copyto_file.replace(copyto_parent / file.name)
                else:
                    continue
            else:
                stdout = output.stdout.decode("utf-8")
                logger.error(output.returncode)
                logger.error(stdout[300])
                logger.error("robocopy output clipped for readability")
                logger.error("there was an error moving a file %s", file)
                return False
    except Exception as e:
        logger.error("there was an error moving a file %s", file)
        logger.error(e)
        return False
    return True

def copy_pres_dvd_files(accession, files, kwargs):
    '''
    copys preservation and DVD files to D:\loc and D:\dvd, respectively
    '''
    accession_fullpath = kwargs.config.raw_captures / accession
    for file in files:
        if "_pres" in file.name:
            cmd = "robocopy " + str(accession_fullpath) + " " + \
                str(kwargs.config.loc) + " " + str(file.name)
        elif "dvd.mpg" in file.name:
            cmd = "robocopy " + str(accession_fullpath) + " " + \
                str(kwargs.config.dvd) + " " + str(file.name)
        else:
            continue
        logger.info("copying %s to %s", file, kwargs.config.loc)
        output = subprocess.run(cmd, capture_output=True)
        if output.returncode < 2:
            logger.info("file copied successfully")
        else:
            logger.error("there was a problem copying %s", file)
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

def make_derivatives(accession, input_file, kwargs):
    '''
    manages derivative creation
    '''
    '''
    mp4 with timecode
    accession_tc.mp4
    '''
    logging.info("creating mp4 with burned-in timecode")
    mp4_with_tc_ok = transcodes.make_mp4_with_tc(accession, input_file, kwargs)
    if not mp4_with_tc_ok:
        logging.error("creation of mp4 with burned-in timecode failed")
        return False
    '''
    mp4 with watermark
    accession_wm.mp4
    '''
    logging.info("creating mp4 with burned-in watermark")
    mp4_with_logo_ok = transcodes.make_mp4_with_logo(accession, input_file, kwargs)
    if not mp4_with_logo_ok:
        logging.error("creation of mp4 with watermark failed")
        return False
    '''
    mpeg file for DVD
    accession_dvd.mpeg
    '''
    logging.info("creating mpeg DVD file")
    mpeg_dvd_ok = transcodes.make_mpg_dvd(accession, input_file, kwargs)
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
    _files = []
    if kwargs.rewrap_mp4:
        for mp4_file in files:
            mov_file = transcodes.rewrap_mp4_streams_in_mov(mp4_file, kwargs)
            if not mov_file:
                logging.error("there was a problem re-wrapping the mp4 file(s) in mov")
                return False
            else:
                _files.append(mov_file)
        files = _files
    if kwargs.input_concatenation and len(files) > 1:
        with util.cd(str(accession_fullpath)):
            logging.info("concatenating raw files in accession dir: %s", str(accession_fullpath))
            pres_file = transcodes.concatenate_raw_captures(accession, files, kwargs)
            pres_file = pathlib.Path(pres_file)
            if not files:
                logging.error("concatenation failed")
                return False
    elif (files[0].suffix == ".MOV" or files[0].suffix == ".mov") \
        and not kwargs.rewrap_mp4:
        with util.cd(str(accession_fullpath)):
            pres_file = transcodes.rewrap_single_file_accession(accession, files[0], kwargs)
            if not pres_file:
                logging.error("rewrap of single file accession failed")
                return False
    else:
        file = files[0]
        ext = file.suffix
        filename = accession + "_pres" + ext
        file.replace(file.parent / filename)
        pres_file = file.parent / filename
    '''
    make derivatives in transcode script
    '''
    with util.cd(str(accession_fullpath)):
        files = make_derivatives(accession, pres_file, kwargs)
    if not files:
        logging.error("derivative creation failed")
        return False
    files.append(pres_file)
    return files

def test(kwargs):
    '''
    here you can define functions/ flows for testing the script
    '''
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
        check mp4 files for invalid pcm audio
        '''
        for file in ingests[accession]:
            if str(file).endswith(".mp4") or str(file).endswith(".MP4"):
                logging.info("testing %s for valid audio codec in mp4",file)
                valid_mp4 = file_validation.detect_valid_mp4(file, kwargs)
                if not valid_mp4:
                    if valid_mp4 == None:
                        logger.error("there was a problem running mediaconch")
                        raise RuntimeError("MediaConch could not be run")
                    else:
                        kwargs.rewrap_mp4 = True
                        break
                else:
                    logging.info("file is valid mp4")
                    kwargs.rewrap_mp4 = False

def verify_startup(kwargs):
    '''
    manages startup of script
    '''
    in_venv = startup.verify_venv()
    if not in_venv:
        logging.error("please enable virtual environment and re-run the script")
        return False
    files_done_copying = startup.verify_file_copying(kwargs)
    if kwargs.copy_files:
        drives_ok = startup.verify_config_drivepaths(kwargs)
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
    if not kwargs.config.logs_path.is_dir():
        print("ERROR: logs directory not found")
        print("ERROR: please create a directory at:")
        print(kwargs.config.logs_path)
        print("alternatively, change the logs location in post-processing config txt file")
        return False
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
    return True

def init_config(kwargs):
    '''
    initialize variables and arguments from config file
    '''
    kwargs.config = util.d({})
    config = configparser.ConfigParser()
    config.read(kwargs.script_dir / "video-post-process-config.txt")
    kwargs.config.logs_path = pathlib.Path(config.get('logs','logs_path'))
    kwargs.config.watermark_white = pathlib.Path(config.get('transcode','whitewatermark'))
    kwargs.config.raw_captures = pathlib.Path(config.get('transcode','rawCaptureDir'))
    kwargs.config.sunnascopyto = pathlib.Path(config.get('fileDestinations','sunnascopyto'))
    kwargs.config.sunnas = pathlib.Path(config.get('fileDestinations','sunnas'))
    kwargs.config.xendata = pathlib.Path(config.get('fileDestinations','xendata'))
    kwargs.config.xendatacopyto = pathlib.Path(config.get('fileDestinations','xendatacopyto'))
    kwargs.config.xcluster = pathlib.Path(config.get('fileDestinations','xcluster'))
    kwargs.config.loc = pathlib.Path(config.get('fileDestinations','loc'))
    kwargs.config.dvd = pathlib.Path(config.get('fileDestinations','dvd'))
    kwargs.config.filetypes = util.d({"input":config.get('filetypes','input')})
    kwargs.config.filemaker_user = config.get('filemaker','user')
    kwargs.config.filemaker_pwd = config.get('filemaker','pwd')
    kwargs.config.mediaconch = util.d( \
        {"input_policies":config.get('mediaconch','input_policies_dir'), \
        "wm_policy":config.get('mediaconch','watermark_mp4'), \
        "tc_policy":config.get('mediaconch','timecode_mp4'), \
        "dvd_policy":config.get('mediaconch','dvd_mpg'), \
        'mp4_pcm_policy':config.get('mediaconch','mp4_pcm_policy')})
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
    parser.add_argument('--sleep', default=0, \
            help="set script to run after n seconds, useful if file is copying")
    parser.add_argument('--mediaconch_policy', default=None,\
            help="run input/output validation against specified mediaconch policy at path")
    parser.add_argument('--continue_on_error', action='store_true', default=False,\
            help="continue processing accessions even if 1 fails")
    parser.add_argument('--no_concat', action='store_true', default=False,\
            help="disable concatenation of input files")
    parser.add_argument('--no_input_validation', action='store_true', default=False, \
        help="disable mediaconch file validation on input files and _pres output file")
    parser.add_argument('--no_copy', action='store_true', default=False, \
        help="disable file copying to sunnas / xendata, useful for testing")
    parser.add_argument('--no_email', action='store_true', default=False, \
        help="disable email notifications")
    parser.add_argument('--test', action='store_true', default=False,\
            help="runs script in test mode")
    args = parser.parse_args()
    kwargs = util.d({})
    kwargs.script_dir = pathlib.Path(__file__).parent.absolute()
    kwargs.input = args.input
    kwargs.test = args.test
    kwargs.sleep = int(args.sleep)
    kwargs.ffmpeg_suffix = " 2> ffmpeg.log"
    '''
    next lines flip the boolean values for concatenation and input/output validation
    makes the code more readable in main()
    '''
    kwargs.input_validation = operator.not_(args.no_input_validation)
    kwargs.input_concatenation = operator.not_(args.no_concat)
    kwargs.copy_files = operator.not_(args.no_copy)
    kwargs.send_email = operator.not_(args.no_email)
    '''
    sets mediaconch location
    sets flag for running each accession against all MC policies
    --i.e. different accessions in XDCAM or ProRes can be run in the same batch
    '''
    try:
        kwargs.accession_mediaconch_policy = pathlib.Path(args.mediaconch_policy)
        kwargs.reset_mediaconch_policy = False
    except:
        kwargs.accession_mediaconch_policy = None
        kwargs.reset_mediaconch_policy = True
    kwargs.rewrap_mp4 = False
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
        log_ok = init_log(kwargs)
        if not log_ok:
            print("log initialization failed. no log created for this run. quitting...")
            accession = None
            quit()
        if kwargs.sleep:
            logging.info("script will resume in " + str(kwargs.sleep) + " seconds")
            time.sleep(kwargs.sleep)
        startup_ok = verify_startup(kwargs)
        if not startup_ok:
            logging.error("startup failed")
            accession = "error"
            raise RuntimeError("the script failed due to an error during startup")
        '''
        determine if script is running in test mode
        '''
        if kwargs.test:
            accession = "test"
            test(kwargs)
            logging.info("script started in test mode, exiting...")
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
                raise RuntimeError("The script could not connect to FileMaker")
            else:
                '''
                do input validation on files, if requested
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
                        raise RuntimeError("the script quit due to an error validating input video files")
                    else:
                        kwargs.accession_mediaconch_policy = accession_mediaconch_policy
                '''
                check mp4 files for invalid pcm audio
                '''
                for file in ingests[accession]:
                    if file.suffix == ".mp4" or file.suffix == ".MP4":
                        logging.info("testing %s for valid audio codec in mp4",file)
                        valid_mp4 = file_validation.detect_valid_mp4(file, kwargs)
                        if not valid_mp4:
                            if valid_mp4 == None:
                                logger.error("there was a problem running mediaconch")
                                raise RuntimeError("MediaConch could not be run")
                            else:
                                kwargs.rewrap_mp4 = True
                                break
                        else:
                            logging.info("file is valid mp4")
                            kwargs.rewrap_mp4 = False
                '''
                detect interlacing / progressive frame format for input accession
                '''
                kwargs = transcodes.detect_interlaced_video(ingests[accession][0], kwargs)
                if not kwargs:
                    logger.error("interlace detection failed for accession %s, quitting", accession)
                    raise RuntimeError("the script quit due to an error detecting interlaced/ progressive video")
                '''
                actually process/ transcode the files
                processing_ok variable is list of full paths to derivative files
                '''
                files = processing_ok = process_accession(accession, ingests[accession], kwargs)
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
                        raise RuntimeError("the script quit due to an error validating output video preservation file")
                '''
                create checksums for each derivative
                hashes is dictionary of full_filepath:hash pairs
                '''
                hashes = hash_files(files, kwargs)
                if not hashes:
                    logging.error("file hashing failed")
                    raise RuntimeError("the script quit due an error at runtime")
                logging.debug(hashes)
                '''
                reconnect to filemaker
                '''
                filemaker_connection, cursor = fm.init_connection(kwargs)
                '''
                send checksums to filemaker
                file transfers are validated post-ingest by Mark Streckers Java app
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
                        logging.info("copying preservation and DVD files")
                        pres_dvd_files_copied_ok = copy_pres_dvd_files(accession, files, kwargs)
                        if not pres_dvd_files_copied_ok:
                            logging.error("there was an error moving the preservation and dvd files to")
                            logging.error(kwargs.config.loc)
                            logging.error(kwargs.config.dvd)
                            raise RuntimeError("the script failed due to an error at runtime")
                        else:
                            for file in accession_fullpath.iterdir():
                                logging.debug(file)
                                file.unlink()
                            time.sleep(1)
                            accession_fullpath.rmdir() #deletes accession dir we just processed
                logging.info("accession %s processed successfully", accession)
                if kwargs.send_email:
                    the_log = logging.getLoggerClass().root.handlers[0].baseFilename
                    tmp_log = format_log_for_email(the_log)
                    if not tmp_log:
                        logger.warning("unable to format log for email")
                        tmp_log = "Unable to format log for email, see log file for further details: " + the_log
                    send_email("ingest notification for " + accession,\
                        "processing successful for " + accession, tmp_log)
    except Exception as e:
        logging.error("processing of accession %s unsuccessful", accession)
        logging.error("ingest.py encountered an error:")
        logging.error(traceback.format_exc())
        if kwargs.send_email:
            the_log = logging.getLoggerClass().root.handlers[0].baseFilename
            tmp_log = format_log_for_email(the_log)
            if not tmp_log:
                logger.warning("unable to format log for email")
                tmp_log = "Unable to format log for email, see log file for further details: " + the_log
            send_email("ingest notification for " + accession, \
                "processing unsuccessful for " + accession, tmp_log)

if __name__ == "__main__":
    main()
