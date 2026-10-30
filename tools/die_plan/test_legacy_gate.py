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
    (tmp_path / 'constraint.sdc').write_text('create_clock -name clk -period 833 [get_ports clk]\n')
    (tmp_path / 'sdc_lint.json').write_text(json.dumps(dict(insertion_ps=250,insertion_ff_ps=190,insertion_tol_ps=40)))
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


def policy_log(corner, mutation=None):
    bound = 250 if corner == 'TT' else 190
    setup = -15 if mutation == 'TT-negative' and corner == 'TT' else 12
    hold = -3 if mutation == 'STD-FF-negative' and corner == 'FF' else 10
    overlay = 'skipped vclks 0' if mutation == 'overlay-missing' else 'applied vclk in_min -40 out_min 0'
    pair = 'nan' if mutation == 'pair-nan' else ('81' if mutation == 'pair-high' else '5')
    return f"""SO CORNER {corner}
SO PARASITICS global_routing
SO DESIGN demo
SO CLOCK_ENDPOINT_MASTERS DFFHQNx1_ASAP7_75t_R
SO CLOCK_ENDPOINT_MAPPING_ERRORS 0
SO CLOCK_PORTS clk
SO CLOCKS clk vclk
SO PERIOD clk 833
SO PERIOD vclk 833
SO SDC_WNS_MAX {setup}
SO SDC_WNS_MIN 12
SO STD_WNS_MAX {setup}
SO STD_WNS_MIN {hold}
SO OVERLAY {overlay}
SO FF_VCLK applied mode pin_flop_mean clock vclk latency_ps {bound+2}
SO PAIR_COUNTS regs 2 no_clock_arrival 0 data_pins 2 pairs 1 inter_clock 0
SO PAIR_max n 1 worst {pair} bounded 0 signed -5 launch a capture b crpr 1 p99_raw 6 searched 1 nopath 0 verify 0
SO PAIR_min n 1 worst {pair} bounded 0 signed 5 launch a capture b crpr 1 p99_raw 6 searched 1 nopath 0 verify 0
SO PAIR_DONE 1
SO CK_ERRORS 0
SO_CK 1 {bound+1} clk
SO_CK 1 {bound+3} clk
SO DONE 1
"""


def write_policy(k, corner, kwargs, mutation=None):
    text=policy_log(corner, mutation)
    if mutation=='pair-missing':text='\n'.join(line for line in text.splitlines() if not line.startswith('SO PAIR_'))
    if mutation=='coverage-nan':text=text.replace('no_clock_arrival 0','no_clock_arrival nan')
    if mutation=='clock-nan':text=text.replace(f'SO_CK 1 {251 if corner=="TT" else 191}', 'SO_CK 1 nan')
    kwargs['stdout'].write(text)
    (k/f'postcts_gate_{corner.lower()}.libraries.json').write_text(json.dumps(dict(status='LOADED',libraries=[])))


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
        write_policy(k, c, kwargs)
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


def test_lec_env_passes_allowlisted_raw_base_steps(tmp_path):
    # S81-CORES-R25: recipe lec_env reaches lec.py through config.mk; other keys never do
    k = kit(tmp_path)
    (k/'config.mk').write_text((k/'config.mk').read_text() + 'export OT_LEC_RAW_BASE_STEPS = 6\nexport OT_LEC_RESET_CYCLES = 16\n')
    seen = {}
    def execute(args, **kwargs):
        seen.update(kwargs['env'])
        (k/'lec/lec.json').write_text('{"verdict":"EQUIVALENT"}')
        return SimpleNamespace(returncode=0)
    assert gate.run(k, 'lec', k/'netlist.v', execute) == 0
    assert seen['OT_LEC_RAW_BASE_STEPS'] == '6'
    assert seen.get('OT_LEC_RESET_CYCLES') != '16'


@pytest.mark.parametrize('bad', ['export OT_LEC_RAW_BASE_STEPS = 99\n', 'export OT_LEC_RAW_BASE_STEPS = x\n',
                                 'export OT_LEC_RAW_BASE_STEPS = 6\nexport OT_LEC_RAW_BASE_STEPS = 2\n'])
def test_lec_env_bad_value_fails_closed(tmp_path, bad):
    k = kit(tmp_path)
    (k/'config.mk').write_text((k/'config.mk').read_text() + bad)
    ran = []
    def execute(args, **kwargs):
        ran.append(1)
        (k/'lec/lec.json').write_text('{"verdict":"EQUIVALENT"}')
        return SimpleNamespace(returncode=0)
    assert gate.run(k, 'lec', k/'netlist.v', execute) == 5
    assert not ran

@pytest.mark.parametrize('declared,receipt_policy,zero,expected', [
    ('info','info',False,0), ('gate','info',False,6),
    ('info','gate',False,6), ('info','info',True,6)])
def test_explicit_info_band_requires_matching_plan_and_measured_receipt(tmp_path, declared, receipt_policy, zero, expected):
    k=kit(tmp_path)
    (k/'master_slice.json').write_text(json.dumps({'core_tree':{'model_qualification':{'band_policy':declared}}}))
    def execute(args, **kwargs):
        c=kwargs['env']['OT_CORNER'];d=passing(c)
        write_policy(k, c, kwargs)
        d.update(dev_ps=126.49,pinreg_mean_ps=d['bound_ps']-126.49,
                 band_policy=receipt_policy,band_verdict='INFO',pinreg_n=0 if zero else 638)
        (k/f'postcts_gate_{c.lower()}.json').write_text(json.dumps(d))
        return SimpleNamespace(returncode=0)
    assert gate.run(k,'grt',execute=execute)==expected


@pytest.mark.parametrize('mutation', ['TT-negative','STD-FF-negative','overlay-missing','pair-high','pair-nan','old-band-only','pair-missing','coverage-nan','clock-nan'])
def test_grt_policy_blocks_data_or_clock_failure_even_when_band_passes(tmp_path, mutation):
    k=kit(tmp_path)
    def execute(args, **kwargs):
        c=kwargs['env']['OT_CORNER']
        (k/f'postcts_gate_{c.lower()}.json').write_text(json.dumps(passing(c)))
        if mutation != 'old-band-only':write_policy(k,c,kwargs,mutation)
        return SimpleNamespace(returncode=0)
    assert gate.run(k,'grt',execute=execute)==6


def test_grt_uses_existing_signoff_overlay_and_same_loaded_corner(tmp_path):
    k=kit(tmp_path)
    disc,ctx,policy=gate.policy_context(k,next((k/'run/results/asap7').glob('*/base')),dict(OT_VCLK_TT='250',OT_VCLK_FF='190'))
    text=gate.policy_session(k,'FF',None,disc,ctx,policy)
    assert text.startswith(f'source {{{k/"postcts_gate.tcl"}}}')
    assert 'estimate_parasitics' not in text and 'read_db' not in text
    assert 'SO_PATH_BEGIN STD_MIN' in text and 'ot_ps_measure' in text
    assert 'set_input_delay -min [expr {-40}]' in text
    assert 'set_output_delay -min 0' in text
    assert 'extract_parasitics' not in text


def test_grt_rejects_std_reference_context_mismatch_before_sta(tmp_path):
    k=kit(tmp_path)
    (k/'sdc_lint.json').write_text(json.dumps(dict(insertion_ps=250,insertion_ff_ps=100)))
    def forbidden(*a, **kw):raise AssertionError('STA must not run against a mismatched STD reference')
    assert gate.run(k,'grt',execute=forbidden)==6


def test_standalone_isolated_python_finds_staged_signoff(tmp_path):
    # The real generated runner uses python -I (script directory is absent).
    # Context construction imports the staged signoff sibling under that mode.
    import subprocess
    k=kit(tmp_path)
    source=Path(gate.__file__).resolve()
    script="import runpy,sys;from pathlib import Path;m=runpy.run_path(sys.argv[1],run_name='gate_test');k=Path(sys.argv[2]);m['policy_context'](k,k/'run/results/asap7/design/base',{'OT_VCLK_TT':'250','OT_VCLK_FF':'190'})"
    r=subprocess.run([sys.executable,'-I','-c',script,str(source),str(k)],capture_output=True,text=True)
    assert r.returncode==0,r.stderr
