#!/usr/bin/env python3
"""Per-bit inter-child join screen + dataflow placement for the BANDED MIX4 copy cluster ot_s81_engram_mixq_b.

Same rule set as tools/s81_engram_mix/localized_candidate/timing.py (Codex frozen R0 screen, 248 negative joins):
  setup90 = 833.333 - 60 (setup unc.) - 90 (inter-root skew) - launch(O-R, actual TT ETM) - capture(S+R, actual TT ETM)
            - 0.76 ps/um * min L1 over the actual LEF terminal rectangles (optimistic wire, no detour)
  skew 150 ps instead of 90 when either actual root insertion R > 300 ps; FF reserve = lmin(FF) - hold(FF) - 100 ps.
Graph = Yosys elaboration of ot_s81_engram_mixq_b with every hardened child black-boxed (actual RTL headers).
Child views = the CLOSED leaf records (leaf_views.json, the same records Codex's frozen screen bound).
ot_s81_engram_mixq_shcol_b is the closed shcol ETM with the new master's planned pins (physical/s81_die_pins/
v21_engram_arithmetic/ot_s81_engram_mixq_shcol_b.tcl: VM side S, cluster side N) and two new registered outputs iv/ph whose
launch is ESTIMATED from the closed view's registered S-face outputs (max h/kv/w launch);
it is replaced by the re-closed view's ETM when that exists (--shcolb-record).
Cluster boundary pins (VM side: shell N faces) are screened against the nearest transport line (placement 'edges' x list:
the cluster E edge and the central station channel) with --edge-reach (horizontal distance).

  python3 tools/s81_engram_mix/banded/screen.py --out DIR [--place placement.json] [--anneal N] [--w W --h H]
"""
import argparse, collections, hashlib, json, math, random, re, subprocess, sys, tempfile
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(R / 'tools/hier_contract'))
import pinreg_audit as A  # noqa: E402

LEAFS = ['mul4', 'chunk8', 'add8', 'norm', 'sum', 'signed_sqrt', 'sigmoid', 'mix_control', 'rly', 'mixq_shcol_b', 'mixq_shctl']
SRC = ['rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv', 'rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_c.sv',
       'rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_banded.sv']
TOP = 'ot_s81_engram_mixq_b'
PERIOD, UNC, WIRE = 833.333, 60.0, .76
CLEAR = 21.6
SHCOLB_TCL = R / 'physical/s81_die_pins/v21_engram_arithmetic/ot_s81_engram_mixq_shcol_b.tcl'


def git_show(rec, path):
    return subprocess.check_output(['git', '-C', str(R), 'show', f'{rec}:{path}'])


def extract_graph(out):
    mods = {}
    for p in SRC:
        s = (R / p).read_text()
        for m in re.finditer(r'\bmodule\s+(\w+)\b.*?\bendmodule\b', s, re.S):
            mods[m[1]] = m[0]
    texts = []
    for n in LEAFS:
        hdr = mods['ot_s81_engram_' + n].split(';', 1)[0] + ';'
        texts.append('(* blackbox *) ' + hdr + '\nendmodule')
    texts += [mods[TOP], mods['ot_s81_engram_gate']]
    (out / 'graph_source.sv').write_text('\n'.join(texts))
    r = subprocess.run(['yosys', '-Q', '-T', '-p', f'read_verilog -sv {out}/graph_source.sv; hierarchy -check -top {TOP} '
                        f'-chparam VM_LAT 13; flatten; opt_expr; opt_clean; write_json {out}/cluster_graph.json'],
                       capture_output=True, text=True)
    (out / 'graph_extract.log').write_text(r.stdout + r.stderr)
    assert r.returncode == 0, r.stderr[-2000:]
    g = json.loads((out / 'cluster_graph.json').read_text())
    return g['modules'][TOP]


def load_views(views):
    pins, dims, metrics, prov = {}, {}, {}, {}
    for master, v in views.items():
        raw = git_show(v['record'], v['path'])
        assert hashlib.sha256(raw).hexdigest() == v['sha256'], master
        base = v['path'].rsplit('/', 1)[0]
        ins = json.loads(git_show(v['record'], base + '/insertion.json'))
        metrics[master], prov[master] = {}, {'record': v['record'], 'lef_sha256': v['sha256']}
        for corner in ('tt', 'ff'):
            lr = git_show(v['record'], f'{base}/{master}_{corner}.lib')
            with tempfile.TemporaryDirectory() as td:
                lp = Path(td) / 'c.lib'; lp.write_bytes(lr); lib = A.parse_lib(lp)
            refs = A.clock_refs(lib, ins, corner)
            metrics[master][corner] = A.pin_metrics(lib, refs)
            prov[master][corner] = {'lib_sha256': hashlib.sha256(lr).hexdigest(), 'clock_refs': refs}
        dims[master] = v['outline_um']; pins[master] = {}
        for m in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$', raw.decode(), re.M | re.S):
            sh = []
            for b in re.finditer(r'\bRECT\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)', m[2]):
                x0, y0, x1, y1 = map(float, b.groups()); sh.append(((x0 + x1) / 2, (y0 + y1) / 2))
            pins[master][m[1]] = sh
    if 'ot_s81_engram_mixq_shcol_b' not in views:
        # shcol_b = closed shcol + iv/ph (estimated launch: max registered S-face data launch of the closed view)
        sc = 'ot_s81_engram_mixq_shcol'; sb = 'ot_s81_engram_mixq_shcol_b'
        dims[sb] = dims[sc]; pins[sb] = {}
        for m in re.finditer(r'place_pin -pin_name \{(\S+)\} -layer \S+ -location \{([\d.]+) ([\d.]+)\}', SHCOLB_TCL.read_text()):
            pins[sb][m[1]] = [(float(m[2]), float(m[3]))]
        metrics[sb] = {}
        for corner in ('tt', 'ff'):
            m = dict(metrics[sc][corner]); outs = [v for k, v in m.items() if re.match(r'(h|kv|w)\[', k) and v['out'] is not None]
            est = dict(dir='output', out=max(o['out'] for o in outs), lmin=min(o['lmin'] for o in outs), inp=None, hold=None, comb=[],
                       clk=outs[0]['clk'])
            m['iv'] = est; m['ph'] = est; metrics[sb][corner] = m
        prov[sb] = dict(prov[sc], estimated_pins={'iv': 'launch = max closed shcol h/kv/w launch', 'ph': 'same'})

    return pins, dims, metrics, prov


def build_joins(cells, pins, metrics, prov):
    D, S = collections.defaultdict(list), collections.defaultdict(list)
    boundary = []
    for n, c in cells.items():
        for port, bits in c['connections'].items():
            if port in ('ck', 'clk', 'arst_n', 'rst'):
                continue
            for i, bit in enumerate(bits):
                pn = port if len(bits) == 1 else f'{port}[{i}]'
                if not isinstance(bit, int):
                    continue
                (D if c['port_directions'][port] == 'output' else S)[bit].append((n, pn))
    joins, consts = [], []
    for bit, tg in S.items():
        if bit not in D:
            boundary += tg; continue
        assert len(D[bit]) == 1
        src = D[bit][0]
        for t in tg:
            joins.append((src, t))
    driven_out = [d[0] for b, d in D.items() if b not in S]
    rows = []
    for src, dst in joins:
        sm, tm = cells[src[0]]['type'], cells[dst[0]]['type']
        at, bt = metrics[sm]['tt'].get(src[1]), metrics[tm]['tt'].get(dst[1])
        af, bf = metrics[sm]['ff'].get(src[1]), metrics[tm]['ff'].get(dst[1])
        if not at or not bt or at['out'] is None or bt['inp'] is None:
            consts.append((src, dst, bool(at and at['out'] is not None), bool(bt and bt['inp'] is not None)))
            continue
        sr = max(prov[sm]['tt']['clock_refs'][k]['rise'] for k in at['clk'])
        tr = max(prov[tm]['tt']['clock_refs'][k]['rise'] for k in bt['clk'])
        skew = 150 if max(sr, tr) > 300 else 90
        budget = PERIOD - UNC - skew - at['out'] - bt['inp']
        ff = af['lmin'] - bf['hold'] - 100 if af and bf and af['lmin'] is not None and bf['hold'] is not None else None
        rows.append(dict(src=src, dst=dst, sm=sm, tm=tm, launch=at['out'], capture=bt['inp'], skew=skew, budget=budget, ff=ff))
    return rows, consts, boundary


class Placer:
    def __init__(s, cells, dims, pins, rows, boundary, W, H, edge_reach, margin):
        s.names = sorted(cells); s.idx = {n: i for i, n in enumerate(s.names)}
        s.wh = np.array([dims[cells[n]['type']] for n in s.names], float); s.W, s.H = W, H
        s.margin = margin
        # one point per join (first terminal shape; leaf pins have one rectangle each)
        s.si = np.array([s.idx[r['src'][0]] for r in rows]); s.ti = np.array([s.idx[r['dst'][0]] for r in rows])
        s.so = np.array([pins[cells[r['src'][0]]['type']][r['src'][1]][0] for r in rows])
        s.to = np.array([pins[cells[r['dst'][0]]['type']][r['dst'][1]][0] for r in rows])
        s.budget = np.array([r['budget'] for r in rows])
        # boundary terminals of the shell (VM side) -> cluster E edge
        bt = [(n, p) for n, p in boundary if cells[n]['type'] in ('ot_s81_engram_mixq_shctl', 'ot_s81_engram_mixq_shcol_b')]
        s.bi = np.array([s.idx[n] for n, p in bt]); s.bo = np.array([pins[cells[n]['type']][p][0] for n, p in bt])
        s.edge_reach = edge_reach; s.blockages = []

    def slack(s, xy):
        a = xy[s.si] + s.so; b = xy[s.ti] + s.to
        return s.budget - WIRE * np.abs(a - b).sum(1)

    def edge(s, xy):
        if not len(s.bi):
            return np.zeros(0)
        p = xy[s.bi] + s.bo
        if getattr(s, 'edge_y', None) is not None:
            return s.edge_reach - np.abs(p[:, 1] - s.edge_y)
        ex = np.array(getattr(s, 'edge_x', [s.W]))
        return s.edge_reach - np.abs(p[:, :1] - ex[None, :]).min(1)

    def cost(s, xy):
        sl = s.slack(xy) - s.margin; e = s.edge(xy)
        return (1e3 * np.maximum(-sl, 0).sum() + 50 * np.maximum(-e, 0).sum() + .02 * (-sl).clip(-400, None).sum())

    def legal(s, xy, i):
        x, y = xy[i]; w, h = s.wh[i]
        if x < 0 or y < 0 or x + w > s.W + 1e-6 or y + h > s.H + 1e-6:
            return False
        for bx0, by0, bx1, by1 in s.blockages:
            if x < bx1 + CLEAR and bx0 < x + w + CLEAR and y < by1 + CLEAR and by0 < y + h + CLEAR:
                return False
        o = xy; dx = np.maximum(o[:, 0] - (x + w), x - (o[:, 0] + s.wh[:, 0])); dy = np.maximum(o[:, 1] - (y + h), y - (o[:, 1] + s.wh[:, 1]))
        bad = (dx < CLEAR - 1e-6) & (dy < CLEAR - 1e-6); bad[i] = False
        return not bad.any()

    def anneal(s, xy, steps, seed=1, t0=3000.0, frozen=()):
        rng = random.Random(seed); xy = xy.copy(); cur = s.cost(xy); best, bxy = cur, xy.copy()
        movable = [i for i, n in enumerate(s.names) if n not in frozen]
        for k in range(steps):
            T = t0 * (1 - k / steps) + 1
            i = rng.choice(movable); oi = xy[i].copy(); j = None
            if rng.random() < .15:
                j = rng.choice(movable)
                if j == i or (s.wh[i] != s.wh[j]).any():
                    continue
                oj = xy[j].copy(); xy[i], xy[j] = oj, oi
                ok = s.legal(xy, i) and s.legal(xy, j)
            else:
                r = max(2.0, 200 * (1 - k / steps))
                xy[i] = [round((oi[0] + rng.uniform(-r, r)) / .216) * .216, round((oi[1] + rng.uniform(-r, r)) / 1.08) * 1.08]
                ok = s.legal(xy, i)
            if ok:
                c = s.cost(xy)
                if c <= cur or rng.random() < math.exp(-(c - cur) / T):
                    cur = c
                    if c < best:
                        best, bxy = c, xy.copy()
                    continue
            xy[i] = oi
            if j is not None:
                xy[j] = oj
        return bxy, best


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, required=True); ap.add_argument('--place', type=Path)
    ap.add_argument('--anneal', type=int, default=0); ap.add_argument('--t0', type=float, default=3000.0); ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--w', type=float, default=1209.6); ap.add_argument('--h', type=float, default=885.6)
    ap.add_argument('--edge-reach', type=float, default=330.0); ap.add_argument('--margin', type=float, default=30.0)
    a = ap.parse_args(); O = a.out; O.mkdir(parents=True, exist_ok=True)
    top = extract_graph(O); cells = top['cells']
    views = json.loads((Path(__file__).parent / 'leaf_views.json').read_text())
    pins, dims, metrics, prov = load_views(views)
    rows, consts, boundary = build_joins(cells, pins, metrics, prov)
    for n, c in cells.items():
        for port, bits in c['connections'].items():
            pass
    pl = Placer(cells, dims, pins, rows, boundary, a.w, a.h, a.edge_reach, a.margin)
    P = json.loads(a.place.read_text()); place = P['placement']; pl.blockages = P.get('blockages', []); a.w, a.h = P.get('outline_um', [a.w, a.h]); pl.W, pl.H = a.w, a.h
    frozen = P.get('frozen', [])
    if 'outline_um' in P and 'timed_joins' in P:
        pl.edge_y = 0.0
    if P.get('edges'):
        pl.edge_x = P['edges']
    if P.get('edge_y') is not None:
        pl.edge_y = P['edge_y']
    xy = np.array([[place[n]['x'], place[n]['y']] for n in pl.names], float)
    rng0 = random.Random(a.seed)
    def relocate(i):
        x0 = xy[i].copy()
        for k in range(400000):          # nearest legal spot by expanding random search
            r = 5 + k * .01
            xy[i] = [round((x0[0] + rng0.uniform(-r, r)) / .216) * .216, round((x0[1] + rng0.uniform(-r, r)) / 1.08) * 1.08]
            if pl.legal(xy, i):
                return
        raise SystemExit(f'no legal start for {pl.names[i]}')
    order = sorted(range(len(pl.names)), key=lambda i: (pl.names[i] in frozen, -pl.wh[i, 0] * pl.wh[i, 1]))
    for _ in range(20):
        bad = [i for i in range(len(pl.names)) if not pl.legal(xy, i)]
        if not bad:
            break
        mov = [i for i in bad if pl.names[i] not in frozen]
        if not mov:
            raise SystemExit(f'illegal frozen start {[pl.names[i] for i in bad]}')
        relocate(min(mov, key=lambda i: pl.wh[i, 0] * pl.wh[i, 1]))
    if a.anneal:
        xy, c = pl.anneal(xy, a.anneal, a.seed, t0=a.t0, frozen=frozen)
    sl = pl.slack(xy); e = pl.edge(xy)
    groups = collections.defaultdict(lambda: dict(bits=0, neg=0, min_slack_ps=1e9))
    for r, v in zip(rows, sl):
        k = f"{r['src'][0]}.{r['src'][1].split('[')[0]} -> {r['dst'][0]}.{r['dst'][1].split('[')[0]}"
        g = groups[k]; g['bits'] += 1; g['neg'] += int(v < 0); g['min_slack_ps'] = min(g['min_slack_ps'], float(v))
    ffs = [r['ff'] for r in rows if r['ff'] is not None]
    placement = {n: dict(x=float(xy[i, 0]), y=float(xy[i, 1]), w=float(pl.wh[i, 0]), h=float(pl.wh[i, 1]), master=cells[n]['type'])
                 for i, n in enumerate(pl.names)}
    rep = dict(status='BANDED_CLUSTER_PERBIT_SCREEN', top=TOP, outline_um=[a.w, a.h], children=len(cells),
               timed_joins=len(rows), untimed_joins=len(consts),
               untimed_detail=sorted({f'{s[0]}.{s[1].split("[")[0]}->{t[0]}.{t[1].split("[")[0]} launch_arc={x} capture_arc={y}' for s, t, x, y in consts}),
               tt_negative_bits=int((sl < 0).sum()), min_tt_setup_ps=float(sl.min()), bits_below_margin=int((sl < a.margin).sum()),
               selected_150ps_bits=sum(r['skew'] == 150 for r in rows), ff_no_wire_reserve_min_ps=min(ffs),
               ff_reserve_fail_bits=sum(f < 0 for f in ffs), edge_terminals=len(e), edge_fail=int((e < 0).sum()),
               edge_worst_um=float(a.edge_reach - e.min()) if len(e) else None,
               rules=dict(period_ps=PERIOD, setup_uncertainty_ps=UNC, skew_ps='90; 150 if actual R>300', wire_ps_per_um=WIRE,
                          hold_reserve_ps=100, clearance_um=CLEAR, edge_reach_um=a.edge_reach),
               worst_groups=sorted(({'pair': k, **v} for k, v in groups.items()), key=lambda g: g['min_slack_ps'])[:40],
               view_provenance=prov, placement=placement, blockages=pl.blockages, frozen=frozen)
    (O / 'screen.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: rep[k] for k in ('timed_joins', 'untimed_joins', 'tt_negative_bits', 'min_tt_setup_ps', 'bits_below_margin',
                                          'ff_no_wire_reserve_min_ps', 'edge_fail', 'edge_worst_um')}, indent=1))
    plot(O / 'screen.json', O / 'placement.png')
    for g in rep['worst_groups'][:12]:
        print(f"{g['min_slack_ps']:8.1f} {g['neg']:4d}/{g['bits']:4d} {g['pair']}")



def plot(screen_json, png):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    d = json.loads(Path(screen_json).read_text()); W, H = d['outline_um']
    fig, ax = plt.subplots(figsize=(14, 14 * H / W + 1))
    col = {'mul4': '#9ecae1', 'chunk8': '#c6dbef', 'add8': '#fdae6b', 'mixq_shcol_b': '#a1d99b', 'mixq_shctl': '#31a354', 'sum': '#bcbddc',
           'norm': '#9e9ac8', 'mix_control': '#e377c2', 'rly': '#d62728', 'sigmoid': '#fdd0a2', 'signed_sqrt': '#fdd0a2'}
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for b in d.get('blockages', []):
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], facecolor='#eeeeee', edgecolor='grey', hatch='//', lw=.5))
    for n, b in d['placement'].items():
        m = b['master'].replace('ot_s81_engram_', '')
        ax.add_patch(Rectangle((b['x'], b['y']), b['w'], b['h'], facecolor=col.get(m, '#cccccc'), edgecolor='k', lw=.6))
        ax.text(b['x'] + b['w'] / 2, b['y'] + b['h'] / 2, n.replace('.leaf', '').replace('g_reduce', 'r').replace('g_chunk', 'c'),
                ha='center', va='center', fontsize=6)
    ax.set_xlim(-20, W + 20); ax.set_ylim(-20, H + 20); ax.set_aspect('equal')
    ax.set_title(f"ot_s81_engram_mixq_b {W:.2f} x {H:.2f} um: {d['timed_joins']} timed joins, TT-negative {d['tt_negative_bits']}, "
                 f"min {d['min_tt_setup_ps']:.1f} ps, FF reserve min {d['ff_no_wire_reserve_min_ps']:.1f} ps; hatched = station channel", fontsize=9)
    fig.tight_layout(); fig.savefig(png, dpi=110)


if __name__ == '__main__':
    main()
