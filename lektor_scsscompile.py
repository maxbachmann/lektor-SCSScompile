# -*- coding: utf-8 -*-
import os
import errno

import sass
from lektor.pluginsystem import Plugin

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
        self.source_comments = config.get('source_comments', False)
        self.precision = config.get('precision', 5)


    def is_enabled(self, build_flags):
        return bool(build_flags.get(COMPILE_FLAG))

    def make_sure_path_exists(self, path):
        # os.makedirs(path,exist_ok=True) in python3
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

    def on_before_build_all(self, builder, **extra):
        try: # lektor 3+
            is_enabled = self.is_enabled(builder.extra_flags)
        except AttributeError: # lektor 2+
            is_enabled = self.is_enabled(builder.build_flags)

        if not is_enabled:
            return
        
        root_scss = os.path.join(self.env.root_path, self.source_dir )
        output = os.path.join(self.env.root_path, self.output_dir )

        # output path has to exist
        self.make_sure_path_exists(output)

        sass.compile(
            dirname=(root_scss, output), 
            output_style=self.output_style,
            precision=int(self.precision),
            source_comments=(self.source_comments.lower()=='true')
        )

