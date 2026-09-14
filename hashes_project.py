'''
manages the hashes project
'''
import sys
import logging
import pathlib
import configparser
import util
import airtable
import filemaker.filemaker_handler as fm



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
    fm_conn, cursor = fm.init_connection(kwvars)


if __name__ == "__main__":
    main()
