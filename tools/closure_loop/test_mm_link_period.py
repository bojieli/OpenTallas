"""Route->FF sign-off refresh keeps exact link-reference periods and IO constraints."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import pytest

ROOT=Path(__file__).resolve().parents[2]
TEXT=(ROOT/'tools/orfs_hold_mm.tcl').read_text()


def proc(name,text=TEXT):
    start=text.index(f'proc {name} ')
    end=text.find('\nproc ',start+1)
    return text[start:end if end>=0 else None]


@pytest.mark.parametrize("wave",[None,"77 308"])
def test_actual_sta_preserves_io_latency_uncertainty_and_other_clocks(tmp_path,wave):
    sta=shutil.which('sta')
    if not sta:pytest.skip('OpenSTA unavailable')
    (tmp_path/'top.v').write_text('module top(input clk,input a,output y);assign y=a;endmodule\n')
    waveform='' if wave is None else ' -waveform {'+wave+'}'
    script=f'''read_verilog {tmp_path}/top.v
link_design top
create_clock -name core_clk -period 770 [get_ports clk]
create_clock -name ot_lb_v_core_clk -period 770{waveform}
create_clock -name window_clk -period 960
create_clock -name vclk -period 910
set_clock_uncertainty -setup 60 [get_clocks ot_lb_v_core_clk]
set_clock_uncertainty -hold 25 [get_clocks ot_lb_v_core_clk]
set_clock_latency 250 [get_clocks ot_lb_v_core_clk]
set_input_delay -max 400 -clock ot_lb_v_core_clk [get_ports a]
set_input_delay -min 12 -clock ot_lb_v_core_clk [get_ports a]
set_output_delay -max 450 -clock ot_lb_v_core_clk [get_ports y]
set_output_delay -min -50 -clock ot_lb_v_core_clk [get_ports y]
create_clock -name core_clk -period 833.333 [get_ports clk]
write_sdc {tmp_path}/before.sdc
{proc('ot_mm_sync_link_periods')}
ot_mm_sync_link_periods
write_sdc {tmp_path}/after.sdc
ot_mm_sync_link_periods
write_sdc {tmp_path}/again.sdc
exit
'''
    (tmp_path/'probe.tcl').write_text(script)
    run=subprocess.run([sta,'-exit',str(tmp_path/'probe.tcl')],capture_output=True,text=True)
    assert run.returncode==0 and 'Error:' not in run.stdout+run.stderr,run.stdout+run.stderr
    def lines(name):
        return [x for x in (tmp_path/name).read_text().splitlines() if x and not x.startswith('#')]
    before,after,again=lines('before.sdc'),lines('after.sdc'),lines('again.sdc')
    expected=[x.replace('ot_lb_v_core_clk -period 770.0000','ot_lb_v_core_clk -period 833.3330').replace('-waveform {77.0000 308.0000}', '-waveform {83.3333 333.3332}') for x in before]
    assert after==expected
    assert again==after
    assert run.stdout.count('OT_HOLD_MM virtual period:')==1


def sync_fixture(text=TEXT):
    return '''set mode ss
set state(ss,core_clk) 770
set state(ss,ot_lb_v_core_clk) 770
set state(ff,core_clk) 770
set state(ff,ot_lb_v_core_clk) 770
set state(ss,vclk) 910
set state(ff,vclk) 910
set ::ot_mm_active 1
set ::ot_mm_stage 3_place.sdc
set ::env(RESULTS_DIR) .
set ::env(OT_MM_FF_SDC) signoff.sdc
close [open signoff.sdc w]
proc set_mode {m} {set ::mode $m}
proc write_sdc {args} {
  set f [lindex $args end];close [open $f w]
  set ::saved [array get ::state]
}
proc read_sdc {f} {
  if {$f eq "signoff.sdc"} {set ::state($::mode,core_clk) 833.333} else {
    set ::state(ff,core_clk) $::state(ss,core_clk)
    set ::state(ff,ot_lb_v_core_clk) $::state(ss,ot_lb_v_core_clk)
  }
}
proc all_clocks {} {return {core_clk ot_lb_v_core_clk vclk}}
proc get_full_name {c} {return $c}
proc get_clocks {args} {return [lindex $args end]}
proc get_property {c prop} {
  if {$prop eq "sources"} {return [expr {$c eq "core_clk"?"clk":""}]}
  return $::state($::mode,$c)
}
proc ot_lb_v_core_clk {prop} {
  set t $::state($::mode,ot_lb_v_core_clk)
  if {$prop eq "period"} {return $t}
  return [list 0 [expr {$t/2.0}]]
}
proc create_clock {args} {
  set n [lindex $args 1];set t [lindex $args 3]
  set ::state($::mode,$n) $t
}
proc set_propagated_clock {args} {}
proc estimate_parasitics {args} {}
proc ot_mm_scene_shim {args} {}
proc set_false_path {args} {}
proc ot_mm_sc {} {return WC}
proc ot_mm_ws {args} {return 0}
'''+proc('ot_mm_sync_link_periods',text)+'\n'+proc('ot_mm_sync',text)+'''
ot_mm_sync
puts "STATE $mode $state(ss,core_clk) $state(ss,ot_lb_v_core_clk) $state(ff,core_clk) $state(ff,ot_lb_v_core_clk) $state(ff,vclk)"
'''


def run_tcl(text):
    with tempfile.TemporaryDirectory() as d:
        r=subprocess.run(['tclsh'],input=text,cwd=d,capture_output=True,text=True)
    assert not r.stderr,r.stderr
    return r.stdout


def test_real_sync_order_changes_only_ff_reference():
    output=run_tcl(sync_fixture())
    assert 'STATE ss 770 770 833.333 833.333 910' in output


def test_missing_or_premature_sync_negative_controls_detect_stale_period():
    missing=TEXT.replace('  ot_mm_sync_link_periods\n  ot_mm_scene_shim 0','  ot_mm_scene_shim 0')
    assert 'STATE ss 770 770 833.333 770 910' in run_tcl(sync_fixture(missing))
    premature=missing.replace('  ot_mm_scene_shim 1','  ot_mm_scene_shim 1\n  ot_mm_sync_link_periods')
    assert 'STATE ss 770 770 833.333 770 910' in run_tcl(sync_fixture(premature))
