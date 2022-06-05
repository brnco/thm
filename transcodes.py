'''
handles all transcodes and concatenations
'''
import sys
import os
import asyncio
from asyncio.subprocess import PIPE
import subprocess
import logging
logger = logging.getLogger(__name__)

@asyncio.coroutine
def read_stream_and_display(stream, display):
    '''
    read from stream line by line until EOF
    display, capture lines
    '''
    output = []
    while True:
        line = yield from stream.readline()
        if not line:
            break
        output.append(line)
        display(line)
    return output

@asyncio.coroutine
def read_and_display(cmd):
    '''
    capture cmd stdout, stderr while also displaying them
    '''
    print(cmd)
    proc = yield from asyncio.create_subprocess_shell(cmd,\
            stdout=PIPE,stderr=PIPE)
    try:
        stdout, stderr = yield from asyncio.gather(\
                read_stream_and_display(proc.stdout, sys.stdout.buffer.write),\
                read_stream_and_display(proc.stderr, sys.stderr.buffer.write))
    except Exception:
        proc.kill()
        raise
    finally:
        rc = yield from proc.wait()
    return rc, stdout, stderr

def run_ffmpeg(cmd):
    '''
    runs cmd for ffmpeg
    '''
    logger.info("running ffmpeg with below command:")
    logger.info("%s", cmd)
    if os.name == 'nt':
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()
    rc, stdout, stderr = loop.run_until_complete(read_and_display(cmd))
    loop.close()
    #stderr = list(stderr)
    print(type(stderr))
    print(len(stderr))
    print("ok parsing this output into fflog")
    fflog = []
    for line in stderr:
        print(type(line))
        input("eh")
        if not line.startswith("frame"):
            fflog.append(line)
        else:
            break
    print(len(fflog))
    logger.info(fflog)
    logger.info(stderr[-1])
    input("eh")
    if rc == 0:
        return True
    else:
        return False
    '''
    try:
        proc = subprocess.Popen(cmd, shell=True)
        proc.communicate()
        if not proc.returncode == 0:
            logger.error("ffmpeg encountered an error")
            #logs.append("ERROR: see ffmpeg output below:")
            #logs.append(stderr)
            return False
        else:
            #logs.append(stdout)
            logger.info("ffmpeg completed successfully")
            return True
    except subprocess.CalledProcessError as e:
        logger.error("ffmpeg encountered an error")
        logger.error("see ffmpeg stderr output below:")
        #logs.append(str(e.stdout))
        return False'''

def make_mpeg_dvd(accession, file, kwargs):
    '''
    make mpg for dvd
    '''
    logger.info("creating mpeg derivative for DVD")
    #endfile.mpeg + timecode
    drawtext = '"drawtext=fontfile=' + "'" + str(kwargs.config.timecode_fontfile) + "'" + ": timecode='00\:00\:00\:00'" + ': r=29.97: x=(w-tw)/2: y=h-(2*lh): fontcolor=white: fontsize=72: box=1: boxcolor=0x00000099'
    ffmpeg_cmd = 'ffmpeg -i concat.mov -target ntsc-dvd -map_channel 0.1.0:0.1 -map_channel 0.2.0:0.1 -ac 2 -b:v 5000k -vtag xvid -vf ' + drawtext + ',scale=720:480" -threads 0 ' + mpeg
    ffmpeg_ok = run_ffmpeg(ffmpeg_cmd, kwargs)
    if not ffmpeg_ok:
        return False
    return True

def make_mp4_with_tc(accession, file, kwargs):
    '''
    creates mp4 with burned in timecode
    '''
    logger.info("creating mp4 derivative with burned-in timecode")
    mp4 = accession + ".mp4"
    drawtext = '"drawtext=fontfile=' + "'" + str(kwargs.config.timecode_fontfile) + "'" + ": timecode='00\:\:00\:00\:00'" + ': r=29.97: x=(w-tw)/2: y=h-(2*lh): fontcolor=white: fontsize=72: box=1: boxcolor=0x0000009    9'
    ffmpeg_cmd = 'ffmpeg -i concat.mov -c:v mpeg4 -b:v 372k -pix_fmt yuv420p -r 29.97 -vf ' + drawtext + ',scale=420:270" -c:a aac -ar 44100 -map_channel 0.1.0:0.1 -map_channel 0.2.0:0.1 -threads 0 ' + mp4
    ffmpeg_ok = run_ffmpeg(ffmpeg_cmd)
    if not ffmpeg_ok:
        return False
    return True

def make_mp4_with_logo(accession, file, kwarg):
    '''
    creates mp4 derivative with logo
    '''
    logger.info("creating mp4 derivative with logo")
    return str(accession) + "-logo.mp4", logs

def make_mxf_mezz(accession, file, kwargs):
    '''
    creates mxf mezzanine file
    '''
    logger.info("creating mxf mezzanine file")
    return str(accession) + ".mxf", logs

def concatenate_raw_captures(accession, files, kwargs):
    '''
    setup accession directory for ffmpeg transcode to concatenate raw captures
    '''
    accession_dir = files[0].parent
    segment = accession.split("_")[-1]
    logger.info("concatenating input files in directory %s", str(accession_dir))
    concat_txt_path = accession_dir / "concat.txt"
    concat_mov = accession_dir / "concat.mov"
    accession_mov = str(accession_dir / accession) + "_pres.mov"
    with open(concat_txt_path,"a") as concat_txt:
        for file in files:
            concat_txt.write('file ' + str(file.name) + "\n")
    ffmpeg_cmd = 'ffmpeg -f concat -i concat.txt -map 0 -c:v copy -c:a copy -ignore_unknown -timecode ' + segment[-2:] + ':00:00:00 concat.mov'
    ffmpeg_ok = run_ffmpeg(ffmpeg_cmd)
    if not ffmpeg_ok:
        logger.error("ffmpeg encountered an error during concatenation")
        return False
    else:
        logger.info("concatenation completed successfully")
        concat_mov.replace(accession_mov)
        concat_txt_path.unlink()
        return [accession_mov]

def make_test_videos(kwargs):
    '''
    creates test outputs per THM spec
    '''

def main():
    '''
    do the thing
    '''
    print("howdy")

if __name__ == "__main__":
    main()
