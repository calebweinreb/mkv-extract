import click, glob, tqdm, os, numpy as np
from mkv_extract.mkv_utils import compress_mkv

@click.command()
@click.argument('input-path', type=str)
@click.option('--slurm/--no-slurm', default=False, help='Submit a slurm job for each .mkv file')
@click.option('--delete/--no-delete', default='False', help='Delete the .mkv file after compressing')
@click.option('--cores', type=int, default=4, help="Number of cores")
@click.option('--memory', type=str, default="8GB", help="RAM string")
@click.option('--wall-time', type=str, default='30:00', help="Wall time")
@click.option('--partition', type=str, default='short', help="Partition name")
def main(input_path, delete, slurm, cores, memory, wall_time, partition):
    mkvfiles = [f for f in glob.glob(input_path) if f.endswith('.mkv')]
    if len(mkvfiles)==0: 
        print('ALERT: there are no .mkv files matching the path '+input_path)
        
    if slurm:
        assert wall_time, 'To use slurm, you must specify --wall-time'
        assert memory,    'To use slurm, you must specify --memory'
        assert partition, 'To use slurm, you must specify --partition'
        assert cores,     'To use slurm, you must specify --cores'
        if delete:
            wall_time_seconds = np.sum([60**i*float(t) for i,t in enumerate(wall_time.split(':')[::-1])])
            if wall_time_seconds<7200: 
                print('Wall-time {} is likely too short to check the video integrity. Increase using the option "--wall-time 2:00:00"'.format(wall_time))
                return
        for mkvfile in mkvfiles:
            os.system('sbatch -p {} -t {} --mem {} -c {} --wrap """mkv-extract {} {}"""'.format(
                partition, wall_time, memory, cores, mkvfile, '--delete' if delete else ''))
            
    else:
        for mkvfile in tqdm.tqdm(mkvfiles):
            compress_mkv(mkvfile, verbose=True, delete=delete)



if __name__ == "__main__":
    main()
