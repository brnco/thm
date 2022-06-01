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
import random
import fcntl
import pathlib
import operator
import argparse
import configparser

'''
import microservice scripts
'''
import util
import startup
import filemaker_handler as fm
import file_validation
import transcodes

'''
functions
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
    log(kwargs.log,"INFO:" + str(ingests),False)
    return ingests

def updateFM(hashlist,scriptRepo,logfile):
	log(logfile,"sending hashes to filemaker")
	for fh in hashlist:
		fname,ext = os.path.splitext(fh)
		fdigi = ext.replace(".","")
		output = subprocess.Popen(["python",os.path.join(scriptRepo,"fm-stuff.py"),"-uSha","-id",fname,"-hash",hashlist[fh],"-fdigi",fdigi],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	return

def verifyFM(hashlist,scriptRepo,logfile):
	log(logfile,"verifying hashes in filemaker")
	verifiedwrong = []
	for fh in hashlist:
		fname,ext=os.path.splitext(fh)
		fdigi = ext.replace(".","")
		sys.stdout.flush()
		output = subprocess.Popen(["python",os.path.join(scriptRepo,"fm-stuff.py"),"-qSha","-id",fname,"-fdigi",fdigi],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		fmhash = output.communicate()
		if any(hashlist[fh] in foo for foo in fmhash):
			log(logfile,"hash of " + str(fh) + " verified correctly as: " + str(fmhash))
		else:
			log(logfile,"hash of " + str(fh) + " verified incorrectly")
			log(logfile,"makevideos calculated hash of: " + hashlist[fh])
			log(logfile,"filemaker hash stored is: " + str(fmhash))
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
    log(kwargs.log,"INFO: moving files from processing dir to preservation")
    '''
    for file in files:
    subprocess.run(rsync file prservation)
    '''
    return True

def hash_files(files, kwargs):
    '''
    creates portable SHA -1 hash for file
    '''
    log(kwargs.log,"INFO: hashing files")
    '''
    dict = {}
    for file in files:
        hash = subprocess(shasum -p)
        dict.file = hash
    '''
    return {"mov":"asdf1234","mp4":"lkjh0987"}

def make_derivatives(accession, input_files, kwargs):
    '''
    manages derivative creation
    '''
    for file in input_files:
        '''
        mp4 with timecode
        accession_tc.mp4
        '''
        mp4_with_tc_ok = transcodes.make_mp4_with_tc(accession, file, kwargs)
        if not mp4_with_tc_ok:
            log(kwargs.log,"ERROR: creation of mp4 with burned-in timecode failed")
            return False
        '''
        mp4 with watermark
        accession_wm.mp4
        '''
        mp4_with_logo_ok = transcodes.make_mp4_with_logo(accession, file, kwargs)
        if not mp4_with_logo_ok:
            log(kwargs.log,"ERROR: creation of mp4 with watermark failed")
            return False
        '''
        mpeg file for DVD
        accession_dvd.mpeg
        '''
        mpeg_dvd_ok = transcodes.make_mpeg(accession, file, kwargs)
        if not mpeg_dvd_ok:
            log(kwargs.log,"ERROR: creation of mpeg DVD file failed")
            return False
        '''
        mezzanine mxf
        mezz.mxf
        '''
        mxf_mezz_ok = transcodes.make_mxf_mezz(accession, file, kwargs)
        if not mxf_mezz_ok:
            log(kwargs.log,"ERROR: creation of mxf mezzanine failed")
            return False
    return [mp4_with_tc_ok, mp4_with_logo_ok, mxf_mezz_ok]

def process_accession(accession, files, cursor, filemaker_connection, kwargs):
    '''
    manages processing of single accession
    '''
    log(kwargs.log,"INFO: Processing accession " + accession)
    '''
    concatenates files by default
    flag for --no_concatenation evaluated here

    files variable changes value based on output from transcodes:
    input is list of raw files in accession directory
    output is list of single concatenated file, named for accession_pres.mov
    '''
    accession_fullpath = kwargs.config.raw_captures / accession
    with util.cd(str(accession_fullpath)):
        if kwargs.input_concatenation:
            log(kwargs.log,"INFO: concatenating raw files in accession dir: " + str(accession_fullpath))
            files, logs = transcodes.concatenate_raw_captures(accession, files, kwargs)
            for _log in logs:
                log(kwargs.log,_log)
            if not files:
                log(kwargs.log,"ERROR: concatenation failed")
                return False
    '''
    make derivatives in transcode script
    '''
    files = make_derivatives(accession, files, kwargs)
    if not files:
        log(kwargs.log,"ERROR: derivative creation failed")
        return False
    '''
    create checksums for each derivative
    '''
    hashes = hash_files(files, kwargs)
    if not hashes:
        log(kwargs.log,"ERROR: file hashing failed, see log")
        return False
    '''
    send checksums to filemaker
    file transfers are validated post-ingest by Mark Strecker's Java script
    '''
    kwargs.id = accession
    for filetype in hashes.keys():
        kwargs.format_digital = filetype
        kwargs.hash = hashes[filetype]
        fm_updates_ok = fm.update_hash(accession, cursor, filemaker_connection, kwargs)
        if not fm_updates_ok:
            log(kwargs.log,"ERROR: FileMaker update for hashes failed, see log")
            return False
    '''
    send file data to various places
    '''
    files_moved_ok = move_files(accession, files, kwargs)
    if not files_moved_ok:
        log(kwargs.log,"ERROR: file transfer to preservation storage failed, see log")
        return False
    return True

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
        msg = "ERROR: makevideos is already running"
        log(kwargs.log,msg)
        return False
    drives_ok = startup.verify_config_drivepaths(kwargs)
    if not drives_ok:
        msg = "ERROR: drives not found"
        log(kwargs.log,msg)
        return False
    timecode_and_watermark_files_ok = startup.verify_config_filepaths(kwargs)
    if not timecode_and_watermark_files_ok:
        msg = "ERROR: timecode and/or watermark files not found"
        log(kwargs.log, msg)
        return False
    raw_captures_files_ok = startup.verify_raw_captures(kwargs)
    if not raw_captures_files_ok:
        msg = "ERROR: files not found in raw capture directory"
        log(kwargs.log, msg)
        return False
    return True

def log(logfile,msg,p=True,e=False):
    '''
    defines the logging function
    '''
    with open(logfile,"a") as txtfile:
        txtfile.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        txtfile.write(msg)
        txtfile.write("\n")
    if p:
        print(msg)
    if e:
        print("send email goes here")
        #send email.py

def init_log(kwargs):
    '''
    initalizes log file location
    '''
    log_filename = pathlib.Path("log-" + time.strftime("%Y-%m-%d %H-%M-%S", time.localtime()) + ".txt")
    log_filepath = str(kwargs.config.logs_path / log_filename)
    log(log_filepath,"INFO: initalizing script and log")
    log(log_filepath,"INFO: kwargs object:",False)
    log(log_filepath,str(kwargs),False)
    return log_filepath

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
    return kwargs

def init_kwargs():
    '''
    initialize variables and arguments from command line

    "kwargs" = KeyWordArguments - this is a single object/ dictionary that stores msot of our variables
    '''
    parser = argparse.ArgumentParser(description='Process videos for ingest')
    parser.add_argument('input', nargs='*', help='the input folder(s)')
    parser.add_argument('--no_concat', action='store_true', default=False, help="disable concatenation of input files")
    parser.add_argument('--continue_on_error', action='store_true', default=False, help="continue processing accessions even if 1 fails")
    parser.add_argument('--mediaconch_policy', default="", help="run input/output validation against specified mediaconch policy at path")
    parser.add_argument('--no_input_validation', action='store_true', default=False, help="disable mediaconch file validation on input files")
    parser.add_argument('--no_output_validation', action='store_true', default=False, help="disable mediaconch file validation on output files")
    parser.add_argument('--make_test_files', action='store_true', default=False, help="create test output files using ffmpeg")
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
    return kwargs

def main():
    '''
    manages the running of the script
    '''
    '''
    initialization
    '''
    kwargs = init_kwargs()
    kwargs = init_config(kwargs)
    kwargs.log = init_log(kwargs)
    startup_ok = verify_startup(kwargs)
    if not startup_ok:
        msg = "ERROR: startup failed"
        log(kwargs.log, msg)
        kwargs.config.lockfile.unlink()
        quit()
    '''
    determine if script is running in test mode
    '''
    if kwargs.mtf:
        make_test_files(kwargs)
        quit()
    '''
    create ingest list
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
            log(kwargs.log,"ERROR: FileMaker record not found for " + accession)
            kwargs.config.lockfile.unlink()
            quit()
        else:
            '''
            do input validation on each file, if requested
            '''
            if kwargs.input_validation:
                log(kwargs.log,"INFO: running mediaconch policies against input files to determine valid inputs")
                accession_mediaconch_policy, logs = file_validation.validate_input(accession, ingests[accession], kwargs)
                for _log in logs:
                    log(kwargs.log,_log)
                if not accession_mediaconch_policy:
                    log(kwargs.log,"ERROR: mediainfo input validation failed for accession " + str(accession) + ", quitting")
                    kwargs.config.lockfile.unlink()
                    quit()
                else:
                    kwargs.accession_mediaconch_policy = accession_mediaconch_policy
            '''
            actually process/ transcode/ hash the files
            '''
            processing_ok = process_accession(accession, ingests[accession], cursor, filemaker_connection, kwargs)
            if not processing_ok:
                log(kwargs.log,"ERROR: processing for accession " + accession + " failed. See log for details")
                if kwargs.continue_on_error:
                    pass
                else:
                    log(kwargs.log,"INFO: script instructed to quit on processing error. Exiting...")
                    break
            else:
                '''
                do output validation on each file, if requested
                '''
                if kwargs.output_validation:
                    outputs_ok = file_validation.validate_output(accession, ingests[accession], kwargs)
                log(kwargs.log,"INFO: accession " + accession + " processed successfully")
    kwargs.config.lockfile.unlink() #delete lockfile so script knows it's not already running

if __name__ == "__main__":
    main()
