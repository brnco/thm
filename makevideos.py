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
import argparse
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

def makepid(pid):
	txtfile = open(pid, "wb"):
	txtfile.write("makevideos - " + time.strftime("%Y-%m-%d %H:%M:%S", gmtime()) + " \n")
	txtfile.close()
	return
	
def makefflist(rawCaptures):
	fflist = {} #initialize a list of files for ffmpeg to transcode
	for dirs, subdirs, files in os.walk('"' + rawCaptures + '"'): #loop thru holding dir on xcluster
		print "in loop"
		for acc in subdirs: #for each accession# (subdir) in the list of subdirs
			print acc
			with cd(os.path.join(dirs,acc)): #cd into accession dir
				rawcaplist = [] #init a list that will contain raw captures in each dir
				for rawmov in os.listdir(os.getcwd()): #for each file in the current working directory
					if rawmov.endswith(".mov") or rawmov.endswith(".MOV"): #if it is a mov
						print rawmov
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
	for acc in fflist: #for each accession full path on xcluster/IncomingQT
		canonicalname = os.path.basename(acc) #set the canonical name of the recording, e.g. A2016_001_001_001.mov (first entry in list fflist[acc])
		ayear,accNum,intNum,segment = canonicalname.split("_")
		flv = canonicalname + ".flv" #filename for flv
		mpeg = canonicalname + ".mpeg" #filename for mpeg
		mp4 = canonicalname + ".mp4" #filename for mp4
		mov = canonicalname + ".mov"
		with cd(acc): #ok, cd into the accession dir
			print "concatenating raw captures"
			try:
				concatstr = 'ffmpeg -f concat -i concat.txt -map 0:0 -map 0:1 -map 0:2 -c:v copy -c:a copy -timecode ' + segment[-2:] + ':00:00:00 concat.mov'
				print concatstr
				output = subprocess.check_output(concatstr, shell=True) #concatenate them
				returncode = 0
			except subprocess.CalledProcessError,e: #check for an error
				output = e.output
				returncode = e.returncode
			if returncode > 0: #if there was an error
				print "concat fail" #tell the user
				#send email to staff
				subprocess.call(['python',os.path.join(scriptrepo,"send-email.py"),'-txt','The concatenation of  ' + canonicalname + ' was unsuccessful\n' + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())])
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
				flvstr = 'ffmpeg -i concat.mov -i "' + watermark + '"' + ' -filter_complex "scale=320:180,overlay=0:0" -c:v libx264 -preset fast -b:v 700k -r 29.97 -pix_fmt yuv420p -c:a aac -map_channel 0.1.0:0.1 -map_channel 0.2.0:0.1 -timecode ' + segment[-2:] + ':00:00:00 ' + flv
				print flvstr
				output = subprocess.check_output(flvstr, shell=True)
				returncode = 0
			except subprocess.CalledProcessError,e:
				output = e.output
				returncode = e.returncode
			if returncode > 0:
				print "flv transcode fail"
				#send email to staff
				subprocess.call(['python',os.path.join(scriptrepo,"send-email.py"),'-txt','The transcode to ' + flv + ' was unsuccessful\n' + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())])
			

			#endfile.mpeg + timecode
			print "transcoding to mpeg with timecode"
			#easier to init this var here rather than include it in the ffmpeg call
			drawtext = '"drawtext=fontfile=' + "'" + fontfile + "'" + ": timecode='" + segment[-2:] + "\:00\:00\:00'" + ': r=29.97: x=(w-tw)/2: y=h-(2*lh): fontcolor=white: fontsize=72: box=1: boxcolor=0x00000099'
			try:
				mpegstr = 'ffmpeg -i concat.mov -map_channel 0.1.0:0.0 -map_channel 0.2.0:0.0 -map 0:0 -c:a mp2 -ar 48000 -sample_fmt s16 -c:v mpeg2video -pix_fmt yuv420p -r 29.97 -vtag xvid -vf ' + drawtext + ',scale=720:480" ' + mpeg
				subprocess.check_output(mpegstr, shell=True)
				returncode = 0
			except subprocess.CalledProcessError,e:
				output = e.output
				returncode = e.returncode
			if returncode > 0:
				print "mpeg transcode fail"
				#send email to staff
				subprocess.call(['python',os.path.join(scriptrepo,"send-email.py"),'-txt','The transcode to ' + mpeg + ' was unsuccessful\n' + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())])
			

			#endfile.mp4 + timecode
			print "transcoding to mp4 with timecode"
			try:
				mp4str = 'ffmpeg -i concat.mov -c:v mpeg4 -b:v 372k -pix_fmt yuv420p -r 29.97 -vf ' + drawtext + ',scale=420:270" -c:a aac -ar 441000 -map_channel 0.1.0:0.1 -map_channel 0.2.0:0.1 ' + mp4
				subprocess.check_output(mp4str, shell=True)
				returncode = 0
			except subprocess.CalledProcessError,e:
				output = e.output
				returncode = e.returncode
			if returncode > 0:
				print "mp4 transcode fail"
				#send email to staff
				subprocess.call(['python',os.path.join(scriptrepo,"send-email.py"),'-txt','The transcode to ' + mp4 + ' was unsuccessful\n' + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())])
			os.rename("concat.mov",mov)
	return	

def movevids(rawCaptures,sunnas,xendata,xcluster,scriptRepo):
	hashlist = {}
	extlist = [".mov",".flv",".mp4",".mpeg"]
	for dirs, subdirs, files in os.walk(rawCaptures):
		for s in subdirs:
			with cd(s):
				if os.path.isfile(s + extlist[0]) and os.path.isfile(s + extlist[1]) and os.path.isfile(s + extlist[2]) and os.path.isfile(s + exlist[3]): #if each file extension exists in there
					#move the mov files
					output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),os.path.join(dirs,s,s + extlist[0]),os.path.join(xendata,s)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
					hashes,err = output.communicate()
					print hashes
					sourcehash = re.search('srce\s\S+\s\w{32}',hashes)
					desthash = re.search('dest\s\S+\s\w{32}',hashes)
					dh = desthash.group()
					sh = sourcehash.group()
					if sh[-32:] == dh[-32:]:
						hashlist[s + extlist[0]] = sh

					#move the flv file
					output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),os.path.join(dirs,s,s + extlist[1]),os.path.join(xendata,s)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
					hashes,err = output.communicate()
					print hashes
					sourcehash = re.search('srce\s\S+\s\w{32}',hashes)
					desthash = re.search('dest\s\S+\s\w{32}',hashes)
					dh = desthash.group()
					sh = sourcehash.group()
					if sh[-32:] == dh[-32:]:
						hashlist[s + extlist[1]] = sh
					
					#move the mp4 file
					output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),os.path.join(dirs,s,s + extlist[2]),os.path.join(xendata,s)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
					hashes,err = output.communicate()
					print hashes
					sourcehash = re.search('srce\s\S+\s\w{32}',hashes)
					desthash = re.search('dest\s\S+\s\w{32}',hashes)
					dh = desthash.group()
					sh = sourcehash.group()
					if sh[-32:] == dh[-32:]:
						hashlist[s + extlist[2]] = sh
						
					#move the mpeg file
					output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),os.path.join(dirs,s,s + extlist[3]),os.path.join(xendata,s)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
					hashes,err = output.communicate()
					print hashes
					sourcehash = re.search('srce\s\S+\s\w{32}',hashes)
					desthash = re.search('dest\s\S+\s\w{32}',hashes)
					dh = desthash.group()
					sh = sourcehash.group()
					if sh[-32:] == dh[-32:]:
						hashlist[s + extlist[3]] = sh
				else:
					output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),os.path.join(dirs,s),os.path.join(xcluster,"troubleshoot",s)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			#ok so the accession dir in the capture folder should be empty
			try:
				os.remove(s)
			#if it's not empty let's move it to a toubleshooting folder
			except:
				output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),os.path.join(dirs,s),os.path.join(xcluster,"troubleshoot",s)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	return

def updateFM(hashlist):
	for file,hash in hashlist:
		subprocess.call(["python",os.path.join(scriptRepo,"fm-embed-hashes.py"),"-id",file,"-hash",hash),shell=True)
	return

def main():
	#initialize a buncha paaths to various resources
	scriptRepo = os.path.dirname(os.path.abspath(__file__))
	config = ConfigParser.ConfigParser()
	config.read(os.path.join(scriptRepo,"video-post-process-config.txt"))
	watermark = config.get('transcode','whitewatermark')
	fontfile = config.get('transcode','timecodefont')
	rawCaptures = config.get('transcode','rawCaptureDir')
	sunnas = config.get('fileDestinations','sunnas')
	xendata = config.get('fileDestinations','xendata')
	xcluster = config.get('fileDestinations','xcluster')
	pid = os.path.join(scriptRepo,"processing.pid")
	
	if not os.path.exists(pid): #make sure this process isn't already running
		#initialize a process id (pid) file to check that this script isn't already running
		makepid(pid)
		
		#makes a list of files for ffmpeg to transcode
		fflist = makefflist(rawCaptures)
		
		#print the concat.txt files in each accession dir, via fflist
		printconcats(fflist)

		#actually transcode the files
		ffprocess(fflist,watermark,fontfile,scriptRepo)

		#hashmove
		hashlist = movevids(rawCaptures,sunnas,xendata,scriptRepo)
		
		#send to filemaker
		updateFM(hashlist)
		
		#if we got this far it means we're successful and we can delete the process id file
		os.remove(pid)
	return

dependencies()
main()