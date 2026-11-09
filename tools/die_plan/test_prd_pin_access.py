"""PRD FlexPA restores pre-existing wire objects on success and original failure."""
from pathlib import Path
import subprocess
import pytest

HOOK = Path(__file__).with_name('post_route_drv') / 'eco_grt_pre.tcl'
MOCK = r'''
namespace eval ord {proc get_db_block {} {return b}}
namespace eval odb {proc dbWire_destroy {w} {set ::destroyed $w; set ::attached NULL}}
set attached w
proc b {method} {return n}
proc n {method args} {global attached; switch -- $method {getSigType {return CLOCK} getWire {return $attached} getName {return clk}}}
proc w {method args} {global attached; switch -- $method {detach {if {[info exists ::detach_fail] && $::detach_fail} {error detach_failure}; set attached NULL} attach {set attached w}}}
proc pin_access {args} {
  set ::seen $args
  if {$::attached ne "NULL"} {error DRT-0415}
  if {$::fail == 1} {error original_failure}
  if {$::fail == 2} {set ::attached unexpected_wire}
  return original_result
}
'''

@pytest.mark.parametrize('fail,expected', [(0,'RESULT 0 original_result'),(1,'RESULT 1 original_failure'),(2,'RESULT 0 original_result')])
def test_restores_wire_and_keeps_pin_access_result(fail, expected):
    script = MOCK + HOOK.read_text() + f'\nset fail {fail}\n' + r'''
set rc [catch {pin_access -db_process_node 7} result]
if {$attached ne "w"} {error wire_not_restored}
if {$seen ne "-db_process_node 7"} {error arguments_changed}
puts "RESULT $rc $result"
'''
    result = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert result.returncode == 0 and not result.stderr, result.stderr
    assert expected in result.stdout


def test_kit_pre_global_route_hook_is_preserved(tmp_path):
    chain=tmp_path/'chain.tcl';chain.write_text('set ::kit_pre_hook_seen 1\n')
    script=MOCK+f'\nset ::env(OT_ECO_GRT_PRE_CHAIN) {{{chain}}}\n'+HOOK.read_text()+r'''
if {![info exists ::kit_pre_hook_seen]} {error lost_kit_hook}
puts CHAIN_OK
'''
    result=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
    assert result.returncode == 0 and not result.stderr
    assert 'CHAIN_OK' in result.stdout


def test_detach_failure_keeps_original_wire_and_error():
    script=MOCK+HOOK.read_text()+r'''
set detach_fail 1
set rc [catch {pin_access} result]
if {$attached ne "w"} {error original_wire_destroyed}
if {[info exists destroyed]} {error original_wire_was_destroyed}
puts "RESULT $rc $result"
'''
    result=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
    assert not result.stderr and 'RESULT 1 detach_failure' in result.stdout
