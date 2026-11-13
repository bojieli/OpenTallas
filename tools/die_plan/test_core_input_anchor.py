"""Generic QN buffers must not hide the named NK pipeline flop."""
from pathlib import Path
import subprocess
import pytest

SRC = Path(__file__).with_name('core_input_anchor.tcl').read_text()
PROC = SRC[SRC.index('proc nka_pipe_chain '):SRC.index('foreach inst [$nka_blk getInsts]')]
HARNESS = r'''
set graph {}
proc object {name attrs} {
  dict set ::graph $name $attrs
  interp alias {} $name {} dispatch $name
  return $name
}
proc dispatch {name method args} {
  return [dict get $::graph $name $method]
}
proc pin {id dir net inst} {
  object ${id}_mt [dict create getIoType $dir]
  object $id [dict create getMTerm ${id}_mt getNet $net getInst $inst]
  return $id
}
proc cell {id master name input output} {
  object ${id}_m [dict create getName $master isBlock 0]
  set ps [list [pin ${id}_out_it OUTPUT $output $id]]
  if {$input ne ""} { lappend ps [pin ${id}_in_it INPUT $input $id] }
  object $id [dict create getMaster ${id}_m getName $name getITerms $ps]
  object $output [dict create getITerms [list ${id}_out_it]]
}
cell pc DFFHQNx1_ASAP7 u_bound.u_pc_nk_u_t_0_2_n_b.q78_DFF data pc_q
cell inv INVxp67_ASAP7 generic_qn_inverter pc_q inv_q
cell buf BUFx2_ASAP7 anonymous_buffer inv_q latch_d
'''


def run(body):
    r = subprocess.run(['tclsh'], input=PROC + HARNESS + body, text=True, capture_output=True)
    assert r.returncode == 0, r.stderr
    assert not r.stderr, r.stderr
    return r.stdout.strip()


def test_generic_qn_inverter_and_buffer_find_actual_named_pc():
    assert run('puts [nka_pipe_chain latch_d]') == 'buf inv pc'


def test_unrelated_reset_dff_never_returns_partial_move_chain():
    assert run('dict set ::graph pc getName reset_flop; puts x[nka_pipe_chain latch_d]x') == 'xx'


def test_arbitrary_logic_even_with_pc_name_is_not_transparent():
    assert run('dict set ::graph inv_m getName AND2x1; dict set ::graph inv getName u_pc_nk_fake; puts x[nka_pipe_chain latch_d]x') == 'xx'


def test_buffer_cycle_fails_closed():
    assert run('dict set ::graph inv_in_it getNet latch_d; puts x[nka_pipe_chain latch_d]x') == 'xx'


def test_depth_is_bounded():
    assert run('puts x[nka_pipe_chain latch_d 2]x') == 'xx'


def test_multiple_drivers_fail_closed():
    assert run('dict set ::graph latch_d getITerms {buf_out_it inv_out_it}; puts x[nka_pipe_chain latch_d]x') == 'xx'


def test_direct_pc_still_supported():
    assert run('puts [nka_pipe_chain pc_q]') == 'pc'


def test_two_input_buffer_master_is_not_unary():
    assert run('pin extra INPUT second buf; dict set ::graph buf getITerms [concat [dict get $::graph buf getITerms] extra]; puts x[nka_pipe_chain latch_d]x') == 'xx'


def test_constant_tap_has_no_pipeline_register_and_is_untouched():
    assert run('dict set ::graph buf_m getName TIELOx1_ASAP7_75t_R; puts x[nka_pipe_chain latch_d]x') == 'xx'


FORWARD = r"""
object hard_m [dict create getName hard_tile isBlock 1]
object hard [dict create getMaster hard_m]
pin hard_in INPUT latch_d hard
dict set ::graph pc_q getITerms {pc_out_it inv_in_it}
dict set ::graph inv_q getITerms {inv_out_it buf_in_it}
dict set ::graph latch_d getITerms {buf_out_it hard_in}
"""


def test_generic_q_buffer_forward_path_has_unique_macro_endpoint():
    assert run(FORWARD + 'puts [nka_macro_path pc_q]') == 'hard_in {inv buf}'


def test_forward_multiple_sinks_refused_without_partial_chain():
    assert run(FORWARD + 'dict set ::graph pc_q getITerms {pc_out_it inv_in_it hard_in}; puts x[nka_macro_path pc_q]x') == 'xx'


def test_forward_non_unary_logic_refused():
    assert run(FORWARD + 'dict set ::graph inv_m getName AND2x1; puts x[nka_macro_path pc_q]x') == 'xx'


def test_forward_cycle_refused():
    assert run(FORWARD + 'dict set ::graph buf_out_it getNet pc_q; puts x[nka_macro_path pc_q]x') == 'xx'


def test_forward_depth_bounded():
    assert run(FORWARD + 'puts x[nka_macro_path pc_q 2]x') == 'xx'
