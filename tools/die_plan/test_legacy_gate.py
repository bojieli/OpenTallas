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
    setup = (-15 if mutation == 'TT-negative' else -80 if mutation == 'TT-deep' else 12) if corner == 'TT' else 12
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


# KW-FIX-4 / OWNER 11-03 (only sign-off blocks): a measured band miss postcts_gate.tcl marked ADVISORY (verdict PASS)
# is reported and the route continues; the same miss without the mark, or with OT_POSTCTS_BAND_GATE=1, still stops.
@pytest.mark.parametrize('band_verdict,band_gate,rc', [('ADVISORY', None, 0), ('ADVISORY', '1', 6), (None, None, 6), ('FAIL', None, 6)])
def test_grt_band_miss_is_advisory_only_when_marked(tmp_path, monkeypatch, capsys, band_verdict, band_gate, rc):
    if band_gate is None: monkeypatch.delenv('OT_POSTCTS_BAND_GATE', raising=False)
    else: monkeypatch.setenv('OT_POSTCTS_BAND_GATE', band_gate)
    k=kit(tmp_path)
    def execute(args, **kwargs):
        c=kwargs['env']['OT_CORNER']
        write_policy(k, c, kwargs)
        d=passing(c); d['pinreg_mean_ps']=d['bound_ps']+43.4; d['dev_ps']=43.4; d['band_policy']='gate'
        if band_verdict: d['band_verdict']=band_verdict
        (k/f'postcts_gate_{c.lower()}.json').write_text(json.dumps(d))
        return SimpleNamespace(returncode=0)
    assert gate.run(k,'grt',execute=execute) == rc
    out=capsys.readouterr().out
    assert ('OT_LEGACY_GATE ADVISORY TT insertion band dev 43.40 > tol 20.0' in out) == (rc == 0)


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
    assert hashlib.sha256(old.encode()).hexdigest()=='0a3438598452a9a704c7d824ef041e474529a37cd3506f27247d76f43c81dd74'
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


@pytest.mark.parametrize('mutation', ['TT-deep','overlay-missing','pair-nan','old-band-only','pair-missing','coverage-nan','clock-nan'])
def test_grt_policy_blocks_data_or_clock_failure_even_when_band_passes(tmp_path, mutation):
    k=kit(tmp_path)
    def execute(args, **kwargs):
        c=kwargs['env']['OT_CORNER']
        (k/f'postcts_gate_{c.lower()}.json').write_text(json.dumps(passing(c)))
        if mutation != 'old-band-only':write_policy(k,c,kwargs,mutation)
        return SimpleNamespace(returncode=0)
    assert gate.run(k,'grt',execute=execute)==6


# FLOW-30 11-04 (COORD 06:35 (1), OWNER 11-03 only sign-off blocks): G2 hold_ff is advisory, the measurement still exists
# in the receipt and the log; OT_G2_HOLD_GATE=1 (env or config.mk) restores the stop.  TT setup is unchanged (above).
@pytest.mark.parametrize('how,rc', [(None, 0), ('env', 6), ('config', 6)])
def test_grt_policy_ff_hold_advisory_unless_restored(tmp_path, monkeypatch, capsys, how, rc):
    monkeypatch.delenv('OT_G2_HOLD_GATE', raising=False)
    k=kit(tmp_path)
    if how == 'env': monkeypatch.setenv('OT_G2_HOLD_GATE', '1')
    if how == 'config':
        with (k/'config.mk').open('a') as f: f.write('export OT_G2_HOLD_GATE = 1\n')
    def execute(args, **kwargs):
        c=kwargs['env']['OT_CORNER']
        (k/f'postcts_gate_{c.lower()}.json').write_text(json.dumps(passing(c)))
        write_policy(k,c,kwargs,'STD-FF-negative')
        return SimpleNamespace(returncode=0)
    assert gate.run(k,'grt',execute=execute)==rc
    receipt=json.loads((k/'grt_policy.json').read_text())
    assert receipt['checks']['hold_ff']['verdict']=='FAIL'
    assert receipt['verdict']==('PASS' if rc==0 else 'FAIL')
    assert receipt['advisory']==(['hold_ff'] if rc==0 else [])
    out=capsys.readouterr()
    assert ('OT_LEGACY_GATE ADVISORY G2 hold_ff' in out.out)==(rc==0)
    assert (k/'FAIL_POSTCTS').exists()==(rc!=0)


@pytest.mark.parametrize('corner,restore,stop', [('TT',False,'G2_REQUIRED_FAIL setup_tt'),('TT',True,'G2_REQUIRED_FAIL setup_tt'),
                                                 ('FF',False,None),('FF',True,'G2_REQUIRED_FAIL hold_ff')])
def test_grt_session_early_stop_only_where_blocking(tmp_path, monkeypatch, corner, restore, stop):
    monkeypatch.delenv('OT_G2_HOLD_GATE', raising=False)
    if restore: monkeypatch.setenv('OT_G2_HOLD_GATE', '1')
    k=kit(tmp_path)
    disc,ctx,policy=gate.policy_context(k,next((k/'run/results/asap7').glob('*/base')),dict(OT_VCLK_TT='250',OT_VCLK_FF='190'))
    text=gate.policy_session(k,corner,None,disc,ctx,policy)
    if stop: assert f'so {stop}' in text
    else: assert 'so G2_REQUIRED_FAIL' not in text


def test_grt_policy_pair_skew_over_target_is_info(tmp_path):
    # COORD 10-31 08:05 (OWNER 12.25/12.28): related pair skew over 80 ps is INFO; the measurement must still exist
    k=kit(tmp_path)
    def execute(args, **kwargs):
        c=kwargs['env']['OT_CORNER']
        (k/f'postcts_gate_{c.lower()}.json').write_text(json.dumps(passing(c)))
        write_policy(k,c,kwargs,'pair-high')
        return SimpleNamespace(returncode=0)
    assert gate.run(k,'grt',execute=execute)==0


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


# KW-FIX-16 11-05 (COORD class G2-TT-SETUP, OWNER 11-03 targets not gates): a TT setup miss on GRT RC within
# setup_continue_ps (default 50) is advisory and recorded; deeper misses, OT_G2_SETUP_GATE=1 or a smaller window stop.
@pytest.mark.parametrize('mutation,how,rc', [('TT-negative', None, 0), ('TT-negative', 'env', 6), ('TT-negative', 'config', 6),
                                             ('TT-negative', 'window10', 6), ('TT-deep', None, 6), ('TT-deep', 'window100', 0)])
def test_grt_policy_small_tt_setup_miss_is_advisory(tmp_path, monkeypatch, capsys, mutation, how, rc):
    for v in ('OT_G2_SETUP_GATE', 'OT_G2_SETUP_CONTINUE_PS', 'OT_G2_HOLD_GATE'): monkeypatch.delenv(v, raising=False)
    k=kit(tmp_path)
    if how == 'env': monkeypatch.setenv('OT_G2_SETUP_GATE', '1')
    if how == 'config':
        with (k/'config.mk').open('a') as f: f.write('export OT_G2_SETUP_GATE = 1\n')
    if how == 'window10': monkeypatch.setenv('OT_G2_SETUP_CONTINUE_PS', '10')
    if how == 'window100':
        with (k/'config.mk').open('a') as f: f.write('export OT_G2_SETUP_CONTINUE_PS = 100\n')
    def execute(args, **kwargs):
        c=kwargs['env']['OT_CORNER']
        (k/f'postcts_gate_{c.lower()}.json').write_text(json.dumps(passing(c)))
        write_policy(k,c,kwargs,mutation)
        return SimpleNamespace(returncode=0)
    assert gate.run(k,'grt',execute=execute)==rc
    receipt=json.loads((k/'grt_policy.json').read_text())
    assert receipt['checks']['setup_tt']['verdict']=='FAIL'
    assert receipt['verdict']==('PASS' if rc==0 else 'FAIL')
    assert ('setup_tt' in receipt['advisory'])==(rc==0)
    assert ('OT_LEGACY_GATE ADVISORY G2 setup_tt' in capsys.readouterr().out)==(rc==0)
    assert (k/'FAIL_POSTCTS').exists()==(rc!=0)


@pytest.mark.parametrize('how,thr', [(None, '-50.00'), ('gate', '-0.00'), ('window', '-12.50')])
def test_grt_tt_session_stops_only_beyond_window(tmp_path, monkeypatch, how, thr):
    for v in ('OT_G2_SETUP_GATE', 'OT_G2_SETUP_CONTINUE_PS'): monkeypatch.delenv(v, raising=False)
    if how == 'gate': monkeypatch.setenv('OT_G2_SETUP_GATE', '1')
    if how == 'window': monkeypatch.setenv('OT_G2_SETUP_CONTINUE_PS', '12.5')
    k=kit(tmp_path)
    disc,ctx,policy=gate.policy_context(k,next((k/'run/results/asap7').glob('*/base')),dict(OT_VCLK_TT='250',OT_VCLK_FF='190'))
    text=gate.policy_session(k,'TT',None,disc,ctx,policy)
    assert 'set ot_g2_wns [so_ps [sta::worst_slack_cmd max]]' in text
    assert f'if {{$ot_g2_wns ne "nan" && $ot_g2_wns < {thr}}}' in text
    assert text.index('so G2_REQUIRED_FAIL setup_tt') > text.index('so_timing STD')


@pytest.mark.parametrize('bad', ['-5', 'x', 'nan'])
def test_setup_window_bad_value_fails_closed(tmp_path, monkeypatch, bad):
    monkeypatch.delenv('OT_G2_SETUP_GATE', raising=False)
    monkeypatch.setenv('OT_G2_SETUP_CONTINUE_PS', bad)
    with pytest.raises(ValueError):
        gate.setup_continue_ps(kit(tmp_path))


@pytest.mark.parametrize('mutation', [None, 'other-coverage', 'raw-clock-error', 'missing-coverage', 'data-fail'])
def test_only_unexpanded_child_etm_clock_is_advisory(mutation):
    import signoff as so
    corners = {c: so.corner_result(so.parse_session(policy_log(c.upper()))) for c in ('tt', 'ff')}
    for value in corners.values():
        value['clock_endpoint_coverage'] = dict(verdict='NOT RUN', status='UNEXPANDED_CHILD_ETM')
    if mutation == 'other-coverage':
        corners['ff']['clock_endpoint_coverage']['status'] = 'MISSING_CHILD_LIBERTY'
    elif mutation == 'raw-clock-error':
        corners['tt']['ck_errors'] = 1
    elif mutation == 'missing-coverage':
        corners['ff'].pop('clock_endpoint_coverage')
    elif mutation == 'data-fail':
        corners['tt']['std_wns_max'] = -90
        corners['tt']['sdc_wns_max'] = -90
    result = gate.policy_record(corners, {})
    assert result['checks']['clock']['verdict'] == 'NOT RUN'
    assert result['verdict'] == ('PASS' if mutation is None else 'FAIL')
    assert ('clock' in result['advisory']) == (mutation in (None, 'data-fail'))
    # The routed sign-off evaluator still rejects the same unqualified child ETMs.
    final = dict(corners=corners, policy={})
    so.evaluate(final)
    assert final['checks']['clock']['verdict'] == 'NOT RUN'


def _grt_log(k, line):
    log = k / 'run/logs/asap7/design/base/5_1_grt.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text('[INFO GRT-0020] Min routing layer: M2\n' + line + '\n')
    return log


def test_grt_layer_check_matches_differs_and_missing(tmp_path):
    """KW-FIX-30 11-07 (COORD 14:48): GRT keeps the floorplan ODB layer; config.mk raised later must fail closed"""
    k = kit(tmp_path)
    assert gate.grt_layer_check(k) is None                       # config.mk names no layer: nothing to compare
    (k / 'config.mk').write_text((k / 'config.mk').read_text() + 'export MAX_ROUTING_LAYER = M7\n')
    with pytest.raises(ValueError, match='no 5_1_grt.log'):
        gate.grt_layer_check(k)
    _grt_log(k, '[INFO GRT-0021] Max routing layer: M7')
    assert gate.grt_layer_check(k)['grt'] == 'M7'
    _grt_log(k, '[INFO GRT-0021] Max routing layer: M6')
    with pytest.raises(ValueError, match='M6 != config.mk MAX_ROUTING_LAYER M7'):
        gate.grt_layer_check(k)
    _grt_log(k, '[INFO GRT-0019] something else')
    with pytest.raises(ValueError, match='no GRT-0021'):
        gate.grt_layer_check(k)
    (k / 'config.mk').write_text((k / 'config.mk').read_text() + 'override export MAX_ROUTING_LAYER = M6\n')
    _grt_log(k, '[INFO GRT-0021] Max routing layer: M6')
    assert gate.grt_layer_check(k)['config'] == 'M6'               # the last (override) assignment is the one make uses


def test_grt_gate_layer_mismatch_stops_before_openroad(tmp_path):
    k = kit(tmp_path)
    (k / 'config.mk').write_text((k / 'config.mk').read_text() + 'export MAX_ROUTING_LAYER = M7\n')
    _grt_log(k, '[INFO GRT-0021] Max routing layer: M6')
    def forbidden(*a, **kw): raise AssertionError('OpenROAD should not run')
    assert gate.run(k, 'grt', execute=forbidden) == 6
    assert 'GRT-0021 Max routing layer M6 != config.mk MAX_ROUTING_LAYER M7' in (k / 'FAIL_POSTCTS').read_text()
