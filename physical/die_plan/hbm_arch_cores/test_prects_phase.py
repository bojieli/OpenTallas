"""Stage-only estimate must clear before the real builder and preserve hard guards."""
import importlib.util
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('coregen_prects', HERE/'gen_core_kit_hbm.py')
coregen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coregen)


def test_phase_estimate_and_clear_order(tmp_path):
    cfg=['export PRE_FLOORPLAN_TCL = /work/first.tcl', 'export PRE_CTS_TCL = /work/builder.tcl']
    result=coregen.prects_phase_hooks(tmp_path,cfg,['clk','buffer_clk'],250)
    (tmp_path/'first.tcl').write_text('lappend events FIRST\n')
    (tmp_path/'builder.tcl').write_text('lappend events BUILDER\n')
    for name in ('prects_estimate.tcl','core_pre_cts.tcl'):
        p=tmp_path/name;p.write_text(p.read_text().replace('/work/',str(tmp_path)+'/'))
    script='''set events {}
proc get_ports {x} {return $x}
proc set_clock_latency {args} {global events; lappend events SET}
proc unset_clock_latency {args} {global events; lappend events CLEAR}
source {%s}
source {%s}
puts $events
'''%(tmp_path/'prects_estimate.tcl',tmp_path/'core_pre_cts.tcl')
    p=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,check=True)
    assert p.stdout.strip()=='FIRST SET CLEAR BUILDER'
    assert result['sdc_changed'] is False
    assert '-source' not in (tmp_path/'prects_estimate.tcl').read_text()
    assert cfg[-1]=='override export PRE_CTS_TCL = /work/core_pre_cts.tcl'


def test_existing_multiport_guard_cannot_be_bypassed(tmp_path):
    cfg=['export PRE_CTS_TCL = /work/density.tcl',
         'override export PRE_CTS_TCL = /work/multiport_clock_stage_hold.tcl',
         'export PRE_CTS_TCL = /work/caller_override.tcl']
    result=coregen.prects_phase_hooks(tmp_path,cfg,['clk[0]','clk[1]'],250)
    assert result['previous_cts_hook']=='/work/multiport_clock_stage_hold.tcl'
    text=(tmp_path/'core_pre_cts.tcl').read_text()
    assert text.index('unset_clock_latency') < text.index('source {')
    assert 'multiport_clock_stage_hold.tcl' in text
    assert 'caller_override' not in text
