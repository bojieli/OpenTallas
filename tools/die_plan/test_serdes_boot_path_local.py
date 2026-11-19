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


DETOUR=r"""
namespace eval ot_reset_anchor {}
proc ot_reset_anchor::free {rect macros core} {
 lassign $rect x0 y0 x1 y1;lassign $core a b c d
 if {$x0<$a || $y0<$b || $x1>$c || $y1>$d} {return 0}
 foreach r $macros {lassign $r a b c d;if {$x0<$c && $x1>$a && $y0<$d && $y1>$b} {return 0}}
 return 1
}
source @SRC@
proc m {op} {switch $op {getWidth {return 1080} getHeight {return 270}}}
# serdes__t1 11-19 (clfe1f0815 / clb45db5be): u_cmem 1533.6..1711.4 x 62.652..143.652 um with its 8.64-um halo; stage 0 below
# it, stage 1 above it.  The straight line runs through the macro; the chain cells take the detour around it.
set macs {{1524960 54012 1720872 152292}}
set core {4320 4320 2881440 1222560}
set g [ot_serdes_boot_detour 1540440 52380 1620810 152550 1000.0 $macs $core]
puts "GUIDE $g"
set ok 1
foreach f {0.1 0.25 0.5 0.75 0.9} {set s [ot_serdes_boot_guide_site $g $f m 1000.0 $macs $core];if {![llength $s]} {set ok 0};puts "SITE $f $s"}
puts "STRAIGHT [ot_serdes_boot_guide_site [list {1540440 52380} {1620810 152550}] 0.5 m 1000.0 $macs $core]"
puts "OK $ok"
"""


@pytest.mark.skipif(shutil.which('tclsh') is None,reason='tclsh missing')
def test_chain_cells_detour_around_a_macro_between_two_stages():
    r=subprocess.run(['tclsh'],input=DETOUR.replace('@SRC@',str(SRC)),text=True,capture_output=True)
    assert 'OK 1' in r.stdout and 'STRAIGHT \n' in r.stdout+'\n', (r.stdout,r.stderr)
    g=[tuple(map(float,p.split())) for p in r.stdout.split('GUIDE ')[1].splitlines()[0].strip('{}').split('} {')]
    L=sum(abs(b[0]-a[0])+abs(b[1]-a[1]) for a,b in zip(g,g[1:]))/1000
    assert 180 < L < 405, g          # around the west or east edge, not through the macro
    for ln in r.stdout.splitlines():
        if ln.startswith('SITE '):
            x,y=map(int,ln.split()[2:4])
            assert not (x<1720872 and x+1080>1524960 and y<152292 and y+270>54012), ln
