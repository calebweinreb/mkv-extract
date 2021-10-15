# mkv-extract
Simple tool to extract and compress data from mkv files that are written by k4arecorder. 

## Installation
Clone this repository, enter the directory `mkv-extract` and run `pip install -e .`

## Behavior
Extracts each video stream from the mkv file and saves to a compressed video file. Timestamps and metadata are also saved. 
* IR and DEPTH streams are encoded losslessly using the FFV1 codec. 
* COLOR stream is encoded using the H264 codec (which is lossy) at a high-quality setting. 
* Timestamps (in seconds) are saved to a text file
* Metadata, including camera calibration, are saved to a json file. 
* All newly created files are named by adding suffixes to the input file. For example, if the input file is `my_recoridng.mkv`, then the output files will be `my_recording.depth.avi`, `my_recording.metadata.json`, `my_recording.timestamps.txt` etc. 
* There is an option to delete .mkv files after extraction. Prior to deletion, the losslessly encoded .avi files will be scanned, and deletion will only occur if they are identical to the original .mkv data.

## Usage
Scenario 1: Extracting a single file
`mkv-extract path/to/my_recoridng.mkv`

Scenario 2: Extracting multiple files
`mkv-extract path/to/*.mkv`

Scenario 3: Extracting multiple files using slurm
`mkv-extract path/to/*.mkv --slurm`

Scenario 4: Extraction followed by deletion
`mkv-extract [ARGS] --delete`

Scenario 5: Running extraction from python
```
from mkv_extract.mkv_utils import *
....
```

*Note: Make sure ffmpeg is installed. If using HMS O2, you must run `module load ffmpeg`.*
