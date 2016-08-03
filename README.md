# thm
video post-processing for The History Makers
=======
# hashmove
better file movement

**General Usage**

python hashmove.py [source file or directory full path] [destination parent directory full path] [flags]

**to move a file**

python hashmove.py C:/path/to/file.ext C:/path/to/parent/dir

**to move a directory**

python hashmove.py /home/path/to/dir/a /home/path/to/dir/b

**to copy a file**

python hashmove.py C:/path/to/file.ext C:/path/to/parent/dir -c

**log the transfer**

python hashmove.py /home/path/to/dir/a /home/path/to/dir/b -l

**verify against another hash or set of hashes**

python hashmove.py "/home/path to/dir/you question" /home/path/to/dir/with/hashes -v



##ffmpeg strings
these aren't implemented quite as they are written here but if you wanted to make each of these derivatives with ffmpeg, this is what you would use:

**concatenate**

ffmpeg -f concat -i concat.txt -c copy [concatenatedMOV].mov


**flv**

ffmpeg -i [concatenatedMOV].mov -i watermark.png -filter_complex "overlay=x=(main_w-overlay_w)/2:y=(main_h-overlay_h)/2,scale=320:180" -c:v libx264 -preset fast -b:v 700k -r 29.97 -c:a aac -ar 44100 -ac 2 -map_metadata 0 [name].flv


**mpeg**

ffmpeg -i [concatenatedMOV].mov -map 0:1 -map 0:0 -c:a mp2 -ar 48000 -sample_fmt s16 -ac 2 -c:v mpeg2video -pix_fmt yuv420p -r 29.97 -vtag xvid -vf "drawtext=fontfile=[/path/to/fontfile].ttf: timecode='00\:00\:00\:00': r=29.97: x=(w-tw)/2: y=h-(2*lh): fontsize=72: fontcolor=white: box=1: boxcolor=0x00000099,scale=720:480" [name].mpeg

**mp4**

ffmpeg -i A2017_004_001_004.mov -c:v mpeg4 -b:v 372k -pix_fmt yuv420p -r 29.97 -vf "drawtext=fontfile=[/path/to/fontfile].ttf: timecode='00\:00\:00\:00': r=29.97: x=(w-tw)/2: y=h-(2*lh): fontsize=72: fontcolor=white: box=1: boxcolor=0x00000099,scale=420:270" -c:a aac -ar 44100 -ac 2 out1.mp4

**test input*

if you want to generate a test input file for this situation here's how

first, make a video file in the usual way

ffmpeg -f lavfi -i "testsrc=duration=10:size=1920x1080:rate=29.97" -c:v mpeg2video [vout].mov

then make an audio file and wrap it in a mov

ffmpeg -f lavfi -i "sine=frequency=1000:sample_rate=48000:duration=10" -c:a pcm_s24be [aout].mov

then warp the video file with the audio file mapped to two different streams

ffmpeg -i 01836001.mov -i [vout].mov -i [aout].mov -c:v copy -c:a pcm_s24be -map 0:v:0 -map 1:a:0 -map 2:a:0 [out].mov
