from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from komet import native_stack

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def test_launcher_preserves_arguments_and_environment(
    monkeypatch: MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert native_stack.booster_command() == [sys.executable, '-m', 'komet.native_stack']
    arguments = ['/some definition.kore', '--smt-tactic', '(check-sat-using smt)']
    monkeypatch.setattr(sys, 'argv', ['native_stack', *arguments])
    existing = '/existing.dylib:relative.dylib:@loader_path/a.dylib:@executable_path/b.dylib:@rpath/c.dylib'
    monkeypatch.setenv('DYLD_INSERT_LIBRARIES', existing)
    monkeypatch.setattr(native_stack.shutil, 'which', lambda name: '/backend')
    monkeypatch.setattr(native_stack, '_stack_library', lambda: tmp_path / 'stack.dylib')
    monkeypatch.setattr(native_stack, 'mkdtemp', lambda **kwargs: str(tmp_path / 'working'))
    change_directory = Mock()
    monkeypatch.setattr(native_stack.os, 'chdir', change_directory)
    execute = Mock()
    monkeypatch.setattr(native_stack.os, 'execvpe', execute)
    native_stack.main()
    backend, argv, env = execute.call_args.args
    assert backend == '/backend' and argv == ['/backend', *arguments]
    assert env['DYLD_INSERT_LIBRARIES'] == (
        f'/existing.dylib:{Path.cwd() / "relative.dylib"}:'
        f'@loader_path/a.dylib:@executable_path/b.dylib:@rpath/c.dylib:{tmp_path / "stack.dylib"}'
    )
    assert os.environ['DYLD_INSERT_LIBRARIES'] == existing
    change_directory.assert_called_once_with(tmp_path / 'working')
    assert capsys.readouterr().err == f'Komet Booster working directory: {tmp_path / "working"}\n'
    monkeypatch.setattr(sys, 'platform', 'linux')
    assert native_stack.booster_command() == [sys.executable, '-m', 'komet.native_stack']


@pytest.mark.parametrize('joined_library', [False, True])
def test_backend_failure_cannot_overwrite_caller_archive(tmp_path: Path, joined_library: bool) -> None:
    caller = tmp_path / 'caller with spaces'
    binaries = caller / 'bin'
    binaries.mkdir(parents=True)
    definition = caller / 'definition.kore'
    definition.write_text('definition')
    library = caller / 'interpreter.so'
    library.write_text('library')
    archive = caller / 'kore-rpc-booster.tar.gz'
    archive.write_bytes(b'original report')
    backend = binaries / 'kore-rpc-booster'
    backend.write_text(
        f'#!{sys.executable}\n'
        'import json, os, sys\n'
        'from pathlib import Path\n'
        'assert Path(sys.argv[1]).read_text() == "definition"\n'
        'library = sys.argv[2].split("=", 1)[1] if "=" in sys.argv[2] else sys.argv[3]\n'
        'assert Path(library).read_text() == "library"\n'
        'Path("kore-rpc-booster.tar.gz").write_bytes(b"backend failure")\n'
        'print(json.dumps({"pid": os.getpid(), "cwd": str(Path.cwd()), '
        '"args": sys.argv[1:], "rts": os.environ["GHCRTS"]}))\n'
        'sys.exit(19)\n'
    )
    backend.chmod(0o755)
    temporary = tmp_path / 'temporary'
    temporary.mkdir()
    env = dict(os.environ, PATH=f'bin{os.pathsep}{os.environ["PATH"]}', TMPDIR=str(temporary), GHCRTS='-N2 -A16m')
    env['PYTHONPATH'] = os.pathsep.join([str(Path(native_stack.__file__).parents[1]), env.get('PYTHONPATH', '')])
    library_args = (
        [f'--llvm-backend-library={library.name}'] if joined_library else ['--llvm-backend-library', library.name]
    )
    args = [definition.name, *library_args, '--server-port', '54321']
    original_cwd = Path.cwd()
    # Exercise exec in a child without loading the macOS interposer into the fake backend.
    driver = 'from komet import native_stack; native_stack.sys.platform = "linux"; native_stack.main()'
    with subprocess.Popen(
        [sys.executable, '-c', driver, *args],
        cwd=caller,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        stdout, stderr = process.communicate(timeout=30)
        assert process.returncode == 19
        captured = json.loads(stdout)
        assert captured['pid'] == process.pid
    working_directory = Path(captured['cwd'])
    assert working_directory.parent == temporary.resolve()
    assert stderr == f'Komet Booster working directory: {working_directory}\n'
    assert (working_directory / archive.name).read_bytes() == b'backend failure'
    assert archive.read_bytes() == b'original report'
    absolute_library_args = (
        [f'--llvm-backend-library={library}'] if joined_library else ['--llvm-backend-library', str(library)]
    )
    assert captured['args'] == [str(definition), *absolute_library_args, '--server-port', '54321']
    assert captured['rts'] == env['GHCRTS']
    assert Path.cwd() == original_cwd


@pytest.mark.skipif(sys.platform != 'darwin', reason='macOS native stack workaround')
def test_atomic_cache_and_native_thread_behavior(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv('XDG_CACHE_HOME', str(tmp_path))
    with ThreadPoolExecutor(max_workers=2) as workers:
        libraries = list(workers.map(lambda _: native_stack._stack_library(), range(2)))
    assert libraries[0] == libraries[1]
    assert list(libraries[0].parent.iterdir()) == [libraries[0]]
    before = libraries[0].stat().st_mtime_ns
    assert native_stack._stack_library().stat().st_mtime_ns == before
    source = tmp_path / 'check.c'
    source.write_text("""#include <assert.h>
#include <pthread.h>
struct check { size_t expected; int called; };
static void *worker(void *argument) {
    struct check *check = argument;
    size_t actual = pthread_get_stacksize_np(pthread_self());
    assert(actual >= check->expected && actual < check->expected + 65536);
    check->called = 1;
    return argument;
}
int main(void) {
    pthread_t thread;
    void *result;
    struct check default_check = {64 * 1024 * 1024, 0};
    assert(pthread_create(&thread, 0, worker, &default_check) == 0);
    assert(pthread_join(thread, &result) == 0);
    assert(result == &default_check && default_check.called);
    pthread_attr_t attributes;
    assert(pthread_attr_init(&attributes) == 0);
    assert(pthread_attr_setstacksize(&attributes, 1024 * 1024) == 0);
    struct check explicit_check = {1024 * 1024, 0};
    assert(pthread_create(&thread, &attributes, worker, &explicit_check) == 0);
    assert(pthread_join(thread, &result) == 0);
    assert(result == &explicit_check && explicit_check.called);
    assert(pthread_attr_destroy(&attributes) == 0);
}
""")
    executable = tmp_path / 'check'
    subprocess.run(['xcrun', 'clang', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(executable)], check=True)
    subprocess.run([str(executable)], env=dict(os.environ, DYLD_INSERT_LIBRARIES=str(libraries[0])), check=True)
