from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest
from pyk.kast.inner import KVariable

from komet.kasmer import ContractBinding, Kasmer
from komet.scval import SCBoolType, SCU32Type
from komet.utils import KSorobanError

if TYPE_CHECKING:
    from pytest import MonkeyPatch


@pytest.mark.parametrize('type_field', ['type', 'type_'])
def test_contract_bindings_cli_type_fields(monkeypatch: MonkeyPatch, type_field: str) -> None:
    entries = [
        {
            'function_v0': {
                'name': 'test_roundtrip',
                'inputs': [{'name': 'amount', type_field: 'u32'}],
                'outputs': ['bool'],
            }
        }
    ]
    monkeypatch.setattr('komet.kasmer.run_process', lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps(entries)))
    reader = SimpleNamespace(_stellar_bin=Path('stellar'))
    assert Kasmer.contract_bindings(reader, Path('contract.wasm')) == [  # type: ignore[arg-type]
        ContractBinding('test_roundtrip', (SCU32Type(),), (SCBoolType(),))
    ]


def _binding_entry(name: str, unsupported: str | None = None) -> dict[str, Any]:
    udt = {'vec': {'element_type': {'udt': {'name': 'PoolState'}}}}
    return {
        'function_v0': {
            'name': name,
            'inputs': [{'name': 'value', 'type': udt}] if unsupported == 'input' else [],
            'outputs': [udt] if unsupported == 'output' else ['bool'],
        }
    }


def _binding_reader(monkeypatch: MonkeyPatch, entries: list[dict[str, Any]]) -> Kasmer:
    monkeypatch.setattr('komet.kasmer.run_process', lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps(entries)))
    monkeypatch.setattr(Kasmer, '_stellar_bin', Path('stellar'))
    return object.__new__(Kasmer)


@pytest.mark.parametrize(
    'id, unrelated', [(None, 'pool_export'), ('test_selected', 'pool_export'), ('test_selected', 'test_other')]
)
@pytest.mark.parametrize('unsupported', ['input', 'output'])
def test_read_bindings_skips_unselected_types(
    monkeypatch: MonkeyPatch, id: str | None, unrelated: str, unsupported: str
) -> None:
    reader = _binding_reader(
        monkeypatch,
        [_binding_entry(unrelated, unsupported), _binding_entry('init'), _binding_entry('test_selected')],
    )
    bindings, has_init = reader.read_bindings(Path('contract.wasm'), id)
    assert has_init
    assert bindings == [ContractBinding('test_selected', (), (SCBoolType(),))]


@pytest.mark.parametrize('name', ['init', 'test_selected'])
@pytest.mark.parametrize('unsupported', ['input', 'output'])
@pytest.mark.parametrize('id', [None, 'test_selected'])
def test_read_bindings_rejects_selected_unsupported_types(
    monkeypatch: MonkeyPatch, name: str, unsupported: str, id: str | None
) -> None:
    entries = [_binding_entry(n, unsupported if n == name else None) for n in ['init', 'test_selected']]
    reader = _binding_reader(monkeypatch, entries)
    with pytest.raises(KSorobanError, match="Unsupported SC value type: 'udt'"):
        reader.read_bindings(Path('contract.wasm'), id)


def test_contract_bindings_default_reads_every_export(monkeypatch: MonkeyPatch) -> None:
    names = ['init', 'pool_export', 'test_selected']
    entries = [_binding_entry(name) for name in names]
    reader = _binding_reader(monkeypatch, entries)
    assert reader.contract_bindings(Path('contract.wasm')) == [
        ContractBinding(name, (), (SCBoolType(),)) for name in names
    ]
    entries.append(_binding_entry('unsupported_pool_export', 'input'))
    with pytest.raises(KSorobanError, match="Unsupported SC value type: 'udt'"):
        reader.contract_bindings(Path('contract.wasm'))


@pytest.mark.parametrize('protocol', [21, 22, 28])
def test_contract_protocol(monkeypatch: MonkeyPatch, protocol: int) -> None:
    entry = {'sc_env_meta_kind_interface_version': {'protocol': protocol, 'pre_release': 0}}
    monkeypatch.setattr('komet.kasmer.run_process', lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps([entry])))
    reader = SimpleNamespace(_stellar_bin=Path('stellar'))
    assert Kasmer.contract_protocol(reader, Path('contract.wasm')) == protocol  # type: ignore[arg-type]


@pytest.mark.parametrize(
    'entries',
    [
        [],
        [{'sc_env_meta_kind_interface_version': {'protocol': 29, 'pre_release': 0}}],
        [{'sc_env_meta_kind_interface_version': {'protocol': 28, 'pre_release': 1}}],
        [{'sc_env_meta_kind_interface_version': {'protocol': '28', 'pre_release': 0}}],
        [{'sc_env_meta_kind_interface_version': {'protocol': 28, 'pre_release': 0}}] * 2,
    ],
)
def test_reject_unmodeled_protocol(monkeypatch: MonkeyPatch, entries: list[Any]) -> None:
    monkeypatch.setattr('komet.kasmer.run_process', lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps(entries)))
    reader = SimpleNamespace(_stellar_bin=Path('stellar'))
    with pytest.raises(ValueError):
        Kasmer.contract_protocol(reader, Path('contract.wasm'))  # type: ignore[arg-type]


@pytest.mark.parametrize('method', ['deploy_and_run', 'deploy_and_prove'])
def test_deployment_preserves_contract_protocols(monkeypatch: MonkeyPatch, method: str) -> None:
    monkeypatch.setattr(Kasmer, 'read_bindings', lambda *args: ([], False))
    monkeypatch.setattr(Kasmer, 'kast_from_wasm', lambda self, path: KVariable(path.stem))
    monkeypatch.setattr(Kasmer, 'contract_protocol', lambda self, path: 21 if path.stem == 'main' else 28)
    deploy = Mock(return_value=(KVariable('CONF'), {}))
    monkeypatch.setattr(Kasmer, 'deploy_test', deploy)
    reader = object.__new__(Kasmer)
    getattr(reader, method)(Path('main.wasm'), (Path('child.wasm'),))
    deploy.assert_called_once_with(KVariable('main'), (KVariable('child'),), False, 21, (28,))
