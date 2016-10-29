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

def startup(logfile,rawCaptures,watermark,fontfile,sunnas,sunnascopyto,xendata,xendatacopyto):
	log(logfile,"running")
	
	#check that there's stuff to work on even
	rawCapList = []
	for f in os.listdir(rawCaptures):
		if not f.startswith('.'):
			rawCapList.append(f)

	if not rawCapList:
		msg = "completed. nothing to process"
		log(logfile,msg)
		sys.exit()

	#check that the files are where we think thye are
	if not os.path.exists(watermark) and not os.path.exists(watermark.strip('"')):
		msg = "The white-watermark file cannot be found. Please put the white watermark file at " + watermark
		with open(logfile,"r+") as l:
			thelog = l.read()
		subprocess.call(["python","send-email.py","-txt",msg + "\n" + str(thelog)])
		log(logfile,msg)
		sys.exit()
	if not os.path.exists(fontfile):
		msg = "The fontfile cannot be found. Please put the fontfile at " + fontfile
		with open(logfile,"r+") as l:
			thelog = l.read()
		subprocess.call(["python","send-email.py","-txt",msg + "\n" + str(thelog)])
		log(logfile,msg)
		sys.exit()
	
	#check that everything is plugged in
	if not os.path.exists(sunnas):
		msg = "The video script is unable to run because SUNNAS is not mounted as expected. Please mount SUNNAS on XCluster at " + sunnas
		with open(logfile,"r+") as l:
			thelog = l.read()
		subprocess.call(["python","send-email.py","-txt",msg + "\n" + str(thelog)])
		log(logfile,msg)
		sys.exit()
	if not os.path.exists(sunnascopyto):
		msg = "The video script is unable to run because SUNNAS is not mounted as expected. Please mount SUNNAS on XCluster at " + sunnascopyto
		with open(logfile,"r+") as l:
			thelog = l.read()
		subprocess.call(["python","send-email.py","-txt",msg + "\n" + str(thelog)])
		log(logfile,msg)
		sys.exit()
	if not os.path.exists(xendata):
		msg = "The video script is unable to run because Xendata is not mounted as expected. Please mount Xendata on XCluster at " + xendata
		with open(logfile,"r+") as l:
			thelog = l.read()
		subprocess.call(["python","send-email.py","-txt",msg + "\n" + str(thelog)])
		log(logfile,msg)
		sys.exit()
	if not os.path.exists(xendatacopyto):
		msg = "The video script is unable to run because Xendata is not mounted as expected. Please mount Xendata on XCluster at " + xendatacopyto
		with open(logfile,"r+") as l:
			thelog = l.read()
		subprocess.call(["python","send-email.py","-txt",msg + "\n" + str(thelog)])
		log(logfile,msg)
		sys.exit()
	
	#check that nothing is being copied currently
	donezo = False
	while donezo is False:
		fs = walk(rawCaptures)
		#print fs
		time.sleep(120)
		fsagain = walk(rawCaptures)
		#print fsagain
		donezo = compare(fs, fsagain)
		#print donezo

	#check that a filemaker record exists for each accession
	for dirs,subdirs,files in os.walk(rawCaptures):
			for s in subdirs:
				output = subprocess.Popen(["python","fm-stuff.py","-qExist","-id",s],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
				#output,err = output.communicate()
				if not output:
					msg = "The video script is unable to run because there is not an accession record for " + s
					with open(logfile,"r+") as l:
						theLog = l.read()
					subprocess.call(["python","send-email.py","-txt",msg + "\n" + str(thelog)])
					log(logfile,msg)	
					sys.exit()
	
def makefflist(rawCaptures,logfile):
	fflist = {} #initialize a list of files for ffmpeg to transcode
	for dirs, subdirs, files in os.walk(rawCaptures): #loop thru holding dir on xcluster
		for acc in subdirs: #for each accession# (subdir) in the list of subdirs
			with cd(os.path.join(dirs,acc)): #cd into accession dir
				rawcaplist = [] #init a list that will contain raw captures in each dir
				for rawmov in os.listdir(os.getcwd()): #for each file in the current working directory
					if rawmov.endswith(".mov") or rawmov.endswith(".MOV"): #if it is a mov
						rawcaplist.append(rawmov) #append it to our list of raw captures
				fflist[os.path.join(dirs,acc)] = sorted(rawcaplist) #add the list of ['rawcapture filenames'] to a dict key of 'full path to accession# on xcluster'
	log(logfile,str(fflist))
	return fflist



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


def ffprocess(fflist,watermark,fontfile,scriptRepo,logfile):
	#concatenate startfiles into endfile.mov
	for acc in fflist: #for each accession full path on xcluster/IncomingQT
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
			except subprocess.CalledProcessError,e:
				output = e.output
				returncode = e.returncode
			if returncode > 0:
				#send email to staff
				msg = 'The concatenation of  ' + canonicalname + ' was unsuccessful\n'
				with open(logfile,"r+") as l:
					thelog = l.read()
				subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt',msg + "\n" + str(thelog)])
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
				flvstr = 'ffmpeg -i concat.mov -i ' + watermark + ' -filter_complex "scale=320:180,overlay=0:0" -c:v libx264 -preset fast -b:v 700k -r 29.97 -pix_fmt yuv420p -c:a aac -map_channel 0.1.0:0.1 -map_channel 0.2.0:0.1 -timecode ' + segment[-2:] + ':00:00:00 ' + flv
				output = subprocess.check_output(flvstr, stderr=open(logfile,"a+"), shell=True)
				returncode = 0
				log(logfile, "transcode to flv successful")
			except subprocess.CalledProcessError,e:
				output = e.output
				returncode = e.returncode
			if returncode > 0:
				#send email to staff
				msg = 'The transcode to ' + flv + ' was unsuccessful\n'
				with open(logfile,"r+") as l:
					thelog = l.read()
				subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt',msg + "\n" + str(thelog)])
				log(logfile,msg)
				sys.exit()

			#endfile.mpeg + timecode
			#easier to init this var here rather than include it in the ffmpeg call
			drawtext = '"drawtext=fontfile=' + "'" + fontfile + "'" + ": timecode='" + segment[-2:] + "\:00\:00\:00'" + ': r=29.97: x=(w-tw)/2: y=h-(2*lh): fontcolor=white: fontsize=72: box=1: boxcolor=0x00000099'
			try:
				mpegstr = 'ffmpeg -i concat.mov -map_channel 0.1.0:0.0 -map_channel 0.2.0:0.0 -map 0:0 -c:a mp2 -ar 48000 -sample_fmt s16 -c:v mpeg2video -pix_fmt yuv420p -r 29.97 -b:v 5000k -vtag xvid -vf ' + drawtext + ',scale=720:480" ' + mpeg
				subprocess.check_output(mpegstr,stderr=open(logfile,"a+"), shell=True)
				returncode = 0
				log(logfile, "transcode to mpeg successful")
			except subprocess.CalledProcessError,e:
				output = e.output
				returncode = e.returncode
			if returncode > 0:
				#send email to staff
				msg = 'The transcode to ' + mpeg + ' was unsuccessful\n'
				with open(logfile,"r+") as l:
					thelog = l.read()
				subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt',msg + "\n" + thelog])
				log(logfile,msg)
				sys.exit()

			#endfile.mp4 + timecode
			try:
				mp4str = 'ffmpeg -i concat.mov -c:v mpeg4 -b:v 372k -pix_fmt yuv420p -r 29.97 -vf ' + drawtext + ',scale=420:270" -c:a aac -ar 44100 -map_channel 0.1.0:0.1 -map_channel 0.2.0:0.1 ' + mp4
				subprocess.check_output(mp4str,stderr=open(logfile,"a+"), shell=True)
				returncode = 0
			except subprocess.CalledProcessError,e:
				output = e.output
				returncode = e.returncode
				log(logfile,"transcode to mp4 successful")
			if returncode > 0:
				#send email to staff
				msg = 'The transcode to ' + mp4 + ' was unsuccessful\n'
				with open(logfile,"r+") as l:
					thelog = l.read()
				subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt',msg + "\n" + str(thelog)])
				log(logfile,msg)
				sys.exit()
			os.rename("concat.mov",mov)
	return	

def movevids(rawCaptures,sunnascopyto,sunnas,xendata,xendatacopyto,xcluster,scriptRepo,logfile):
	hashlist = {}
	extlist = [".mov",".flv",".mp4",".mpeg"]
	for dirs, subdirs, files in os.walk(rawCaptures):
		for s in subdirs:
			with cd(os.path.join(dirs,s)):
				if os.path.isfile(s + extlist[0]) and os.path.isfile(s + extlist[1]) and os.path.isfile(s + extlist[2]) and os.path.isfile(s + extlist[3]): #if each file extension exists in there
					
					#copy pres file to lc directory
					output = subprocess.Popen(["cp",os.path.join(dirs,s,s + extlist[0]),os.path.join(xcluster,"toLC",s + extlist[0])],stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True) #copy the mov to xendata/copyto
					log(logfile,"copying archival master to lc folder\n")
					
					#move the mov files
					output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),"-a","sha1","-np",os.path.join(dirs,s,s + extlist[0]),xendatacopyto],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
					hashes,err = output.communicate()
					log(logfile,hashes)
					sourcehash = re.search('srce\s\S+\s\w{40}',hashes)
					desthash = re.search('dest\s\S+\s\w{40}',hashes)
					dh = desthash.group()
					sh = sourcehash.group()
					if sh[-40:] == dh[-40:]:
						hashlist[s + extlist[0]] = sh[-40:]

					#move the flv file
					print "moving flv file"
					output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),"-a","sha1","-np",os.path.join(dirs,s,s + extlist[1]),sunnascopyto],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
					hashes,err = output.communicate()
					log(logfile, hashes)
					sourcehash = re.search('srce\s\S+\s\w{40}',hashes)
					desthash = re.search('dest\s\S+\s\w{40}',hashes)
					dh = desthash.group()
					sh = sourcehash.group()
					if sh[-40:] == dh[-40:]:
						hashlist[s + extlist[1]] = sh[-40:]
					
					#move the mp4 file
					print "moving mp4 file"
					output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),"-a","sha1","-np",os.path.join(dirs,s,s + extlist[2]),sunnascopyto],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
					hashes,err = output.communicate()
					log(logfile,hashes)
					sourcehash = re.search('srce\s\S+\s\w{40}',hashes)
					desthash = re.search('dest\s\S+\s\w{40}',hashes)
					dh = desthash.group()
					sh = sourcehash.group()
					if sh[-40:] == dh[-40:]:
						hashlist[s + extlist[2]] = sh[-40:]
						
					#move the mpeg file
					print "moving mpeg file"
					output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),"-a","sha1","-np",os.path.join(dirs,s,s + extlist[3]),xendatacopyto],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
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
					output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),"-a","sha1","-np",os.path.join(dirs,s),os.path.join(xcluster,"troubleshoot",s)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			#ok so the accession dir in the capture folder should be empty
			try:
				time.sleep(5)
				log(logfile,"removing " + os.path.join(dirs,s,".DS_Store"))
				if os.path.exists(os.path.join(dirs,s,".DS_Store")):
					os.remove(os.path.join(dirs,s,".DS_Store"))
				log(logfile,"removing accession dir " + os.path.join(dirs,s) +  " from IncomingQT")
				if os.path.exists(os.path.join(dirs,s)):
					os.rmdir(os.path.join(dirs,s))
			#if it's not empty let's move it to a toubleshooting folder
			except:
				output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),"-a","sha1","-np",os.path.join(dirs,s),os.path.join(xcluster,"troubleshoot",s)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	return

def updateFM(hashlist,scriptRepo,logfile):
	log(logfile,"sending hashes to filemaker")
	for fh in hashlist:
		fname,ext = os.path.splitext(fh)
		fdigi = ext.replace(".","")
		output = subprocess.Popen(["python",os.path.join(scriptRepo,"fm-stuff.py"),"-id",fname,"-hash",hashlist[fh],"-fdigi",fdigi],stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
	return

def log(logfile,msg):
	with open(logfile,"ab") as txtfile:
		txtfile.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
		txtfile.write("\n")
		txtfile.write(msg)
		txtfile.write("\n")

def main():
	#initialize a buncha paaths to various resources
	scriptRepo = os.path.dirname(os.path.abspath(__file__))
	config = ConfigParser.ConfigParser()
	config.read(os.path.join(scriptRepo,"video-post-process-config.txt"))
	watermark = config.get('transcode','whitewatermark')
	fontfile = config.get('transcode','timecodefont')
	rawCaptures = config.get('transcode','rawCaptureDir')
	sunnascopyto = config.get('fileDestinations','sunnascopyto')
	sunnas = config.get('fileDestinations','sunnas')
	xendata = config.get('fileDestinations','xendata')
	xendatacopyto = config.get('fileDestinations','xendatacopyto')
	xcluster = config.get('fileDestinations','xcluster')
	logfile = os.path.join(scriptRepo,"logs","log-" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ".txt")
	
	rawCaptures = rawCaptures.strip('"')
	xcluster = xcluster.strip('"')
	
	try:
		startup(logfile,rawCaptures,watermark,fontfile,sunnas,sunnascopyto,xendata,xendatacopyto)
		
		#makes a list of files for ffmpeg to transcode
		fflist = makefflist(rawCaptures,logfile)

		#actually transcode the files
		ffprocess(fflist,watermark,fontfile,scriptRepo,logfile)

		#hashmove
		movevids(rawCaptures,sunnascopyto,sunnas,xendata,xendatacopyto,xcluster,scriptRepo,logfile)
	
		msg = "makevideos completed successfully"
		with open(logfile,"r+") as l:
			thelog = l.read()
		subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt', msg + "\n" + str(thelog)])
		log(logfile,msg)
	
	except Exception,e:
		print str(e)
		msg = "The script crashed due to an internal error\n"
		msg = msg + str(e)
		with open(logfile,"r+") as l:
			thelog = l.read()
		msg = msg + "\n" + str(thelog)
		subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt', msg])
		log(logfile,msg)
		log(logfile,str(e))
	return

dependencies()
main()