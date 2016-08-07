#testmounts

import os
import subprocess

try:
	subprocess.call(['ls', '/Volumes/ProxyHolding'])
except:
	subprocess.call('mkdir','/Volumes/ProxyHolding')
	subprocess.call('mount','-t','smb','guest@192.168.20.74/ProxyHolding','ProxyHolding')