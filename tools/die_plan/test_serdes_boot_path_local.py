"""Private BOOT reset-path placement: reject graph hazards before mutation."""
import shutil
import subprocess
from pathlib import Path
import pytest
SRC=Path(__file__).with_name('serdes_boot_release_local.tcl')
MOCK=r'''
source @SRC@
set ::shared @SHARED@
set ::foreign @FOREIGN@
proc src {op args} {if {$op eq "getName"} {return src}; error "unexpected src $op"}
proc dst {op args} {if {$op eq "getITerms"} {return {sink}};if {$op eq "getName"} {return dst};error "unexpected dst $op"}
proc sink {op args} {switch $op {getMTerm {return reset} getNet {return out} isInputSignal {return 1} isOutputSignal {return 0}};error "unexpected sink $op"}
proc reset {op args} {if {$op eq "getName"} {return RESETN};error "unexpected reset $op"}
proc out {op args} {switch $op {getName {return out} getBTerms {return {}} getITerms {if {$::shared} {return {inv_o sink other}};return {inv_o sink}}};error "unexpected out $op"}
proc other {op args} {if {$op eq "isInputSignal"} {return 1};if {$op eq "isOutputSignal"} {return 0};error "unexpected other $op"}
proc inv_o {op args} {switch $op {isOutputSignal {return 1} isInputSignal {return 0} getInst {return inv}};error "unexpected inv_o $op"}
proc inv {op args} {switch $op {getMaster {return master} getName {return inv} getPlacementStatus {return PLACED} getITerms {return {inv_i inv_o}}};error "mutation/unexpected inv $op"}
proc master {op args} {switch $op {getName {if {$::foreign} {return AND2};return INVx1} isBlock {return 0} isSequential {return 0}};error "unexpected master $op"}
proc inv_i {op args} {switch $op {isInputSignal {return 1} isOutputSignal {return 0} getNet {return input}};error "unexpected inv_i $op"}
proc input {op args} {switch $op {getName {return input} getBTerms {return {}} getITerms {return {src_o inv_i}}};error "unexpected input $op"}
proc src_o {op args} {switch $op {isOutputSignal {return 1} isInputSignal {return 0} getInst {return src}};error "unexpected src_o $op"}
set rc [catch {ot_serdes_boot_private_chain src dst} result]
puts "RC=$rc RESULT=$result"
'''
@pytest.mark.skipif(shutil.which('tclsh') is None,reason='tclsh missing')
@pytest.mark.parametrize('shared,foreign,expected',[(0,0,'RC=0 RESULT=inv'),(1,0,'shared control'),(0,1,'non-buffer private path')])
def test_private_chain_and_graph_negative_controls(shared,foreign,expected):
    script=MOCK.replace('@SRC@',str(SRC)).replace('@SHARED@',str(shared)).replace('@FOREIGN@',str(foreign))
    r=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,check=True)
    assert expected in r.stdout,(r.stdout,r.stderr)

def test_default_path_remains_opt_in():
    s=SRC.read_text()
    assert 'OT_SERDES_BOOT_PATH_LOCAL' in s
    assert 'if {[info exists ::env(OT_SERDES_BOOT_PATH_LOCAL)] && $::env(OT_SERDES_BOOT_PATH_LOCAL) eq "1"}' in s
    helper=s[s.index('proc ot_serdes_boot_private_chain'):s.index('proc ot_serdes_boot_release_local')]
    assert 'connect' not in helper and 'disconnect' not in helper
