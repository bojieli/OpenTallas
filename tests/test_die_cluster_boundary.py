"""tools/die_cluster/boundary.py: no straddling bodies, ports ON the outline (track-legal, crossing point), fail closed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from die_cluster import boundary as CB  # noqa: E402

OL = [100.0, 100.0, 600.0, 400.0]


def body(name, x, y, w=20.0, h=20.0, m='rly'):
    return dict(name=name, master=m, x=x, y=y, w=w, h=h, orient='R0')


def test_straddle_snaps_inside_and_outside_without_overlap():
    bs = [body('in_ok', 200, 200), body('str_in', 590, 200),      # centre 600 is not < 600 -> outside
          body('str_in2', 585, 250), body('str_out', 85, 300, w=20), body('out_ok', 700, 200)]
    r = CB.resolve_bodies(OL, bs, 'snap', grid_um=0.216)
    assert r['errors'] == []
    assert r['straddling_after'] == 0
    names_in = {b['name'] for b in r['inside']}
    assert {'in_ok', 'str_in2'} <= names_in and 'out_ok' not in names_in
    for b in r['inside']:
        assert OL[0] <= b['x'] and b['x'] + b['w'] <= OL[2] + 1e-9 and OL[1] <= b['y'] and b['y'] + b['h'] <= OL[3]
    mv = {m['name']: m for m in r['moved']}
    assert mv['str_in2']['side'] == 'inside' and mv['str_in2']['to'][0] <= 580.0
    assert mv['str_out']['side'] == 'outside' and mv['str_out']['to'][0] + 20 <= 100.0 + 1e-9  # centre 95 -> outside


def test_snap_refuses_overlap_and_fail_policy():
    bs = [body('block', 570, 200, w=25), body('str', 590, 205)]
    r = CB.resolve_bodies(OL, bs, 'snap', grid_um=0.216)
    # block itself is inside (570..595); str (590..610, centre 600 = outside) -> moves out E without overlap
    assert r['straddling_after'] == 0 and not r['errors']
    bs2 = [body('wall', 560, 190, w=40, h=40), body('str', 590, 200)]  # centre 600 outside: out E is free
    r2 = CB.resolve_bodies(OL, bs2, 'snap')
    assert not r2['errors']
    bs3 = [body('wall', 565, 190, w=18, h=40), body('str', 588, 200)]   # centre 598 inside: plain clamp hits the wall
    r3 = CB.resolve_bodies(OL, bs3, 'snap')                                  # slides (or flips) instead
    assert not r3['errors'] and r3['straddling_after'] == 0
    m3 = r3['moved'][0]
    x, y = m3['to']
    assert not (565 - 20 < x < 583 and 190 - 20 < y < 230) and m3['dist_um'] <= 100
    bs5 = bs3 + [body('wall_e', 609, 150, w=40, h=120)]                     # no slide room, no flip room
    r5 = CB.resolve_bodies(OL, bs5, 'snap', search_um=0.0)
    assert [e['kind'] for e in r5['errors']] == ['snap_blocked']
    r6 = CB.resolve_bodies(OL, bs5, 'snap', max_move_um=1.0)                 # every free spot is too far -> refused
    assert [e['kind'] for e in r6['errors']] == ['snap_blocked']
    r4 = CB.resolve_bodies(OL, [body('s', 590, 200)], 'fail')
    assert r4['errors'][0]['kind'] == 'straddle'


def test_grow_policy_matches_legacy():
    r = CB.resolve_bodies(OL, [body('s', 585, 200)], 'grow')
    assert r['outline'][2] == 605.0 and not r['errors'] and r['straddling_after'] == 0


def test_pins_on_outline_at_crossing_on_tracks():
    ports = [dict(name='a', direction='output', inside=[[300, 300]], outside=[[300, 900]]),   # straight up -> N x=300
             dict(name='b', direction='input', inside=[[500, 250]], outside=[[900, 250]]),   # -> E y=250
             dict(name='c', direction='input', inside=[[120, 300]], outside=[])]             # no outside -> nearest W
    r = CB.assign_pins(OL, ports, [], 'NESW')
    assert r['errors'] == []
    p = {q['name']: q for q in r['pins']}
    W, H = 500.0, 300.0
    assert p['a']['edge'] == 'N' and p['a']['y'] == H and abs(p['a']['x'] - 200) < 0.1 and p['a']['layer'] in ('M5', 'M7')
    assert p['b']['edge'] == 'E' and p['b']['x'] == W and abs(p['b']['y'] - 150) < 0.1 and p['b']['layer'] in ('M4', 'M6')
    assert p['c']['edge'] == 'W' and p['c']['x'] == 0.0
    for q in r['pins']:
        off, pitch = CB.TRACKS[q['layer']]
        v = q['x'] if q['layer'] in CB.VERTICAL else q['y']
        assert abs((v - off) / pitch - round((v - off) / pitch)) < 1e-6


def test_pins_spread_without_clash_and_density_gate():
    ports = [dict(name=f'p{i}', direction='input', inside=[[300, 300]], outside=[[300, 900]]) for i in range(200)]
    r = CB.assign_pins(OL, ports, [], 'NESW', spacing_tracks=2)
    assert not r['errors']
    for layer in ('M5', 'M7'):                    # per layer, at least spacing_tracks tracks apart
        xs = sorted(q['x'] for q in r['pins'] if q['layer'] == layer)
        pitch = CB.TRACKS[layer][1]
        assert xs and all(b - a >= 2 * pitch - 1e-9 for a, b in zip(xs, xs[1:]))
    assert all(q['edge'] == 'N' for q in r['pins'])
    r2 = CB.assign_pins(OL, ports, [], 'NESW', max_density_per_um=0.1)
    assert any(e['kind'] == 'pin_density' for e in r2['errors'])
    many = [dict(name=f'q{i}', direction='input', inside=[[300, 300]], outside=[[300, 900]]) for i in range(12000)]
    r3 = CB.assign_pins(OL, many, [], 'NESW', spacing_tracks=2, max_density_per_um=100)
    assert any(e['kind'] == 'edge_capacity' for e in r3['errors'])


def test_pins_avoid_bodies_touching_edge_and_respect_allowed_edges():
    wall = body('flush', 250, 380, w=100, h=20)           # touches N edge over x 250..350
    ports = [dict(name='a', direction='input', inside=[[300, 300]], outside=[[300, 900]])]
    r = CB.assign_pins(OL, ports, [wall], 'NESW')
    x = r['pins'][0]['x'] + OL[0]
    assert not (249.5 <= x <= 350.5)
    r2 = CB.assign_pins(OL, [dict(name='w', direction='input', inside=[[110, 300]], outside=[[0, 300]])], [], 'NE')
    assert r2['pins'][0]['edge'] in 'NE'


def test_fixed_top_down_pins_validated():
    ok = dict(name='f', direction='input', at=[100 + 0.012 + 0.048 * 100, 100.0], layer='M5')
    bad = dict(name='g', direction='input', at=[300.001, 250.0], layer='M5')
    r = CB.assign_pins(OL, [ok, bad], [], 'NESW')
    kinds = [e for e in r['errors'] if e['kind'] == 'fixed_pin_illegal']
    assert len(kinds) == 1 and kinds[0]['name'] == 'g'


def test_lef_pins_and_orientation():
    lef = '''MACRO m
  SIZE 10 BY 4 ;
  PIN a[0]
    PORT
      LAYER M4 ;
        RECT 9.9 1 10 1.2 ;
    END
  END a[0]
END m
'''
    info = CB.parse_lef_pins(lef)
    assert info['m']['w'] == 10 and abs(info['m']['pins']['a[0]'][0] - 9.95) < 1e-9
    b = dict(master='m', x=100, y=50, w=10, h=4, orient='MY')
    x, y = CB.pin_xy(b, 'a[0]', info)
    assert abs(x - 100.05) < 1e-9 and abs(y - 51.1) < 1e-9
    assert CB.oriented_point(1, 1, 10, 4, 'R90') == (3, 1)


def test_pins_tcl_and_flow_fragments():
    r = CB.assign_pins(OL, [dict(name='a', direction='input', inside=[[300, 300]], outside=[[300, 900]])], [], 'NESW')
    t = CB.pins_tcl(r['pins'])
    assert 'place_pin -pin_name {a} -layer M5' in t and '-force_to_die_boundary' in t and 'place_pins' not in t
    fp = CB.floorplan_tcl(500, 300)
    assert '-core_area {1.080 1.080 498.920 298.920}' in fp
    assert 'exit 3' in CB.bounds_check_tcl() and 'detailed_placement' in CB.legalize_tcl()
    assert 'proc ot_cluster_bounds' in CB.bounds_tcl_path().read_text()


def test_clean_cut_moves_edge_off_a_relay_row():
    row = [body(f'r{i}', 200 + 21.6 * i, 390, w=21.6, h=20) for i in range(10)]   # row across the N edge y=400
    row.append(body('under', 200, 360, w=216, h=30))                               # blocks a slide below the row
    r = CB.resolve_bodies(OL, row, 'cut')
    assert not r['errors'] and r['straddling_after'] == 0 and not r['moved']
    assert r['cut_shifts'] == [dict(edge='N', frm=400.0, to=390.0)] and r['outline'][3] == 390.0  # nearest clean line
    assert [b['name'] for b in r['inside']] == ['under']


def test_snap_does_not_count_preexisting_parent_overlap():
    big = body('sm', 100, 300, w=300, h=90)                 # parent already overlaps the straddler (illegal parent)
    r = CB.resolve_bodies(OL, [big, body('rly', 200, 385, w=20, h=30)], 'snap', search_um=0.0)
    assert not r['errors'] and r['moved'][0]['preexisting_overlap'] == ['sm']
