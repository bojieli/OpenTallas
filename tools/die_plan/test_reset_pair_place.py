"""Small geometry primitive and actual fail-closed API surface of paired reset placement."""
from pathlib import Path
import subprocess


def test_rectangle_contact_is_legal_overlap_is_not():
    p=Path(__file__).with_name('reset_pair_place.tcl')
    script=f'source {{{p}}}\n'+'''
if {[::ot_rpp::hit {0 0 1 1} {1 0 2 1}]} {error "abutting legal sites reported overlap"}
if {![::ot_rpp::hit {0 0 1 1} {0.9 0 2 1}]} {error "real overlap missed"}
if {[llength [info args ot_reset_pair_place]] != 4} {error "allocator API changed"}
puts RESET_PAIR_API_PASS
'''
    r=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
    assert r.returncode==0 and not r.stderr,r.stderr
    assert 'RESET_PAIR_API_PASS' in r.stdout
