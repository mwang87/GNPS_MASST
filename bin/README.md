# MASST+

## Indexing

#### Usage:

```
./load <library_file(list)_name>
              [--reference-list]
       --reference-list, -r: indicate library is a file list
```

#### Examples:

- `./load my_library.mgf` (for single mgf file)
- `./load my_library_list.txt -r` (see example library list below)

Library list file should look like:
```
file_1.mgf
file_2.mgf
file_3.mgf
file_xyz.mgf
```

#### Notes:
- The first time this is run, a `library` directory will be created automatically in the current directory. On subsequent runs, spectra will be added to the existing library. (Command must be run from the same directory for this to work.)
- Searches on this library need to be executed from the same directory (i.e. it should contain the `library` subdirectory).

## Searching

#### Usage:

```
./search <query_file_name>
                [--analog]
                [--peaktol <peak-tolerance>]
                [--thresh <threshold>]
       --analog, -a: Run analog search (without this, exact search is run)
       --peaktol, -p <peak-tolerance>: Specify the peak tolerance (peak masses +- this amount will be considered a match; default 0.02)
       --thresh, -t <threshold>: specify matching score threshold for search, default 0.7
```

#### Examples:

- `./search my_query.mgf` (exact search with 0.02 peak tolerance, 0.7 score threshold)
- `./search my_query.mgf -a` (analog search with 0.02 peak tolerance, 0.7 score threshold)
- `./search my_query.mgf -a -p 0.01` (analog search with 0.01 peak tolerance, 0.7 score threshold)
- `./search my_query.mgf -a -p 0.01 -t 0.8` (analog search with 0.01 peak tolerance, 0.8 score threshold)

#### Notes:
- Spectra with a match score above the threshold will be listed in the output file `matches-all.tsv` created in the directory where the search is run.

## Build instructions

Required GCC: gcc-8 or later

Instructions:

```
$ cd <root_directory>
$ mkdir build
$ cd build
$ cmake ..
$ make
```

Executable file locations after build:
- Indexing: `build/source/tools/load`
- Searching: `build/source/tools/search`
