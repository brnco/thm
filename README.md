# The History Makers

This repository contains scripts and configurations to process preservation files, generate checksums, and create and move derivatives of The History Makers oral history interviews.

# Installation

clone the repository to your local machine

# Configuration

1. open video-post-processing-config.txt in the text editor of your choice

2. fill out fields per your local specifications

## General Configuration Notes

general format is:

```
[section_header]

variable_name = variable value
```

do not enclose paths with quotes, even if they have spaces - do not escape whitespace either

## Configuration Fields Reference

### Filetypes

#### Input

comma-separated list of acceptable file extensions for input files, each extension is enclosed in quotes

e.g. ".mov",".MOV"

### Transcode

this section contains filepaths for assets which are required in order to transcode derivative files

#### White Watermark

#### Black Watermark

#### Timecode Font

#### raw_captures

specifies the path to the main ingest directory. This directory can be considered "hot" in that any subfolders will be attempted to be processed when the script is run with no arguments. Individual accessions should be saved at this path in a folder named with the accession number - alternatively, folder can contain any name if an alternative accession number is supplied at runtime (see Usage section of this document)

Example folder setup, tree view

```
/raw_captures
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
├── An Evening with Valerie Jarrett
│   ├── AEWVJA CAM1_1.mov
│   └── AEWVJA CAM1_2.mov
```

### File Destinations

This section describes folder paths for derivatives

### Email

This section contains info for email notifications from the script

### Logs

This section contains folder paths for the directory containing the logs, as well as the path of the lockfile that makevideos creates in order to only one a single instance of the script at a time

### MediaConch

This section delineates the folderpath for MediaConch policies

# Usage

## General

`makevideos.py --options accession_number(s)`

## Help

`makevideos.py -h`

## Examples

ingest everything in raw_captures directory, as configured in config file

`makevideos.py`

ingest a single accession, A2022_012_001_001

`makevideos.py A2022_012_001_001`

ingest multiple accessions

`makevideos.py A2022_012_001_001 A2022_033_001_001`

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

this script uses [MediaConch](https://mediaarea.net/MediaConch) validation to ensure that only valid input files are passed to the script for preservation/ transcode. MediaConch policies are managed in the directory specified in the config file. For each input file, this script checks it against available file policies in the MediaConch policies folder - if a match is found, that policy is used to validate all other input and output files for tha accession.

## filemaker_handler

this script handles all calls to FileMaker database, requires ODBC

## send_email

this script sends emails per info in config file

## util

utility functions required by other scripts in this repository

## venv

This script uses Python's [venv](https://docs.python.org/3/library/venv.html) module to create a virutal environment, the venv folder contains configuration info for this virtual environment, and should not need to be modified
