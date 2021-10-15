# mkv-extract
Simple tool to extract and compress data from mkv files that are written by k4arecorder. 

## Installation
Clone this repository, enter the directory `mkv-extract` and run `pip install -e .`

## Behavior
IR and DEPTH streams are encoded losslessly using the FFV1 codec. The COLOR stream is encoded using H264 (lossy) at a high-quality setting. Timestamps, metadata and camera calibration data all extracted and saved to a json file. The extracted files are named as extensions of the input file. For example, if the input file is `my_recoridng.mkv`, then the output files will be `my_recording.DEPTH.avi`, `my_recording.metadata.json`, etc. **Note that the `.mkv` file is not deleted after extraction**. 

## Usage
Scenario 1: Extracting a single file
`mkv-extract path/to/my_recoridng.mkv`

Scenario 2: Extracting multiple files
`mkv-extract path/to/*.mkv`

Scenario 3: Extracting multiple files using slurm
`mkv-extract path/to/*.mkv --slurm`

*Note: Make sure ffmpeg is installed. If using HMS O2, you must run `module load ffmpeg`.*
