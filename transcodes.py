'''
handles all transcodes and concatenations
'''
import subprocess

def run_ffmpeg(cmd):
    '''
    runs cmd for ffmpeg
    '''
    logs = []
    logs.append("INFO: running ffmpeg with below command:")
    logs.append("INFO: " + cmd)
    try:
        proc = subprocess.Popen(cmd, shell=True)
        proc.communicate()
        if not proc.returncode == 0:
            logs.append("ERROR: ffmpeg encountered an error")
            #logs.append("ERROR: see ffmpeg output below:")
            #logs.append(stderr)
            return False, logs
        else:
            #logs.append(stdout)
            logs.append("INFO: ffmpeg completed successfully")
            return True, logs
    except subprocess.CalledProcessError as e:
        logs.append("ERROR: ffmpeg encountered an error")
        logs.append("ERROR: see ffmpeg stderr output below:")
        #logs.append(str(e.stdout))
        return False, logs

def make_mpeg_dvd(accession, file, kwargs):
    '''
    make mpg for dvd
    '''
    logs = []
    logs.append("INFO: creating mpeg derivative for DVD")
    #endfile.mpeg + timecode
    drawtext = '"drawtext=fontfile=' + "'" + str(kwargs.config.timecode_fontfile) + "'" + ": timecode='00\:00\:00\:00'" + ': r=29.97: x=(w-tw)/2: y=h-(2*lh): fontcolor=white: fontsize=72: box=1: boxcolor=0x00000099'
    ffmpeg_cmd = 'ffmpeg -i concat.mov -target ntsc-dvd -map_channel 0.1.0:0.1 -map_channel 0.2.0:0.1 -ac 2 -b:v 5000k -vtag xvid -vf ' + drawtext + ',scale=720:480" -threads 0 ' + mpeg
    ffmpeg_ok = run_ffmpeg(ffmpeg_cmd, kwargs)
    if not ffmpeg_ok:
        return False, logs
    return True, logs

def make_mp4_with_tc(accession, file, kwargs):
    '''
    creates mp4 with burned in timecode
    '''
    logs = []
    logs.append("INFO: creating mp4 derivative with burned-in timecode")
    mp4 = accession + ".mp4"
    drawtext = '"drawtext=fontfile=' + "'" + str(kwargs.config.timecode_fontfile) + "'" + ": timecode='00\:\:00\:00\:00'" + ': r=29.97: x=(w-tw)/2: y=h-(2*lh): fontcolor=white: fontsize=72: box=1: boxcolor=0x0000009    9'
    ffmpeg_cmd = 'ffmpeg -i concat.mov -c:v mpeg4 -b:v 372k -pix_fmt yuv420p -r 29.97 -vf ' + drawtext + ',scale=420:270" -c:a aac -ar 44100 -map_channel 0.1.0:0.1 -map_channel 0.2.0:0.1 -threads 0 ' + mp4
    ffmpeg_ok = run_ffmpeg(ffmpeg_cmd, kwargs)
    if not ffmpeg_ok:
        return False, logs
    return True, logs

def make_mp4_with_logo(accession, file, kwargs):
    '''
    creates mp4 derivative with logo
    '''
    logs = []
    logs.append("INFO: creating mp4 derivative with logo")
    return str(accession) + "-logo.mp4", logs

def make_mxf_mezz(accession, file, kwargs):
    '''
    creates mxf mezzanine file
    '''
    logs = []
    logs.append("INFO: creating mxf mezzanine file")
    return str(accession) + ".mxf", logs

def concatenate_raw_captures(accession, files, kwargs):
    '''
    setup accession directory for ffmpeg transcode to concatenate raw captures
    '''
    logs = []
    accession_dir = files[0].parent
    segment = accession.split("_")[-1]
    logs.append("INFO: concatenating input files in directory " + str(accession_dir))
    concat_txt_path = accession_dir / "concat.txt"
    concat_mov = accession_dir / "concat.mov"
    accession_mov = str(accession_dir / accession) + "_pres.mov"
    with open(concat_txt_path,"a") as concat_txt:
        for file in files:
            concat_txt.write('file ' + str(file.name) + "\n")
    ffmpeg_cmd = 'ffmpeg -f concat -i concat.txt -map 0 -c:v copy -c:a copy -ignore_unknown -timecode ' + segment[-2:] + ':00:00:00 concat.mov'
    ffmpeg_ok, fflogs = run_ffmpeg(ffmpeg_cmd)
    for fflog in fflogs:
        logs.append(fflog)
    if not ffmpeg_ok:
        logs.append("ERROR: ffmpeg encountered an error during concatenation")
        return False, logs
    else:
        logs.append("INFO: concatenation completed successfully")
        concat_mov.replace(accession_mov)
        concat_txt_path.unlink()
        return [accession_mov], logs

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
