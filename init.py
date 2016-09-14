#initializes everything for makevideos
#this is the script that is triggered by cron

import ConfigParser
import sys
import subprocess
import time
import os

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
	print rawCapList
	if not rawCapList:
		with open(pid,"ab") as txtfile:
			txtfile.write("success\n")
		sys.exit()

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
	
	#again if we make it here we should be good
	subprocess.call(["python","makevideos.py"])
	return

def main():
	#initialize a buncha paths to various resources
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
	pid = os.path.join(scriptRepo,"processing.pid")
	rawCaptures = rawCaptures.strip('"')
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

main()