import click, glob, tqdm
from mkv_utils import compress_mkv

@click.command()
@click.argument('input-path', type=str)
@click.option('--slurm/--no-slurm', default=False, help='Submit a slurm job for each .mkv file')
@click.option('--cores', type=int, default=4, help="Number of cores")
@click.option('--memory', type=str, default="8GB", help="RAM string")
@click.option('--wall-time', type=str, default='30:00', help="Wall time")
@click.option('--partition', type=str, default='short', help="Partition name")
def main(input_path, slurm, cores, memory, wall_time, partition):
    mkvfiles = glob.glob(input_path)
    if slurm:
        assert wall_time, 'To use slurm, you must specify --wall-time'
        assert memory,    'To use slurm, you must specify --memory'
        assert partition, 'To use slurm, you must specify --partition'
        assert cores,     'To use slurm, you must specify --cores'
        for mkvfile in mkvfiles:
            os.system('sbatch -p {} -t {} --mem {} -c {} --wrap """mkv-extract {}"""'.format(
                partition, wall_time, memory, cores, mkvfile))
    else:
        for mkvfile in tqdm.tqdm(mkvfiles):
            compress_mkv(mkvfile, verbose=True)

    

if __name__ == "__main__":
    main()
