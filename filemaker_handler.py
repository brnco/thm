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

def verify_record_exists(accession, cursor, kwargs):
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
    query = "update PBCoreInstantiation set ShaDigest = '" + kwargs.hash + "' where filename = '" + kwargs.filename + "'"
    logger.info(query)
    cursor.execute(query)
    filemaker_connection.commit()
    return True

def init_connection(kwargs):
    '''
    initalizes connection to filemaker
    '''
    conn_str = "DRIVER={FileMaker ODBC};SERVER=192.168.19.3;DATABASE=PBCore_Catalog;PORT=2399;" + \
        "UID=" + kwargs.config.filemaker_user + ";PWD=" + kwargs.config.filemaker_pwd + ";CHARSET=UTF-16"
    logger.debug(conn_str)
    filemaker_connection = pyodbc.connect(conn_str)
    cursor = filemaker_connection.cursor()
    logger.info("connected to FileMaker successfully")
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
