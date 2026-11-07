"""gate_rehome planner on a small synthetic census."""
import json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
T = "I\t{n}\t{m}\t{k}\t{x}\t{y}\t{x1}\t{y1}\t{i}\t{o}\tPLACED\t0\n"
def inst(n, m, k, x, y, i='', o=''):
    return T.format(n=n, m=m, k=k, x=x, y=y, x1=x + 500, y1=y + 270, i=i, o=o)
def plan(rows, *extra):
    d = tempfile.mkdtemp(); c = os.path.join(d, 'c.tsv')
    open(c, 'w').write(''.join(rows) + 'C\t0\t0\t1000000\t1000000\n')
    r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'gate_rehome.py'), c, '--tcl', d + '/p.tcl', '--json', d + '/p.json', *extra], capture_output=True, text=True, check=True)
    return open(d + '/p.tcl').read(), json.load(open(d + '/p.json')), r.stdout
BASE = [inst('a', 'DFF', 'F', 100000, 100000, '', 'n1'), inst('b', 'DFF', 'F', 150000, 100000, 'n3', ''),
        inst('w1', 'BUF', 'B', 400000, 400000, 'n1', 'n2')]
def test_far_gate_and_its_single_fanout_buffer_move_back():
    tcl, j, out = plan(BASE + [inst('g', 'AND2', 'G', 800000, 800000, 'n2', 'n3')])
    assert j['gates'] == 1 and j['cells_moved'] == 2
    assert 'ot_rh {g} ' in tcl and 'ot_rh {w1} ' in tcl
    x, y = [int(v) for v in tcl.split('ot_rh {g} ')[1].split()[:2]]
    assert 100000 <= x <= 151000 and 100000 <= y <= 101000
def test_gate_inside_its_box_stays():
    tcl, j, out = plan(BASE + [inst('g', 'AND2', 'G', 120000, 100000, 'n2', 'n3')])
    assert j['gates'] == 0 and 'ot_rh {g}' not in tcl
def test_target_inside_macro_snaps_out():
    rows = [inst('a', 'DFF', 'F', 0, 500000, '', 'n1'), inst('b', 'DFF', 'F', 1000000 - 500, 500000, 'n2', ''),
            T.format(n='m', m='M', k='M', x=400000, y=0, x1=600000, y1=900000, i='', o=''),
            inst('g', 'AND2', 'G', 500000, 990000, 'n1', 'n2')]
    tcl, j, out = plan(rows)
    x, y = [int(v) for v in tcl.split('ot_rh {g} ')[1].split()[:2]]
    assert not (400000 <= x <= 600000 and y <= 900000)
