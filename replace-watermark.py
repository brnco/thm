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
	#initialize a buncha paaths to various resources
	scriptRepo = os.path.dirname(os.path.abspath(__file__))
	config = ConfigParser.ConfigParser()
	config.read(os.path.join(scriptRepo,"video-post-process-config.txt"))
	watermark = config.get('transcode','blackwatermark')
	#grab args fromCLI
	parser = argparse.ArgumentParser(description="concatenates, transcodes, hashmoves videos")
	parser.add_argument("input",dest="i",help="the full path to the input file whose watermark you'd like to replace")
	args = vars(parser.parse_args())
	name = os.path.basename(args.1)
	ayear,acc,interview,segment = name.split("_")
	ffstring = 'ffmpeg -i ' + args.i + ' -i "' + blackwatermark + '" -filter_complex "scale=320:180,overlay=0:0" -c:v libx264 -preset fast -b:v 700k -r 29.97 -pix_fmt yuv420p -c:a aac -map_channel 0.1.0:0.1 -map_channel 0.2.0:0.1 -timecode ' + segment[-2:] + ':00:00:00 ' + name + ".flv"
	subprocess.call(ffstring,shell=True)
	return

dependencies()
main()