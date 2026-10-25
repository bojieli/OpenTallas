"""The generated runner must stop costly downstream stages when an early gate fails."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys
import port_bind_gate as PB


def test_port_bits_missing_extra_and_scalar():
    pins=[dict(bus='clk',bit=None),dict(bus='d',bit=0),dict(bus='d',bit=1),dict(bus='q',bit=0)]
    net='module t(clk,d,q);\n input clk;\n input [1:0] d;\n output q;\nendmodule\n'
    assert PB.check(net,'t',pins)['verdict']=='PASS'
    assert PB.check(net.replace('[1:0]','[0:0]'),'t',pins)['missing']==1
    assert PB.check(net.replace('output q;', 'output q;\n output ghost;'),'t',pins)['extra']==1
    assert PB.check(net,'wrong',pins)['verdict']=='FAIL'


@pytest.mark.parametrize('gate,code', [('rtl_lint',1),('rtl_lint',2),('sdc_lint',1),('selrange_gate',1),('selrange_gate',2),
                                      ('port_bind_gate',1),('face_guard',1),('hold_gate',1)])
def test_runner_stops_before_costly_stage(tmp_path,gate,code):
    kit=tmp_path/'kit'; kit.mkdir(); fake=tmp_path/'bin'; fake.mkdir()
    (kit/'config.mk').write_text('')
    out=kit/'run/results/asap7/top/base';out.mkdir(parents=True)
    for f in ['1_2_yosys.v','1_synth.odb','4_cts.odb','4_cts.sdc']:(out/f).write_text('')
    for name in ['rtl_lint','reg_fanout_gate','sdc_lint','selrange_gate','port_bind_gate','face_guard','signoff','pin_audit']:
        (kit/(name+'.py')).write_text('import sys\nraise SystemExit('+str(code if name==gate else 0)+')\n')
    envsh=tmp_path/'env.sh'; envsh.write_text('export PATH='+str(fake)+':$PATH\n')
    (fake/'docker').write_text('#!'+sys.executable+'\nimport os,subprocess,sys\na=sys.argv[1:]\n'
        'if "bash" not in a: raise SystemExit(0)\n'
        'c=a[a.index("-lc")+1].replace("/work",os.environ["TEST_KIT"]).replace("/OpenROAD-flow-scripts/env.sh",os.environ["TEST_ENV"])\n'
        'raise SystemExit(subprocess.run(["bash","-lc",c]).returncode)\n')
    (fake/'make').write_text('#!/bin/bash\necho "$*" >> "$TEST_KIT/make.log"\n'
        'case "$*" in *print-BC_LIB_FILES*) echo "BC_LIB_FILES: fake_ff.lib";; esac\nexit 0\n')
    (fake/'openroad').write_text('#!/bin/bash\ncase "$*" in *hold_gate.tcl*) exit '+str(code if gate=='hold_gate' else 0)+';; esac\nexit 0\n')
    for f in fake.iterdir():f.chmod(0o755)
    run=tmp_path/'run.sh';run.write_text(gen_phys.RUN_KIT)
    env={**os.environ,'PATH':str(fake)+':'+os.environ['PATH'],'TEST_KIT':str(kit),'TEST_ENV':str(envsh)}
    p=subprocess.run(['bash',str(run),str(kit),'route','16','2'],env=env,capture_output=True,text=True)
    assert p.returncode!=0, p.stdout+p.stderr
    calls=(kit/'make.log').read_text() if (kit/'make.log').exists() else ''
    assert not any(line.endswith(' route') or line.endswith(' grt') or line.endswith(' do-finish') for line in calls.splitlines()),calls
    if gate=='hold_gate':
        assert 'cts SKIP_CTS_REPAIR_TIMING=1' in calls
        assert (kit/'FAIL_POSTCTS').exists()
    else:
        assert not any(' cts' in line for line in calls.splitlines()),calls
        assert (kit/'FAIL_PREFLOOR').exists()
        if gate=='rtl_lint':   # FLOW-FIX 10-25: lint is the first gate, rc 8, before sdc_lint / synth
            assert 'FAIL_PREFLOOR lint' in (kit/'FAIL_PREFLOOR').read_text() and p.returncode==8 and not calls


@pytest.mark.parametrize('wns,count,failed', [(-100,2000,False),(-100.01,1,True),(0,2001,True),(-0.1,2000,False)])
def test_ff_only_hold_thresholds(tmp_path,wns,count,failed):
    # Exercise the complete Tcl entry point with controlled STA observations.
    # Only the FF-only process entrypoint may use these observations; no MM flags.
    (tmp_path/'setRC.tcl').write_text('')
    p=tmp_path/'gate.tcl'
    p.write_text('''proc read_liberty {args} {}
proc read_db {args} {}
proc read_sdc {args} {}
proc set_propagated_clock {args} {}
proc estimate_parasitics {args} {}
proc all_clocks {} {return {clk vclk}}
proc get_property {c p} {if {$c eq "clk"} {return {clk}};return {}}
proc get_full_name {x} {return $x}
proc all_inputs {} {return {}}
proc all_outputs {} {return {}}
namespace eval sta {}
proc sta::time_sta_ui {x} {return $x}
''' + f'proc sta::worst_slack_cmd {{args}} {{return {wns}}}\n'
        + f'proc sta::endpoint_violation_count {{args}} {{return {count}}}\n'
        + f'set ::env(PLIBS) ff.lib\nset ::env(ODB) cts.odb\nset ::env(SDC) cts.sdc\nset ::env(PLATFORM_DIR) {{{tmp_path}}}\n'
        + f'if {{[catch {{source {{{Path(__file__).with_name("hold_gate.tcl")}}}}} e]}} {{puts $e;exit 1}}\n')
    r=subprocess.run(['tclsh',str(p)],capture_output=True,text=True)
    assert (r.returncode!=0)==failed,r.stdout+r.stderr
    assert ('OT_HOLD_GATE FAIL' if failed else 'OT_HOLD_GATE PASS') in r.stdout


def test_stage_only_clock_estimate_keeps_golden_and_core_contract(tmp_path,monkeypatch):
    import schema
    raw=json.loads((Path(__file__).parent/'examples/tiny_plan.json').read_text())
    p=schema.Plan(raw)
    original=gen_phys.sdc(p,'src',gen_phys.type_pins(p,'src'))
    kit=gen_phys.write_type_kit(p,'src',tmp_path,[])
    assert (kit/'constraint.sdc').read_text()==original
    assert 'set_clock_latency -clock clk' not in original
    assert 'PRE_FLOORPLAN_TCL = /work/prects_estimate.tcl' in (kit/'config.mk').read_text()
    assert 'PRE_CTS_TCL = /work/pre_cts.tcl' in (kit/'config.mk').read_text()
    clear=(kit/'pre_cts.tcl').read_text()
    assert clear.index('unset_clock_latency -clock clk')<clear.index('source /work/clock_taps.tcl')
    # Add a dedicated early core tap to the port inventory. Stage-only local
    # estimates must never capture this pin or clear its source -early contract.
    monkeypatch.setattr(gen_phys,'core_tap_pins',lambda p,t:[('clk_c0',1,1)])
    assert 'clk_c0' not in gen_phys.clock_phase_tcl(p,'src')
    assert 'clk_c0' not in gen_phys.clock_phase_tcl(p,'src',before_cts=True)
    assert '-source' not in gen_phys.clock_phase_tcl(p,'src',before_cts=True)
