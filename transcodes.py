#!/usr/bin/env python
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

    limit here is used to limit the amount of output text
    we need it because ffmpeg outputs a lot of text data
    keep the 1024 * to start, second number is number of bytes
    total limit is expressed in kibibytes (roughly same as kilobytes)
    default is 2MiB
    '''
    proc = yield from asyncio.create_subprocess_shell(cmd,\
            limit = 1024 * 2048, stdout=PIPE,stderr=PIPE)
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
    fflog = []
    for line in stderr:
        if not line.startswith(b'frame'):
            fflog.append(line.decode("utf-8"))
        else:
            break
    ffstr = ''
    for line in fflog:
        ffstr += line
    logger.info(ffstr)
    try:
        logger.info(stderr[-1].decode("utf-8"))
    except:
        pass
    if rc == 0:
        return True
    else:
        return False

def make_mpg_dvd(accession, file, kwargs):
    '''
    make mpg for dvd
    '''
    logger.info("creating mpeg derivative for DVD")
    mpeg = accession + "_dvd.mpg"
    mpeg_fullpath = kwargs.config.raw_captures / accession / mpeg
    segment = accession.split("_")[-1]
    if kwargs.is_interlaced:
        yadif = "yadif,"
    else:
        yadif = ""
    drawtext = '"drawtext=fontfile=' + r"'C\:\\Windows\\Fonts\\arial.ttf':timecode='"+ segment[-2:] + \
        "\:00\:00\;00':r=29.97:x=(w-tw)/2:y=h-(2*lh):fontcolor=white:fontsize=72:box=1:boxcolor=0x00000099"
    ffmpeg_cmd = 'ffmpeg -loglevel warning -i ' + str(file) + ' -target ntsc-dvd -ac 2 -b:v 5000k -vtag xvid -vf ' + yadif + drawtext + \
        ',scale=720:480" -threads 0 -y ' + str(mpeg_fullpath)
    ffmpeg_ok = run_ffmpeg(ffmpeg_cmd)
    if not ffmpeg_ok:
        return False
    return mpeg_fullpath

def make_mp4_with_tc(accession, file, kwargs):
    '''
    creates mp4 with burned in timecode
    '''
    logger.info("creating mp4 derivative with burned-in timecode")
    mp4 = accession + "_tc.mp4"
    mp4_fullpath = kwargs.config.raw_captures / accession / mp4
    segment = accession.split("_")[-1]
    if kwargs.is_interlaced:
        yadif = "yadif,"
    else:
        yadif = ""
    drawtext = '"drawtext=fontfile=' + r"'C\:\\Windows\\Fonts\\arial.ttf':timecode='"+ segment[-2:] + \
        "\:00\:00\;00':r=29.97:x=(w-text_w)/2:y=(h-text_h)/1.2:fontcolor=white:fontsize=72:box=1:boxcolor=0x00000099"
    ffmpeg_cmd = 'ffmpeg -loglevel warning -i ' + str(file) + \
        ' -c:v libx264 -b:v 372k -pix_fmt yuv420p -r 29.97 -vf ' +  yadif + drawtext + \
        ',scale=420:270" -c:a aac -ar 44100 -ac 2 -map -0:d? -threads 0 -y ' + str(mp4_fullpath)
    ffmpeg_ok = run_ffmpeg(ffmpeg_cmd)
    if not ffmpeg_ok:
        return False
    return mp4_fullpath

def make_mp4_with_logo(accession, file, kwargs):
    '''
    creates mp4 derivative with logo
    '''
    logger.info("creating mp4 derivative with logo")
    mp4 = accession + "_wm.mp4"
    mp4_fullpath = kwargs.config.raw_captures / accession / mp4
    if kwargs.is_interlaced:
        yadif = "[0]yadif,"
    else:
        yadif = ""
    ffmpeg_cmd = 'ffmpeg -loglevel warning -i ' + str(file) + ' -i ' + str(kwargs.config.watermark_white) + \
        ' -filter_complex ' + yadif + 'overlay=0:0,scale=420:270 ' \
        + '-c:v libx264 -b:v 372k -pix_fmt yuv420p -r 29.97 -c:a aac -ar 44100 -ac 2 -map -0:d? -threads 0 -y ' + str(mp4_fullpath)
    ffmpeg_ok = run_ffmpeg(ffmpeg_cmd)
    if not ffmpeg_ok:
        return False
    return mp4_fullpath

def make_mxf_mezz(accession, file, kwargs):
    '''
    creates mxf mezzanine file
    '''
    logger.info("creating mxf mezzanine file")
    mxf = accession + "_mezz.mxf"
    mxf_fullpath = kwargs.config.raw_captures / accession / mxf
    ffmpeg_cmd = 'ffmpeg -loglevel warning -i ' + str(file) + \
        ' -c:v libx264 -pix_fmt yuv422p -b:v 15000k -r 30/1.001 -c:a pcm_s24le -map 0:v -map 0:a -map -0:d? -threads 0 -y ' + str(mxf_fullpath)
    ffmpeg_ok = run_ffmpeg(ffmpeg_cmd)
    if not ffmpeg_ok:
        return False
    return mxf_fullpath

def concatenate_raw_captures(accession, files, kwargs):
    '''
    concatenates raw captures in accession folder
    '''
    accession_dir = files[0].parent
    file_ext = files[0].suffix
    if ".MOV" in file_ext:
        file_ext = ".mov"
    segment = accession.split("_")[-1]
    logger.info("concatenating input files in directory %s", str(accession_dir))
    concat_txt_path = accession_dir / "concat.txt"
    concat_vid = concat_txt_path.with_suffix(file_ext)
    accession_pres = concat_txt_path.with_name(accession + "_pres" + file_ext)
    with open(concat_txt_path,"a") as concat_txt:
        for file in files:
            concat_txt.write('file ' + str(file.name) + "\n")
    ffmpeg_cmd = 'ffmpeg -loglevel warning -f concat -i concat.txt -map 0:v -map 0:a -map -0:d? -c:v copy -c:a copy -ignore_unknown -timecode ' + segment[-2:] + \
        ':00:00;00 -y ' + str(concat_vid)
    ffmpeg_ok = run_ffmpeg(ffmpeg_cmd)
    if not ffmpeg_ok:
        logger.error("ffmpeg encountered an error during concatenation")
        return False
    else:
        logger.info("concatenation completed successfully")
        concat_vid.replace(accession_pres)
        concat_txt_path.unlink()
        return str(accession_pres)

def detect_interlaced_video(file, kwargs):
    '''
    detects if input file is interlaced
    '''
    logger.info("testing %s file for interlaced video", str(file))
    ffmpeg_cmd = "ffmpeg -filter:v idet -frames:v 360 -an -f rawvideo -y NUL -i " + str(file)
    ffmpeg_cmd = "ffprobe -v quiet -select_streams v -show_entries stream=field_order -of csv=p=0 -i " + str(file)
    logger.info(ffmpeg_cmd)
    ffmpeg_ok = subprocess.run(ffmpeg_cmd, capture_output=True)
    logger.info(ffmpeg_ok.stdout.decode("utf-8").strip())
    if not ffmpeg_ok.returncode == 0:
        logger.error("ffmpeg encountered an error during interlace detection")
        return False
    else:
        output = ffmpeg_ok.stdout.decode("utf-8").strip()
        if "tff" in output or "bff" in output or "tb" in output or "bt" in output:
            kwargs.is_interlaced = True
            return kwargs
        elif "progressive" in output or "unknown" in output:
            kwargs.is_interlaced = False
            return kwargs
    logger.error("ffprobe unable to detect progressive or interlaced video")
    return False


def main():
    '''
    do the thing
    '''
    print("howdy")

if __name__ == "__main__":
    main()
