# -*- coding: utf-8 -*-
import os
import click
import sass
import re
from lektor.pluginsystem import Plugin
from lektor.reporter import reporter
import threading
import time

COMPILE_FLAG = "scsscompile"

class SCSScompilePlugin(Plugin):
    name = u'Lektor SCSScompile'
    description = u'SASS compiler for Lektor, thats based on libsass.'

    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)
        config = self.get_config()
        self.source_dir_short = config.get('source_dir', 'assets/scss/')
        self.output_dir_short = config.get('output_dir', 'assets/css/')
        self.output_style = config.get('output_style', 'compressed')
        self.source_comments = config.get('source_comments', 'False')
        self.precision = config.get('precision', '5')
        self.name_prefix = config.get('name_prefix', '')
        self.watcher = None
        self.run_server = False

    @property
    def source_dir(self) -> str:
        return os.path.join(self.env.root_path, self.source_dir_short )
    
    @property
    def output_dir(self) -> str:
        return os.path.join(self.env.root_path, self.output_dir_short )
    
    @property
    def config_file(self) -> str:
        config_file = os.path.join(self.env.root_path, 'configs/scsscompile.ini')
        if (os.path.isfile(config_file)):
            return config_file
        return None
        
    def is_enabled(self, extra_flags) -> bool:
        return bool(extra_flags.get(COMPILE_FLAG))

    def is_current(self, dependencies) -> bool:
        for dependency in dependencies:
            if ( not os.path.isfile(output_file) or os.path.getmtime(dependency) > os.path.getmtime(output_file)):
                return False
        return True
    
    def find_imports(self, target) -> list:
        with open(target, 'r') as f:
            data = f.read()
        imports = re.findall(r'@import\s+((?:[\'|\"]\S+[\'|\"]\s*(?:,\s*(?:\/\/\s*|)|;))+)', data)
        for files in imports:
            files = re.sub('[\'\"\n\r;]', '', files)
        return [x.strip() for x in files.split(',')]
    
    def add_prefix(self, target, output) -> str:
        filename = os.path.splitext(os.path.basename(target))[0]
        if not filename.endswith(self.name_prefix):
            filename += self.name_prefix
        filename += '.css'
        return os.path.join(output, filename)

    def find_dependencies(self, target) -> list:
        dependencies = [target]
        if self.config_file is not None:
            dependencies.append(self.config_file)

        basepath = os.path.dirname(target)
        # find correct filename and add to watchlist (recursive so dependencies of dependencies get added aswell)
        for file in self.find_imports(target):
            # when filename ends with css libsass converts it to a url()
            if file.endswith('.css'):
                continue
                    
            filepath = os.path.dirname(file)
            basename = os.path.basename(file)
            filenames = [
                basename,
                '_' + basename,
                basename + '.scss',
                basename + '.css',
                '_' + basename + '.scss',
                '_' + basename + '.css'
            ]

            for filename in filenames:
                path = os.path.join(basepath, filepath, filename)
                if os.path.isfile(path):
                    dependencies += self.find_dependencies(path)
        return dependencies
    
    def compile_file(self, target, dependencies):
        """
        Compiles the target scss file.
        """
        # check if dependency changed and rebuild if it did
        if self.is_current(dependencies):
            return

        result = sass.compile(
                filename=target,
                output_style=self.output_style,
                precision=int(self.precision),
                source_comments=(self.source_comments.lower()=='true')
            )
        with open(self.add_prefix(target, self.output_dir), 'w') as fw:
            fw.write(result)
            
        sign = click.style('css', fg='green')
        click.echo('{} {} {} {}'.format(
            sign,
            os.path.join(self.source_dir_short, os.path.basename(target)),
            '\u27a1',
            self.add_prefix(target, self.output_dir_short)
        ))

    def find_files(self, destination) -> Iterator[str]:
        """
        Finds all scss files in the given destination. (ignore files starting with _)
        """
        for root, dirs, files in os.walk(destination):
            for f in files:
                if (f.endswith('.scss') or f.endswith('.sass')) and not f.startswith('_'):
                    yield os.path.join(root, f)            

    def thread(self, watch_files):
        reporter.report_generic('Spawning scss watcher')
        while True:
            if not self.run_server:
                self.watcher = None
                reporter.report_generic('Stopping scss watcher')
                break
            for filename, dependencies in watch_files:
                self.compile_file(filename, dependencies)
            time.sleep(1)

    def on_server_spawn(self, **extra):
        self.run_server = True

    def on_server_stop(self, **extra):
        self.run_server = False
  
    def on_before_build_all(self, builder, **extra):
        extra_flags = getattr(
            builder, "extra_flags", getattr(builder, "build_flags", None)
        )
        if not self.is_enabled(extra_flags) \
           or self.watcher is not None:
             return

        # output path has to exist
        os.makedirs(self.output_dir_long, exist_ok=True)

        if self.run_server:
            watch_files = []
            for filename in self.find_files(self.source_dir):
                watch_files.append([filename, self.find_dependencies(filename)])
            self.watcher = threading.Thread(target=self.thread, args=(watch_files))
            self.watcher.start()
        else:
            reporter.report_generic('Starting scss compiling')
            for filename in self.find_files(self.source_dir):
                self.compile_file(filename, self.find_dependencies(filename))
            reporter.report_generic('Finished compiling scss')
