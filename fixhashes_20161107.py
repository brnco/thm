#!/usr/bin/env python

import re
import subprocess
import os
import time
import sys


def getstuff(result):
	match = ''
	match = re.search('A\d{4}_\d{3}_\d{3}_\d{3}\.\S{3,4}',result)
	if match:
		file = match.group()
	match = re.search('\w{40}',result)
	if match:
		hash = match.group()
	return file, hash

txt = open("/Volumes/G-SPEED Q/Titan-HD/HM/thm/logs/log-2016-11-05 12-52-14.txt","r+")
ftxt = txt.read()

acclist = []
extlist = [".mp4",".flv"]	

for f in os.listdir("/Volumes/ProxyHolding/copyto"):
	file,ext = os.path.splitext(f)
	if not file in acclist and not file.endswith(".mov628") and not file.endswith(".mov534") and not file.endswith(".DS_Store"):
		acclist.append(file)

	
for acc in acclist:
	for ext in extlist:
		match = ''
		match = re.search(r"hash of " + acc + ext + " verified\sincorrectly\n2016-11-..\s..:..:..\nmakevideos calculated hash of: .*",ftxt)
		if match:
			result = match.group()
			file, hash = getstuff(result)
			id,fdigi = os.path.splitext(file)
			subprocess.call(["python","fm-stuff.py","-uSha","-id",id,"-fdigi",fdigi.replace(".",""),"-hash",hash])
			time.sleep(1)
			sys.stdout.flush()
			output = subprocess.Popen(["python","fm-stuff.py","-qSha","-id",id,"-fdigi",fdigi.replace(".","")],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			out = output.communicate()
			print str(out)
			#foo = raw_input("eh")
			if not any(hash in foo for foo in out):
				print "this file didn't match"
				print acc + ext	
				print ""
			else:
				if os.path.exists(os.path.join("/Volumes/ProxyHolding/copyto",file)):
					subprocess.call(["mv",os.path.join("/Volumes/ProxyHolding/copyto",file),"/Volumes/ProxyHolding"])
			print file
			print hash
