#send hashes to filemaker
#takes input args for hash and id of accession

import pyodbc
import argparse
import ConfigParser

def main()
	parser = argparse.ArgumentParser(description="concatenates, transcodes, hashmoves videos")
	acc = parser.add_argumnet("-id",help="filename.ext of file that was hashed")
	sha1 = parser.add_argumnet("-hash",help="SHA1 hash value of file")
	args = vars(parser.parse_args())
	scriptRepo = os.path.dirname(os.path.abspath(__file__))
	config = ConfigParser.ConfigParser()
	config.read(os.path.join(scriptRepo,"video-post-process-config.txt"))
	ipaddr = config.get('filemaker','ip')
	uid = config.get('filemaker','uid')
	pwd = config.get('filemaker','pwd')
	port = "2399"
	cnxn = pyodbc.connect('"DRIVER={FileMaker ODBC};SERVER=' + ipaddr + ';PORT=' + port + ';UID=' + uid + ';PWD=' + pwd + '"')
	cursor = cnxn.cursor()
	#be super careful with the quotes here
	#whole string in () needs to be enclosed in double quotes
	#values for SQL commands need to be enclosed in single quotes
	cursor.execute('"' + "update PBCoreInstantiation set ShaDigest='" + args['sha1'] + "' where identifier='" + args['id'] + "'" + '"') 
	
	return

main()