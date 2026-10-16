"""S-DIE 0600 10-16: generated face groups never sit on another port's pins (c26b_r DRT-0073 bf_front_static
f_prog on x0[175], sp_vm t_pqx on f_capture[9116])."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
_spec = importlib.util.spec_from_file_location('s81fd_pc', ROOT / 'tools/dsrom_s81_fulldie.py')
fd = importlib.util.module_from_spec(_spec)
_argv, sys.argv = sys.argv, ['x']
_spec.loader.exec_module(fd)
sys.argv = _argv


def _hit(a, b):
    return a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6


def _clashes(Mx, port):
    rs = fd.pin_rects(Mx, 1, {})
    mine = [r for r in rs if r[0].rsplit('[', 1)[0] == port]
    other = [r for r in rs if r[0].rsplit('[', 1)[0] != port]
    return sum(1 for a in mine for b in other if a[1] == b[1] and _hit(a[2], b[2]))


def test_face_group_moves_off_fixed_pins():
    Mx = fd.Q.Master('t_bf', 100.224, 198.72, 7, 't')
    Mx.ports['x0'] = ('rects', [(f'x0[{i}]', 'M5', (48.0 + 0.096 * i, 0, 48.024 + 0.096 * i, 0.192)) for i in range(40)])
    Mx.order.append('x0')
    Mx.face('f_prog', 38, 'S', 'M5', 49.0, 1)
    assert _clashes(Mx, 'f_prog') > 0
    fd._resolve_pin_collisions(Mx)
    assert _clashes(Mx, 'f_prog') == 0
    assert Mx.ports['f_prog'][2] == 'S'                      # same face, nearest free stretch
    assert fd.PIN_COLLISIONS['t_bf']['moved'][0]['port'] == 'f_prog'


def test_no_collision_is_untouched():
    Mx = fd.Q.Master('t_ok', 100, 100, 7, 't')
    Mx.face('a', 10, 'S', 'M5', 20, 1)
    Mx.face('b', 10, 'S', 'M5', 60, 1)
    before = dict(Mx.ports)
    fd._resolve_pin_collisions(Mx)
    assert Mx.ports == before and 't_ok' not in fd.PIN_COLLISIONS


def test_fixed_vs_fixed_is_recorded_not_moved():
    Mx = fd.Q.Master('t_fx', 50, 50, 7, 't')
    Mx.ports['p'] = ('rects', [('p[0]', 'M5', (10, 0, 10.024, 0.192))]); Mx.order.append('p')
    Mx.ports['q'] = ('rects', [('q[0]', 'M5', (10, 0, 10.024, 0.192))]); Mx.order.append('q')
    fd._resolve_pin_collisions(Mx)
    assert fd.PIN_COLLISIONS['t_fx']['fixed_conflict_pairs'] == 1
