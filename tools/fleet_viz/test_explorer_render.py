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
    (tmp / 'cores' / 'a.json').write_text(json.dumps(pins([('d_o', 32), ('clk', 1), ('rs', 1)], 50.0)))
    (tmp / 'cores' / 'b.json').write_text(json.dumps(pins([('d_i', 32), ('q_o', 8), ('rs', 1)], 0.0)))
    hc = [dict(inst='u_top.u_a', module='ma', origin_um=[10, 10], outline_um=[50, 40], orient='R0', pins_file='cores/a.json'),
          dict(inst='u_top.u_b', module='mb', origin_um=[600, 10], outline_um=[50, 40], orient='MY', pins_file='cores/b.json')]
    t = dict(module='m_t', outline_um=[700, 200], hard_cores=hc,
             buses=[dict(name='x_o', dir='out', width=8, face='E', window_um=[20, 30])],
             ft_slots=[dict(name='ft0', in_face='W', out_face='E', width=16, in_window_um=[150, 151], out_window_um=[150, 151],
                            stations=2, regs_um=[[0, 150], [350, 150]]),
                       # hd_spn form: a station count, no regs_um / bit sites (kit spreads k-1 at L*j/k, station 0 at the in face)
                       dict(name='ft2', in_face='S', out_face='N', width=8, in_window_um=[400, 410], out_window_um=[400, 410], stations=4)],
             internal_stations=[], clock=dict(tap_um=[350, 100], taps=[dict(name='u_top.u_a.clk', xy=[12, 12])]))
    ft = dict(module='m_ft', outline_um=[700, 200], hard_cores=[],
              ft_slots=[dict(name='ft1', in_face='W', out_face='E', width=64, in_window_um=[100, 101], out_window_um=[100, 101],
                             stations=3, regs_um=[[0, 100], [300, 100], [500, 100]])])
    P = dict(die=dict(name='testdie', label='test die', outline_um=[2100, 200], reach_um=405.0),
             partition_types=dict(T=t, F=ft),
             partitions=[dict(name='p0', type='T', origin_um=[0, 0], orient='R0'), dict(name='p1', type='F', origin_um=[700, 0], orient='R0'),
                         dict(name='p2', type='T', origin_um=[1400, 0], orient='MY')],
             ports=[dict(id='L0_0', src=dict(part='p0', bus='x_o'), dst=dict(part='p1', bus='ft1_i'), width=64, kind='data', face='E', window_um=[100, 101]),
                    dict(id='L0_1', src=dict(part='p1', bus='ft1_o'), dst=dict(part='p2', bus='x_i'), width=64, kind='data', face='E', window_um=[100, 101])],
             lanes=[dict(id='L0', ports=['L0_0', 'L0_1'], note='test', fixed_cycles=3)])
    (tmp / 'plan.json').write_text(json.dumps(P))
    (tmp / 'core_conns.json').write_text(json.dumps(dict(T={'u_top.u_a': {'d_o': ['core:u_top.u_b.d_i'], 'clk': ['tap:x']},
                                                            'u_top.u_b': {'d_i': ['core:u_top.u_a.d_o'], 'q_o': ['bus:x_o'],
                                                                          'rs': ['core:u_top.u_a.rs']}})))
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
    assert l['s'] == 3 and l['b'] == 64 and l['via'] == ['p1']
    assert l['L'] == 700.0 and l['mh'] == 300.0          # crossings clamp to the regs' y=100 inside windows [100, 101]
    assert l['x'] == 0                                    # its own ft partition is not a bypass
    assert l['hs'] == ['reg'] * 3 and l['hp'] == ['p1'] * 3 and l['hk'] == ['pin', 'reg', 'reg', 'pin']
    assert ER.hop_verdict('pin', 'reg', 'reg', 500, 405)[0] == 'REAL'
    assert ER.hop_verdict('edge', 'reg', 'reg', 500, 405)[0] == 'MODEL'
    assert ER.hop_verdict('edge', 'reg', 'reg', 500, 405, lower=450)[0] == 'REAL'   # every edge point is over reach
    assert ER.minimax_cross((0, 0), [100, -500, 100, 500], (200, 2000)) > 1000   # a vertical edge cannot shorten a 2 mm run
    assert ER.seg_gap([0, 100, 0, 300], (50, 500)) == 250.0 and ER.seg_gap([0, 0, 10, 0], [20, 5, 30, 5]) == 15.0
    assert ER.hop_verdict('pin', 'pin', 'noslot', 900, 405)[0] == 'MODEL'
    run(['audit', '--record', str(out / 'die_testdie.links.json.gz'), '--out', str(out)])
    assert (out / 'die_testdie__hop_audit.tsv').exists()
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
    cc = [l for l in rec['links'] if l['c'] == 'core-core' and not l.get('stat')]
    rs = [l for l in rec['links'] if l.get('stat')]
    assert len(rs) == 1 and rs[0]['stat'] == 'reset' and ER.classify(rec, rs[0]) == 4   # reset fan-out: quasi-static
    tsv = (out / 'type_T.links.tsv').read_text().splitlines()
    assert tsv[-1].split('\t')[0] == '' and 'reset' in tsv[-1]                       # never ranked, listed last
    assert len(cc) == 1 and cc[0]['b'] == 32 and cc[0]['d'] == 1       # both sides listed once; d_o drives d_i
    assert rec['blocks']['name'][cc[0]['e'][0][0]] == 'u_top.u_a'
    assert cc[0]['L'] > 405 and ER.classify(rec, cc[0]) == 2            # 550 um direct hop > reach: red
    cf = [l for l in rec['links'] if l['c'] == 'core-face']
    assert len(cf) == 1 and cf[0]['b'] == 8 and cf[0]['e'][1][0] == -1
    fts = {l['i']: l for l in rec['links'] if l['c'] == 'ft'}
    assert fts['ft:ft0']['s'] == 2 and fts['ft:ft2']['s'] == 4 and abs(fts['ft:ft2']['mh'] - 50.0) < 0.5   # 200 um / 4 hops
    # three delta formats give the same after view
    deltas = {'cs.json': {'T': {'u_top.u_b': [300, 10, 'MY']}},
              'rs.json': {'partition_types': {'T': {'hard_cores': {'u_top.u_b': {'origin_um': [300, 10]}}}}},
              'rows.json': [{'type': 'T', 'inst': 'u_top.u_b', 'origin_um': [300, 10]}]}
    Ls = []
    for fn, D in deltas.items():
        (d / fn).write_text(json.dumps(D))
        run(base + ['--delta', str(d / fn), '--name', fn[:-5]])
        aft = ER.load_json(out / (fn[:-5] + '__after.links.json.gz'))
        Ls.append([l['L'] for l in aft['links'] if l['c'] == 'core-core' and not l.get('stat')][0])
        assert (out / (fn[:-5] + '.png')).stat().st_size > 0
    assert Ls[0] == Ls[1] == Ls[2] and Ls[0] < cc[0]['L']


def test_hd_spn_count_only_slots():
    # CPL-HEAD 11-11: HEAD hd_spn ft slots carry only `stations: 6` (no regs_um, no bit sites); the kit builds 6 stages
    # (face_flops.tcl: station 0 at the in face, j at L*j/k), so the 2073.6-um slot is 6 hops of 345.6 um, not one hop
    hu = dict(name='hu', in_face='S', out_face='N', width=276, stations=6, in_window_um=[314.408, 383.658],
              out_window_um=[314.408, 383.658])
    slots = [('replica', 2073.6, hu)]
    real = Path(__file__).resolve().parents[2] / 'physical/die_plan/s81_head/plan_of_record/l48hp1/source_plan.json.gz'
    if real.exists():
        t = json.load(gzip.open(real))['partition_types']['hd_spn']
        slots += [('l48hp1', t['outline_um'][1], f) for f in t['ft_slots']]
    for tag, H, f in slots:
        k, r, kd = ER.ft_slot_stages(f)
        assert (k, r, kd) == (int(f['stations']), None, 'spread'), tag
        a0, b0 = ER.face_pt(587.52, H, f['in_face'], f['in_window_um']), ER.face_pt(587.52, H, f['out_face'], f['out_window_um'])
        ch = [a0] + ER.spread_on(ER.slot_route(a0, b0, f['in_face'], f['out_face']), k) + [b0]
        hops = [abs(q[0] - p[0]) + abs(q[1] - p[1]) for p, q in zip(ch, ch[1:])]
        assert len(hops) == k and max(hops) < 405 and abs(sum(hops) - H) < 1e-6, (tag, hops)
    assert ER.ft_slot_stages(dict(stations=3, regs_um=[[0, 0], [1, 1], [2, 2]]))[1:] == ([(1, 1), (2, 2)], 'reg')
    assert ER.ft_slot_stages(dict(stations=2, bit_sites_um=[[[4, 4], [6, 6]]]))[1:] == ([(5.0, 5.0)], 'site')
    assert ER.ft_slot_stages(dict(stations=2), extra=1)[0] == 3                       # built_station_extra
    t = dict(internal_stations=[dict(conn='bus:a', bits=2, regs_um=[[0, 0]]), dict(conn='bus:a', bits=2, regs_um=[[0, 0], [10, 10]]),
                                dict(conn='bus:a', bits=6, regs_um=[[0, 0], [20, 30]]), dict(conn='u_x.o|u_y.i', regs_um=[[1, 1]])])
    m = ER.bus_station_entries(t)                    # kit_istations.bus_entries: one chain per bus, deepest, bits centroid
    assert len(m) == 2 and [e for e in m if e['conn'] == 'bus:a'][0]['regs_um'] == [[0.0, 0.0], [17.5, 25.0]]


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


if __name__ == '__main__':          # plain runner where pytest is not installed (fleet hosts)
    import inspect, tempfile
    for n, f in sorted((n, f) for n, f in globals().items() if n.startswith('test_') and callable(f)):
        with tempfile.TemporaryDirectory() as td:
            f(*([Path(td)] if inspect.signature(f).parameters else []))
        print('ok', n)
