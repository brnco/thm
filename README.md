# The History Makers

This repository contains scripts to process preservation files, generate checksums, and create and move derivatives of The History Makers oral history interviews.

# Installation

1. Install Git

2. Install Python

3. Clone this repo

4. Install dependencies

5. Install and configure ODBC driver

6. Get watermark files

7. Config

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

## makevideos

this script takes the raw video captures delivered by THM personnel and:

1. concatenates the < 4GB files into 1 long file

2. transcodes that file to flv, mp4, and mpeg

3. embeds timecode and watermarks where appropriate

4. hashmoves (see below) them to their destiantions

5. triggers script to embed those hashes into a Filemaker db named PBCore_Catalog

makevideos also checks to make sure that everything is plugged in and that all necessary files (like watermarks) are in their expected locations.

makevideos is triggered every 15minutes, M-F, 7am-9pm local time by cron

makevideos can also be run manually by cd'ing into the repo directory (look for that in the config.txt file) and running "python makevideos.py"

## startup

this script checks the values in the config file against the configuration currently present on the workstation running the script. Predominantly, it verifies that filepaths specified in the config actually exist.

## file_validation

this script uses [MediaConch](https://mediaarea.net/MediaConch) validation to ensure that only valid input files are passed to the script for preservation/ transcode. MediaConch policies are managed in the directory specified in the config file. For each input file, this script checks it against available file policies in the MediaConch policies folder - if a match is found, that policy is used to validate all other input and output files for the accession.

### MediaConch GUI

if a file doesn't pass validation, follow these steps to find out why:

1. open MediaConch

2. in the "Checker" tab, use the dropdown menu to select the policy to check against -- see log for list of policies attempted

3. still in the "Checker" tab, select a file to check against the policy from step 1

4. select "check file"

5. MediaConch will analyze the file and add it to a list at the bottom of the window

6. to view pass/ fail for each field, click the eyeball icon

for more info, see official how-to's at [this link](https://mediaarea.net/MediaConch/Documentation/HowToUse)

## filemaker_handler

this script handles all calls to FileMaker database, requires ODBC

## send_email

this script sends emails per info in config file

## util

utility functions required by other scripts in this repository

## venv

This script uses Python's [venv](https://docs.python.org/3/library/venv.html) module to create a virutal environment, the venv folder contains configuration info for this virtual environment, and should not need to be modified
