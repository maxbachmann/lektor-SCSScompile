# -*- coding: utf-8 -*-
import os

import sass
import re
from lektor.pluginsystem import Plugin
from lektor.reporter import reporter
from termcolor import colored
import threading
import time

COMPILE_FLAG = "scsscompile"

class SCSScompilePlugin(Plugin):
    name = u'Lektor SCSScompile'
    description = u'SASS compiler for Lektor, thats based on libsass.'

    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)
        config = self.get_config()
        self.source_dir = config.get('source_dir', 'asset_sources/scss/')
        self.output_dir = config.get('output_dir', 'assets/css/')
        self.output_style = config.get('output_style', 'compressed')
        self.source_comments = config.get('source_comments', 'False')
        self.precision = config.get('precision', '5')
        self.name_prefix = config.get('name_prefix', '')
        self.watcher = None
        self.run_watcher = False

    def is_enabled(self, extra_flags) -> bool:
        return bool(extra_flags.get(COMPILE_FLAG))

    def find_dependencies(self, target) -> list:
        dependencies = [target]
        with open(target, 'r') as f:
            data = f.read()

        imports = re.findall(r'@import\s+((?:[\'|\"]\S+[\'|\"]\s*(?:,\s*(?:\/\/\s*|)|;))+)', data)
        for files in imports:
            files = re.sub('[\'\"\n\r;]', '', files)

        file_list = [x.strip() for x in files.split(',')]
        basepath = os.path.dirname(target)
        # find correct filename and add to watchlist (recursive so dependencies of dependencies get added aswell)
        for file in file_list:
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

    def is_current(self, dependencies) -> bool:
        for dependency in dependencies:
            if ( not os.path.isfile(output_file) or os.path.getmtime(dependency) > os.path.getmtime(output_file)):
                return False
        return True
    
    def compile_file(self, target, output, dependencies):
        """
        Compiles the target scss file.
        """
        filename = os.path.splitext(os.path.basename(target))[0]
        if not filename.endswith(self.name_prefix):
            filename += self.name_prefix
        filename += '.css'
        output_file = os.path.join(output, filename)

        # check if dependency changed and rebuild if it did
        if is_current(dependencies):
            return

        result = sass.compile(
                filename=target,
                output_style=self.output_style,
                precision=int(self.precision),
                source_comments=(self.source_comments.lower()=='true')
            )
        with open(output_file, 'w') as fw:
            fw.write(result)
        
        print(colored('css', 'green'), self.source_dir + os.path.basename(target), '\u27a1', self.output_dir + filename)
        

    def find_files(self, destination) -> Iterator[str]:
        """
        Finds all scss files in the given destination. (ignore files starting with _)
        """
        for root, dirs, files in os.walk(destination):
            for f in files:
                if (f.endswith('.scss') or f.endswith('.sass')) and not f.startswith('_'):
                    yield os.path.join(root, f)            

    def thread(self, output, watch_files):
        while True:
            if not self.run_watcher:
                self.watcher = None
                break
            for filename, dependencies in watch_files:
                self.compile_file(filename, output, dependencies)
            time.sleep(1)

    def on_server_spawn(self, **extra):
        extra_flags = extra.get("extra_flags") or extra.get("build_flags") or {}
        if not self.is_enabled(extra_flags):
            return
        self.run_watcher  = True

    def on_server_stop(self, **extra):
        if self.watcher is not None:
            self.run_watcher = False
  
    def on_before_build_all(self, builder, **extra):
        extra_flags = getattr(
            builder, "extra_flags", getattr(builder, "build_flags", None)
        )
        if not self.is_enabled(extra_flags) \
           or self.watcher is not None:
             return

        root_scss = os.path.join(self.env.root_path, self.source_dir )
        output = os.path.join(self.env.root_path, self.output_dir )
        config_file = os.path.join(self.env.root_path, 'configs/scsscompile.ini')

        # output path has to exist
        os.makedirs(output, exist_ok=True)

        dependencies = []
        if ( os.path.isfile(config_file)):
            dependencies.append(config_file)

        if self.run_watcher:
            watch_files = []
            for filename in self.find_files(root_scss):
                dependencies += self.find_dependencies(filename)
                watch_files.append([filename, dependencies])
            self.watcher = threading.Thread(target=self.thread, args=(output, watch_files))
            self.watcher.start()
        else:
            for filename in self.find_files(root_scss):
                # get dependencies by searching imports in target files
                dependencies += self.find_dependencies(filename)
                self.compile_file(filename, output, dependencies)
