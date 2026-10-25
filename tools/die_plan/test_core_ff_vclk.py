"""Real-scene contract, coherent IO reference, and fail-closed controls."""
import subprocess
from pathlib import Path

HELPER=Path(__file__).with_name('core_ff_vclk.sdc')
MOCK=r'''
set ::ot_mm_active 1
set ::ot_ioref_scene BC
set mode ff
set env(OT_FF_VCLK_MODE) pin_flop_mean
set env(OT_FF_VCLK_CONTRACT) source@abc123
array set latency {tt,vclk 256 ff,vclk 256}
array set budgets {in_max 166.6 in_min -40 out_max 166.6 out_min 0 setup 60 hold 25}
proc all_clocks {} { return {clk vclk} }
proc get_full_name {x} { return $x }
proc get_property {obj prop} {
 if {$prop eq "sources"} { return [expr {$obj eq "clk" ? "clk" : ""}] }
 if {$prop eq "period"} { return 833 }
 if {$prop eq "clocks"} { return clk }
 error "unexpected property"
}
proc all_inputs {} { return {clk a} }
proc all_outputs {} { return y }
proc all_registers {arg} {
 switch -- $arg { -clock_pins {return {i/CLK o/CLK}} -data_pins {return {i/D o/D}} -async_pins {return {}} }
}
proc get_fanout {args} { return i/D }
proc get_fanin {args} { return o/QN }
proc ot_mm_arrival_bc {p prop} { return [expr {$p eq "i/CLK" ? 190.0 : 200.0}] }
proc ot_mm_ws {check scene} { return [expr {$::latency(ff,vclk)==256 ? -60.0 : 1.0}] }
proc set_clock_latency {flag value clock} {
 if {$::mode ne "ff"} {error "wrong mode"}
 set ::latency(ff,$clock) $value
}
'''

def run(extra='',tail=''):
    return subprocess.run(['tclsh'],input=MOCK+'\n'+extra+'\n'+f'set rc [catch {{source {{{HELPER}}}}} msg]\nputs "RESULT $rc $msg"\n'+tail,text=True,capture_output=True)


def test_actual_bc_reference_changes_shared_ff_clock_only():
    r=run(tail='puts "REF $latency(tt,vclk) $latency(ff,vclk) [array get budgets]"')
    assert 'RESULT 0' in r.stdout
    assert 'REF 256 195.0' in r.stdout
    assert 'scene BC' in r.stdout and 'samples 2' in r.stdout
    assert 'raw_hold_ps -60.0 referenced_hold_ps 1.0' in r.stdout
    assert 'in_min -40' in r.stdout and 'out_min 0' in r.stdout and 'setup 60' in r.stdout and 'hold 25' in r.stdout


def test_missing_or_wrong_scene_is_not_a_tt_slack_shift():
    for change in ['unset ::ot_mm_active','set ::ot_ioref_scene TC','rename ot_mm_arrival_bc {}']:
        r=run(change,tail='puts "REF $latency(tt,vclk) $latency(ff,vclk)"')
        assert 'RESULT 1' in r.stdout
        assert 'REF 256 256' in r.stdout


def test_missing_boundary_measurement_mutant_fails_closed():
    r=run('proc ot_mm_arrival_bc {p prop} {return ""}',tail='puts "REF $latency(ff,vclk)"')
    assert 'RESULT 1' in r.stdout and 'missing=2' in r.stdout and 'REF 256' in r.stdout


def test_explicit_contract_required_and_default_inert():
    r=run('unset env(OT_FF_VCLK_CONTRACT)')
    assert 'RESULT 1' in r.stdout and 'source-pinned' in r.stdout
    r=run('unset env(OT_FF_VCLK_MODE); unset ::ot_mm_active',tail='puts "REF $latency(ff,vclk)"')
    assert 'RESULT 0' in r.stdout and 'REF 256' in r.stdout
