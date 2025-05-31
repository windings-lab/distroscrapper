# Distroscrapper

Distroscrapper is a Python program for creating linux hierarchy graph.<br>
1. It scraps data from [distrowatch](https://distrowatch.com/), putting everything in cache to avoid too many requests.
2. From scrapped data, creates a graph using graphviz

## Installation

Use the package manager [uv](https://docs.astral.sh/uv/) to install distroscrapper.

```bash
uv sync
```

## Usage

```
usage: distroscrapper [-h] [-o OUT] [-s] [-u] [-f {pdf,png,svg} | -cf CUSTOM_FORMAT] [--no-parser-cache] [--no-html-cache] [--no-image-cache]

options:
  -h, --help            show this help message and exit
  -o, --out OUT         Output file name. Can be used with directory too
  -s, --save-source     Create graphviz source file
  -u, --update          Request new search query from distrowatch and create new htmls if not in cache
  -f, --format {pdf,png,svg}
                        Graphviz output format. Default: pdf
  -cf, --custom-format CUSTOM_FORMAT
                        EXPERIMENTAL. Custom graph output format. Read graphviz docs about different formats.

Cache options:
  --no-parser-cache     Reparse distro htmls. Without requesting to distrowatch
  --no-html-cache       Request new htmls from distrowatch
  --no-image-cache      Request new image icons from distrowatch
```

## Building binaries

```
uv build --os linux --arch x86_64
or
uv build --os windows --arch x86_64
```

## Contributing

Pull requests are welcome
