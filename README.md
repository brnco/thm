# The History Makers

This repository contains scripts to process preservation files, generate checksums, and create and move derivatives of The History Makers oral history interviews.

# Contents

[Installation](https://github.com/brnco/thm/tree/dev#installation)

[Configuration](https://github.com/brnco/thm/tree/dev#configuration)

[Usage](https://github.com/brnco/thm/tree/dev#usage)

[Script Descriptions](https://github.com/brnco/thm/tree/dev#script-descriptions)

# Installation

1. Install Git

2. Install Python

3. Clone this repo

4. Install python dependencies

5. Install and configure ODBC driver

6. Install MediaConch

7. Install ffmpeg

8. Get watermark files

9. Config

# Configuration

This repo ships with a template configuration file `template_video-post-processing.config`

To set up the configuration for the scripts:

1. copy and paste the file, renaming it to `video-post-processing.config`

2. fill out fields per the local specifications

## General Configuration Notes

general format is:

```
[section_header]
variable_name = variable value
```

Do not enclose paths with quotes, even if they have spaces - do not escape whitespace (e.g. with `\`).

## Configuration Fields Reference

### Filetypes

These are the file extensions which the script will process. If video files exist in an accession directory, and have a different extention than defined in this config file, then they will not be processed. `.dv` files are not processed by this script by default, for example (although you can add that!).

### Ingest

This section contains paths to the folders where the files to be transcoded are located. There are two folders, one for standard HistoryMakers interviews, and another for Special Collections. Individual accessions should be saved at these paths in a folder named with the accession number.

Example folder setup, tree view

```
/hm_interviews
├── A2022_034_001_001
│   ├── DOH_HEJ_006_000.mov
│   ├── DOH_HEJ_006_001.mov
│   ├── DOH_HEJ_006_002.mov
│   └── DOH_HEJ_006.XML
├── A2022_034_001_002
│   ├── DOH_HEJ_007_000.mov
│   ├── DOH_HEJ_007_001.mov
│   ├── DOH_HEJ_007_002.mov
│   └── DOH_HEJ_007.XML
├── A2022_047_001_001
│   ├── 01275001.MOV
│   ├── 01275002.MOV
│   ├── 01275003.MOV
│   └── 01275004.MOV
/special_collections
├── S2023_012_001_001
│   └── NINJAV_023_ABC_789.mp4
```

### File Destinations

This section defines the paths to the folders where files are sent after processing.

### Email

This section defines the info for email notifications from the script.

### Logs

This section defines the folder path for the directory containing the logs.

### MediaConch

This section defines the paths for MediaConch policies (for input file validation).

### FileMaker

This section defines the information for authenticating to FileMaker. When hashes are sent to FM, this is the user who will be shown to have made those changes.

# Usage

## tl;dr

`(venv) C:\Users\archadmin\code\thm: python ingest.py`

## Help

To list all of the options available for the script, type `python ingest.py -h` and hit enter

## General

1. Open cmd.exe

   - press `Windows key` and search 'cmd.exe' and hit enter

   - right-click on the terminal icon in the menu bar, select 'cmd.exe'
  
2. Navigate to the scripts directory

   - type `cd code\thm` and hit enter
  
3. Start the virtual environment

   - type `venv\Scripts\activate.bat` and hit enter

   - you should see `(venv)` at the start of your command prompt

4. Run the script

   - type `python ingest.py` and hit enter

## Examples

### Ingest everything in the `hm_interviews` directory

as configured in the config file

`python ingest.py`

### Ingest a single accession, A2022_012_001_001

the script will first check the `hm_interviews` folder then will check `special_collections`, as configured in the config file

`python ingest.py A2022_012_001_001`

### Ingest multiple accessions

same rules as above

`python ingest.py A2022_012_001_001 A2022_033_001_001`

### Ingest special collections

You can specify that an accession is special collections using the flag (but you don't have to flag it)

`python ingest.py --special_collections A2022_001_001_001`

Ingest every accession folder in `special_collections`

`python ingest.py --special_collections`

### Change what is printed to terminal window

Ingest in `verbose` mode, printing more to the terminal window

`python ingest.py -v`

Ingest in `quiet` mode, printing less to the terminal window

`python ingest.py -q`

note that `quiet` or `verbose` modes do not impact the logs, which always log in `verbose` mode, they only change what is printed to the terminal window

### Other options

Run the script without sending emails using the `--no_email` flag

`python ingest.py --no_email`

Run the script without copying files to the connected drives using the `--no_copy` flag

`python ingest.py --no_copy`

### Using multiple flags

these options can be strung together in a single command. the command below will process two accessions, printing every log entry to the terminal window, without copying files and without emailing anyone

`python ingest.py -v --no_copy --no_email A2022_999_001_001 A2017_088_001_001`

# Script Descriptions

## ingest

This is the main script in this repository and it manages the ingest process.

Folders containing a single accession are located in one of two holding directories, one for HistoryMakers interviews and one for Special Collections. The script then examines each file in a single accession folder and determines which processing steps are necessary to create the final deliverables: audio and video streams may need to be transcoded to preservation codecs; a sequence of files may need to be concatenated to form a single preservation file.

The deliverables for this script are:

1. A single preservation file, wrapped in MXF, containing PCM audio and video with a codec of either JPEG2000, ProRes, or DNxHD.

2. Two derivates MP4 files, one with a watermark and one with burned-in timecode

3. Hashes for all of the above files, sent to FileMaker

## transcodes

This script handles all of the ffmpeg calls and transcoding functions for the ingest process.

## startup

This script runs at the beginning of th eingest process and ensures that things are set up correctly: that `ingest.py` is being run from within the virtual environment (`venv`); that the diectories containing raw accessions exist; that the drives where final deliverables are sent exist.

It also is responsible for getting the list of files to process for each individual accession and adding/ removing lockfiles on individual accession direcotires, so that they're not processed by two instances of the script at the same time.

## file_validation

This script uses [MediaConch](https://mediaarea.net/MediaConch) validation to detect the audio and video codecs present in the input files. Depending on the codecs, audio and video streams may or may not be transcoded during processing. 

This script was formally used to verify that HistoryMakers interview files were made according to the spec; however, since we've normalized to a single preservation filetype (JPEG2000), this functionality is no longer needed.

## filemaker_handler

This script handles all calls to FileMaker database. During processing it: checks that the script's connection to FileMaker is active; that a metadata record for the accession being processed exists; and it updates the checksum values for individual files.

## send_email

This script sends emails per the info in config file. Emails are sent at the conclusion of a run of the script, or after an error.

## util

Utility functions required by other scripts in this repository.
