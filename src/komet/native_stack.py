"""Give macOS Booster workers enough native stack for recursive LLVM serialization."""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def booster_command() -> list[str] | None:
    return [sys.executable, '-m', 'komet.native_stack'] if sys.platform == 'darwin' else None


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
    env = os.environ.copy()
    if sys.platform == 'darwin':
        libraries = [env['DYLD_INSERT_LIBRARIES']] if env.get('DYLD_INSERT_LIBRARIES') else []
        libraries.append(str(_stack_library()))
        env['DYLD_INSERT_LIBRARIES'] = ':'.join(libraries)
    os.execvpe(backend, [backend, *sys.argv[1:]], env)


if __name__ == '__main__':
    main()
