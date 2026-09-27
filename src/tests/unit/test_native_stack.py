from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from komet import native_stack

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


def test_launcher_preserves_arguments_and_environment(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert native_stack.booster_command() == [sys.executable, '-m', 'komet.native_stack']
    arguments = ['--definition', '/some definition.kore', '--smt-tactic', '(check-sat-using smt)']
    monkeypatch.setattr(sys, 'argv', ['native_stack', *arguments])
    monkeypatch.setenv('DYLD_INSERT_LIBRARIES', '/existing.dylib')
    monkeypatch.setattr(native_stack.shutil, 'which', lambda name: '/backend')
    monkeypatch.setattr(native_stack, '_stack_library', lambda: tmp_path / 'stack.dylib')
    execute = Mock()
    monkeypatch.setattr(native_stack.os, 'execvpe', execute)
    native_stack.main()
    backend, argv, env = execute.call_args.args
    assert backend == '/backend' and argv == ['/backend', *arguments]
    assert env['DYLD_INSERT_LIBRARIES'] == f'/existing.dylib:{tmp_path / "stack.dylib"}'
    assert os.environ['DYLD_INSERT_LIBRARIES'] == '/existing.dylib'
    monkeypatch.setattr(sys, 'platform', 'linux')
    assert native_stack.booster_command() is None


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
