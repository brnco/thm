#replace-watermark
#takes input for full path to file
#replaces white watermark (defualt for makevideos) with black watermark

import os
import sys
import subprocess
import sys
import time
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

def main ():
	#initialize a buncha paths to various resources
	scriptRepo = os.path.dirname(os.path.abspath(__file__))
	config = ConfigParser.ConfigParser()
	config.read(os.path.join(scriptRepo,"video-post-process-config.txt"))
	watermark = config.get('transcode','blackwatermark')
	watermark = watermark.strip('"')
	#grab args fromCLI
	parser = argparse.ArgumentParser(description="replaces default white watermark with a black one")
	parser.add_argument("input",help='the full path to the input file whose watermark youd like to replace, e.g. "/Volumes/ProxyHolding/copyto/A2016_001_001_001.flv"')
	args = vars(parser.parse_args())
	name = os.path.basename(args['input']).strip('"')
	ayear,acc,interview,segment = name.split("_")
	with cd(os.path.dirname(args['input'].strip('"'))):
		ffstring = 'ffmpeg -i ' + name + ' -i "' + watermark + '" -filter_complex "scale=320:180,overlay=0:0" -c:v libx264 -preset fast -b:v 700k -r 29.97 -pix_fmt yuv420p -c:a copy -timecode ' + segment[-2:] + ':00:00:00 ' + name + "-blackwatermark.flv"
		print ffstring
		subprocess.call(ffstring,shell=True)
	return

dependencies()
main()