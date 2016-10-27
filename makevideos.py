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

#make sure that everything is where it should be
def init(watermark,fontfile,rawCaptures,sunnas,sunnascopyto,xendata,xendatacopyto,pid):
	watermark = watermark.strip('"')
	if os.path.exists(pid):
		with open(pid,"rb") as txtfile:
			last = None
			for line in (line for line in txtfile if line.rstrip('\n')):
				#for line in txtfile:
				last = line
		if "running" in last:
			sys.exit()
		elif "crashed" in last:
    		#check that watermarks and fontfiles are where they should be
			if not os.path.exists(watermark):
				if not "no email" in last:
					subprocess.call(["python","send-email.py","-txt","The white-watermark file cannot be found. Please put the white watermark file at " + watermark])
				with open(pid,"a") as txtfile:
					txtfile.write("crashed - no email\n")
				sys.exit()
			if not os.path.exists(fontfile):
				if not "no email" in last:
					subprocess.call(["python","send-email.py","-txt","The fontfile cannot be found. Please put the fontfile at " + fontfile])
				with open(pid,"a") as txtfile:
					txtfile.write("crashed - no email\n")
				sys.exit()
    		#test that everything is plugged in
			if not os.path.exists(sunnas):
				if not "no email" in last:
					subprocess.call(["python","send-email.py","-txt","The video script is unable to run because SUNNAS is not mounted as expected. Please mount SUNNAS on XCluster at " + sunnas])
				with open(pid,"a") as txtfile:
					txtfile.write("crashed - no email\n")
				sys.exit()
			if not os.path.exists(sunnascopyto):
				if not "no email" in last:
					subprocess.call(["python","send-email.py","-txt","The video script is unable to run because SUNNAS is not mounted as expected. Please mount SUNNAS on XCluster at " + sunnascopyto])
				with open(pid,"a") as txtfile:
					txtfile.write("crashed - no email\n")
				sys.exit()
			if not os.path.exists(xendata):
				if not "no email" in last:
					subprocess.call(["python","send-email.py","-txt","The video script is unable to run because Xendata is not mounted as expected. Please mount Xendata on XCluster at " + xendata])
				with open(pid,"a") as txtfile:
					txtfile.write("crashed - no email\n")
				sys.exit()
			if not os.path.exists(xendatacopyto):
				if not "no email" in last:
					subprocess.call(["python","send-email.py","-txt","The video script is unable to run because Xendata is not mounted as expected. Please mount Xendata on XCluster at " + xendatacopyto])
				with open(pid,"a") as txtfile:
					txtfile.write("crashed - no email\n")			
				sys.exit()
    		
    		#if we make it this far, everything is where it should be, we're gonna try running it again
			startup(pid,rawCaptures,watermark,fontfile,sunnas,sunnascopyto,xendata,xendatacopyto)
    	
    	#if it worked last time let's do it again
		elif "success" in last:
			startup(pid,rawCaptures,watermark,fontfile,sunnas,sunnascopyto,xendata,xendatacopyto)
	else:
		startup(pid,rawCaptures,watermark,fontfile,sunnas,sunnascopyto,xendata,xendatacopyto)
	return

def startup(pid,rawCaptures,watermark,fontfile,sunnas,sunnascopyto,xendata,xendatacopyto):
	if os.path.exists(pid):
		os.remove(pid)
	txtfile = open(pid, "wb")
	txtfile.write("makevideos - " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " \n")
	txtfile.write("running\n")
	txtfile.close()
	
	#check that there's stuff to work on even
	rawCapList = []
	for f in os.listdir(rawCaptures):
		if not f.startswith('.'):
			rawCapList.append(f)

	if not rawCapList:
		with open(pid,"ab") as txtfile:
			txtfile.write("success\n")
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
	
	#check that watermarks and fontfiles are where they should be
	if not os.path.exists(watermark):
		subprocess.call(["python","send-email.py","-txt","The white-watermark file cannot be found. Please put the white watermark file at " + watermark])
		with open(pid,"a") as txtfile:
			txtfile.write("crashed - no email\n")
		sys.exit()
	if not os.path.exists(fontfile):
		subprocess.call(["python","send-email.py","-txt","The fontfile cannot be found. Please put the fontfile at " + fontfile])
		with open(pid,"a") as txtfile:
			txtfile.write("crashed - no email\n")
		sys.exit()
	#check that everything is plugged in
	if not os.path.exists(sunnas):
		subprocess.call(["python","send-email.py","-txt","The video script is unable to run because SUNNAS is not mounted as expected. Please mount SUNNAS on XCluster at " + sunnas])
		with open(pid,"a") as txtfile:
			txtfile.write("crashed - no email\n")
		sys.exit()
	if not os.path.exists(sunnascopyto):
		subprocess.call(["python","send-email.py","-txt","The video script is unable to run because SUNNAS is not mounted as expected. Please mount SUNNAS on XCluster at " + sunnascopyto])
		with open(pid,"a") as txtfile:
			txtfile.write("crashed - no email\n")
		sys.exit()
	if not os.path.exists(xendata):
		subprocess.call(["python","send-email.py","-txt","The video script is unable to run because Xendata is not mounted as expected. Please mount Xendata on XCluster at " + xendata])
		with open(pid,"a") as txtfile:
			txtfile.write("crashed - no email\n")
		sys.exit()
	if not os.path.exists(xendatacopyto):
		subprocess.call(["python","send-email.py","-txt","The video script is unable to run because Xendata is not mounted as expected. Please mount Xendata on XCluster at " + xendatacopyto])
		with open(pid,"a") as txtfile:
			txtfile.write("crashed - no email\n")	
		sys.exit()
	#check that a filemaker record exists for each accession
	for dirs,subdirs,files in os.walk(rawCaptures):
			for s in subdirs:
				output = subprocess.Popen(["python","fm-stuff.py","-query","-id",s],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
				#output,err = output.communicate()
				if not output:
					subprocess.call(["python","send-email.py","-txt","The video script is unable to run because there is not an accession record for " + s])
					with open(pid,"a") as txtfile:	
						txtfile.write("crashed - no email\n")	
					sys.exit()
	
def makefflist(rawCaptures):
	fflist = {} #initialize a list of files for ffmpeg to transcode
	for dirs, subdirs, files in os.walk(rawCaptures): #loop thru holding dir on xcluster
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

def sizeloop(thing):
	print thing
	startsize = os.stat(thing)
	print startsize.st_size
	time.sleep(1)
	endsize = os.stat(thing)
	print endsize.st_size
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
	print thefiles
	for f in thefiles:
		fpath = os.path.join(pth,f)
		sizeloop(fpath)
	return thefiles

def compare(fs, fsagain):
	print fs
	print fsagain
	for f in fsagain:
		if not f in fs:
			return False
	return True
	
def printconcats(fflist):	
	for acc in fflist: #for each accession full path on xcluster
		with cd(acc): #cd into it
			txtfile = open("concat.txt","w") #initialize a txt file that we'll use to concat
			for rawmov in fflist[acc]: #for each file name in the lsit of filenames associated with this accession#
				txtfile.write("file " + rawmov + "\n") #append the filename to the txt file with a newline
			txtfile.close #housekeeping
	return 

def ffprocess(fflist,watermark,fontfile,scriptRepo):
	#concatenate startfiles into endfile.mov
	for acc in fflist: #for each accession full path on xcluster/IncomingQT
		canonicalname = os.path.basename(acc) #set the canonical name of the recording, e.g. A2016_001_001_001.mov (first entry in list fflist[acc])
		#ayear,accNum,intNum,segment = canonicalname.split("_")
		segment = canonicalname.split("_")[-1]
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
				subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt','The concatenation of  ' + canonicalname + ' was unsuccessful\n' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())])
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
				flvstr = 'ffmpeg -i concat.mov -i ' + watermark + ' -filter_complex "scale=320:180,overlay=0:0" -c:v libx264 -preset fast -b:v 700k -r 29.97 -pix_fmt yuv420p -c:a aac -map_channel 0.1.0:0.1 -map_channel 0.2.0:0.1 -timecode ' + segment[-2:] + ':00:00:00 ' + flv
				print flvstr
				output = subprocess.check_output(flvstr, shell=True)
				returncode = 0
			except subprocess.CalledProcessError,e:
				output = e.output
				returncode = e.returncode
			if returncode > 0:
				print "flv transcode fail"
				#send email to staff
				subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt','The transcode to ' + flv + ' was unsuccessful\n' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())])
				with open(pid,"a") as txtfile:
					txtfile.write("crashed - no email - flv tanscode fail\n")
				sys.exit()

			#endfile.mpeg + timecode
			print "transcoding to mpeg with timecode"
			#easier to init this var here rather than include it in the ffmpeg call
			drawtext = '"drawtext=fontfile=' + "'" + fontfile + "'" + ": timecode='" + segment[-2:] + "\:00\:00\:00'" + ': r=29.97: x=(w-tw)/2: y=h-(2*lh): fontcolor=white: fontsize=72: box=1: boxcolor=0x00000099'
			try:
				mpegstr = 'ffmpeg -i concat.mov -map_channel 0.1.0:0.0 -map_channel 0.2.0:0.0 -map 0:0 -c:a mp2 -ar 48000 -sample_fmt s16 -c:v mpeg2video -pix_fmt yuv420p -r 29.97 -b:v 5000k -vtag xvid -vf ' + drawtext + ',scale=720:480" ' + mpeg
				subprocess.check_output(mpegstr, shell=True)
				returncode = 0
			except subprocess.CalledProcessError,e:
				output = e.output
				returncode = e.returncode
			if returncode > 0:
				print "mpeg transcode fail"
				#send email to staff
				subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt','The transcode to ' + mpeg + ' was unsuccessful\n' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())])
				with open(pid,"a") as txtfile:
					txtfile.write("crashed - no email - mpeg transcode fail\n")
				sys.exit()

			#endfile.mp4 + timecode
			print "transcoding to mp4 with timecode"
			try:
				mp4str = 'ffmpeg -i concat.mov -c:v mpeg4 -b:v 372k -pix_fmt yuv420p -r 29.97 -vf ' + drawtext + ',scale=420:270" -c:a aac -ar 44100 -map_channel 0.1.0:0.1 -map_channel 0.2.0:0.1 ' + mp4
				subprocess.check_output(mp4str, shell=True)
				returncode = 0
			except subprocess.CalledProcessError,e:
				output = e.output
				returncode = e.returncode
			if returncode > 0:
				print "mp4 transcode fail"
				#send email to staff
				subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt','The transcode to ' + mp4 + ' was unsuccessful\n' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())])
				with open(pid,"a") as txtfile:
					txtfile.write("crashed - no email - mp4 transcode fail\n")
				sys.exit()
			os.rename("concat.mov",mov)
	return	

def movevids(rawCaptures,sunnascopyto,sunnas,xendata,xendatacopyto,xcluster,scriptRepo):
	hashlist = {}
	extlist = [".mov",".flv",".mp4",".mpeg"]
	
	for dirs, subdirs, files in os.walk(rawCaptures):
		for s in subdirs:
			with cd(os.path.join(dirs,s)):
				if os.path.isfile(s + extlist[0]) and os.path.isfile(s + extlist[1]) and os.path.isfile(s + extlist[2]) and os.path.isfile(s + extlist[3]): #if each file extension exists in there
					#copy pres file to lc director
					subprocess.call(["cp",os.path.join(dirs,s,s + extlist[0]),os.path.join(xcluster,"toLC",s + extlist[0])],shell=True) #copy the mov to xendata/copyto
					
					#move the mov files
					print "moving mov file"
					output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),"-a","sha1","-np",os.path.join(dirs,s,s + extlist[0]),xendatacopyto],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
					hashes,err = output.communicate()
					print hashes
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
					print hashes
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
					print hashes
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
					print hashes
					sourcehash = re.search('srce\s\S+\s\w{40}',hashes)
					desthash = re.search('dest\s\S+\s\w{40}',hashes)
					dh = desthash.group()
					sh = sourcehash.group()
					if sh[-40:] == dh[-40:]:
						hashlist[s + extlist[3]] = sh[-40:]
					
					#send file hashes to filemaker
					updateFM(hashlist,scriptRepo)
					
					#move the files to various copytos
					print "copying files"
					subprocess.call(["mv",os.path.join(xendatacopyto,s + extlist[0]),os.path.join(xendata,s + extlist[0])]) #copy the mov to xendata
					subprocess.call(["mv",os.path.join(xendatacopyto,s + extlist[3]),os.path.join(xendata,s + extlist[3])]) #copy the mpeg to xendata
					subprocess.call(["mv",os.path.join(sunnascopyto,s + extlist[1]),os.path.join(sunnas,s + extlist[1])]) #copy the flv to sunnas
					subprocess.call(["mv",os.path.join(sunnascopyto,s + extlist[2]),os.path.join(sunnas,s + extlist[2])]) #copy the mp4 to sunnas
				
				else:
					output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),"-a","sha1","-np",os.path.join(dirs,s),os.path.join(xcluster,"troubleshoot",s)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			#ok so the accession dir in the capture folder should be empty
			try:
				time.sleep(5)
				os.remove(os.path.join(dirs,s,".DS_Store"))
				os.rmdir(os.path.join(dirs,s))
			#if it's not empty let's move it to a toubleshooting folder
			except:
				output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),"-a","sha1","-np",os.path.join(dirs,s),os.path.join(xcluster,"troubleshoot",s)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	return

def updateFM(hashlist,scriptRepo):
	for fh in hashlist:
		print fh
		print hashlist[fh]
		fname,ext = os.path.splitext(fh)
		fdigi = ext.replace(".","")
		subprocess.call(["python",os.path.join(scriptRepo,"fm-stuff.py"),"-id",fname,"-hash",hashlist[fh],"-fdigi",fdigi])
	return

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
	pid = os.path.join(scriptRepo,"processing.pid")
	
	rawCaptures = rawCaptures.strip('"')
	xcluster = xcluster.strip('"')
	
	try:
		init(watermark,fontfile,rawCaptures,sunnas,sunnascopyto,xendata,xendatacopyto,pid)
		
		#makes a list of files for ffmpeg to transcode
		fflist = makefflist(rawCaptures)

		#print the concat.txt files in each accession dir, via fflist
		printconcats(fflist)

		#actually transcode the files
		ffprocess(fflist,watermark,fontfile,scriptRepo)

		#hashmove
		movevids(rawCaptures,sunnascopyto,sunnas,xendata,xendatacopyto,xcluster,scriptRepo)
		
		#send to filemaker
		#updateFM(hashlist,scriptRepo)
	
		with open(pid,"a") as txtfile:
			txtfile.write("success\n")
	except Exception,e:
		print str(e)
		subprocess.call(['python',os.path.join(scriptRepo,"send-email.py"),'-txt','The script crashed due to an internal error (Traceback, AttributeError, etc. Please check Terminal output and adjsut as necessary\n' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())])
		with open(pid,"a") as txtfile:
			txtfile.write("crashed")	
	return

dependencies()
main()