"""explorer_render.py: die / type / record renders on a synthetic plan (no fleet data needed)."""
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import explorer_render as ER  # noqa: E402

RS_STUB = '''
import gzip, json, re
from pathlib import Path
REF_DIRS = []
_CONNS_SRC = {}
def read_json(p):
    p = Path(p)
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_text())
def orient_pt(h, x, y):
    w, hh = h["outline_um"]; o = h.get("orient", "R0")
    X = w - x if o in ("MY", "R180") else x
    Y = hh - y if o in ("MX", "R180") else y
    return h["origin_um"][0] + X, h["origin_um"][1] + Y
def core_pins(h, die_dir, repo):
    for d in REF_DIRS + [str(die_dir), str(repo)]:
        c = Path(d) / h["pins_file"]
        if c.is_file():
            return [(re.sub(r"\\[\\d+\\]$", "", p["name"]),) + orient_pt(h, p["x"], p["y"]) for p in read_json(c)["pins"]]
    return []
def load_conns(die_dir, path=None, plan_dir=None, ref_dirs=()):
    f = Path(plan_dir) / "core_conns.json"
    d = json.loads(f.read_text())
    for t in d:
        _CONNS_SRC[t] = str(f)
    return d
'''


def pins(names_bits, face_x):
    out = []
    for n, b in names_bits:
        for i in range(b):
            out.append(dict(name='%s[%d]' % (n, i), x=face_x, y=5.0 + i * 0.5))
    return dict(pins=out)


def make_plan(tmp):
    tmp = Path(tmp)
    (tmp / 'cores').mkdir()
    (tmp / 'cores' / 'a.json').write_text(json.dumps(pins([('d_o', 32), ('clk', 1)], 50.0)))
    (tmp / 'cores' / 'b.json').write_text(json.dumps(pins([('d_i', 32), ('q_o', 8)], 0.0)))
    hc = [dict(inst='u_top.u_a', module='ma', origin_um=[10, 10], outline_um=[50, 40], orient='R0', pins_file='cores/a.json'),
          dict(inst='u_top.u_b', module='mb', origin_um=[600, 10], outline_um=[50, 40], orient='MY', pins_file='cores/b.json')]
    t = dict(module='m_t', outline_um=[700, 200], hard_cores=hc,
             buses=[dict(name='x_o', dir='out', width=8, face='E', window_um=[20, 30])],
             ft_slots=[dict(name='ft0', in_face='W', out_face='E', width=16, in_window_um=[150, 151], out_window_um=[150, 151],
                            regs_um=[[350, 150]])],
             internal_stations=[], clock=dict(tap_um=[350, 100], taps=[dict(name='u_top.u_a.clk', xy=[12, 12])]))
    ft = dict(module='m_ft', outline_um=[700, 200], hard_cores=[],
              ft_slots=[dict(name='ft1', in_face='W', out_face='E', width=64, in_window_um=[100, 101], out_window_um=[100, 101],
                             regs_um=[[300, 100], [500, 100]])])
    P = dict(die=dict(name='testdie', label='test die', outline_um=[2100, 200], reach_um=405.0),
             partition_types=dict(T=t, F=ft),
             partitions=[dict(name='p0', type='T', origin_um=[0, 0], orient='R0'), dict(name='p1', type='F', origin_um=[700, 0], orient='R0'),
                         dict(name='p2', type='T', origin_um=[1400, 0], orient='MY')],
             ports=[dict(id='L0_0', src=dict(part='p0', bus='x_o'), dst=dict(part='p1', bus='ft1_i'), width=64, kind='data', face='E', window_um=[100, 101]),
                    dict(id='L0_1', src=dict(part='p1', bus='ft1_o'), dst=dict(part='p2', bus='x_i'), width=64, kind='data', face='E', window_um=[100, 101])],
             lanes=[dict(id='L0', ports=['L0_0', 'L0_1'], note='test', fixed_cycles=3)])
    (tmp / 'plan.json').write_text(json.dumps(P))
    (tmp / 'core_conns.json').write_text(json.dumps(dict(T={'u_top.u_a': {'d_o': ['core:u_top.u_b.d_i'], 'clk': ['tap:x']},
                                                            'u_top.u_b': {'d_i': ['core:u_top.u_a.d_o'], 'q_o': ['bus:x_o']}})))
    (tmp / 'rs.py').write_text(RS_STUB)
    return tmp


def run(argv):
    ER.main(argv)


def test_die_view(tmp_path):
    d = make_plan(tmp_path)
    out = tmp_path / 'out'
    run(['die', '--plan', str(d / 'plan.json'), '--out', str(out), '--dpi', '60'])
    rec = ER.load_json(out / 'die_testdie.links.json.gz')
    assert rec['schema'] == 'opentallas.dataflow.links.v1'
    (l,) = rec['links']
    assert l['s'] == 2 and l['b'] == 64 and l['via'] == ['p1']
    assert l['L'] == 700.0 and l['mh'] == 300.0          # crossings clamp to the regs' y=100 inside windows [100, 101]
    assert l['x'] == 0                                    # its own ft partition is not a bypass
    for ext in ('png', 'svg', 'links.tsv'):
        assert (out / ('die_testdie.' + ext)).stat().st_size > 0
    rows = (out / 'die_testdie.links.tsv').read_text().splitlines()
    assert rows[0].startswith('worst_rank\tid') and rows[1].split('\t')[1] == 'L0'


def test_type_view_and_delta_formats(tmp_path):
    d = make_plan(tmp_path)
    out = tmp_path / 'out'
    base = ['type', '--plan', str(d / 'plan.json'), '--type', 'T', '--repo', str(d), '--route-supply', str(d / 'rs.py'),
            '--out', str(out), '--dpi', '60']
    run(base)
    rec = ER.load_json(out / 'type_T.links.json.gz')
    cc = [l for l in rec['links'] if l['c'] == 'core-core']
    assert len(cc) == 1 and cc[0]['b'] == 32 and cc[0]['d'] == 1       # both sides listed once; d_o drives d_i
    assert rec['blocks']['name'][cc[0]['e'][0][0]] == 'u_top.u_a'
    assert cc[0]['L'] > 405 and ER.classify(rec, cc[0]) == 2            # 550 um direct hop > reach: red
    cf = [l for l in rec['links'] if l['c'] == 'core-face']
    assert len(cf) == 1 and cf[0]['b'] == 8 and cf[0]['e'][1][0] == -1
    assert [l['s'] for l in rec['links'] if l['c'] == 'ft'] == [1]
    # three delta formats give the same after view
    deltas = {'cs.json': {'T': {'u_top.u_b': [300, 10, 'MY']}},
              'rs.json': {'partition_types': {'T': {'hard_cores': {'u_top.u_b': {'origin_um': [300, 10]}}}}},
              'rows.json': [{'type': 'T', 'inst': 'u_top.u_b', 'origin_um': [300, 10]}]}
    Ls = []
    for fn, D in deltas.items():
        (d / fn).write_text(json.dumps(D))
        run(base + ['--delta', str(d / fn), '--name', fn[:-5]])
        aft = ER.load_json(out / (fn[:-5] + '__after.links.json.gz'))
        Ls.append([l['L'] for l in aft['links'] if l['c'] == 'core-core'][0])
        assert (out / (fn[:-5] + '.png')).stat().st_size > 0
    assert Ls[0] == Ls[1] == Ls[2] and Ls[0] < cc[0]['L']


def test_split_ip_and_rank():
    idx = {'u_r0.u_e0.u_w': 0, 'u_r0': 1}
    assert ER.split_ip('u_r0.u_e0.u_w.perr', idx) == ('u_r0.u_e0.u_w', 'perr')
    assert ER.split_ip('u_r0.rs', idx) == ('u_r0', 'rs')
    r = ER.pipeline_rank(4, {0: {1}, 1: {2}, 2: {1, 3}}, {0})
    assert r[0] == 0 and r[1] == r[2] == 1 and r[3] == 2           # the 1<->2 loop shares one rank


def test_record_view(tmp_path):
    d = make_plan(tmp_path)
    run(['die', '--plan', str(d / 'plan.json'), '--out', str(tmp_path / 'a'), '--dpi', '60'])
    run(['record', '--record', str(tmp_path / 'a' / 'die_testdie.links.json.gz'), '--out', str(tmp_path / 'b'), '--dpi', '60'])
    assert (tmp_path / 'b' / 'die_testdie.png').stat().st_size > 0
