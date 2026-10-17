"""hub_router: real-face endpoints and obstacle-free routes (S-DIE 2026-10-15)."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from s81 import hub_router as HR


class I:
    def __init__(s, name, x, y, w, h, orient='R0'):
        s.name, s.x, s.y, s.w, s.h, s.orient = name, x, y, w, h, orient


VM = I('vm', 13000, 16500, 4104, 4644)
CAP = I('cap', 14192, 21166, 1728, 561.6)
GA = I('ga', 14192, 21770, 1728, 1045)
COL = I('col', 17190, 16500, 1728, 2721)
HCS = I('hcs', 19354, 12600, 1816, 9130)
BOX = [(b.name, b.x, b.y, b.w, b.h) for b in (VM, CAP, GA, COL, HCS)]
DIE = (0, 0, 33000, 26000)


def test_abut_straight():
    rec = {'ports': {'t_vm': {'per_bit': [['S', 'M5', 100.0, .1], ['S', 'M5', 1600.0, .1]]}}}
    f, a = HR.endpoint(CAP, 't_vm', rec, VM)
    assert f == 'S' and abs(a[0] - (CAP.x + 850)) < 1e-6
    fb, b = HR.endpoint(VM, 'f_capture', None, CAP)
    assert fb == 'N'
    p = HR.route(a, f, (a[0], VM.y + VM.h), 'N', BOX, DIE)
    assert len(p) == 2 and not HR.path_hits(p, BOX)


def test_detour_around_blocks():
    # gather E face -> collective W face: must go round the VM top, never through capture / VM
    a = (GA.x + GA.w, GA.y + 500)
    b = (COL.x, COL.y + 1000)
    t = time.time()
    p = HR.route(a, 'E', b, 'W', BOX, DIE)
    assert p and not HR.path_hits(p, BOX), p
    assert time.time() - t < 30


def test_mirrored_face():
    rec = {'ports': {'f_lid': {'face': 'E', 'bits': 10, 'uniform': True, 'at': [0, 10.0]}}}
    w = I('wfc', 17190, 19300, 1728, 328, 'MY')
    f, _ = HR.endpoint(w, 'f_lid', rec, VM)
    assert f == 'W'


def test_assigned_slices_use_the_selected_physical_contacts():
    rec = {'ports': {'d': {'bits': 4, 'per_bit': [
        ['N', 'M5', 2.0, .192], ['N', 'M5', 20.0, .192],
        ['S', 'M5', 80.0, .192], ['S', 'M5', 100.0, .192]]}}}
    assert HR.assigned_face(rec, 'd[0:1]') == ('N', 11.0)
    assert HR.assigned_face(rec, 'd[3:2]') == ('S', 90.0)
    it = I('tile', 100, 200, 120, 80, 'R180')
    assert HR.endpoint(it, 'd[0]', rec, VM) == ('S', (218.0, 200))


def test_uniform_and_explicit_positions_preserve_pitch_and_corners():
    uniform = {'ports': {'d': {'face': 'N', 'bits': 4, 'uniform': True, 'at': [0, .192]}}}
    f, c = HR.assigned_face(uniform, 'd[2:3]')
    assert f == 'N' and abs(c - .48) < 1e-12
    assert HR.endpoint(I('tile', 10, 20, 100, 80), 'd[0]', uniform, VM) == ('N', (10, 100))
    explicit = {'ports': {'d': {'face': 'W', 'bits': 3, 'uniform': False, 'at': [1., 40., 75.]}}}
    assert HR.assigned_face(explicit, 'd[1:2]') == ('W', 57.5)
