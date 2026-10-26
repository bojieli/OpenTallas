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


def test_reset_start_entries_and_all_relay_copies_protected_then_released():
    names = {
        'rst': 'u_bound.u_rst_in/q',
        'run': 'u_bound.u_run_in/q',
        'root': 'u_bound/u_run_root/p',
        'raw': 'u_bound.u_rrl_4_r/q',
        'gate': 'u_bound/u_rrl_4_g/q',
        'start': 'u_bound.u_srl_12/q',
        'miss': 'u_bound.u_srl_12_user/q',
    }
    d = ' '.join(k+' '+v for k,v in names.items())
    tcl = ('proc get_cells {args} {return {'+' '.join(names)+'}}\n'
           'proc get_full_name {c} {return [dict get {'+d+'} $c]}\n'
           'proc set_dont_touch {cells} {puts "HELD $cells"}\n'
           'proc unset_dont_touch {cells} {puts "FREED $cells"}\n')
    for name in ('face_keep.tcl','face_keep_release.tcl'):
        tcl += f'source {{{HERE/name}}}\n'
    r = subprocess.run(['tclsh'], input=tcl, text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr, r.stderr
    assert 'HELD rst run root raw gate start\n' in r.stdout
    assert 'FREED rst run root raw gate start\n' in r.stdout
