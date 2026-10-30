"""FLOW-7 10-30 (DIE-QC-45): die_trial ot_place text must carry the exact plan origin.  The old '{ox:g}' text kept 6
significant digits (16390.08 -> 16390.1), so 221/377 QC partitions were placed 20-40 nm off plan and 438,159 port bits
did not abut; the same text was used by every die (S81/HEAD/KV/HBM GRT0 kits)."""
from pathlib import Path
from types import SimpleNamespace
import inspect, re, sys
sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D

PARTS = {'c_E0_bf_00': dict(origin_um=[16390.08, 2617.92], orient='MX'),
         'c_W5_tn_01': dict(origin_um=[1563.84, 18420.48], orient='R0'),
         'ctl': dict(origin_um=[8760.96, 14999.04]),
         'z': dict(origin_um=[0, 0.0])}


def _xy(lines):
    out = {}
    for l in lines:
        m = re.match(r'^ot_place (\S+) (\S+) (\S+) (\S+)$', l)
        assert m, l
        out[m.group(1)] = (float(m.group(2)), float(m.group(3)), m.group(4))
    return out


def test_place_lines_exact_origin():
    got = _xy(D.place_lines(SimpleNamespace(parts=PARTS)))
    for n, p in PARTS.items():
        x, y, o = got[D.sv(n)]
        assert (x, y) == tuple(float(v) for v in p['origin_um']), (n, x, y)
        assert o == p.get('orient', 'R0')


def test_place_lines_dbu_exact_at_4000():
    # ot_place rounds x*dbu: the text must give the plan's integer DBU at the finest ASAP7 DBU we use (4000/um)
    for l in D.place_lines(SimpleNamespace(parts=PARTS)):
        n, x, y = l.split()[1:4]
        p = next(v for k, v in PARTS.items() if D.sv(k) == n)
        assert round(float(x) * 4000) == round(p['origin_um'][0] * 4000)
        assert round(float(y) * 4000) == round(p['origin_um'][1] * 4000)


def test_no_six_digit_coordinate_text_left():
    # grt_tcl / psm_tcl place partitions through place_lines; bump coordinates use gen_phys._um
    src = inspect.getsource(D)
    assert not re.search(r'ot_place \{sv\(n\)\} \{ox:g\}', src)
    assert not re.search(r'ot_pad \{net\} \{k\} \{x:g\}', src)
    assert '{{{x:g}*$bump_dbu}}' not in src
    assert 'place_lines(P)' in inspect.getsource(D.grt_tcl) and 'place_lines(P)' in inspect.getsource(D.psm_tcl)
