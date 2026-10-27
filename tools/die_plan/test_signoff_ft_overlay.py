"""Die-owned FT pins never receive a core boundary-hold override."""
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent))
import signoff


def overlay_result(t, mutant=False):
    start = t.index('set so_reference_ok 1\n')
    end = t.index('so_timing STD', start)
    overlay = t[start:end]
    if mutant:
        overlay = overlay.replace('if {[get_full_name $p] in $so_ft_out} continue; ', '')
    fixture = r'''
set so_vclk vclk
set so_din {bus_i[1]}
set so_dout {bus_o[1]}
set so_ft_in {bus_i[0]}
set so_ft_out {bus_o[0]}
proc get_full_name {p} {return $p}
proc get_ports {patterns} {
  set out {}
  foreach pattern $patterns {
    if {$pattern eq {bus_i[*]}} {lappend out {bus_i[0]} {bus_i[1]}}
    if {$pattern eq {bus_o[*]}} {lappend out {bus_o[0]} {bus_o[1]}}
  }
  return $out
}
proc all_outputs {} {return {bus_o[0] bus_o[1]}}
proc set_input_delay {args} {foreach p [lindex $args end] {puts [list INPUT {*}[lrange $args 0 end-1] $p]}}
proc set_output_delay {args} {foreach p [lindex $args end] {puts [list OUTPUT {*}[lrange $args 0 end-1] $p]}}
proc so {args} {}
'''
    p = subprocess.run(['tclsh'], input=fixture + overlay, text=True, capture_output=True, check=True)
    assert not p.stderr, p.stderr
    return p.stdout


def session():
    return signoff.session_tcl('ff', [], True, hold_in_min=-40, hold_out_min=-5,
        hold_in_min_ports={'bus_i': 12.5}, hold_out_min_ports={'bus_o': -78.5},
        tap_window=20, ft_decl={'ports': [
            {'name': 'bus_i[0]', 'direction': 'INPUT'},
            {'name': 'bus_o[0]', 'direction': 'OUTPUT'}], 'arcs': []})


def test_resolved_bits_excluded_and_normal_io_budgets_preserved():
    calls = overlay_result(session())
    assert 'bus_i[0]' not in calls
    assert 'bus_o[0]' not in calls
    assert 'INPUT -min -40 -clock vclk {bus_i[1]}' in calls
    assert 'INPUT -min 12.5 -clock vclk {bus_i[1]}' in calls
    assert 'OUTPUT -min 15 -clock vclk {bus_o[1]}' in calls
    assert 'OUTPUT -min -58.5 -clock vclk {bus_o[1]}' in calls


def test_mutant_reintroducing_die_owned_output_is_observable():
    assert 'bus_o[0]' in overlay_result(session(), mutant=True)


def test_without_ft_keeps_existing_input_overlay_and_sender_shift():
    t = signoff.session_tcl('ff', [], True, hold_in_min_ports={'bus_i': 12.5},
        hold_out_min_ports={'bus_o': -78.5}, tap_window=20)
    assert '  set_input_delay -min 12.5 -clock [lindex $so_vclk 0] [get_ports {bus_i[*]}]\n' in t
    assert '  set_output_delay -min -58.5 -clock [lindex $so_vclk 0] [get_ports {bus_o[*]}]\n' in t
    assert 'so_override_ports' not in t
