"""Modern legacy kits cannot route using stale, unproven, or placement-only gates."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import legacy_gate as gate


def kit(tmp_path):
    (tmp_path / 'lec.py').touch()
    (tmp_path / 'netlist.v').touch()
    (tmp_path / 'postcts_gate.tcl').touch()
    (tmp_path / 'setRC_rcx.tcl').touch()
    (tmp_path / 'config.mk').write_text('export OT_VCLK_TT = 250\nexport OT_VCLK_FF = 190\nexport LAYER_PARASITICS_FILE = /work/setRC_rcx.tcl\n')
    odb = tmp_path / 'run/results/asap7/design/base/5_1_grt.odb'
    odb.parent.mkdir(parents=True)
    odb.touch()
    return tmp_path


@pytest.mark.parametrize('verdict,code,expected', [('EQUIVALENT',0,0),('UNPROVEN',0,5),('NEQ',1,5),('EQUIVALENT',3,5),('malformed',0,5)])
def test_lec_requires_new_equivalent_receipt(tmp_path, verdict, code, expected):
    k = kit(tmp_path)
    def execute(args, **kwargs):
        (k/'lec/lec.json').write_text(json.dumps([] if verdict=='malformed' else dict(verdict=verdict)))
        return SimpleNamespace(returncode=code)
    assert gate.run(k, 'lec', k/'netlist.v', execute) == expected


def test_stale_equivalent_cannot_pass_without_new_receipt(tmp_path):
    k=kit(tmp_path)
    (k/'lec').mkdir()
    (k/'lec/lec.json').write_text('{"verdict":"EQUIVALENT"}')
    assert gate.run(k,'lec',k/'netlist.v',lambda *a, **kw: SimpleNamespace(returncode=0)) == 5
    assert len(list((k/'lec').glob('lec.json.previous.*'))) == 1


def passing(corner):
    bound = 250 if corner == 'TT' else 190
    return dict(verdict='PASS',corner=corner,parasitics='global_routing',pinreg_n=3,
                bound_ps=bound,dev_ps=2,tol_ps=20,pinreg_mean_ps=bound+2)


@pytest.mark.parametrize('mutation', [None, 'placement', 'FF-fail', 'missing-FF', 'zero-pins', 'nan', 'waiver', 'wrong-bound', 'tool-error'])
def test_grt_requires_both_new_calibrated_corner_receipts(tmp_path, mutation):
    k=kit(tmp_path)
    seen=[]
    for c in ['tt','ff']:
        (k/f'postcts_gate_{c}.json').write_text(json.dumps(passing(c.upper())))
    def execute(args, **kwargs):
        env=kwargs['env']; c=env['OT_CORNER']; seen.append(c)
        assert env['OT_POSTCTS_GRT']=='1' and env['OT_POSTCTS_TOL']=='20.0'
        d=passing(c)
        if mutation=='placement': d['parasitics']='placement'
        if mutation=='FF-fail' and c=='FF': d['verdict']='FAIL'
        if mutation=='zero-pins': d['pinreg_n']=0
        if mutation=='nan': d['dev_ps']=float('nan')
        if mutation=='waiver': d['tol_ps']=100
        if mutation=='wrong-bound': d['bound_ps']+=50
        if not (mutation=='missing-FF' and c=='FF'):
            (k/f'postcts_gate_{c.lower()}.json').write_text(json.dumps(d))
        return SimpleNamespace(returncode=1 if mutation=='tool-error' else 0)
    assert gate.run(k,'grt',execute=execute) == (0 if mutation is None else 6)
    if mutation is None:
        assert seen==['TT','FF']
        assert len(list(k.glob('postcts_gate_*.json.previous.*')))==2


def test_missing_calibrated_rc_stops_before_openroad(tmp_path):
    k=kit(tmp_path)
    (k/'setRC_rcx.tcl').unlink()
    def forbidden(*a, **kw): raise AssertionError('OpenROAD should not run')
    assert gate.run(k,'grt',execute=forbidden)==6


def test_modern_runner_order_and_legacy_bytes():
    import hashlib
    import subprocess
    source=Path(__file__).resolve().parents[2]/'physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py'
    spec=importlib.util.spec_from_file_location('legacy_gen_under_test',source)
    gen=importlib.util.module_from_spec(spec); spec.loader.exec_module(gen)
    old=gen.run_kit(False)
    assert hashlib.sha256(old.encode()).hexdigest()=='a70a25f57b9dad96bc2bbae058403ab8c113bfc88cf1fe41289d849e581bc08c'
    modern=gen.run_kit(True)
    assert modern.index('/work/legacy_gate.py /work lec') < modern.index('/work/reg_fanout_gate.py')
    assert modern.index('OT_VCLK_CORNER=ff') < modern.index('/work/legacy_gate.py /work grt') < modern.index('then \\$M $GOAL;')
    assert subprocess.run(['bash','-n'],input=modern,text=True).returncode==0
