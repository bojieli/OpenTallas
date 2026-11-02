"""Explicit unloaded driver profiles never turn loaded/foreign nets into aliases."""
from pathlib import Path
import subprocess
import pytest

HELPER=Path(__file__).with_name('frozen_clock_rc.tcl')
MOCK=r'''
namespace eval ord {proc get_db_block {} {return block}}
proc block {cmd arg} {if {$cmd eq "findNet"} {return net};if {$cmd eq "findInst"} {return inst};return root}
proc net {cmd} {switch $cmd {getSigType {return CLOCK} getBTerms {return $::bterms} getITerms {return $::iterms} getWire {return $::wire}}}
proc inst {cmd args} {switch $cmd {getMaster {return master} findITerm {return input}}}
proc master {cmd} {return $::master}
proc out {cmd} {switch $cmd {getInst {return inst} getMTerm {return om}}}
proc om {cmd} {if {$cmd eq "getName"} {return Y};return $::odirection}
proc input {cmd} {if {$cmd eq "getMTerm"} {return im};return innet}
proc im {cmd} {return INPUT}
proc innet {cmd} {return clkbranch}
proc root {cmd} {return INPUT}
proc wire {cmd} {return 4}
proc get_pins {args} {return inputpin}
proc get_fanin {args} {return $::roots}
proc get_full_name {x} {return $x}
proc all_clocks {} {return clock}
proc get_property {args} {return $::clockroots}
set bterms {};set iterms out;set wire NULL
set master BUFx24_ASAP7_75t_R;set odirection OUTPUT
set roots clk;set clockroots clk
set spec [dict create instance branch master BUFx24_ASAP7_75t_R input A output Y root clk source_net clkbranch]
'''

@pytest.mark.parametrize('mutation,ok', [('',True),('set bterms port',False),('set iterms {out load}',False),('set wire wire',False),('set master BUFx12_ASAP7_75t_R',False),('set odirection INPUT',False),('set roots data',False),('set roots {clk data}',False),('set clockroots other',False),('dict set spec source_net foreign',False),('dict set spec surprise value',False)])
def test_native_shape_and_root_join(mutation,ok):
    text=f'source {{{HELPER}}}\n'+MOCK+'\n'+mutation+'\nif {[catch {ot_clock_rc_check_empty_driver spur $spec} why]} {puts "REJECT $why"} else {puts ACCEPT}\n'
    p=subprocess.run(['tclsh'],input=text,text=True,capture_output=True,check=True)
    assert not p.stderr
    assert ('ACCEPT' in p.stdout)==ok,p.stdout
