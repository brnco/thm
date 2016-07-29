#the history makers makevideos.py
#concatenates, transcodes, moves videos for The History Makers

import os
import sys
import subprocess
import sys
import glob
import re
import time
import argparse
import ConfigParser
from distutils import spawn
blah = 'foo'

#Context manager for changing the current working directory
class cd:
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
		os.chdir(self.savedPath)


#check that we have required software installed
def dependencies():
	depends = ['ffmpeg','ffprobe']
	for d in depends:
		if spawn.find_executable(d) is None:
			print "Buddy, you gotta install " + d
			sys.exit()
	return

def makemovelist(harddrive):
	#try:
	flist = {}
	accessionlist = []
	rawfs = []
	for dirs, subdirs, files in os.walk(harddrive): #walk through capture directory
		for f in files: #for each file found
			if f.endswith(".mov"): #if it's a mov
				rawfs.append(os.path.join(dirs,f)) #append the full path to the raw files to the rawfs list
				ayear, acc, rest = f.split("_",2) #split the file name into 3 parts, the year, the accession#, everything else
				if not acc in accessionlist: #if the accession# isn't already in our list of accession#s
					accessionlist.append(ayear + "_" + acc) #appens the Ayear_accession# to the list of accession#s
	for acc in accessionlist: #for each acession# in our list of accession#s
		result = [] #init a list for the files found that are part of this accession
		for f in rawfs: #iterate thru the file list again
			match = re.search(acc + "_\d{3}_\d{3}.mov",f) #file matches the naming convention, with the accession# in it "A\d{4}_" + 
			if match: #if yes the above ^^ did work
				result.append(f) #write it to a list of matches	
		flist[acc] = sorted(result) #sort the list, append to a dictionary of {'acc#' : 'list of fullpath/files for the accession'} pairs
	#except:
		#foo = blah
		#send email to THM staff
	return flist

def hashmove1(flist,scriptRepo,harddrive,xcluster):
	for f in flist: #loop thru list of files on the hard drive
		ayear,acc = f.split("_") #split the ayear and accession# values at the underscore
		xcldirpath = os.path.join(xcluster,ayear,acc) #make a string for the directory path on xcluster that these files will soon inhabit
		for mov in flist[f]: #flist[f] returns a list of files, loop thru that
			#use hashmove to move them to xcluster
			output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),mov,xcldirpath,"-c"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	return

def makefflist(xcluster):
	fflist = {} #initialize a list of files for ffmpeg to transcode
	for dirs, subdirs,files in os.walk(xcluster): #loop thru holding dir on xcluster
		for acc in subdirs: #for each accession# (subdir) in the list of subdirs
			if not acc.startswith("A"): #don't worry about the Ayear dirs
				with cd(os.path.join(dirs,acc)): #cd into accession dir
					rawcaplist = [] #init a list that will contain raw captures in each dir
					for rawmov in os.listdir(os.getcwd()): #for each file in the current working directory
						if rawmov.endswith(".mov"): #if it is a mov
							rawcaplist.append(rawmov) #append it to our list of raw captures
					fflist[os.path.join(dirs,acc)] = sorted(rawcaplist) #add the list of ['rawcapture filenames'] to a dict key of 'full path to accession# on xcluster'
	return fflist

def printconcats(fflist):	
	for acc in fflist: #for each accession full path on xcluster
		with cd(acc): #cd into it
			txtfile = open("concat.txt","w") #initialize a txt file that we'll use to concat
			for rawmov in fflist[acc]: #for each file name in the lsit of filenames associated with this accession#
				txtfile.write("file " + rawmov + "\n") #append the filename to the txt file with a newline
			txtfile.close #housekeeping
	return 

def ffprocess(fflist,watermark,fontfile,scriptrepo):
	#concatenate startfiles into endfile.mov
	for acc in fflist: #for each accession full path on xcluster
		canonicalname = fflist[acc][0] #set the canonical name of the recording, e.g. A2016_001_001_001.mov (first entry in list fflist[acc])
		canonicalname = canonicalname.replace(".mov","") #drop the extension
		flv = canonicalname + ".flv" #filename for flv
		mpeg = canonicalname + ".mpeg" #filename for mpeg
		mp4 = canonicalname + ".mp4" #filename for mp4
		with cd(acc): #ok, cd into the accession dir
			print "concatenating raw captures"
			try:
				output = subprocess.check_output(["ffmpeg","-f","concat","-i","concat.txt","-c","copy","concat.mov"]) #concatenate them
				returncode = 0
			except subprocess.CalledProcessError,e: #check for an error
				output = e.output
				returncode = e.returncode
			if returncode > 0: #if there was an error
				print "concat fail" #tell the user
				#send email to staff
				subprocess.call(['python',os.path.join(scriptrepo,"send-email.py"),'-txt','The concatenation of  ' + canonicalname + ' was unsuccessful\n' + strftime("%Y-%m-%d %H:%M:%S", gmtime())])
				sys.exit() #quit now because this concat is really important
			if returncode == 0: #if there wasn't an error
				for rawmov in fflist[acc]: #for each raw file name in the list of concats that are the raw captures
					os.remove(rawmov) #delete them (they've been concatted into 1 big ol file successfully)
					if os.path.exists(rawmov + ".md5"): #if they have any associated files get rid of them
						os.remove(rawmov + ".md5")
	
				os.remove("concat.txt") #also delete the txt file because we don't need it anymore

			#transcode endfiles
			#endfile.flv + HistoryMakers watermark
			print "transcoding to flv with HM watermark"
			try:
				output = subprocess.check_output(["ffmpeg","-i","concat.mov","-i",watermark,"-filter_complex","overlay=x=(main_w-overlay_w)/2:y=(main_h-overlay_h)/1.2","-c:v","libx264","-preset","fast","-c:a","copy",flv])
				returncode = 0
			except subprocess.CalledProcessError,e:
				output = e.output
				returncode = e.returncode
			if returncode > 0:
				print "flv transcode fail"
				#send email to staff
				subprocess.call(['python',os.path.join(scriptrepo,"send-email.py"),'-txt','The transcode to ' + flv + ' was unsuccessful\n' + strftime("%Y-%m-%d %H:%M:%S", gmtime())])
			#endfile.mpeg + timecode
			print "transcoding to mpeg with timecode"
			#easier to init this var here rather than include it in the ffmpeg call
			drawtext = "drawtext=fontfile=" + fontfile + ": timecode='09\:57\:00\:00': r=23.976: x=(w-tw)/2: y=h-(2*lh): fontcolor=white: box=1: boxcolor=0x00000099"
			try:
				subprocess.check_output(["ffmpeg","-i","concat.mov","-c:v","mpeg4","-vtag","xvid","-vf",drawtext,"-c:a","copy",mpeg])
				returncode = 0
			except subprocess.CalledProcessError,e:
				output = e.output
				returncode = e.returncode
			if returncode > 0:
				print "mpeg transcode fail"
				#send email to staff
				subprocess.call(['python',os.path.join(scriptrepo,"send-email.py"),'-txt','The transcode to ' + mpeg + ' was unsuccessful\n' + strftime("%Y-%m-%d %H:%M:%S", gmtime())])
			#endfile.mp4 + timecode
			print "transcoding to mp4 with timecode"
			try:
				subprocess.check_output(["ffmpeg","-i","concat.mov","-c:v","libx264","-preset","fast","-vf",drawtext,"-c:a","copy",mp4])
				returncode = 0
			except subprocess.CalledProcessError,e:
				output = e.output
				returncode = e.returncode
			if returncode > 0:
				print "mp4 transcode fail"
				#send email to staff
				subprocess.call(['python',os.path.join(scriptrepo,"send-email.py"),'-txt','The transcode to ' + mp4 + ' was unsuccessful\n' + strftime("%Y-%m-%d %H:%M:%S", gmtime())])
			os.rename("concat.mov",flist[acc][0])
	return	

def hashmove2(flist,sunnas,xendata):
	try:
		foo = blah
		#iterate thru flist
			#hashmove endfile.mov and endfile.mpeg to LTO
				#send SHA1 hashes to FileMaker
			#hashmove endfile.mp4 to SUNNAS/Proxy
				#send SHA1 hash to FileMaker
			#hashmove endfile.flv to "SUNNAS/Digital Archive"
				#send SHA1 hash to FileMaker
	except:
		foo = blah
		
		#send email to THM staff
	return



def main():
	#initialize a buncha paaths to various resources
	scriptRepo = os.path.dirname(os.path.abspath(__file__))
	config = ConfigParser.ConfigParser()
	config.read(os.path.join(scriptRepo,"video-post-process-config.txt"))
	watermark = config.get('transcode','watermark')
	fontfile = config.get('transcode','timecodefont')
	rawCaptures = config.get('transcode','rawCaptureDir')
	emailaddy = config.get('global','email')
	harddrive = config.get('fileDestinations','hardDrivePath')
	sunnas = config.get('fileDestinations','sunnas')
	xendata = config.get('fileDestinations','xendata')
	xcluster = config.get('fileDestinations','xcluster')
	
	#grab args fromCLI
	parser = argparse.ArgumentParser(description="concatenates, transcodes, hashmoves videos")
	#parser.add_argument("-s","--single",help="single mode, only process a single accession. takes canonical foldername as arg e.g.A2016_012_001_000")
	parser.add_argument("-skiphd","--skipharddrive",dest="shd",action="store_true",default=False,help="skip the step of moving things from the hard drive, process from xcluster only")
	args = vars(parser.parse_args())
	
	#if we're grabbing files from the hard drive, start here
	if args['shd'] is False:
		#make a list of things to work on
		flist = makemovelist(harddrive)

		#move files from hard drive to xcluster
		hashmove1(flist,scriptRepo,harddrive,xcluster)
		
		#gives teh registry a couple seconds to understand what just happened
		time.sleep(2)
	

	#makes a list of files for ffmpeg to transcode
	fflist = makefflist(xcluster)
	
	#print the concat.txt files in each accession dir, via fflist
	printconcats(fflist)

	#actually transcode the files
	ffprocess(fflist,watermark,fontfile,scriptrepo)

	#hashmove
	#hashmove2(flist,sunnas,xendata)

	return

dependencies()
main()