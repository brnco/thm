'''
manages the hashes project
'''
import sys
import logging
import pathlib
import configparser
from pprint import pprint, pformat
import util
import airtable
import filemaker.filemaker_handler as fm


def hash_files(filepath):
    '''
    creates portable SHA256 hash for file
    '''
    cmd = 'certutil -hashfile "' + file + '" SHA1'
    logger.debug(cmd)
    output = subprocess.run(cmd, capture_output=True)
    if output.returncode == 0:
        lines = output.stdout.split(b"\r\n")
        sha_hash = lines[1].strip().decode("utf-8")
    else:
        logging.error(output.stderr)
        return False
    logger.info("hashing completed successfully")
    return sha_hash


def verify_hashes(kwvars):
    '''
    loops through airtable view
    for files where "SHA1 - Check" is empty
    hashes file at path with SHA1 hash
    sends hash to airtable
    '''
    atbl_tbl = airtable.connect_to_table()
    atbl_tbl_iterator = atbl_tbl.iterate(view="Hashes to Verify", fields=["Xendata Filepath"], page_size=10)
    while True:
        atbl_results = next(atbl_tbl_iterator)
        for atbl_rec in atbl_results:
            filepath = pathlib.Path(atbl_rec['fields']['Xendata Filepath'])
            if not filepath.is_file():
                raise FileNotFoundError(f"python could not find file at path {filepath}")
            logger.info(f"hashing {filepath}")
            sha1_hash = hash_file(filepath)
            atbl_tbl.update(atbl_rec['id'], {"SHA1 - Check": sha1_hash})
        input("yo")


def get_every_filemaker_record(kwvars):
    '''
    gets every filemaker record with _pres in the filename
    converts and uploads it to airtable
    '''
    atbl_tbl = airtable.connect_to_table()
    fm_conn, cursor = fm.init_connection(kwvars)
    cursor, field_names = fm.get_every_pres_file(cursor, kwvars)
    logger.info("query completed")
    while True:
        atbl_recs = []
        fm_recs = cursor.fetchmany(1000)
        if not fm_recs:
            break
        for fm_rec_vals in fm_recs:
            fm_rec = dict(zip(field_names, fm_rec_vals))
            atbl_rec = airtable.THMHashRecord().from_filemaker(fm_rec)
            atbl_recs.append(atbl_rec.__dict__['_fields'])
        atbl_tbl.batch_create(atbl_recs)  


def init_log():
    '''
    initalizes log for whole run of script
    '''
    message_format = logging.Formatter('%(asctime)s %(levelname)s: %(message)s',\
            datefmt='%Y-%m-%d %H:%M:%S')
    global logger
    logger = logging.getLogger()
    '''
    make a handler for printing to terminal screen, add to logger
    '''
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(message_format)
    stream_handler.setLevel(logging.DEBUG)
    logger.addHandler(stream_handler)
    logger.setLevel(logging.DEBUG)
    '''
    do a test log output
    '''
    logger.info("initializing script and log")


def init():
    '''
    initializes things
    '''
    kwvars = util.d({})
    kwvars.script_dir = pathlib.Path(__file__).parent.absolute()
    kwvars.config = util.d({})
    config = configparser.ConfigParser()
    config.read(kwvars.script_dir / "video-post-processing.config")
    kwvars.config.filemaker_user = config.get('filemaker','user')
    kwvars.config.filemaker_pwd = config.get('filemaker','pwd')
    return kwvars


def main():
    '''
    do the thing
    '''
    kwvars = init()
    init_log()
    #get_every_filemaker_record(kwvars)
    verify_hashes(kwvars)


if __name__ == "__main__":
    main()
