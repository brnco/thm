#the history makers makevideos.py
#concatenates, transcodes, moves videos for The History Makers

import os
import subprocess
import sys
import glob
import re
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
				rawfs.append(os.path.join(dirs,f))
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
	hm1list = {}
	for f in flist:
		ayear,acc = f.split("_")
		xcldirpath = os.path.join(xcluster,ayear,acc)
		for mov in flist[f]:
			output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),mov,xcldirpath,"-c"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	return

def makefflist(xcluster,watermark):
	#try:
	fflist = {}
	
	for dirs, subdirs,files in os.walk(xcluster):
		for acc in subdirs:
			if not acc.startswith("A"):
				with cd(os.path.join(dirs,acc)):
					rawcaplist = []
					for rawmov in os.listdir(os.getcwd()):
						if rawmov.endswith(".mov"):
							rawcaplist.append(rawmov)
					fflist[os.path.join(dirs,acc)] = sorted(rawcaplist)
	return fflist

def printconcats(fflist):	
	for acc in fflist:
		with cd(acc):
			txtfile = open("concat.txt","w")
			for rawmov in fflist[acc]:
				txtfile.write("file " + rawmov + "\n")
			txtfile.close
	return 

def ffprocess(fflist):
	#concatenate startfiles into endfile.mov
	for acc in fflist:
		output = fflist[acc][0]
		output = output.replace(".mov","-concat.mov")
		print output
		foo = raw_input("eh")
		with cd(acc):
			print os.getcwd()
			output = subprocess.Popen(["ffmpeg","-f","concat","-i","concat.txt","-c","copy",output],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			foo,err = output.communicate()
			#print foo
			#print err
	#transcode endfiles
		#endfile.flv + HistoryMakers watermark
		#endfile.mpeg + timecode
		#endfile.mp4 + timecode
	foo = blah
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
	#initialize a buncha stuff

	scriptRepo = os.path.dirname(os.path.abspath(__file__))
	config = ConfigParser.ConfigParser()
	config.read(os.path.join(scriptRepo,"video-post-process-config.txt"))
	watermark = config.get('transcode','watermark')
	rawCaptures = config.get('transcode','rawCaptureDir')
	#fileMakerLoc = config.get('fileMaker','location')
	#fileMakerlogin = config.get('fileMaker','login')
	#fileMakerpwd = config.get('fileMaker','password')
	#fmConfig = [fileMakerLoc,fileMakerlogin,FileMakerpwd]
	emailaddy = config.get('global','email')
	harddrive = config.get('fileDestinations','hardDrivePath')
	sunnas = config.get('fileDestinations','sunnas')
	xendata = config.get('fileDestinations','xendata')
	xcluster = config.get('fileDestinations','xcluster')
	
	#grab args fromCLI
	parser = argparse.ArgumentParser(description="concatenates, transcodes, hashmvoes videos")
	#parser.add_argument("-i","--ignore",action="store_true",default=False,help="ignore policy errors")
	parser.add_argument("-s","--single",help="single mode, only process a single accession. takes canonical foldername as arg e.g.A2016_012_001_000")
	parser.add_argument("-skiphd","--skipharddrive",dest="shd",action="store_true",default=False,help="skip the step of moving things from the hard drive, process from xcluster only")
	args = vars(parser.parse_args())
	
	if args['shd'] is False:
		#make a list of things to work on
		flist = makemovelist(harddrive)

		#move files from hard drive to xcluster
		hashmove1(flist,scriptRepo,harddrive,xcluster)

	#ffprocess
	fflist = makefflist(xcluster,watermark)
	
	#print the concat.txt files in each accession dir, via fflsit
	printconcats(fflist)

	ffprocess(fflist)

	#hashmove
	#hashmove2(flist,sunnas,xendata)

	return

dependencies()
main()