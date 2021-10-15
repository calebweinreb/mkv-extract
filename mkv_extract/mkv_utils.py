import subprocess, json, os

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
    if verbose: print('...detected streams',list(streams.keys()))
    
    # create a parallel process for each stream
    processes = []
    for stream_name,ix in streams.items():
        if stream_name == 'COLOR': ext,codec,pixel_format,crf = 'mp4','h264','rgb24','24'
        if stream_name == 'DEPTH': ext,codec,pixel_format,crf = 'avi','ffv1','gray16','10'
        if stream_name == 'IR'   : ext,codec,pixel_format,crf = 'avi','ffv1','gray16','18'
        if verbose: print('...starting',stream_name,'extraction')
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
            output_prefix+'.'+stream_name+'.'+ext
        ]
        processes.append(subprocess.Popen(command))
    
    # initiate processes
    exit_codes = [p.wait() for p in processes]
    if verbose: print('...finished extracting frames (exit codes =',exit_codes,')')
        
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

def compress_mkv(input_file, verbose=True, output_prefix=None):
    if verbose: print('Extracting',input_file)
    if output_prefix is None:
        base_filename = os.path.splitext(os.path.basename(input_file))[0]
        output_prefix = os.path.join(os.path.dirname(input_file),base_filename)
        
    # extract metadata (including timestamps and calibration params)
    if verbose: print('...extracting metadata and timestamps')
    metadata = extract_metadata_from_mkv(input_file)
    metadata['timestamps'] = extract_timestamps_from_mkv(input_file)
    metadata['calibration'] = extract_calibration_from_mkv(input_file)
    json.dump(metadata, open(output_prefix+'.metadata.json','w'), indent=4)
    
    # extract frames
    extract_frames_from_mkv(input_file, output_prefix, verbose=verbose)

