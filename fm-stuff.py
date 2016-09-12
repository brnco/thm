#send hashes to filemaker
#takes input args for hash and id of accession

import pyodbc
import argparse

def main():
	parser = argparse.ArgumentParser(description="deals with filemaker")
	acc = parser.add_argument("-id",help="filename of file that was hashed")
	sha1 = parser.add_argument("-hash",help="SHA1 hash value of file")
	formatDigi = parser.add_argument("-fdigi",help="formatDigital, the file whose hash we have")
	query = parser.add_argument("-query",action="store_true",default=False,help="query mode, for finding if a record exists")
	args = vars(parser.parse_args())
	
	cnxn = pyodbc.connect("DRIVER={FileMaker ODBC};SERVER=192.168.19.3;DATABASE=PBCore_Catalog;PORT=2399;UID=Strecker;PWD=123456")
	cursor = cnxn.cursor()
	
	if args['query'] is False:
		#be super careful with the quotes here
		#whole string in () needs to be enclosed in double quotes
		#values for SQL commands need to be enclosed in single quotes
		updatestr = "update PBCoreInstantiation set ShaDigest='" + args['hash'] + "' where identifier='" + args['id'] + "' AND formatDigital='" + args['fdigi'] + "'"
		#print updatestr
		cursor.execute(updatestr) 
		
		cursor.commit()
	else:
		outstring = ''
		qstring = "select identifier from PBCoreInstantiation where identifier='" + args['id'] + "'"
		outstring = cursor.fetchone()
		if outstring:
				print outstring
	return

main()