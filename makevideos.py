#the history makers makevideos.py
#concatenates, transcodes, moves videos for The History Makers

import os
import subprocess
import sys
import glob
import re
import ConfigParser
from distutils import spawn

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

def makelist():
	try:
		flist = []
		#walk through capture directory
		#gather file names based on policy
		#return dictionary of [endfilename : 'startfile1','startfile2','startfie3']
	except:
		#send email to THM staff
	return flist

def ffproces(flist):
	try:
		#iterate thru flist
		#concatenate startfiles into endfile.mov
		#transcode endfiles
			#endfile.flv + HistoryMakers watermark
			#endfile.mpeg + timecode
			#endfile.mp4 + timecode
	except:
		#send email to THM staff
	return

def hashmove(flist,sunnas,xendata,fmConfig):
	try:
		#iterate thru flist
			#hashmove endfile.mov and endfile.mpeg to LTO
				#send SHA1 hashes to FileMaker
			#hashmove endfile.mp4 to SUNNAS/Proxy
				#send SHA1 hash to FileMaker
			#hashmove endfile.flv to "SUNNAS/Digital Archive"
				#send SHA1 hash to FileMaker
	except:
		#send email to THM staff
	return

def playback(flist):
	#iterate thru flist
		#ffplay endfile.mov
		#ffplay endfile.mpeg
		#ffplay endfile.mp4
		#ffplay endfile.flv
	return

def main():
	#initialize a buncha stuff
	config = ConfigParser.ConfigParser()
	config.read(s.path.join(os.cwd(),"video-post-process-config.txt"))
	scriptRepo = config.get('global','scriptRepo')
	watermark = config.get('transcode','watermark')
	rawCaptures = config.get('transcode','rawCaptureDir')
	fileMakerLoc = config.get('fileMaker','location')
	fileMakerlogin = config.get('fileMaker','login')
	fileMakerpwd = config.get('fileMaker','password')
	emailaddy = config.get('global','email')
	sunnas = config.get('fileDestinations','sunnas')
	xendata = config.get('fileDestinations','xendata')
	fmConfig = [fileMakerLoc,fileMakerlogin,FileMakerpwd]
	
	#make a list of things to work on
	flist = makelist()

	#ffprocess
	ffprocess(flist,watermark)

	#hashmove
	hashmove(flist,sunnas,xendata,fmConfig)

	#playback
	playback(flist)

	return

dependencies()
main()