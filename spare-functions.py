#spare functions

def makemovelist(harddrive):
	#try:
	flist = {}
	accessionlist = []
	rawfs = []
	for dirs, subdirs, files in os.walk(harddrive): #walk through capture directory
		for f in files: #for each file found
			if f.endswith(".mov"): #if it's a mov
				rawfs.append(os.path.join(dirs,f)) #append the full path to the raw files to the rawfs list
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
	for f in flist: #loop thru list of files on the hard drive
		ayear,acc = f.split("_") #split the ayear and accession# values at the underscore
		xcldirpath = os.path.join(xcluster,ayear,acc) #make a string for the directory path on xcluster that these files will soon inhabit
		for mov in flist[f]: #flist[f] returns a list of files, loop thru that
			#use hashmove to move them to xcluster
			output = subprocess.Popen(["python",os.path.join(scriptRepo,"hashmove.py"),mov,xcldirpath,"-c"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	return

parser.add_argument("-skiphd","--skipharddrive",dest="shd",action="store_true",default=False,help="skip the step of moving things from the hard drive, process from xcluster only")

#if we're grabbing files from the hard drive, start here
	if args['shd'] is False:
		#make a list of things to work on
		flist = makemovelist(harddrive)

		#move files from hard drive to xcluster
		hashmove1(flist,scriptRepo,harddrive,xcluster)
		
		#gives teh registry a couple seconds to understand what just happened
		time.sleep(2)