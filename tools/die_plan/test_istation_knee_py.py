"""KNEE-1: the Python planner mirror (istation_knee) must agree with the kit's own is_knee_site depth guard."""
from pathlib import Path
import random, re, subprocess, sys
sys.path.insert(0, str(Path(__file__).parent))
import kit_istations as I
import istation_knee as KN
PROC = I.TCL_HEAD[I.TCL_HEAD.index('proc is_knee_site'):I.TCL_HEAD.index('proc is_bits')]


def kit_worst(face, direction, leaf, bbox, edges):
    """worst ideal hop the kit reports (None: kit accepts the depth)"""
    xmin, ymin, xmax, ymax = bbox
    body = (f'if {{[catch {{is_knee_site {xmin} {ymin} {leaf[0]} {leaf[1]} {face} 1 {edges} {direction} '
            f'{{{xmin} {ymin} {xmax} {ymax}}}}} msg]}} {{ puts $msg }} else {{ puts OK }}')
    p = subprocess.run(['tclsh'], input=PROC + '\n' + body, text=True, capture_output=True)
    assert p.returncode == 0, p.stderr
    out = p.stdout.strip()
    if out == 'OK':
        return None
    m = re.search(r'worst ideal hop ([0-9.eE+-]+) >403um', out)
    assert m, out
    return float(m.group(1))


def py_worst(face, direction, leaf, bbox, edges):
    xmin, ymin, xmax, ymax = bbox
    return KN.worst_hop(face, direction, leaf, [(xmin, ymin), (xmax, ymax)], edges - 1)


def test_reproduces_sle_fw_v3_st_eo_442_99():
    # sle_fw_v3 st_eo (a7 3_3_place_gp stop): W-face out bus, leaf (622.08, 1044.022), 2 stations (3 edges); the old
    # straight estimate L1/(n+1) = 355 um passed, the kit's shared knee split gives max(443/1, 622/2) = 443 um.
    leaf, bbox = (622.08, 1044.022), (0.0, 601.032, 0.0, 1044.022)
    k = kit_worst('W', 'out', leaf, bbox, 3)
    assert k is not None and abs(k - 442.99) < 1e-6
    assert abs(py_worst('W', 'out', leaf, bbox, 3) - k) < 1e-9
    first, second = KN.legs('W', 'out', leaf, [bbox[:2], bbox[2:]])
    assert (first + second) / 3 < 403.0          # the old model's estimate: why it was missed
    n = KN.stations_needed('W', 'out', leaf, [bbox[:2], bbox[2:]], 2)
    assert n == 3 and kit_worst('W', 'out', leaf, bbox, n + 1) is None


def test_in_bus_checked_with_reversed_legs():
    # sle_fw_v3 x_ctl_i: N-face in bus, 1 station: 668 um normal leg in one hop; never checked by the old tool.
    leaf, bbox = (298.278, 670.846), (211.95, 1339.2, 384.55, 1339.2)
    k = kit_worst('N', 'in', leaf, bbox, 2)
    assert k is not None and abs(k - py_worst('N', 'in', leaf, bbox, 2)) < 1e-9
    assert KN.stations_needed('N', 'in', leaf, [bbox[:2], bbox[2:]], 1) == 2


def test_python_matches_kit_guard_on_random_chains():
    rnd = random.Random(1110)
    for _ in range(150):
        face, direction = rnd.choice('NSEW'), rnd.choice(('in', 'out'))
        leaf = (rnd.uniform(50, 1150), rnd.uniform(50, 1300))
        if face in 'EW':
            x = 0.0 if face == 'W' else 1226.88
            y0 = rnd.uniform(0, 1200)
            bbox = (x, y0, x, y0 + rnd.uniform(0, 300))
        else:
            y = 0.0 if face == 'S' else 1339.2
            x0 = rnd.uniform(0, 1100)
            bbox = (x0, y, x0 + rnd.uniform(0, 300), y)
        edges = rnd.randint(2, 6)
        k, p = kit_worst(face, direction, leaf, bbox, edges), py_worst(face, direction, leaf, bbox, edges)
        if k is None:
            assert p <= 403.0 + 1e-9
        else:
            assert abs(k - p) < 1e-6 and p > 403.0
