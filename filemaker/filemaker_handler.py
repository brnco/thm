#!/usr/bin/env python
'''
handles all interactions with FileMaker
uses ODBC driver for connections
uses SQL syntax for queries
'''
import pyodbc
import argparse
import logging
logger = logging.getLogger(__name__)

def verify_record_exists(accession, cursor, kwvars):
    '''
    verifies that filemaker record exists for each accession
    return True
    '''
    output = ''
    query = "select identifier from PBCoreInstantiation where identifier='" + accession + "'"
    logger.debug(query)
    cursor.execute(query)
    output = cursor.fetchone()
    if output:
        logger.debug(output)
        return True
    else:
        msg = "The video script is unable to run because there is not an accession record for " + accession + " in FileMaker"
        logger.error(output)
        logger.error(msg)
        return False

def query_hash(accession, cursor, kwvars):
    '''
    queries filemaker for hash of file
    '''
    output = ''
    query = "select ShaDigest from PBCoreInstantiation where identifier='" + kwvars.id + "' AND formatDigital='" + kwvars.format_digital + "'"
    cursor.execute(query)
    output = cursor.fetchone()
    if output:
        #log(kwvars.logfile,"INFO: found hash for file " + kwvars.id + " = " + str(output))
        return output

def update_hash(accession, cursor, filemaker_connection, kwvars):
    '''
    updates record with (new) hash for accession

    be super careful with the quotes here
    whole string in () needs to be enclosed in double quotes
    values for SQL commands need to be enclosed in single quotes
    '''
    query = "update PBCoreInstantiation set ShaDigest = '" + kwvars.hash + "' where filename = '" + kwvars.filename + "'"
    logger.info(query)
    cursor.execute(query)
    filemaker_connection.commit()
    return True

def init_connection(kwvars):
    '''
    initalizes connection to filemaker
    '''
    conn_str = "DRIVER={FileMaker ODBC};SERVER=192.168.19.3;DATABASE=PBCore_Catalog;PORT=2399;" + \
        "UID=" + kwvars.config.filemaker_user + ";PWD=" + kwvars.config.filemaker_pwd + ";CHARSET=UTF-16"
    filemaker_connection = pyodbc.connect(conn_str)
    cursor = filemaker_connection.cursor()
    logger.info("connected to FileMaker successfully")
    return filemaker_connection, cursor

def init():
    '''
    initalize variables and config
    '''
    kwvars = util.d({})
    parser = argparse.ArgumentParser(description="handles Filemaker calls")
    parser.add_argument('-m','--mode',choices=['query_record','update_hash','query_hash'])
    parser.add_argument("-id",help="filename of file that was hashed")
    parser.add_argument("-hash",help="SHA1 hash value of file")
    parser.add_argument('-fdigi','--format_digital',help="formatDigital, the file extension (without the '.') whose hash we have")
    args = parser.parse_args()
    kwvars.m = args.m
    kwvars.id = args.id
    kwvars.format_digital = args.format_digital
    return kwvars

def main():
    '''
    do the thing
    '''
    kwvars = init()
    filemaker_connection, cursor = init_connection(kwvars)
    if kwvars.m == "update_hash":
        update_hash(kwvars.id,kwvars)
    if kwvars.m == "query_hash":
        query_hash(kwvars.id,kwvars)
    if kwvars.m == "query_record":
        verify_record_exists(kwvars.id,kwvars)
    return

if __name__ == "__main__":
    main()
