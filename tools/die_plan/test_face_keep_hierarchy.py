"""Real Tcl selection of face cells at flat and bound hierarchy depths."""
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def test_nested_face_cells_protected_and_released():
    tcl = '''
proc get_cells {args} {return {a b c other}}
proc get_full_name {c} {return [dict get {a u_bin_x/q b u_bound.u_bin_x/u_ep/eq c u_bound/u_ft_ft0_o_0/q other u_logic/q} $c]}
proc set_dont_touch {cells} {puts "HELD $cells"}
proc unset_dont_touch {cells} {puts "FREED $cells"}
'''
    for name in ('face_keep.tcl','face_keep_release.tcl'):
        tcl += f'source {{{HERE/name}}}\n'
    r = subprocess.run(['tclsh'],input=tcl,text=True,capture_output=True)
    assert not r.stderr, r.stderr
    assert 'HELD a b c' in r.stdout and 'FREED a b c' in r.stdout
