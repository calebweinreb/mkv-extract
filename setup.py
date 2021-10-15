from setuptools import setup, find_packages

setup(
    name='mkv-extract',
    packages=find_packages(),
    platforms=['mac', 'unix'],
    install_requires=['click', 'tqdm', 'numpy'],
    python_requires='>=3.6',
    entry_points={'console_scripts': ['mkv-extract = mkv_extract.cli:main']}
)