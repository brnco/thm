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
import shutil
import fcntl
import pathlib
import argparse
import configparser
from distutils import spawn
import util
import startup

def get_files_for_ingest(kwargs):
    '''
    parses raw_captures directory for files to work on
    '''
    ingests = util.d({})
    raw_captures = [path for path in kwargs.config.raw_captures.glob('**/*.*') \
            if not any(part.startswith('.') for part in path.parts) \
            and not any(part.startswith('Thumbs.db') for part in path.parts)]
    for file in raw_captures:
        print(file.name)
        grandcestors = str(file.parents[1])
        accession_number = str(file).replace(grandcestors,"").replace(str(file.name),"").replace("/","")
        try:
            ingests[accession_number].append(str(file))
        except:
            ingests[accession_number] = []
            ingests[accession_number].append(str(file))
    log(kwargs.log,str(ingests),False)
    return ingests



#following three functions are called in startup to check that nothing is being copied currently
def sizeloop(thing):
	#print thing
	startsize = os.stat(thing)
	#print startsize.st_size
	time.sleep(1)
	endsize = os.stat(thing)
	#print endsize.st_size
	if startsize.st_size == endsize.st_size:
		return
	else:
		sizeloop(thing)

def walk(pth):
	thefiles =[]
	for dirs, subdirs, files in os.walk(pth):
		for files in files:
			fullpath = os.path.join(dirs,files)
			thefiles.append(fullpath)
	#print thefiles
	for f in thefiles:
		fpath = os.path.join(pth,f)
		sizeloop(fpath)
	return thefiles

def compare(fs, fsagain):
	#print fs
	#print fsagain
	for f in fsagain:
		if not f in fs:
			return False
	return True


def ffprocess(acc,fflist,watermark,fontfile,scriptRepo,logfile):
	#concatenate startfiles into endfile.mov
	with cd(acc): #cd into it
		txtfile = open("concat.txt","w") #initialize a txt file that we'll use to concat
		for rawmov in fflist[acc]: #for each file name in the lsit of filenames associated with this accession#
			txtfile.write("file " + rawmov + "\n") #append the filename to the txt file with a newline
		txtfile.close() #housekeeping
		canonicalname = os.path.basename(acc) #set the canonical name of the recording, e.g. A2016_001_001_001.mov (first entry in list fflist[acc])
		segment = canonicalname.split("_")[-1] #the last set of chars in the sequence is the segment number
		flv = canonicalname + ".flv" #filename for flv
		mpeg = canonicalname + ".mpeg" #filename for mpeg
		mp4 = canonicalname + ".mp4" #filename for mp4
		mov = canonicalname + ".mov"

		concatstr = 'ffmpeg -f concat -i concat.txt -map 0:0 -map 0:1 -map 0:2 -c:v copy -c:a copy -timecode ' + segment[-2:] + ':00:00:00 concat.mov'
		try:
			output = subprocess.check_output(concatstr,stderr=open(logfile,"a+"),shell=True) #concatenate them
			returncode = 0
			log(logfile, "concatenation of raw MOVs successful")
		except (subprocess.CalledProcessError,e):
			output = e.output
			returncode = e.returncode
		if returncode > 0:
			#send email to staff
			msg = 'The concatenation of  ' + canonicalname + ' was unsuccessful\n'
			subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt',msg,'-att',logfile])
			log(logfile,msg)
			sys.exit() #quit now because this concat is really important
		for rawmov in fflist[acc]: #for each raw file name in the list of concats that are the raw captures
			os.remove(rawmov) #delete them (they've been concatted into 1 big ol file successfully)
			if os.path.exists(rawmov + ".md5"): #if they have any associated files get rid of them
				os.remove(rawmov + ".md5")
			if os.path.exists("concat.txt"):
				os.remove("concat.txt") #also delete the txt file because we don't need it anymore

		#transcode endfiles
		#endfile.flv + HistoryMakers watermark
		try:
			flvstr = 'ffmpeg -i concat.mov -i ' + watermark + ' -filter_complex "scale=320:180,overlay=0:0" -c:v libx264 -preset fast -b:v 700k -r 29.97 -pix_fmt yuv420p -c:a aac -map_channel 0.1.0:0.1 -map_channel 0.2.0:0.1 -timecode ' + segment[-2:] + ':00:00:00 -threads 0 ' + flv
			output = subprocess.check_output(flvstr, stderr=open(logfile,"a+"), shell=True)
			returncode = 0
			log(logfile, "transcode to flv successful")
		except (subprocess.CalledProcessError,e):
			output = e.output
			returncode = e.returncode
		if returncode > 0:
			#send email to staff
			msg = 'The transcode to ' + flv + ' was unsuccessful\n'
			subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt',msg,'-att',logfile])
			log(logfile,msg)
			sys.exit()

		#endfile.mpeg + timecode
		#easier to init this var here rather than include it in the ffmpeg call
		drawtext = '"drawtext=fontfile=' + "'" + fontfile + "'" + ": timecode='" + segment[-2:] + "\:00\:00\:00'" + ': r=29.97: x=(w-tw)/2: y=h-(2*lh): fontcolor=white: fontsize=72: box=1: boxcolor=0x00000099'
		try:
			mpegstr = 'ffmpeg -i concat.mov -target ntsc-dvd -map_channel 0.1.0:0.1 -map_channel 0.2.0:0.1 -ac 2 -b:v 5000k -vtag xvid -vf ' + drawtext + ',scale=720:480" -threads 0 ' + mpeg
			subprocess.check_output(mpegstr,stderr=open(logfile,"a+"), shell=True)
			returncode = 0
			log(logfile, "transcode to mpeg successful")
		except (subprocess.CalledProcessError,e):
			output = e.output
			returncode = e.returncode
		if returncode > 0:
			#send email to staff
			msg = 'The transcode to ' + mpeg + ' was unsuccessful\n'
			subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt',msg,'-att',logfile])
			log(logfile,msg)
			sys.exit()

		#endfile.mp4 + timecode
		try:
			mp4str = 'ffmpeg -i concat.mov -c:v mpeg4 -b:v 372k -pix_fmt yuv420p -r 29.97 -vf ' + drawtext + ',scale=420:270" -c:a aac -ar 44100 -map_channel 0.1.0:0.1 -map_channel 0.2.0:0.1 -threads 0 ' + mp4
			subprocess.check_output(mp4str,stderr=open(logfile,"a+"), shell=True)
			returncode = 0
		except (subprocess.CalledProcessError,e):
			output = e.output
			returncode = e.returncode
			log(logfile,"transcode to mp4 successful")
		if returncode > 0:
			#send email to staff
			msg = 'The transcode to ' + mp4 + ' was unsuccessful\n'
			subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt',msg,'-att',logfile])
			log(logfile,msg)
			sys.exit()
		if os.path.exists("concat.mov"):
			os.rename("concat.mov",mov)
	return

def movevids(acc,sunnascopyto,sunnas,xendata,xendatacopyto,xcluster,scriptRepo,logfile):
	hashlist = {}
	extlist = [".mov",".flv",".mp4",".mpeg"]
	s = os.path.basename(acc)
	with cd(acc):
		if os.path.isfile(s + extlist[0]) and os.path.isfile(s + extlist[1]) and os.path.isfile(s + extlist[2]) and os.path.isfile(s + extlist[3]): #if each file extension exists in there

			#copy pres file to lc directory
			log(logfile,"copying archival master to lc folder\n")
			shutil.copy2(os.path.join(acc,s + ".mov"), os.path.join(xcluster,"toLC")) #copy the mov to xendata/copyto


			#move the mov files
			sys.stdout.flush()
			output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),"-a","sha1","-np",os.path.join(acc,s + extlist[0]),xendatacopyto],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			hashes,err = output.communicate()
			log(logfile,hashes)
			sourcehash = re.search('srce\s\S+\s\w{40}',hashes)
			desthash = re.search('dest\s\S+\s\w{40}',hashes)
			dh = desthash.group()
			sh = sourcehash.group()
			if sh[-40:] == dh[-40:]:
				hashlist[s + extlist[0]] = sh[-40:]

			#move the flv file
			#print "moving flv file"
			output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),"-a","sha1","-np",os.path.join(acc,s + extlist[1]),sunnascopyto],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			hashes,err = output.communicate()
			log(logfile, hashes)
			sourcehash = re.search('srce\s\S+\s\w{40}',hashes)
			desthash = re.search('dest\s\S+\s\w{40}',hashes)
			dh = desthash.group()
			sh = sourcehash.group()
			if sh[-40:] == dh[-40:]:
				hashlist[s + extlist[1]] = sh[-40:]

			#move the mp4 file
			#print "moving mp4 file"
			output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),"-a","sha1","-np",os.path.join(acc,s + extlist[2]),sunnascopyto],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			hashes,err = output.communicate()
			log(logfile,hashes)
			sourcehash = re.search('srce\s\S+\s\w{40}',hashes)
			desthash = re.search('dest\s\S+\s\w{40}',hashes)
			dh = desthash.group()
			sh = sourcehash.group()
			if sh[-40:] == dh[-40:]:
				hashlist[s + extlist[2]] = sh[-40:]

			#move the mpeg file
			#print "moving mpeg file"
			output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),"-a","sha1","-np",os.path.join(acc,s + extlist[3]),xendatacopyto],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			hashes,err = output.communicate()
			log(logfile,hashes)
			sourcehash = re.search('srce\s\S+\s\w{40}',hashes)
			desthash = re.search('dest\s\S+\s\w{40}',hashes)
			dh = desthash.group()
			sh = sourcehash.group()
			if sh[-40:] == dh[-40:]:
				hashlist[s + extlist[3]] = sh[-40:]

			#send file hashes to filemaker
			updateFM(hashlist,scriptRepo,logfile)

			time.sleep(5) #give FM a chance to catch up

			#verify hashes
			moveyn = verifyFM(hashlist,scriptRepo,logfile)

			if moveyn is True:
				#move the files to various copytos
				output = subprocess.Popen(["mv",os.path.join(xendatacopyto,s + extlist[0]),os.path.join(xendata,s + extlist[0])],stdout=subprocess.PIPE,stderr=subprocess.PIPE) #copy the mov to xendata
				log(logfile,"moving archival master from copyto")
				output = subprocess.Popen(["mv",os.path.join(xendatacopyto,s + extlist[3]),os.path.join(xendata,s + extlist[3])],stdout=subprocess.PIPE,stderr=subprocess.PIPE) #copy the mpeg to xendata
				log(logfile,"moving mpeg from copyto")
				output = subprocess.Popen(["mv",os.path.join(sunnascopyto,s + extlist[1]),os.path.join(sunnas,s + extlist[1])],stdout=subprocess.PIPE,stderr=subprocess.PIPE) #copy the flv to sunnas
				log(logfile,"moving flv from copyto")
				output = subprocess.Popen(["mv",os.path.join(sunnascopyto,s + extlist[2]),os.path.join(sunnas,s + extlist[2])],stdout=subprocess.PIPE,stderr=subprocess.PIPE) #copy the mp4 to sunnas
				log(logfile,"moving mp4 from copyto")
			else:
				msg = "hashes in FileMaker do not match hashes calculated for one or more files. Files not moved from /copyto.\nSee included log for details"

				subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt', msg,'-att',logfile])
				log(logfile,msg)
		else:
			output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),"-a","sha1","-np",acc,os.path.join(xcluster,"troubleshoot",s)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)

	#cd out of accession dir
	#ok so the accession dir in the capture folder should be empty
	try:
		time.sleep(5)
		log(logfile,"removing " + os.path.join(acc,".DS_Store"))
		if os.path.exists(os.path.join(acc,".DS_Store")):
			os.remove(os.path.join(acc,".DS_Store"))
		log(logfile,"removing accession dir " + acc + " from IncomingQT")
		if os.path.exists(acc):
			os.rmdir(acc)
		#if it's not empty let's move it to a toubleshooting folder
	except:
		output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),"-a","sha1","-np",acc,os.path.join(xcluster,"troubleshoot",s)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	return

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

def verify_startup(kwargs):
    '''
    manages startup of script
    '''
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
    print(raw_captures_files_ok)
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
    print(log_filepath)
    log(log_filepath,"initalizing script and log")
    log(log_filepath,"kwargs object:",False)
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
    kwargs.config.watermark_white = pathlib.Path(config.get('transcode','whitewatermark'))
    kwargs.config.timecode_fontfile = pathlib.Path(config.get('transcode','timecodefont'))
    kwargs.config.raw_captures = pathlib.Path(config.get('transcode','rawCaptureDir'))
    kwargs.config.sunnascopyto = pathlib.Path(config.get('fileDestinations','sunnascopyto'))
    kwargs.config.sunnas = pathlib.Path(config.get('fileDestinations','sunnas'))
    kwargs.config.xendata = pathlib.Path(config.get('fileDestinations','xendata'))
    kwargs.config.xendatacopyto = pathlib.Path(config.get('fileDestinations','xendatacopyto'))
    kwargs.config.xcluster = pathlib.Path(config.get('fileDestinations','xcluster'))
    return kwargs

def init_kwargs():
    '''
    initialize variables and arguments from command line

    "kwargs" = KeyWordArguments - this is a single object/ dictionary that stores msot of our variables
    '''
    parser = argparse.ArgumentParser(description='Process videos for ingest')
    parser.add_argument('input', nargs='*', help='the input folder(s)')
    #parser.add_argument('--sum', dest='accumulate', action='store_const', const=sum, default=max,help='sum the integers (default: find the max)')
    args = parser.parse_args()
    kwargs = util.d({})
    kwargs.script_dir = pathlib.Path(__file__).parent.absolute()
    kwargs.input = args.input
    return kwargs

def main():
    '''
    manages the running of the script
    '''
    kwargs = init_kwargs()
    kwargs = init_config(kwargs)
    kwargs.log = init_log(kwargs)
    startup_ok = verify_startup(kwargs)
    if not startup_ok:
        msg = "ERROR: startup failed"
        log(kwargs.log, msg)
    ingests = get_files_for_ingest(kwargs)
    print(ingests)
    '''
	try:

		#makes a list of files for ffmpeg to transcode
		fflist = makefflist(rawCaptures,logfile)


		for acc in sorted(fflist):
			#actually transcode the files
			ffprocess(acc,fflist,watermark,fontfile,scriptRepo,logfile)

			#hashmove
			movevids(acc,sunnascopyto,sunnas,xendata,xendatacopyto,xcluster,scriptRepo,logfile)

			#notify that it worked for single accession
			msg = "makevideos processed accession " + str(acc) + " successfully"
			subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt', msg])
			log(logfile,msg)

		msg = "makevideos completed successfully"

		subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt', msg,'-att',logfile])
		log(logfile,msg)

	except Exception,e:
		print str(e)
		msg = "The script crashed due to an internal error\n"
		msg = msg + str(e)
		subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt', msg,'-att',logfile])
		log(logfile,msg)
		log(logfile,str(e))
	'''

if __name__ == "__main__":
    main()
