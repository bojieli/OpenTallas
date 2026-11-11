"""DIE-QC-97 11-11 SHARED-OCC: face pin registers and ft stations share one FIRM occupancy map in face_flops.tcl."""
from pathlib import Path
import os
import subprocess

SRC = Path(__file__).with_name('face_flops.tcl').read_text()


def run(face_rects=None, env=None, x=10, y=0):
    body = 'set ff_gocc {}' + SRC.split('set ff_gocc {}', 1)[1].split('set ff_st 0', 1)[0]
    script = '''set ff_x0 0; set ff_y0 0; set ff_x1 100; set ff_y1 30
set ff_rh 10; set ff_sw 1; set ff_cpitch 10; set ff_dbu 1
set ff_orient [dict create 0 R0 10 R0 20 R0]
proc master {cmd} {if {$cmd eq "getWidth"} {return 5}; return 10}
proc cell {cmd args} {if {$cmd eq "getMaster"} {return master}; if {$cmd eq "getPlacementStatus"} {return UNPLACED}; if {$cmd eq "getName"} {return cell}}
'''
    if face_rects is not None:
        script += 'set ff_face_rects {%s}\n' % ' '.join('{%s}' % ' '.join(map(str, r)) for r in face_rects)
    script += body + 'puts [ff_put_near cell %d %d]\n' % (x, y)
    e = dict(os.environ); e.pop('OT_FF_SHARED_OCC', None); e.update(env or {})
    out = subprocess.run(['tclsh'], input=script, text=True, capture_output=True, check=True, env=e)
    assert not out.stderr, out.stderr
    return tuple(map(int, out.stdout.splitlines()[-1].split()))


def test_station_never_takes_a_face_register_site():
    # a26 form: the S face register sits on the station grid cell the station wants
    assert run([[10, 0, 5, 10]]) == (0, 0)


def test_partial_overlap_from_an_offset_face_grid_is_also_blocked():
    # E/N face grids are offset from the station grid: any body overlap counts, not only the same origin
    assert run([[12, 3, 5, 10]]) == (0, 0)


def test_edge_touching_face_register_and_no_face_registers_stay_exact():
    assert run([[5, 0, 5, 10]]) == (10, 0)
    assert run([]) == (10, 0)
    assert run(None) == (10, 0)


def test_opt_out_restores_separate_maps():
    assert run([[10, 0, 5, 10]], env={'OT_FF_SHARED_OCC': '0'}) == (10, 0)


def test_face_pass_records_every_firm_face_body():
    face = SRC.split('foreach pass {INPUT OUTPUT}', 1)[1].split('# ---- ft stations', 1)[0]
    assert face.count('setPlacementStatus FIRM') == face.count('lappend ff_face_rects') == 2
