# SCSScompile
[![PyPI version](https://badge.fury.io/py/lektor-scsscompile.svg)](https://badge.fury.io/py/lektor-scsscompile)

SCSS compiler for Lektor that automatically compiles sass.

Uses [libsass](https://github.com/sass/libsass-python)  and looks for .scss/.sass files (ignores part files that begin with a underscore e.g. '_testfile.scss'),
compiling them as part of the build process.

## Installing

You can install the plugin with Lektor's installer::
```bash
lektor plugins add lektor-scsscompile
```

Or by hand, adding the plugin to the packages section in your lektorproject file::
```bash
[packages]
lektor-scsscompile = 1.0.1
```

## Usage
#####

To enable scsscompile, pass the `scsscompile` flag when starting the development
server or when running a build::
```bash
lektor build -f scsscompile
```

The Plugin has the following settings you can adjust to your needs:

|parameter      |default value      |description                                                                                       |
|---------------|-------------------|--------------------------------------------------------------------------------------------------|
|source_dir     |asset_sources/scss/| the directory in which the plugin searchs for sass files (subdirectories are included)           |
|output_dir     |assets/css/        | the directory the compiled css files get place at                                                |
|output_style   |compressed         | coding style of the compiled result. choose one of: 'nested', 'expanded', 'compact', 'compressed'|
|source_comments|False              | whether to add comments about source lines                                                       |
|precision      |5                  | precision for numbers                                                                            |

An example file with the default config can be found at `configs/scsscompile.ini`
