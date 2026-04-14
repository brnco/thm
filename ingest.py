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
import filemaker.filemaker_handler as fm
import file_validation
from send_email import send_email, format_log_for_email
import startup

#logger = logging.getLogger(__name__)


def move_files(accession, files, kwvars):
    '''
    moves files from processing directory to preservation server
    '''
    logging.info("moving files from processing dir to preservation")
    accession_fullpath = kwvars.config.raw_captures / accession
    try:
        for file in files:
            if "_pres" in str(file.name):
                #xendata
                file = pathlib.Path(file)
                cmd = "robocopy " + str(accession_fullpath) + " " + \
                    str(kwvars.config.xendatacopyto) + " " + str(file.name)
                copyto_parent = kwvars.config.xendata
                copyto_file = kwvars.config.xendatacopyto / file.name
            if "wm.mp4" in str(file.name) or "tc.mp4" in str(file.name):
                #sunnas
                file = pathlib.Path(file)
                cmd = "robocopy " + str(accession_fullpath) + " " + \
                    str(kwvars.config.sunnascopyto) + " " + str(file.name)
                copyto_parent = kwvars.config.sunnas
                copyto_file = kwvars.config.sunnascopyto / file.name
            logger.info("copying %s", str(file))
            logger.debug(cmd)
            output = subprocess.run(cmd, capture_output=True)
            if output.returncode < 2:
                logger.debug("copy completed successfully")
                if not "_pres" in str(file.name):
                    #move files up to their anchor X:\ or whatever
                    logger.debug(f"moving {file} to parent {copyto_parent}")
                    copyto_file_complete = copyto_file.replace(copyto_parent / file.name)
                    logger.debug(f"file moved to {copyto_file_complete}")
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


def copy_pres_files(accession, files, kwvars):
    '''
    copys preservation files to D:/loc
    '''
    accession_fullpath = kwvars.config.raw_captures / accession
    for file in files:
        if "_pres" in file.name:
            cmd = "robocopy " + str(accession_fullpath) + " " + \
                str(kwvars.config.loc) + " " + str(file.name)
        else:
            continue
        logger.info("copying %s to %s", file, kwvars.config.loc)
        output = subprocess.run(cmd, capture_output=True)
        if output.returncode < 2:
            logger.info("file copied successfully")
        else:
            logger.error("there was a problem copying %s", file)
            return False
    return True


def hash_files(files, kwvars):
    '''
    creates portable SHA256 hash for file
    '''
    logging.info("hashing files")
    hashes = {}
    for file in files:
        file = str(file)
        logger.info("hashing " + file)
        cmd = 'certutil -hashfile "' + file + '" SHA256'
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


def get_watermark_for_frame_dimensions(kwvars):
    '''
    gets the appropriate watermark file for given dimensions
    '''
    this_dirpath = pathlib.Path(__file__).parent.absolute()
    png_files = [f for f in this_dirpath.iterdir() if f.is_file() and f.suffix == ".png"]
    file_comps = {}
    for file in png_files:
        file_dimensionsx = file.stem.replace("THM-Watermark", "")
        file_dimensions = file_dimensionsx.split("x")
        file_dimensions_w = int(file_dimensions[0])
        file_dimensions_h = int(file_dimensions[1])
        file_diff_w = kwvars.frame_width - file_dimensions_w
        file_diff_h = kwvars.frame_height - file_dimensions_h
        file_diff = abs(file_diff_w + file_diff_h)
        file_comps[file] = file_diff
    #print(file_comps)
    lowest_diff = sorted(file_comps.values())[0]
    #print(lowest_diff)
    png_file_for_overlay = list(file_comps.keys())[list(file_comps.values()).index(lowest_diff)]
    #print(png_file_for_overlay)
    kwvars.watermark_white = png_file_for_overlay
    return kwvars


def make_derivatives(accession, input_file, kwvars):
    '''
    manages derivative creation
    '''
    '''
    mp4 with timecode
    accession_tc.mp4
    '''
    logging.info("creating mp4 with burned-in timecode")
    mp4_with_tc_ok = transcodes.make_mp4_with_tc(accession, input_file, kwvars)
    if not mp4_with_tc_ok:
        logging.error("creation of mp4 with burned-in timecode failed")
        return False
    '''
    mp4 with watermark
    accession_wm.mp4
    '''
    logging.info("creating mp4 with burned-in watermark")
    kwvars = get_watermark_for_frame_dimensions(kwvars)
    mp4_with_logo_ok = transcodes.make_mp4_with_logo(accession, input_file, kwvars)
    if not mp4_with_logo_ok:
        logging.error("creation of mp4 with watermark failed")
        return False
    '''
    NOT IMPLEMENTED
    mezzanine mxf
    mezz.mxf

    logging.info("creating mxf mezzanine")
    mxf_mezz_ok = transcodes.make_mxf_mezz(accession, file, kwvars)
    if not mxf_mezz_ok:
        logging.error("creation of mxf mezzanine failed")
        return False
    return [mp4_with_tc_ok, mp4_with_logo_ok, mxf_mezz_ok]
    '''
    return [mp4_with_tc_ok, mp4_with_logo_ok]


def process_accession(accession_number, files, kwvars):
    '''
    manages processing of single accession
    '''
    logging.info(f"Processing accession {accession_number}")
    '''
    concatenates files by default
    flag for --no_concatenation evaluated here
    files variable changes value based on output from transcodes:
    input is list of raw files in accession directory
    input files have their full paths
    output is list of single concatenated file, named for accession_pres.mov
    output is also full path
    '''
    accession_fullpath = files[0].parent
    if kwvars.reencode_audio or kwvars.reencode_video:
        _files = transcodes.reencode_accession(accession_number, files, kwvars) 
        files = _files
        logger.debug(files)
    if len(files) > 1:
        with util.cd(str(accession_fullpath)):
            logging.info(f"concatenating raw files in accession dir: {accession_fullpath}")
            pres_file = transcodes.concatenate_raw_captures(accession_number, files, kwvars)
            pres_file = pathlib.Path(pres_file)
    else:
        '''
        accession contains single file
        we used to filter out special collections and not re-encode/ rewrap
        but then we switched to MXF
        '''
        if not files[0].suffix == ".mxf":
            with util.cd(str(accession_fullpath)):
                pres_file = transcodes.rewrap_single_file_accession(accession_number, files[0], kwvars)
                if not pres_file:
                    logging.error("rewrap of single file accession failed")
                    return False
        else:
            pres_file = files[0]
    '''
    make derivatives in transcode script
    '''
    with util.cd(str(accession_fullpath)):
        files = make_derivatives(accession_number, pres_file, kwvars)
    if not files:
        logging.error("derivative creation failed")
        return False
    files.append(pres_file)
    return files


def get_codecs_frameformat_size(accession_to_process, kwvars):
    '''
    gets the codec info, frame format, and frame size
    sets relevant transcode vars in kwvars
    '''
    accession_number = next(iter(accession_to_process))
    '''
    check files for valid video codecs
    ProRes/ ProResHQ
    DNxHD/ DNxHR
    h.264
    JPEG2000
    '''
    logging.info("checking input files for valid preservation video codecs")
    for file in accession_to_process[accession_number]:
        logging.info(f"testing {file} for valid preservation video codec")
        valid_video_in_file = file_validation.detect_video_codec(file, kwvars)
        if not valid_video_in_file:
            if valid_video_in_file ==  None:
                logger.error("there was a problem running mediaconch")
                raise RuntimeError("MediaConch could not be run")
            else:
                kwvars.reencode_video = True
                break
        else:
            kwvars.reencode_video = False
    '''
    check files for pcm audio
    '''
    logging.info("checking input files for pcm audio")
    for file in accession_to_process[accession_number]:
        logging.info(f"testing {file} for pcm audio codec")
        pcm_audio_in_file = file_validation.detect_pcm(file, kwvars)
        if not pcm_audio_in_file:
            if pcm_audio_in_file == None:
                logger.error("there was a problem running mediaconch")
                raise RuntimeError("MediaConch could not be run")
            else:
                kwvars.reencode_audio = True
                break
        else:
            kwvars.reencode_audio = False
    '''
    detect interlacing / progressive frame format for input accession
    '''
    kwvars = transcodes.detect_interlaced_video(accession_to_process[accession_number][0], kwvars)
    if not kwvars:
        logger.error(f"interlace detection failed for accession {accession_number}, quitting")
        raise RuntimeError("the script quit due to an error detecting interlaced/ progressive video")
    '''
    detect frame size for correct png overlay
    '''
    kwvars = transcodes.detect_frame_dimensions(accession_to_process[accession_number][0], kwvars)
    if not kwvars:
        logger.error(f"frame dimensions detection failed for accession {accession}, quitting")
        raise RuntimeError("the script quit du to an error detecting the frame dimensions")


def init_log_accession(kwvars):
    '''
    initializes log for single accession
    '''
    log_filename = pathlib.Path("log-most-recent-accession.txt")
    log_filepath = kwvars.config.logs_path / log_filename
    if log_filepath.is_file():
        log_filepath.unlink()
    message_format = logging.Formatter('%(asctime)s %(levelname)s: %(message)s',\
            datefmt='%Y-%m-%d %H:%M:%S')
    log_handler = logging.FileHandler(str(log_filepath))
    log_handler.setFormatter(message_format)
    log_handler.setLevel(logging.INFO)
    logger.addHandler(log_handler)
    return log_handler, pathlib.Path(log_filepath)


def init_log_full_run(kwvars):
    '''
    initalizes log for whole run of script
    '''
    log_filename = pathlib.Path("log-" + time.strftime("%Y-%m-%d %H-%M-%S", time.localtime()) + ".txt")
    log_filepath = str(kwvars.config.logs_path / log_filename)
    message_format = logging.Formatter('%(asctime)s %(levelname)s: %(message)s',\
            datefmt='%Y-%m-%d %H:%M:%S')
    global logger
    logger = logging.getLogger()
    '''
    make a handler for log file, add to logger
    '''
    if not kwvars.config.logs_path.is_dir():
        print("ERROR: logs directory not found")
        print("ERROR: please create a directory at:")
        print(kwvars.config.logs_path)
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
    stream_handler.setLevel(kwvars.print_loglevel)
    logger.addHandler(stream_handler)
    logger.setLevel(logging.DEBUG)
    '''
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',\
            datefmt='%Y-%m-%d %H:%M:%S', filename=log_filepath, \
            stream=sys.stdout, encoding='utf-8', level=logging.DEBUG)
    '''
    logger.info("initializing script and log")
    logger.debug("kwvars object: %s", str(kwvars))
    return True


def init_config(kwvars):
    '''
    initialize variables and arguments from config file
    '''
    kwvars.config = util.d({})
    config = configparser.ConfigParser()
    config.read(kwvars.script_dir / "video-post-process-config.txt")
    kwvars.config.logs_path = pathlib.Path(config.get('logs','logs_path'))
    kwvars.config.hm_interviews_dir = pathlib.Path(config.get('ingest','HM_interviews'))
    kwvars.config.special_colls_dir = pathlib.Path(config.get('ingest','special_collections'))
    kwvars.config.sunnascopyto = pathlib.Path(config.get('fileDestinations','sunnascopyto'))
    kwvars.config.sunnas = pathlib.Path(config.get('fileDestinations','sunnas'))
    kwvars.config.xendata = pathlib.Path(config.get('fileDestinations','xendata'))
    kwvars.config.xendatacopyto = pathlib.Path(config.get('fileDestinations','xendatacopyto'))
    #kwvars.config.xcluster = pathlib.Path(config.get('fileDestinations','xcluster'))
    kwvars.config.loc = pathlib.Path(config.get('fileDestinations','loc'))
    kwvars.config.filetypes = util.d({"input":config.get('filetypes','input')})
    kwvars.config.filemaker_user = config.get('filemaker','user')
    kwvars.config.filemaker_pwd = config.get('filemaker','pwd')
    kwvars.config.mediaconch = util.d( \
        {"input_policies": config.get('mediaconch','input_policies_dir'), \
        'mp4_pcm_policy': config.get('mediaconch','mp4_pcm_policy'), \
        'pcm_in_file_policy': config.get('mediaconch','pcm_in_file_policy'), \
        'accepted_video_codecs_policy': config.get('mediaconch','accepted_video_codecs_policy')})
    return kwvars


def init_kwvars():
    '''
    initialize variables and arguments from command line

    "kwvars" = KeyWordArguments - this is a single object/ dictionary that stores most of our variables
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
    parser.add_argument('--no_copy', action='store_true', default=False, \
        help="disable file copying to sunnas / xendata, useful for testing")
    parser.add_argument('--no_email', action='store_true', default=False, \
        help="disable email notifications")
    parser.add_argument('--special_collections', action='store_true', default=False,\
            help="runs the script in 'Special Collections' mode, "
                        "where original file timecode is preserved")
    parser.add_argument('--dev', action='store_true', default=False, \
            help="runs the script in 'developer mode' (for testing)")
    args = parser.parse_args()
    kwvars = util.d({})
    kwvars.script_dir = pathlib.Path(__file__).parent.absolute()
    kwvars.input = args.input
    kwvars.sleep = int(args.sleep)
    kwvars.ffmpeg_suffix = " 2> ffmpeg.log"
    kwvars.special_collections = args.special_collections
    kwvars.copy_files = operator.not_(args.no_copy)
    kwvars.send_email = operator.not_(args.no_email)
    kwvars.dev_mode = args.dev
    '''
    next lines set console output verbosity
    running script with both -qv is possible, but the -v will override the -q
    log file unaffected by either choice, logs debug and up
    '''
    if args.verbose:
        kwvars.print_loglevel = logging.DEBUG
    elif args.quiet:
        kwvars.print_loglevel = logging.WARNING
    else:
        kwvars.print_loglevel = logging.INFO
    return kwvars


def init():
    '''
    initializes the script, returns args from config and cli
    '''
    kwvars = init_kwvars()
    kwvars = init_config(kwvars)
    log_ok = init_log_full_run(kwvars)
    if not log_ok:
        print("log initialization failed. no log created for this run. quitting...")
        accession_number = "startup"
        quit()
    if kwvars.sleep:
        logging.info("script will resume in " + str(kwvars.sleep) + " seconds")
        time.sleep(kwvars.sleep)
    in_venv = startup.verify_venv()
    if not in_venv:
        logger.error("please enable virtual environment and re-run the script")
        quit()
    dirs_exist = startup.verify_incoming_dirs_exist(kwvars)
    if not dirs_exist:
        logger.error("the directory with the incoming footage cannot be found")
        logger.error("this is probably an error with the config file")
        logger.error("Please check video-post-processing-config.txt "
                + "and verify the directory paths are spelled correctly")
        quit()
    return kwvars


def main():
    '''
    manages the running of the script
    '''
    try:
        '''
        initialization
        '''
        kwvars = init()
        check_accessions = []
        while True:
            '''
            initialize for processing a single accession
            check that drives are still mounted
            '''
            drives_ok = startup.verify_config_drivepaths(kwvars)
            if not drives_ok:
                logger.error("Drive paths from config unable to be located, please ensure they're mounted")
                raise RuntimeError("The drives configured in the video-post-processing.txt could not be found")
            '''
            create ingest list
            technically ingests dictionary with list of full filepaths (as pathlib objects) for each accession folder
            {A2022_012_001_001:['D:/file1.mov','D:/file2.mov'],A2022_034_001_001:['D:/file3.mov', 'D/:file4.mov']}
            '''
            accession_to_process = startup.get_files_for_ingest(kwvars)
            accession_number = next(iter(accession_to_process))
            accession_fullpath = accession_to_process[accession_number][0].parent
            '''
            if a directory has files copying into it
            add it to a list
            if all the dirs in the raw_captures directory are in the list
            log it and quit
            '''
            if accession_number in check_accessions:
                logger.warning("all accessions appear to be processing or have files copying into them")
                logger.warning("exiting...")
                quit()
            accession_files_done_copying = startup.verify_file_copying(accession_to_process)
            if not accession_files_done_copying:
                check_accessions.append(accession_number)
                continue
            logger.debug(accession_to_process)
            logger.info(f"processing {accession_number}")
            logger.info(f"at path {accession_fullpath}")
            '''
            init logs for this accession
            '''
            accession_log, accession_log_filepath = init_log_accession(kwvars)
            '''
            init lockfile
            '''
            lockfile_path = accession_fullpath / "processing.lock"
            logger.debug(f"creating lockfile at {lockfile_path}")
            lockfile_path.touch()
            '''
            check filemaker records for each accession
            '''
            if not kwvars.dev_mode:
                filemaker_connection, cursor = fm.init_connection(kwvars)
                filemaker_ok = fm.verify_record_exists(accession_number, cursor, kwvars)
                if not filemaker_ok:
                    logging.error(f"FileMaker record not found for {accession_number}")
                    raise RuntimeError("The script could not connect to FileMaker")
            '''
            get relevant codec, frame format, and frame size info
            '''
            kwvars = get_codecs_frameformat_size(accession_to_process, kwvars)
            '''
            actually process/ transcode the files
            processing_ok variable is list of full paths to derivative files
            '''
            output_files = processing_ok = process_accession(accession_number, 
                                            accession_to_process[accession_number], kwvars)
            if not processing_ok:
                raise RuntimeError("there was a problem processing that accession, see log for details")
            '''
            create checksums for each derivative
            hashes is dictionary of full_filepath:hash pairs
            '''
            hashes = hash_files(output_files, kwvars)
            if not hashes:
                logging.error("file hashing failed")
                raise RuntimeError("the script quit due an error at runtime")
            logging.debug(hashes)
            if not kwvars.dev_mode:
                '''
                reconnect to filemaker
                '''
                filemaker_connection, cursor = fm.init_connection(kwvars)
                '''
                send checksums to filemaker
                file transfers are validated post-ingest by Mark Streckers Java app
                '''
                kwvars.id = accession_number
                for file in hashes.keys():
                    file = pathlib.Path(file)
                    kwvars.hash = hashes[str(file)]
                    kwvars.filename = str(file.name)
                    fm_updates_ok = fm.update_hash(accession_number, cursor, filemaker_connection, kwvars)
                    if not fm_updates_ok:
                        logging.error("FileMaker update for hashes failed")
                        raise RuntimeError("the script failed due to a FileMaker-related error at runtime")
                '''
                send file data to various places
                '''
                if kwvars.copy_files:
                    files_moved_ok = move_files(accession_number, output_files, kwvars)
                    if not files_moved_ok:
                        logging.error("file transfer to preservation storage failed")
                        raise RuntimeError("the script failed due to an error at runtime")
                    else:
                        logging.info("files moved successfully")
                        logging.info("copying preservation files")
                        pres_files_copied_ok = copy_pres_files(accession_number, output_files, kwvars)
                        if not pres_files_copied_ok:
                            logging.error("there was an error moving the preservation files to")
                            logging.error(kwvars.config.loc)
                            raise RuntimeError("the script failed due to an error at runtime")
                        else:
                            for file in accession_fullpath.iterdir():
                                logging.debug(file)
                                file.unlink()
                            time.sleep(1)
                            lockfile.unlink()
                            accession_fullpath.rmdir() #deletes accession dir we just processed
                        logging.info(f"accession {accession_number} processed successfully")
                if kwvars.send_email:
                    send_email("ingest notification for " + accession_number,\
                            "processing successful for " + accession_number, str(accession_log_filepath))
            '''
            close the accession log file
            remove the handler
            delete (unlink) the accession log file from the OS
            '''
            accession_log.close()
            logger.removeHandler(accession_log)
            accession_log_filepath.unlink()
    except Exception as e:
        try:
            lockfile_path.unlink()
        except FileNotFoundError:
            pass
        try:
            foo = accession_number
        except Exception:
            accession_number = "startup"
        logging.error(f"processing of accession {accession_number} unsuccessful")
        logging.error("ingest.py encountered an error:")
        logging.error(traceback.format_exc())
        if kwvars.send_email:
            send_email("ingest notification for " + accession_number, \
                "processing unsuccessful for " + accession_number, str(accession_log_filepath))
            accession_log.close()
            logger.removeHandler(accession_log)
            accession_log_filepath.unlink()


if __name__ == "__main__":
    main()
