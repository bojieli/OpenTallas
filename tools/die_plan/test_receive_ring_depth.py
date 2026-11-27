"""Pure known-answer checks for the opt-in pre-GPL ring selector."""

from pathlib import Path
import shutil
import subprocess
import unittest

import receive_ring_depth as rx


class ReceiveRingDepthTest(unittest.TestCase):
    def test_absent_is_empty(self):
        self.assertIsNone(rx.validate({}, "untouched"))

    @unittest.skipUnless(shutil.which("tclsh"), "requires Tcl")
    def test_live_role_and_area_guards(self):
        source = Path(rx.__file__).with_suffix(".tcl")
        script = r'''
source [lindex $argv 0]
set name {\u_bound.u_cland_b/u_ring.dch\[3\].sd_c\[17\]$_DFF_P_}
if {[ot_rx_depth_key $name] ne {b 3 storage 17}} {error "normalized native role"}
set name {u_bound.u_cland_b/u_ring.dch[3].u_dsel/y[12]$_DFF_P_}
if {[ot_rx_depth_key $name] ne {b 3 read 12}} {error "native read role"}
set anchors [dict create {b 3 storage 17} storage]
set regions [dict create inner {b {20 5 30 15} 8.0}]
set floors [dict create {0 0} 1.0]
set picks [list {{0 0} inner {3 storage 17} {{D INVx1} {A AO21x1}} 1.5}]
set graph [dict create {storage D} gateA {gateA A} renamedCell]
set roles [dict create gateA {b INVx1 0 0} renamedCell {b AO21x1 0 0} storage {b DFF 1 1}]
proc smoke_in {i p} {global graph; if {[dict exists $graph [list $i $p]]} {return [dict get $graph [list $i $p]]}; return {}}
proc smoke_role {i} {global roles; return [dict get $roles $i]}
proc smoke_area {i} {return 1.5}
proc smoke_select {direct} {
    global anchors regions floors picks
    return [ot_rx_depth_select $regions $floors $picks $anchors $direct smoke_in smoke_role smoke_area]
}
proc rejects {script reason} {
    if {![catch {uplevel 1 $script} msg] || ![string match "*$reason*" $msg]} {
        error "did not reject $reason: $msg"
    }
}
lassign [smoke_select {}] members selected totals
if {[dict get $members inner] ne {renamedCell}} {error "stable route did not select renamed body"}
lassign [smoke_select [dict create gateA 1]] members selected totals
if {[dict get $members inner] ne {renamedCell}} {error "direct writer used as a reference changed membership"}
rejects {smoke_select [dict create renamedCell 1]} {conflicting role}
dict set roles renamedCell {b AO21x1 0 1}
rejects {smoke_select {}} {conflicting role}
dict set roles renamedCell {b AO21x2 0 0}
rejects {smoke_select {}} {conflicting role}
dict set roles renamedCell {b AO21x1 0 0}
dict set graph {gateA A} storage
rejects {smoke_select {}} {conflicting role}
dict set graph {gateA A} renamedCell
dict set floors {0 0} 2.0
rejects {smoke_select {}} {source budget short}
dict set floors {0 0} 1.0
dict set regions inner {b {20 5 30 15} 1.0}
rejects {smoke_select {}} {receiving budget exceeded}
dict set regions inner {b {20 5 30 15} 8.0}
set picks [concat $picks $picks]
rejects {smoke_select {}} {aliased role}
'''
        # Tclsh reads stdin in interactive mode. eval under catch propagates failures.
        wrapper = "\n".join([
            "set argv [list {" + str(source) + "}]",
            "if {[catch {",
            script,
            "} msg]} {puts stderr $msg; exit 1}",
        ]) + "\n"
        subprocess.run(["tclsh"], input=wrapper, text=True, check=True)


if __name__ == "__main__":
    unittest.main()
