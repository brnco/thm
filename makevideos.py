#!/usr/bin/python
#the history makers makevideos.py
#concatenates, transcodes, moves videos for The History Makers

import os
import sys
import subprocess
import sys
import glob
import re
import time
import random
import fcntl
import pathlib
import operator
import argparse
import configparser
import util
import startup
import filemaker_handler as fm
import file_validation

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

def run_ffmpeg(cmd, kwargs):
    '''
    runs cmd for ffmpeg
    '''
    log(kwargs.log,"INFO: running ffmpeg with below command:")
    log(kwargs.log,cmd)
    try:
        proc = subprocess.Popen(cmd, check=True)
        stdout, stderr = proc.communicate()
        log(kwargs.log,"INFO: ffmpeg completed successfully")
        return True
    except CalledProcessError as e:
        log(kwargs.log,"ERROR: ffmpeg encountered an error")
        log(kwargs.log,"ERROR: see ffmpeg stderr output below:")
        log(kwargs.log,str(e.stderr))
        return False

def make_mpg(accession, file, kwargs):
    '''
    make mpg for dvd
    '''
    #endfile.mpeg + timecode
    drawtext = '"drawtext=fontfile=' + "'" + str(kwargs.config.timecode_fontfile) + "'" + ": timecode='00\:00\:00\:00'" + ': r=29.97: x=(w-tw)/2: y=h-(2*lh): fontcolor=white: fontsize=72: box=1: boxcolor=0x0000009    9'
    mpegstr = 'ffmpeg -i concat.mov -target ntsc-dvd -map_channel 0.1.0:0.1 -map_channel 0.2.0:0.1 -ac 2 -b:v 5000k -vtag xvid -vf ' + drawtext + ',scale=720:480" -threads 0 ' + mpeg

def make_mp4_with_tc(accession, file, kwargs):
    '''
    creates mp4 with burned in timecode
    '''
    log(kwargs.log,"INFO: creating mp4 derivative with burned-in timecode")
    mp4 = accession + ".mp4"
    drawtext = '"drawtext=fontfile=' + "'" + str(kwargs.config.timecode_fontfile) + "'" + ": timecode='00\:\:00\:00\:00'" + ': r=29.97: x=(w-tw)/2: y=h-(2*lh): fontcolor=white: fontsize=72: box=1: boxcolor=0x0000009    9'
    ffmpeg_cmd = 'ffmpeg -i concat.mov -c:v mpeg4 -b:v 372k -pix_fmt yuv420p -r 29.97 -vf ' + drawtext + ',scale=420:270" -c:a aac -ar 44100 -map_channel 0.1.0:0.1 -map_channel 0.2.0:0.1 -threads 0 ' + mp4
    return mp4

def make_mp4_with_logo(accession, file, kwargs):
    '''
    creates mp4 derivative with logo
    '''
    log(kwargs.log,"INFO: creating mp4 derivative with logo")
    return str(accession) + "-logo.mp4"

def make_mxf_mezz(accession, file, kwargs):
    '''
    creates mxf mezzanine file
    '''
    log(kwargs.log,"INFO: creating mxf mezzanine file")
    return str(accession) + ".mxf"

def make_derivatives(accession, input_files, kwargs):
    '''
    manages derivative creation
    '''
    for file in input_files:
        mp4_with_tc_ok = make_mp4_with_tc(accession, file, kwargs)
        if not mp4_with_tc_ok:
            log(kwargs.log,"ERROR: creation of mp4 with burned-in timecode failed")
            return False
        mp4_with_logo_ok = make_mp4_with_logo(accession, file, kwargs)
        if not mp4_with_logo_ok:
            log(kwargs.log,"ERROR: creation of mp4 with watermark failed")
            return False
        #make_mpg(accession, file, kwargs)
        mxf_mezz_ok = make_mxf_mezz(accession, file, kwargs)
        if not mxf_mezz_ok:
            log(kwargs.log,"ERROR: creation of mxf mezzanine failed")
            return False
    return [mp4_with_tc_ok, mp4_with_logo_ok, mxf_mezz_ok]

def concatenate_raw_captures(accession, files, kwargs):
    '''
    setup accession directory for ffmpeg transcode to concatenate raw captures
    '''
    accession_dir = files[0].parent
    log(kwargs.log,"INFO: concatenating input files in directory " + accession_dir)
    concat_txt_path = accession_dir / "concat.txt"
    concat_mov = accession_dir / "concat.mov"
    accession_mov = accession_dir / accession + ".mov"
    with open(concat_txt_path,"a") as concat_txt:
        for file in files:
            concat_txt.write(str(file.name))
    ffmpeg_cmd = 'ffmpeg -f concat -i concat.txt -map 0:0 -map 0:1 -map 0:2 -c:v copy -c:a copy -timecode ' + segment[-2:] + ':00:00:00 concat.mov'
    ffmpeg_ok = run_ffmpeg(ffmpeg_cmd)
    if not ffmpeg_ok:
        log(kwargs.log,"ERROR: ffmpeg encountered an error during concatenation")
        return False
    else:
        log(kwargs.log,"INFO: concatenation completed successfully")
        concat_mov.replace(accession_mov)
        concat_txt_path.unlink()
        return [accession_mov]
        
def process_accession(accession, files, cursor, filemaker_connection, kwargs):
    '''
    manages processing of single accession
    '''
    log(kwargs.log,"INFO: Processing accession " + accession)
    if kwargs.concat:
        files = concatenate_raw_captures(accession, files, kwargs)
        if not files:
            log(kwargs.log,"ERROR: concatenation failed")
            return False
    files = make_derivatives(accession, files, kwargs)
    if not files:
        log(kwargs.log,"ERROR: derivative creation failed")
        return False
    hashes = hash_files(files, kwargs)
    if not hashes:
        log(kwargs.log,"ERROR: file hashing failed, see log")
        return False
    kwargs.id = accession
    for filetype in hashes.keys():
        kwargs.format_digital = filetype
        kwargs.hash = hashes[filetype]
        fm_updates_ok = fm.update_hash(accession, cursor, filemaker_connection, kwargs)
        if not fm_updates_ok:
            log(kwargs.log,"ERROR: FileMaker update for hashes failed, see log")
            return False
    files_moved_ok = move_files(accession, files, kwargs)
    if not files_moved_ok:
        log(kwargs.log,"ERROR: file transfer to preservation storage faield, see log")
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

def log(logfile,msg,p=True):
    '''
    defines the logging function
    '''
    if p:
        print(msg)
    with open(logfile,"a") as txtfile:
        txtfile.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        txtfile.write("\n")
        txtfile.write(msg)
        txtfile.write("\n")

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
    parser.add_argument('-c','--concat', action='store_true', default=False, help="concatenate input files")
    parser.add_argument('--continue_on_error', action='store_true', default=False, help="continue processing accessions even if 1 fails")
    parser.add_argument('--mediaconch_policy', default="", help="run input/output validation against specified mediaconch policy at path")
    parser.add_argument('--no_input_validation', action='store_true', default=False, help="disable mediaconch file validation on input files")
    parser.add_argument('--no_output_validation', action='store_true', default=False, help="disable mediaconch file validation on output files")
    parser.add_argument('--make_test_files', action='store_true', default=False, help="create test output file susing ffmpeg")
    args = parser.parse_args()
    kwargs = util.d({})
    kwargs.script_dir = pathlib.Path(__file__).parent.absolute()
    kwargs.input = args.input
    kwargs.concat = args.concat
    kwargs.mtf = args.make_test_files
    #next two lines flip the boolean values for input/ output validation
    #makes the code more readable in main()
    kwargs.input_validation = operator.not_(args.no_input_validation)
    kwargs.output_validation = operator.not_(args.no_output_validation)
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

