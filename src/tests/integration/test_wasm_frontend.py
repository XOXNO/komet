from __future__ import annotations

from pathlib import Path

import pytest
from pyk.kast.inner import KSort
from pyk.ktool.krun import KRunOutput

from komet.kast.syntax import (
    account_id,
    call_tx,
    contract_id,
    deploy_contract,
    sc_bool,
    set_account,
    set_exit_code,
    steps_of,
    upload_wasm,
)
from komet.utils import concrete_definition
from komet.wasm import wasm2kast


@pytest.mark.parametrize('condition', [False, True])
def test_binary_if_else_executes_only_selected_branch(condition: bool) -> None:
    # choose(x): if i64.eqz(x) then return true else return false.
    wasm = Path(__file__).parent / 'data' / 'if_else.wasm'
    steps = steps_of(
        [
            set_exit_code(1),
            upload_wasm(b'if-else', wasm2kast(wasm.read_bytes()), 28),
            set_account(b'test-account', 9876543210),
            deploy_contract(b'test-account', b'test-contract', b'if-else'),
            call_tx(
                account_id(b'test-account'),
                contract_id(b'test-contract'),
                'choose',
                [sc_bool(condition)],
                sc_bool(not condition),
            ),
            set_exit_code(0),
        ]
    )
    result = concrete_definition().krun_with_kast(steps, sort=KSort('Steps'), output=KRunOutput.KORE)
    assert result.returncode == 0, result.stderr
