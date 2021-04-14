import sys
import logging
import textwrap

from pyscriptpacker import utils
from pyscriptpacker import files
from pyscriptpacker import compression
from pyscriptpacker.modules import ModuleManager
from pyscriptpacker.environment import VirtualEnvironment


def pack(
    module_names,
    search_paths,
    output,
    compress_src,
    minify_src,
    main_file,
    zip_file,
    resource_list,
    package_list,
    python_path,
):
    try:
        # Python virtual environment
        venv = None
        if package_list:
            venv = VirtualEnvironment(python_path)
            venv.install_packages(package_list)
            search_paths = [venv.get_site_packages_path()] + search_paths

        # Lookup module files
        module_manager = ModuleManager(
            compress_src,
            minify_src,
        )
        module_manager.parse_paths(search_paths, module_names)

        # Add all module source codes
        script = '_virtual_modules = {\n'
        for data in module_manager.generate_data():
            script += '    "' + data.get('name') + '": {\n'
            script += '        "is_package": ' + str(
                data.get('is_package')) + ',\n'
            script += '        "code": ('

            # Wrap the code content to a more reasonable length.
            lines = textwrap.wrap(data.get('code'),
                                  drop_whitespace=False,
                                  break_on_hyphens=False,
                                  break_long_words=False,
                                  replace_whitespace=False)
            for line in lines:
                script += repr(line) + '\n'

            script += '),\n    },\n'
        script += '}\n\n'

        # Get the setup code to execute the module data
        script += utils.get_setup_code()

        if main_file:
            script += '\n' + module_manager.process_file_content(main_file)
        if minify_src == 'all':
            script = compression.minify_source(script)
        if compress_src == 'all':
            script = compression.compress_source(script)

        # Write either the target python file or a zip file
        if not zip_file:
            files.write_output(output, script)
        else:
            compression.zip_output(zip_file, script, output, resource_list)

    finally:
        if venv:
            venv.cleanup()

    if logging.error.counter > 0:
        logging.info('%s error(s) occured', logging.error.counter)
        sys.exit(1)
