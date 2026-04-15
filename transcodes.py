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
import pathlib
import traceback


logger = logging.getLogger(__name__)


def format_ffmpeg_log():
    '''
    formats ffmpeg.log for THM log file
    '''
    fflog_raw = []
    fflog_proc = ''
    fflog_path = pathlib.Path("ffmpeg.log")
    try:
        with open(str(fflog_path),"r") as ffmpeg_log:
            while True:
                line = ffmpeg_log.readline()
                if not line.startswith("frame"):
                    fflog_raw.append(line)
                else:
                    break
        for line in fflog_raw:
            fflog_proc += line
        logger.debug(fflog_proc)
        fflog_path.unlink()
        return True
    except Exception as e:
        logger.error("there was an issue formatting the ffmpeg log")
        logger.error(traceback.format_exc())
        return False


def run_ffmpeg(cmd):
    '''
    runs cmd for ffmpeg
    '''
    try:
        logger.info("running ffmpeg with below command:")
        logger.info("%s", cmd)
        output = subprocess.run(cmd, shell=True)
        if not output.returncode == 0:
            logger.error("there was an error transcoding that file, see log for details")
            return False
        else:
            format_ffmpeg_log()
            logger.info("ffmpeg ran successfully")
            return True
    except Exception as e:
        logger.error("there was an issue running ffmpeg")
        logger.error(traceback.format_exc())
        return False


def make_mp4_with_tc(accession, file, kwvars):
    '''
    creates mp4 with burned in timecode
    '''
    logger.info("creating mp4 derivative with burned-in timecode")
    mp4 = file.with_name(accession + "_tc.mp4")
    segment = accession.split("_")[-1]
    if kwvars.is_interlaced:
        yadif = "yadif,"
    else:
        yadif = ""
    drawtext = '"drawtext=fontfile=' + r"'C\:\\Windows\\Fonts\\arial.ttf':timecode='"+ segment[-2:] + \
        "\:00\:00\;00':r=29.97:x=(w-text_w)/2:y=(h-text_h)/1.2:fontcolor=white:fontsize=72:box=1:boxcolor=0x00000099"
    ffmpeg_cmd = 'ffmpeg -i ' + str(file) + \
            ' -c:v libx264 -b:v 372k -pix_fmt yuv420p -r 29.97 -vf ' +  yadif + '"crop=trunc(iw/2)*2:trunc(ih/2)*2,' + drawtext[1:] + \
        ',scale=420:trunc(ow/a/2)*2" -c:a aac -ar 44100 -ac 2 -map -0:d? ' + \
        '-threads 0 -movflags +faststart -y ' + \
        str(mp4) + kwvars.ffmpeg_suffix
    ffmpeg_ok = run_ffmpeg(ffmpeg_cmd)
    if not ffmpeg_ok:
        return False
    return mp4


def make_mp4_with_logo(accession, file, kwvars):
    '''
    creates mp4 derivative with logo
    '''
    logger.info("creating mp4 derivative with logo")
    mp4 = file.with_name(accession + "_wm.mp4")
    if kwvars.is_interlaced:
        yadif = "[0]yadif,"
    else:
        yadif = ""
    ffmpeg_cmd = 'ffmpeg -i ' + str(file) + ' -i ' + str(kwvars.watermark_white) + \
            ' -filter_complex ' + yadif + '"overlay=0:0,crop=trunc(iw/2)*2:trunc(ih/2)*2,scale=420:trunc(ow/a/2)*2" ' \
        + '-c:v libx264 -b:v 372k -pix_fmt yuv420p -r 29.97 -c:a aac -ar 44100 -ac 2 -map -0:d? ' \
        + '-threads 0 -movflags +faststart -y ' \
        + str(mp4) + kwvars.ffmpeg_suffix
    ffmpeg_ok = run_ffmpeg(ffmpeg_cmd)
    if not ffmpeg_ok:
        return False
    return mp4


def reencode_accession(accession, files, kwvars):
    '''
    if files in accession folder need to be reencoded for preservation
    that process managed here
    '''
    _files = []
    for input_file in files:
        logger.info(f"reencoding {input_file}")
        segment = accession.split("_")[-1]
        output_file = input_file.with_name(accession + "_pres.mxf")
        if kwvars.reencode_video and kwvars.reencode_audio:
            '''
            ffmpeg -i file -c:v jpeg2000 -c:a pcm_s24le file.mxf
            '''
            ffmpeg_cmd_base = "ffmpeg -i " + str(input_file) + \
                    " -map 0:v -map 0:a -c:v jpeg2000 -pred 1 -c:a pcm_s24le -strict unofficial -ignore_unknown "
        elif kwvars.reencode_audio:
            '''
            ffmpeg -i file -c:v copy -c:a pcm_s24le file.mxf
            '''
            ffmpeg_cmd_base = "ffmpeg -i " + str(input_file) + \
                    " -map 0:v -map 0:a -c:v copy -c:a pcm_s24le -strict unofficial -ignore_unknown "
        elif kwvars.reencode_video:
            '''
            ffmpeg -i file -c:v jpeg2000 -c:a copy file.mxf
            '''
            ffmpeg_cmd_base = "ffmpeg -i " + str(input_file) + \
                    " -map 0:v -map 0:a -c:v jpeg2000 -pred 1 -c:a copy -strict unofficial -ignore_unknown "
        ffmpeg_cmd_timecode = '-timecode "' + segment[-2:] + ':00:00;00" '
        ffmpeg_cmd_out = '-y ' + str(output_file) + kwvars.ffmpeg_suffix
        if kwvars.special_collections:
            ffmpeg_cmd = ffmpeg_cmd_base + ffmpeg_cmd_out
        else:
            ffmpeg_cmd = ffmpeg_cmd_base + ffmpeg_cmd_timecode + ffmpeg_cmd_out
        ffmpeg_ok = run_ffmpeg(ffmpeg_cmd)
        if not ffmpeg_ok:
            raise RuntimeError("ffmpeg encountered an error during reencoding")
        else:
            logger.info("reencoding completed successfully")
            _files.append(output_file)
    return _files


def concatenate_raw_captures(accession, files, kwvars):
    '''
    concatenates raw captures in accession folder
    '''
    accession_dir = files[0].parent
    in_file_ext = files[0].suffix
    out_file_ext = ".mxf"
    segment = accession.split("_")[-1]
    logger.info("concatenating input files in directory %s", str(accession_dir))
    concat_txt_path = accession_dir / "concat.txt"
    concat_vid = concat_txt_path.with_suffix(out_file_ext)
    accession_pres = concat_txt_path.with_name(accession + "_pres" + out_file_ext)
    with open(concat_txt_path,"a") as concat_txt:
        for file in sorted(files):
            concat_txt.write('file ' + str(file.name) + "\n")
    ffmpeg_cmd_base = 'ffmpeg -f concat -dn -i concat.txt -map 0:v -map 0:a -c:v copy -c:a copy -ignore_unknown -strict unofficial '
    ffmpeg_cmd_timecode = '-timecode "' + segment[-2:] + ':00:00;00" '
    ffmpeg_cmd_out = '-y ' + str(concat_vid) + kwvars.ffmpeg_suffix
    if kwvars.special_collections:
        ffmpeg_cmd = ffmpeg_cmd_base + ffmpeg_cmd_out
    else:
        ffmpeg_cmd = ffmpeg_cmd_base + ffmpeg_cmd_timecode + ffmpeg_cmd_out
    ffmpeg_ok = run_ffmpeg(ffmpeg_cmd)
    if not ffmpeg_ok:
        raise RuntimeError("ffmpeg encountered an error during concatenation")
    else:
        logger.info("concatenation completed successfully")
        concat_vid.replace(accession_pres)
        concat_txt_path.unlink()
        return str(accession_pres)


def detect_frame_dimensions(file, kwvars):
    '''
    detects the frame width and height of file
    '''
    logger.info(f"getting frame dimensions for {file}")
    ffmpeg_cmd = "ffprobe -v error -select_streams v -show_entries stream=width,height -of csv=p=0:s=x -i " + str(file)
    logger.info(ffmpeg_cmd)
    ffmpeg_ok = subprocess.run(ffmpeg_cmd, capture_output=True, shell=True)
    output = ffmpeg_ok.stdout.decode("utf-8").strip()
    logger.info(f"ffmpeg found these frame dimensions: {output}")
    if not ffmpeg_ok.returncode == 0:
        raise RuntimeError("ffmpeg encountered an error during frame dimensions detection")
    wh = output.split("x")
    if len(wh) < 2:
        logger.error("there was a problem detecting frame dimensions")
        logger.error(f"expected 2 values but got: {wh}")
        raise RuntimeError(f"The script encountered a problem detecting frame dimensions for {file}")
    kwvars.frame_width = int(wh[0])
    kwvars.frame_height = int(wh[1])
    return kwvars


def detect_interlaced_video(file, kwvars):
    '''
    detects if input file is interlaced
    '''
    logger.info("testing %s file for interlaced video", str(file))
    #ffmpeg_cmd = "ffmpeg -filter:v idet -frames:v 360 -an -f rawvideo -y NUL -i " + str(file)
    ffmpeg_cmd = "ffprobe -v quiet -select_streams v -show_entries stream=field_order -of csv=p=0 -i " + str(file)
    logger.info(ffmpeg_cmd)
    ffmpeg_ok = subprocess.run(ffmpeg_cmd, capture_output=True, shell=True)
    output = ffmpeg_ok.stdout.decode("utf-8").strip()
    logger.info(f"ffmpeg found this field order: {output}")
    if not ffmpeg_ok.returncode == 0:
        raise RuntimeError("ffmpeg encountered an error during interlace detection")
    else:
        interlaced_formats = ["tff", "bff", "tb", "bt", "tt", "bb"]
        for iformat in interlaced_formats:
            if iformat in output:
                kwvars.is_interlaced = True
                return kwvars
        if "progressive" in output or "unknown" in output:
            kwvars.is_interlaced = False
            return kwvars
    raise RuntimeError("ffprobe unable to detect progressive or interlaced video")


def reencode_audio_to_pcm(in_file, kwvars):
    '''
    takes input file with pcm audio
    outputs new file with pcm audio
    '''
    logger.info("re-encoding file with pcm audio")
    out_file = in_file.with_stem(in_file.stem + "_pcm")
    ffmpeg_cmd = "ffmpeg -i " + str(in_file) + " -c:v copy -c:a pcm_s24le -map -0:d? " \
        "-y " + str(out_file) + kwvars.ffmpeg_suffix
    output = run_ffmpeg(ffmpeg_cmd)
    if not output:
        logger.error("ffmpeg encountered an error during re-encoding")
        return False
    else:
        return out_file


def rewrap_single_file_accession(accession, input_file, kwvars):
    '''
    for single file accessions, we need to rewrap the files with correct timecode
    '''
    logger.info("rewrapping single video file accession with correct timecode")
    segment = accession.split("_")[-1]
    pres_file = input_file.parent / pathlib.Path(accession + "_pres" + ".mxf")
    ffmpeg_cmd = "ffmpeg -i " + str(input_file) + " -c copy -map -0:d? " \
            '-timecode "' + segment[-2:] + ':00:00;00" -strict unofficial -y ' \
            + str(pres_file) + kwvars.ffmpeg_suffix
    output = run_ffmpeg(ffmpeg_cmd)
    if not output:
        logger.error("there was an issue rewrapping that file")
        return False
    else:
        return pres_file

