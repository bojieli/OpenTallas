"""hbmdie 2026-10-13: the die reach lint is PIN TO PIN (owner rule: register at the pin -> wire <= 500 um -> register
at the pin).  The box-to-box walk (fp_margin_lint.die_margin) passes a hop into a pin on the far face of a wide block;
fp_margin_lint.die_pin_hops must fail it, flag pin-less placeholders as box-to-box, and count reset nets."""
import sys
from pathlib import Path
from types import SimpleNamespace as N

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fp_margin_lint as FPL  # noqa: E402


def _die():
    # a 3,200 x 1,100 um block (the SM outline), a relay station 100 um W of it, a second station 400 um further W
    insts = [N(name='sm', kind='sm', master='hfd_sm', x=1000.0, y=0.0, w=3200.0, h=1100.0),
             N(name='s0', kind='waypoint', master='stn', x=880.0, y=500.0, w=20.0, h=40.0),
             N(name='s1', kind='waypoint', master='stn', x=460.0, y=500.0, w=20.0, h=40.0),
             N(name='ph', kind='hub', master='hfd_placeholder', x=0.0, y=480.0, w=300.0, h=80.0),
             N(name='rr', kind='waypoint', master='hfd_rrl', x=900.0, y=1200.0, w=12.0, h=12.0)]
    buses = [('r_sm', 'result', 272, [('sm', 'r'), ('s0', 'a')]),          # sm.r is on the FAR (E) face
             ('x_sm', 'x', 2064, [('s0', 'b'), ('sm', 'x')]),              # sm.x is on the near (W) face
             ('r_s', 'result', 272, [('s0', 'b'), ('s1', 'a')]),
             ('r_ph', 'result', 272, [('s1', 'b'), ('ph', 'i')]),          # placeholder: no pins
             ('clk', 'clock_trunk', 1, [('rr', 'o'), ('sm', 'ck'), ('ph', 'ck')]),
             ('rst_leaf', 'reset_tree', 1, [('rr', 'o'), ('sm', 'rst'), ('s1', 'rst')])]
    pins = {('sm', 'r'): (4200.0, 1000.0), ('sm', 'x'): (1000.0, 520.0), ('sm', 'rst'): (1500.0, 1100.0),
            ('s0', 'a'): (900.0, 520.0), ('s0', 'b'): (880.0, 520.0), ('s1', 'a'): (480.0, 520.0), ('s1', 'b'): (460.0, 520.0),
            ('s1', 'rst'): (470.0, 540.0), ('rr', 'o'): (906.0, 1206.0)}
    return insts, buses, (lambda i, p: pins.get((i, p)))


def test_box_walk_passes_what_the_pin_rule_fails():
    insts, buses, pt = _die()
    data = [b for b in buses if b[1] not in ('clock_trunk', 'reset_tree')]
    box = FPL.die_margin(insts, data, ('waypoint',), reach_um=504.0, edges=True)
    assert box['reach_violations'] == 0                     # 100 um box to box: the old lint is silent
    ph = FPL.die_pin_hops(insts, buses, pt, relay_kinds=('waypoint',))
    assert ph['verdict'] == 'FAIL'
    over = {h['net']: h for h in ph['examples']}
    assert set(over) == {'r_sm', 'rst_leaf'}
    assert over['r_sm']['um'] == 3780.0 and over['r_sm']['measure'] == 'pin-to-pin' and over['r_sm']['kind'] == 'data'
    assert over['r_sm']['cause'].startswith('block <-> station')
    assert over['rst_leaf']['kind'] == 'reset' and over['rst_leaf']['um'] == 1030.0 + 666.0   # half perimeter of 3 pins
    assert (ph['data_hops_over'], ph['reset_nets_over'], ph['nets'], ph['reset_nets']) == (1, 1, 5, 1)   # clock skipped


def test_placeholder_without_pins_is_flagged_box_to_box():
    insts, buses, pt = _die()
    ph = FPL.die_pin_hops(insts, buses, pt, relay_kinds=('waypoint',))
    assert ph['box_to_box_nets'] == 1 and ph['box_to_box_over'] == 0 and ph['box_to_box_masters'] == {'hfd_placeholder': 1}
    # the same placeholder moved 1 mm away fails, and says it was measured box to box (a lower bound)
    insts[3].x = -1000.0
    ph = FPL.die_pin_hops(insts, buses, pt, relay_kinds=('waypoint',))
    h = next(h for h in ph['examples'] if h['net'] == 'r_ph')
    assert h['measure'].startswith('box-to-box') and h['um'] == 1160.0 and ph['box_to_box_over'] == 1


def test_all_hops_within_reach_pass():
    insts, buses, pt = _die()
    pins2 = lambda i, p: (1000.0, 600.0) if (i, p) == ('sm', 'r') else (1000.0, 1100.0) if (i, p) == ('sm', 'rst') else pt(i, p)
    buses = [b for b in buses if b[0] != 'rst_leaf'] + [('rst_leaf', 'reset_tree', 1, [('rr', 'o'), ('sm', 'rst')])]
    ph = FPL.die_pin_hops(insts, buses, pins2, relay_kinds=('waypoint',))
    assert ph['verdict'] == 'PASS' and ph['hops_over'] == 0 and ph['max_um'] == 0.0
