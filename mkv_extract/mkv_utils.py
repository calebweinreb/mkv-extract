import subprocess
import json
import os
import tqdm
import datetime
import numpy as np

import pdb

def get_stream_names(input_file, stream_tag="title"):
    '''
    Runs an FFProbe command to determine whether an input video file contains multiple streams, and
     returns a stream_name to paired int values to extract the desired stream.
    If no streams are detected, then the 0th (default) stream will be returned and used.
    Parameters
    ----------
    input_file (str): path to video file to get streams from.
    stream_tag (str): value of the stream tags for ffprobe command to return
    Returns
    -------
    out (dict): Dictionary of string to int pairs for the included streams in the mkv file.
     Dict will be used to choose the correct mapping number to choose which stream to read in read_frames().
    '''
    command = [
        "ffprobe",
        "-v","fatal",
        "-show_entries", "stream_tags={}".format(stream_tag),
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_file,
    ]
    ffmpeg = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    out, err = ffmpeg.communicate()
    if err or len(out) == 0: return {'DEPTH': 0}
    out = out.decode("utf-8").rstrip("\n").split("\n")
    return {o: i for i, o in enumerate(out)}

def extract_frames_from_mkv(input_file, output_prefix, verbose=True, threads=8):        
    # detect which streams are present (ir, color, depth)
    streams = get_stream_names(input_file)
    if verbose: print('  ...detected streams',list(streams.keys()))
    
    # create a parallel process for each stream
    processes = []
    for stream_name,ix in streams.items():
        if stream_name == 'COLOR': ext,codec,pixel_format,crf = 'mp4','h264','rgb24','24'
        if stream_name == 'DEPTH': ext,codec,pixel_format,crf = 'avi','ffv1','gray16','10'
        if stream_name == 'IR'   : ext,codec,pixel_format,crf = 'avi','ffv1','gray16','18'
        if verbose: print('  ...starting',stream_name,'extraction')
        command = [
            'ffmpeg',
            '-y',
            '-vsync','0',
            '-i', input_file,
            '-threads', str(threads),
            '-map','0:{}'.format(ix),
            '-pix_fmt', pixel_format,
            '-vcodec', codec,
            '-crf',crf,
            output_prefix+'.'+stream_name.lower()+'.'+ext
        ]
        processes.append(subprocess.Popen(command))
    
    # initiate processes
    exit_codes = [p.wait() for p in processes]
    if verbose: print('  ...finished extracting frames (exit codes =',exit_codes,')')
        
def extract_timestamps_from_mkv(input_file, threads=8, mapping='DEPTH'):
    command = [
        'ffprobe',
        '-v', 'quiet',
        '-select_streams',f'v:DEPTH',
        '-threads', str(threads),
        '-show_entries','frame=pkt_pts_time',
        '-print_format', 'json',
        input_file
    ] 
    output = subprocess.run(command, stdout=subprocess.PIPE).stdout
    print(output, flush=True)
    timestamps = [float(t['pkt_pts_time']) for t in json.loads(output.decode('utf-8'))['frames']]
    return timestamps

def extract_calibration_from_mkv(input_file):
    command = [
        'ffmpeg', 
        "-dump_attachment:t:0",
        "pipe:1","-i", input_file]
    output = subprocess.run(command, stdout=subprocess.PIPE).stdout
    return json.loads(output.decode('utf-8'))

def extract_metadata_from_mkv(input_file):
    command = [
        'ffprobe', 
        '-show_format',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        input_file
    ]
    output = subprocess.run(command, stdout=subprocess.PIPE).stdout
    return json.loads(output.decode('utf-8'))

def compress_mkv(input_file, verbose=True, output_prefix=None, delete=False, overwrite=False):
    if verbose: print('Extracting',input_file)
    if output_prefix is None:
        base_filename = os.path.splitext(os.path.basename(input_file))[0]
        output_prefix = os.path.join(os.path.dirname(input_file),base_filename)
        
    # extract metadata (including timestamps and calibration params)
    fname = output_prefix+'.metadata.json'
    if os.path.exists(fname) and not overwrite:
        if verbose: print('* metadata already exists, continuing...')
    else:
        if verbose: print('* extracting metadata')
        metadata = extract_metadata_from_mkv(input_file)
        metadata['calibration'] = extract_calibration_from_mkv(input_file)
        json.dump(metadata, open(fname,'w'), indent=4)
    
    fname = output_prefix+'.timestamps.txt'
    if os.path.exists(fname) and not overwrite:
        if verbose: print('* timestamps already extracted, continuing...')
    else:
        if verbose: print('* extracting timestamps')
        timestamps = extract_timestamps_from_mkv(input_file)
        timestamps_txt = '\n'.join([str(t) for t in timestamps])
        open(fname,'w').write(timestamps_txt)
    
    # extract frames
    if all([os.path.exists(prefix + suffix) for prefix in [output_prefix] for suffix in ['.depth.avi', '.ir.avi']]) and not overwrite:
        if verbose: print('* frames already extracted, continuing...')    
    else:
        if verbose: print('* extracting frames')
        extract_frames_from_mkv(input_file, output_prefix, verbose=verbose)
    
    # check compression integrity and delete
    if delete: check_mkv_extraction_integrity(input_file, output_prefix, delete=True)

    
def read_frames(filename, frames, threads=6, fps=30, frames_is_timestamp=False,
                pixel_format='gray16le', movie_dtype='uint16', frame_size=(576,640),
                slices=24, slicecrc=1, mapping='DEPTH', get_cmd=False, **kwargs):
    '''
    Reads in frames from the .mp4/.avi file using a pipe from ffmpeg.
    Parameters
    ----------
    filename (str): filename to get frames from
    frames (list or 1d numpy array): list of frames to grab
    threads (int): number of threads to use for decode
    fps (int): frame rate of camera in Hz
    frames_is_timestamp (bool): if False, indicates timestamps represent kinect v2 absolute machine timestamps,
     if True, indicates azure relative start_time timestamps (i.e. first frame timestamp == 0.000).
    pixel_format (str): ffmpeg pixel format of data
    movie_dtype (str): An indicator for numpy to store the piped ffmpeg-read video in memory for processing.
    frame_size (str): wxh frame size in pixels
    slices (int): number of slices to use for decode
    slicecrc (int): check integrity of slices
    mapping (str): chooses the stream to read from mkv files. (Will default to if video is not an mkv format).
    get_cmd (bool): indicates whether function should return ffmpeg command (instead of executing).
    Returns
    -------
    video (3d numpy array):  frames x h x w
    '''

    # Compute starting time point to retrieve frames from
    if frames_is_timestamp:
        start_time = str(datetime.timedelta(seconds=frames[0]))
    else:
        start_time = str(datetime.timedelta(seconds=frames[0] / fps))

    command = [
        'ffmpeg',
        '-loglevel', 'fatal',
        '-ss', start_time,
        '-i', filename,
        '-vframes', str(len(frames)),
        '-f', 'image2pipe',
        '-s', '{:d}x{:d}'.format(frame_size[0], frame_size[1]),
        '-pix_fmt', pixel_format,
        '-threads', str(threads),
        '-slices', str(slices),
        '-slicecrc', str(slicecrc),
        '-vcodec', 'rawvideo',
    ]

    if isinstance(mapping, str):
        mapping_dict = get_stream_names(filename)
        mapping = mapping_dict.get(mapping, 0)

    if filename.endswith(('.mkv', '.avi')):
        command += ['-map', f'0:{mapping}']
        command += ['-vsync', '0']

    command += ['-']

    if get_cmd:
        return command

    pipe = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    out, err = pipe.communicate()

    if err:
        print('Error:', err)
        return None

    video = np.frombuffer(out, dtype=movie_dtype).reshape((len(frames), frame_size[1], frame_size[0]))

    return video.astype('uint16')



def get_number_of_frames(filepath):
    command = 'ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames -of default=nokey=1:noprint_wrappers=1'
    out = subprocess.Popen(command.split(' ')+[filepath], 
               stdout=subprocess.PIPE, 
               stderr=subprocess.STDOUT)
    stdout,stderr = out.communicate()    
    return int(stdout.decode('utf8').strip('\n'))


def check_mkv_extraction_integrity(input_file, output_prefix, verbose=True, threads=8, chunk_size=100, delete=False):
    # detect which streams are present (ir, color, depth)
    integrity_check = True
    streams = get_stream_names(input_file)
    timestamps = np.loadtxt(output_prefix+'.timestamps.txt')
    for stream_name,ix in streams.items():
        
        if stream_name in ['DEPTH','IR']:
            print('Checking integrity of {} compression'.format(stream_name))
            output_file = output_prefix+'.'+stream_name.lower()+'.avi'
            if not os.path.exists(input_file):
                print(f'Looks like {output_file} for stream {stream_name} was already deleted, continuing...')
                continue

            if not os.path.exists(output_file):
                print('Integrity check failed for stream {}: The file {} was not found'.format(
                    stream_name, output_file))
                integrity_check = False
                continue
                
            length = get_number_of_frames(output_file)
            for chunk_start in tqdm.trange(0,length,100):
                chunk_end = np.min([chunk_start+100, length])
                mkv_data = read_frames(input_file, timestamps[chunk_start:chunk_end], mapping=stream_name, frames_is_timestamp=True)
                avi_data = read_frames(output_file, range(chunk_start,chunk_end))
                if not np.equal(mkv_data, avi_data).all(): 
                    print('Integrity check failed for stream {}: error in frame range {}-{}'.format(
                        stream_name, chunk_start, chunk_end))
                    integrity_check = False
                    
    if integrity_check:
        print('Integrity check succeeded')
        if delete: 
            print('Deleting {}'.format(input_file))
            os.remove(input_file)
            
            
            
            
            
                
