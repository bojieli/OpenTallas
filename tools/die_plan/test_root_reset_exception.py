"""The whole-die asynchronous reset exception must never mask forwarded reset."""
import copy
import sys
from pathlib import Path

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys
import reset_tree
import schema
from test_sdc_lint import TINY, _kit, _errs


def test_two_root_reset_pins_only():
    text, ctx = _kit(TINY)
    ctx['root_async_reset'] = True
    assert _errs(text + gen_phys.ROOT_RESET_FALSE_PATH + '\n', ctx) == []
    assert _errs(text, ctx)
    assert _errs(text + (gen_phys.ROOT_RESET_FALSE_PATH + '\n') * 2, ctx)


@pytest.mark.parametrize('old,new', [('u_rst_root','u_rst_in'), ('/RESETN','/D'),
    ('p\\[[01]\\]','.*'), ('[get_ports {arst_n}]','[all_inputs]')])
def test_forwarded_reset_and_broad_waiver_mutants_fail(old,new):
    text, ctx = _kit(TINY)
    ctx['root_async_reset'] = True
    assert _errs(text + gen_phys.ROOT_RESET_FALSE_PATH.replace(old,new) + '\n', ctx)


def test_receiver_context_cannot_carry_exception():
    text, ctx = _kit(TINY)
    assert _errs(text + gen_phys.ROOT_RESET_FALSE_PATH + '\n', ctx)


def test_root_role_and_replication_fail_closed(monkeypatch):
    raw = copy.deepcopy(TINY)
    raw['reset']['release'] = 'wavefront'
    p = schema.Plan(raw)
    root = next(iter(p.types))
    monkeypatch.setattr(reset_tree, 'wf_solve', lambda p: {'root_type': root})
    assert gen_phys.root_async_reset(p, root)
    for tn in p.types:
        if tn != root:
            assert not gen_phys.root_async_reset(p, tn)
    p.parts['duplicate_root'] = {'type': root}
    with pytest.raises(ValueError, match='unique root'):
        gen_phys.root_async_reset(p, root)


def test_standalone_linter_without_generator(tmp_path):
    import json
    import subprocess
    import shutil
    text,ctx=_kit(TINY)
    ctx['root_async_reset']=True
    (tmp_path/'constraint.sdc').write_text(text+gen_phys.ROOT_RESET_FALSE_PATH+'\n')
    (tmp_path/'sdc_lint.json').write_text(json.dumps(ctx))
    shutil.copyfile(Path(__file__).with_name('sdc_lint.py'),tmp_path/'sdc_lint.py')
    result=subprocess.run([sys.executable,'-I',str(tmp_path/'sdc_lint.py'),str(tmp_path)],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr



def test_broadcast_root_guards_both_native_s2_exceptions(monkeypatch):
    from sdc_lint import root_s2_async_block

    raw = copy.deepcopy(TINY)
    raw["reset"].update(release="wavefront", start="broadcast")
    plan = schema.Plan(raw)
    root = next(iter(plan.types))
    monkeypatch.setattr(reset_tree, "wf_solve", lambda p: {"root_type": root})
    assert gen_phys.root_async_start(plan, root)
    assert all(not gen_phys.root_async_start(plan, name) for name in plan.types if name != root)

    text, ctx = _kit(TINY)
    ctx.update(root_async_reset=True, root_async_start=True)
    reset = root_s2_async_block("arst_n", "u_rst_root")
    start = root_s2_async_block("start_i", "u_run_root")
    assert _errs(f"{text}{reset}\n{start}\n", ctx) == []
    assert _errs(f"{text}{reset}\n", ctx)
    assert _errs(f"{text}{reset}\n{start}\n{start}\n", ctx)
    assert _errs(f"{text}{reset.replace('sync_rst_n', '.*')}\n{start}\n", ctx)
    assert _errs(f"{text}{reset}\n{start}\n", {**ctx, "root_async_reset": False})
