"""Isolate Booster output and give macOS workers enough native stack."""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp


def booster_command() -> list[str]:
    return [sys.executable, '-m', 'komet.native_stack']


def _stack_library() -> Path:
    source = Path(__file__).with_suffix('.c')
    flags = ['-dynamiclib', '-O2', '-Wall', '-Wextra', '-Werror']
    digest = hashlib.sha256(source.read_bytes() + repr((platform.machine(), flags)).encode()).hexdigest()
    cache = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'komet' / 'native-stack'
    library = cache / f'{digest}.dylib'
    if not library.is_file():
        cache.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=cache) as temporary:
            output = Path(temporary) / 'stack.dylib'
            subprocess.run(['xcrun', 'clang', *flags, str(source), '-o', str(output)], check=True)
            os.replace(output, library)
    return library


def main() -> None:
    backend = shutil.which('kore-rpc-booster')
    if backend is None:
        raise SystemExit('kore-rpc-booster was not found on PATH')
    backend = str(Path(backend).resolve())
    arguments = sys.argv[1:]
    # pyk passes the definition first; archived reports can replay it relatively.
    if arguments and not arguments[0].startswith('-'):
        arguments[0] = str(Path(arguments[0]).absolute())
    for index, argument in enumerate(arguments):
        if argument == '--llvm-backend-library' and index + 1 < len(arguments):
            arguments[index + 1] = str(Path(arguments[index + 1]).absolute())
        elif argument.startswith('--llvm-backend-library='):
            arguments[index] = '--llvm-backend-library=' + str(Path(argument.split('=', 1)[1]).absolute())
    env = os.environ.copy()
    if sys.platform == 'darwin':
        libraries = []
        for library in env.get('DYLD_INSERT_LIBRARIES', '').split(':'):
            if not library:
                continue
            # dyld expands these tokens relative to loaded images, not the CWD.
            if not library.startswith(('@loader_path/', '@executable_path/', '@rpath/')):
                library = str(Path(library).absolute())
            libraries.append(library)
        libraries.append(str(_stack_library().resolve()))
        env['DYLD_INSERT_LIBRARIES'] = ':'.join(libraries)
    # Booster writes a fixed crash-report name in its CWD. Keep that output away
    # from caller files and retain the directory for diagnostics after exec.
    working_directory = Path(mkdtemp(prefix='komet-booster-')).resolve()
    os.chdir(working_directory)
    print(f'Komet Booster working directory: {working_directory}', file=sys.stderr, flush=True)
    os.execvpe(backend, [backend, *arguments], env)


if __name__ == '__main__':
    main()
