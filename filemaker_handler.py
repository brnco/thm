#send hashes to filemaker
#takes input args for hash and id of accession
import sys
egg_path = '/Library/Python/2.7/site-packages/pyodbc-3.0.7-py2.7-macosx-10.11-intel.egg'
sys.path.append(egg_path)
#import pyodbc
import argparse

def verify_record_exists(accession, cursor, kwargs):
    '''
    verifies that filemaker record exists for each accession
    '''

    output = ''
    query = "select identifier from PBCoreInstantiation where identifier='" + accession + "'"
    cursor.execute(query)
    output = cursor.fetchone()
    if output:
        return True
    else:
        return False

def query_hash(accession, cursor, kwargs):
    '''
    queries filemaker for hash of file
    '''
    output = ''
    query = "select ShaDigest from PBCoreInstantiation where identifier='" + kwargs.id + "' AND formatDigital='" + kwargs.format_digital + "'"
    cursor.execute(query)
    output = cursor.fetchone()
    if output:
        #log(kwargs.logfile,"INFO: found hash for file " + kwargs.id + " = " + str(output))
        return output

def update_hash(accession, cursor, filemaker_connection, kwargs):
    '''
    updates record with (new) hash for accession

    be super careful with the quotes here
    whole string in () needs to be enclosed in double quotes
    values for SQL commands need to be enclosed in single quotes
    '''
    try:
        query = "update PBCoreInstantiation set ShaDigest='" + kwargs.hash + "' where FileName='" + kwargs.filename + "'"
        cursor.execute(query)
        filemaker_connection.commit()
    except:
        return False
    return True

def init_connection(kwargs):
    '''
    initalizes connection to filemaker
    '''
    '''
    filemaker_connection = pyodbc.connect("DRIVER={FileMaker ODBC};SERVER=;DATABASE=PBCore_Catalog;PORT=2399;UID=;PWD=;CHARSET=UTF-8")
    cursor = filemaker_connection.cursor()
    '''
    filemaker_connection = True
    cursor = True
    return filemaker_connection, cursor

def init():
    '''
    initalize variables and config
    '''
    kwargs = util.d({})
    parser = argparse.ArgumentParser(description="handles Filemaker calls")
    parser.add_argument('-m','--mode',choices=['query_record','update_hash','query_hash'])
    parser.add_argument("-id",help="filename of file that was hashed")
    parser.add_argument("-hash",help="SHA1 hash value of file")
    parser.add_argument('-fdigi','--format_digital',help="formatDigital, the file extension (without the '.') whose hash we have")
    args = parser.parse_args()
    kwargs.m = args.m
    kwargs.id = args.id
    kwargs.format_digital = args.format_digital
    return kwargs

def main():
    '''
    do the thing
    '''
    kwargs = init()
    filemaker_connection, cursor = init_connection(kwargs)
    if kwargs.m == "update_hash":
        update_hash(kwargs.id,kwargs)
    if kwargs.m == "query_hash":
        query_hash(kwargs.id,kwargs)
    if kwargs.m == "query_record":
        verify_record_exists(kwargs.id,kwargs)
    return

if __name__ == "__main__":
    main()
