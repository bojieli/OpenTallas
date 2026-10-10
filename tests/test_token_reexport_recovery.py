"""Checks for newly implemented targets and refresh source provenance."""
import ast
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def functions_from(path, names, constants=()):
    tree = ast.parse((ROOT / path).read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names
             or isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in n.targets)]
    ns = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, 'exec'), ns)
    return ns


def test_optional_target_requires_implementation():
    ns = functions_from('tools/token_path_export.py', ('target_functions', 'optional_mtp_qualified'), ('OPTIONAL_TARGETS',))
    base = {n: lambda: None for n in ('qwen', 'ds_rom', 'hbm', 'ds_rom_mtp', 'hbm_mtp')}
    fns, mtps = ns['target_functions'](base)
    assert list(fns) == ['qwen_rom', 'ds_rom', 'hbm_ds']
    base.update(qwen_hbm=lambda: {}, qwen_hbm_mtp=lambda r: {})
    fns, mtps = ns['target_functions'](base)
    assert 'qwen_hbm' in fns and 'qwen_hbm' in mtps
    assert not ns['optional_mtp_qualified']({'tau': 3.4, 'deployment_qualified': False})
    assert not ns['optional_mtp_qualified']({'qualification': {'deployment_qualified': False}})
    assert ns['optional_mtp_qualified']({'qualification': {'deployment_qualified': True}})


def test_optional_price_has_no_fabricated_default():
    ns = functions_from('tools/reprice_20261008.py', ('optional_prices',), ('OPTIONAL_TARGETS',))
    assert ns['optional_prices']({}) == {}
    assert ns['optional_prices']({'qwen_hbm': lambda: {'status': 'priced'}}) == {'qwen_hbm': {'status': 'priced'}}


def test_read_then_modified_input_remains_watched(tmp_path):
    spec = importlib.util.spec_from_file_location('refresh', ROOT / 'tools/token_path_refresh.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.git = lambda *args: 'tools/model.py\nresults/arch/token_path_20261008/index.json\n'
    trace = tmp_path / 'trace'
    trace.mkdir()
    source = str(tmp_path / 'tools/model.py')
    output = str(tmp_path / 'results/arch/token_path_20261008/index.json')
    (trace / 't1.json').write_text(json.dumps({'read': [source, output], 'write': [source, output], 'listed': []}))
    inputs, writes = m.traced_inputs(trace, tmp_path, 'base')
    assert inputs == ['tools/model.py']
    assert 'tools/model.py' in writes


def test_refresh_refuses_unmanaged_worktree(tmp_path):
    import pytest
    spec = importlib.util.spec_from_file_location('refresh_guard', ROOT / 'tools/token_path_refresh.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.WT = tmp_path / 'existing'
    m.WT.mkdir()
    (m.WT / '.git').write_text('gitdir: other-agent')
    m.REPO = tmp_path / 'central'
    m.git = lambda *args, **kwargs: pytest.fail('must not run git in another agent worktree')
    with pytest.raises(RuntimeError, match='unmanaged'):
        m.ensure_worktree('base')
