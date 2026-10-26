"""Publication-order tests; native audit causal negatives live with pg_receipt."""
import ast
import importlib.util
import os
from pathlib import Path
import subprocess
import types
from unittest import mock

import pytest

HERE = Path(__file__).resolve().parent


def selected(*names):
    tree = ast.parse((HERE / 'closure_loop.py').read_text())
    tree.body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    ns = dict(os=os, shlex=__import__('shlex'), Path=Path,
              HO=types.SimpleNamespace(pg_strict=lambda spec: spec.get("pg_strict", False)))
    exec(compile(tree, 'closure_loop.py', 'exec'), ns)
    return ns


def job():
    return dict(run='/run', host='test', spec=dict(block='leaf', pg_strict=True, verdict=dict(corner_sta='/sta.json')),
                eco=dict(rb='/route/base', ob='/signoff/base'))


def test_eco_audit_precedes_first_mutation_and_all_exports():
    ns = selected('eco_install_cmd', 'pg_strict', 'native_pg_cmd')
    ns.update(subst=lambda s, j: s, eco_output=lambda j: '/eco', verdict_macros=lambda j: [])
    j = job()
    j['spec']['hold_eco'] = dict(reexport='CUSTOM_EXPORT')
    with mock.patch.dict(os.environ, OT_PG_STRICT='1'):
        cmd = ns['eco_install_cmd'](j)
    first = cmd.index('pg_receipt.py verify "$EB/6_final.odb"')
    assert first < cmd.index('install_write_def.log') < cmd.index('cp $EB/6_final.odb')
    assert cmd.index('cmp -- "$EB/6_final.odb" /route/base/6_final.odb') < cmd.index('CUSTOM_EXPORT')
    assert cmd.index('verify /signoff/base/6_final.odb') < cmd.index('CUSTOM_EXPORT')
    assert cmd.index('cmp -- "$EB/6_final.spef" /signoff/base/6_final.spef') < cmd.index('CUSTOM_EXPORT')
    j['spec']['pg_strict'] = False
    with mock.patch.dict(os.environ, OT_PG_STRICT='1'):
        off = ns['eco_install_cmd'](j)
    assert 'pg_receipt' not in off and 'OT_PG_' not in off and 'cmp --' not in off


def test_eco_refusal_happens_before_mutation(tmp_path):
    ns = selected('eco_install_cmd', 'pg_strict', 'native_pg_cmd')
    ns.update(subst=lambda s, j: s, eco_output=lambda j: str(tmp_path / 'eco'), verdict_macros=lambda j: [])
    eb = tmp_path / 'eco/orfs/results/asap7/leaf/base'
    eb.mkdir(parents=True)
    (eb / '6_final.odb').write_text('candidate')
    (eb / '6_final.spef').write_text('*DESIGN "leaf"\n*D_NET n 1\n')
    cl = tmp_path / 'cl'
    cl.mkdir()
    (cl / 'pg_receipt.py').write_text('raise SystemExit(42)\n')
    with mock.patch.dict(os.environ, OT_PG_STRICT='1'):
        cmd = ns['eco_install_cmd'](job()).replace('{CL}', str(cl))
    result = subprocess.run(['bash', '-c', cmd], capture_output=True)
    assert result.returncode == 42
    assert not (eb / 'install_write_def.log').exists()
    assert not (eb / '6_final.def').exists()


def test_ambiguous_and_missing_active_odb_refuse(tmp_path):
    ns = selected('active_pg_cmd', 'native_pg_cmd')
    ns['route_bases_glob'] = lambda j, run: str(tmp_path / '*')
    for name in ['one', 'two']:
        (tmp_path / name).mkdir()
        (tmp_path / name / '6_final.odb').write_text(name)
    cmd = ns['active_pg_cmd'](dict(run='/run'))
    r = subprocess.run(['bash', '-c', cmd], capture_output=True, text=True)
    assert r.returncode == 86 and 'ambiguous' in r.stderr
    ns['route_bases_glob'] = lambda j, run: None
    r = subprocess.run(['bash', '-c', ns['active_pg_cmd'](dict(run='/run'))], capture_output=True)
    assert r.returncode == 86


def test_verdict_and_record_stop_before_any_work_on_pg_refusal():
    ns = selected('do_verdict', 'do_commit')
    ns.update(adoption_held=lambda j: False, require_job_pg=lambda j: False,
              get_metrics=lambda j: pytest.fail('timing should not run after PG refusal'))
    assert ns['do_verdict']({}, None, []) is None
    assert ns['do_commit']({}) is None


def test_collection_and_custom_export_guards_execute_first():
    ns = selected('launch_now', 'pg_strict')
    calls = []
    ns.update(ship_helpers=lambda *a: calls.append('ship'), active_pg_cmd=lambda j: 'NATIVE_AUDIT',
              launch_stage=lambda j, st, cmd: calls.append(cmd), event=lambda *a: None,
              experiment=lambda *a: None, host_cfg=lambda h: dict(label='host'))
    fleet = types.SimpleNamespace(launch_complete=lambda *a: None)
    for kind in ['collect', 'export', 'record']:
        st = dict(kind=kind, key=kind, cmd='CUSTOM_EXPORT', admission_launch_token=1)
        with mock.patch.dict(os.environ, OT_PG_STRICT='1'):
            ns['launch_now'](dict(host='host', run='/run', attempt=1, spec={'pg_strict': True}), fleet, st)
        assert calls[-1].index('NATIVE_AUDIT') < calls[-1].index('CUSTOM_EXPORT')
        assert '|| exit $?' in calls[-1]
    with mock.patch.dict(os.environ, OT_PG_STRICT='1'):
        ns['launch_now'](dict(host='host', run='/run', attempt=1, spec={}), fleet, st)
    assert calls[-1] == 'CUSTOM_EXPORT'


def test_abstract_opt_off_never_loads_runner_and_strict_uses_actual_path(tmp_path):
    spec = importlib.util.spec_from_file_location('abstract_pg_test', HERE.parent / 'hbm_fmax_attn_abstract.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    runner = tmp_path / 'runner.py'
    runner.write_text('def require_native_pg(odb, **kw):\n    raise RuntimeError("native refusal: " + str(odb))\n')
    with mock.patch.dict(os.environ, OT_PG_STRICT='0', OT_PG_RUNNER=str(runner)):
        assert module.require_export_pg(tmp_path / 'actual.odb', tmp_path / 'receipts') is None
    with mock.patch.dict(os.environ, OT_PG_STRICT='1', OT_PG_RUNNER=str(runner)):
        with pytest.raises(RuntimeError, match='native refusal: .*actual.odb'):
            module.require_export_pg(tmp_path / 'actual.odb', tmp_path / 'receipts')


def test_abstract_refuses_before_any_export_output(tmp_path):
    spec = importlib.util.spec_from_file_location('abstract_pg_main_test', HERE.parent / 'hbm_fmax_attn_abstract.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    base = tmp_path / 'orfs/results/asap7/leaf/base'
    base.mkdir(parents=True)
    (base / '6_final.odb').write_text('actual ODB')
    out = tmp_path / 'view'
    with mock.patch.dict(os.environ, OT_PG_STRICT='1'), mock.patch.object(module, 'require_export_pg', side_effect=RuntimeError('PG_HOLD')):
        with mock.patch('sys.argv', ['abstract', '--orfs-dir', str(tmp_path / 'orfs'), '--out', str(out), '--name', 'leaf']):
            with pytest.raises(RuntimeError, match='PG_HOLD'):
                module.main()
    assert not out.exists()


def test_resta_preserves_timing_result_and_separate_pg_hold(tmp_path):
    import json
    src = tmp_path / 'src'
    (src / 'tools/w18').mkdir(parents=True)
    (src / 'tools/w18/corner_sta.py').write_text(
        'import json,sys\nfrom pathlib import Path\n'
        'Path(sys.argv[sys.argv.index("--output")+1]).write_text(json.dumps('
        '{"setup_ss":{"worst_slack_ps":10},"hold_ff":{"worst_slack_ps":20}}))\n')
    base = tmp_path / 'orfs/results/asap7/leaf/base'
    base.mkdir(parents=True)
    for name in ['6_final.odb', '6_final.spef', '6_final.sdc']:
        (base / name).write_text('original')
    runner = tmp_path / 'runner.py'
    runner.write_text('raise SystemExit(42)\n')
    env = dict(os.environ, OT_PG_STRICT='1', OT_PG_RUNNER=str(runner))
    out = tmp_path / 'resta'
    result = subprocess.run(['bash', str(HERE / 'resta_hold.sh'), str(tmp_path / 'orfs'), str(out), str(src), 'post', 'test.sdc'],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 42 and 'PG_HOLD' in result.stderr
    assert json.loads((out / 'corner_sta.json').read_text())['hold_ff']['worst_slack_ps'] == 20
    assert 'RESTA 10 20' in result.stdout
    assert (base / '6_final.odb').read_text() == 'original'


def test_active_installed_route_and_signoff_must_match_and_both_audit():
    ns = selected('active_pg_cmd', 'native_pg_cmd')
    j = job()
    j['eco']['installed'] = True
    cmd = ns['active_pg_cmd'](j)
    assert 'set -- /route/base/6_final.odb' in cmd
    assert 'cmp -- "$1" /signoff/base/6_final.odb || exit $?' in cmd
    assert 'verify /signoff/base/6_final.odb' in cmd
    assert cmd.count('pg_receipt.py verify') == 2


def test_strict_existing_job_cannot_fallback_to_unfrozen_dependencies():
    ns = selected('ship_helpers', 'pg_strict')
    j = job()
    with pytest.raises(ValueError, match='source-bound frozen strict helper plan required'):
        ns['ship_helpers']('host', '/run', j)


def test_same_design_spef_changed_after_audit_refuses_before_install(tmp_path):
    ns = selected('eco_install_cmd', 'pg_strict', 'native_pg_cmd')
    ns.update(subst=lambda s, j: s, eco_output=lambda j: str(tmp_path / 'eco'), verdict_macros=lambda j: [])
    eb = tmp_path / 'eco/orfs/results/asap7/leaf/base'
    eb.mkdir(parents=True)
    (eb / '6_final.odb').write_text('candidate')
    spef = eb / '6_final.spef'
    spef.write_text('*DESIGN "leaf"\n*D_NET n 1\n')
    cl = tmp_path / 'cl'
    cl.mkdir()
    (cl / 'pg_receipt.py').write_text('import sys\nfrom pathlib import Path\np=Path(sys.argv[2]).with_suffix(".spef")\np.write_text(\'*DESIGN "leaf"\\n*D_NET n 999\\n\')\n')
    cmd = ns['eco_install_cmd'](job()).replace('{CL}', str(cl))
    result = subprocess.run(['bash', '-c', cmd], capture_output=True)
    assert result.returncode != 0
    assert spef.read_text().startswith('*DESIGN "leaf"')
    assert '999' in spef.read_text()
    assert not (eb / 'install_write_def.log').exists()
    assert not (eb / '6_final.def').exists()


def test_matching_odb_with_stale_same_design_signoff_spef_refuses(tmp_path):
    ns = selected('active_pg_cmd', 'native_pg_cmd')
    rb, ob = tmp_path / 'route', tmp_path / 'signoff'
    rb.mkdir(); ob.mkdir()
    for base in (rb, ob):
        (base / '6_final.odb').write_text('same ODB')
    (rb / '6_final.spef').write_text('*DESIGN "leaf"\n*D_NET n 1\n')
    (ob / '6_final.spef').write_text('*DESIGN "leaf"\n*D_NET n 999\n')
    cl = tmp_path / 'cl'; cl.mkdir()
    (cl / 'pg_receipt.py').write_text('print("mock native audit passed")\n')
    j = job(); j['eco'].update(installed=True, rb=str(rb), ob=str(ob))
    cmd = ns['active_pg_cmd'](j).replace('{CL}', str(cl))
    result = subprocess.run(['bash', '-c', cmd], capture_output=True)
    assert result.returncode != 0
    assert 'mock native audit passed' in result.stdout.decode()
