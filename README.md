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

ffmpeg -i [concatenatedMOV].mov -i watermark.png -filter_complex "overlay=x=(main_w-overlay_w)/2:y=(main_h-overlay_h)/2" -c:v libx264 -preset fast -b:v 700k -r 29.97 -vf scale=320:180 -c:a aac -ar 44100 -ac 2 -map_metadata 0 [name]flv


**mpeg**

ffmpeg -i [concatenatedMOV].mov -map 0:1 -map 0:0 -c:a mp2 -ar 48000 -sample_fmt s16 -ac 2 -c:v mpeg2video -pix_fmt yuv420p -r 29.97 -vtag xvid -vf "drawtext=fontfile=" + [fontfile].ttf + ": timecode='09\:57\:00\:00': r=29.97: x=(w-tw)/2: y=h-(2*lh): fontcolor=white: box=1: boxcolor=0x00000099" -vf scale=720:480 [name].mpeg

**mp4**

ffmpeg -i [concatenatedMOV].mov -c:v mpeg4 -vtag xvid -b:v 372k -pix_fmt yuv420p -r 29.97 -vf "drawtext=fontfile=" + [fontfile].ttf + ": timecode='09\:57\:00\:00': r=29.97: x=(w-tw)/2: y=h-(2*lh): fontcolor=white: box=1: boxcolor=0x00000099" -vf scale=420:270 -c:a aac -ar 44100 -ac 2 [name].mp4