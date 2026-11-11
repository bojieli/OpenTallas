#!/usr/bin/env python3
"""Headless Chip / Dataflow Explorer: the explorer's views as PNG + SVG + TSV, for lanes and subagents to inspect.

OWNER 11-11: the explorer is a tool for agents to look at, not a show piece.  This CLI renders without a browser.

Choice (EXPLORER-SCRIPT-1): the views are re-drawn in Python from the SAME link model the browser uses, not by driving
the page headless.  Every link is built and measured by dataflow_links.py (Builder: pin ends, hops, register stages,
Manhattan length, bit-um, flight-line crossings of unrelated blocks) and written as an opentallas.dataflow.links.v1
record, so the browser explorer can load the same record.  The drawing copies the floor view's encoding
(explorer/dataflow/floor.js + model.js): colour = reach verdict (green within reach, amber relayed / needs relay, red a
single hop beyond reach, grey unplaced), stroke width = min(5, 0.45 + 0.32 log2 bits), dashed = crosses an unrelated
block (bypass), dark die palette.  Reasons: no browser or playwright on the fleet; the page needs the live fleet-viz
server and its protected data dirs; the intra-type view does not exist in the page.

Sub-commands (all write <out>/<name>.png, .svg, .links.tsv and the links record <name>.links.json.gz + index.json):

  die     one die plan (die_plan.json schema: partitions + ports + lanes): partitions as type blocks, every lane as
          one link through its ports' face windows and the ft-slot stations of the partitions it passes.
  type    one partition type: hard cores (outline, orient, pins per face, pipeline rank), face windows, ft_slots,
          internal stations, clock taps; core-core and core-face links from core_conns (bit width = pin bits of the
          bus); --delta renders before | after side by side; --supply overlays route_supply ratio maps.
  record  any existing links record (e.g. explorer/dataflow/data/*.links.json.gz), the browser's floor view.

  python3 -I tools/fleet_viz/explorer_render.py type --plan P --type T --repo R [--delta D.json] [--supply] --out DIR
  python3 -I tools/fleet_viz/explorer_render.py die  --plan P --out DIR [--top 20]
  python3 -I tools/fleet_viz/explorer_render.py record --record R.links.json.gz --out DIR

See EXPLORER_RENDER.md.  ADVISORY: a picture and a table, never a gate.
"""
import argparse, collections, colorsys, copy, gzip, hashlib, json, math, os, re, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    import matplotlib  # noqa: F401
except ImportError:      # python3 -I drops the user site, where the fleet's numpy / matplotlib live: append it (after stdlib)
    import site
    sys.path.append(site.getusersitepackages())
import dataflow_links as DL  # noqa: E402

os.environ.setdefault('MPLCONFIGDIR', tempfile.gettempdir())
import matplotlib  # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection, PatchCollection  # noqa: E402
from matplotlib.patches import Rectangle, Polygon  # noqa: E402
import matplotlib.patheffects as PE  # noqa: E402

# ---------------------------------------------------------------- visual encoding (explorer/dataflow/model.js, floor.js)
STATUS = [('ok', 'within reach', '#3ccf7e'), ('relay', 'relayed / needs relay', '#f2b134'),
          ('over', 'hop beyond reach', '#ff5c5c'), ('unknown', 'unplaced', '#6b7894'),
          ('static', 'quasi-static: reset / strap / dead (not ranked)', '#7c6fd6')]
BYPASS = '#c58cff'
BG, DIE, DIE_EDGE, BLOCK, BLOCK_EDGE, LABEL, INK = '#05070d', '#070b16', '#2a3558', '#131c30', '#26324f', '#8a97b8', '#dfe5f5'
FACE_IN, FACE_OUT, REG, TAP, MOVED = '#5ad1ff', '#ff9f43', '#e6e9f2', '#ffd166', '#ff6bd6'
CONTROL_PORT = re.compile(r'^(clk|ck|clock|clk_pair|cr|cr_s|scan\w*|tap\w*|vdd\w*|vss\w*)$', re.I)   # clock tree: not drawn
# quasi-static classes (drawn, flagged 'static', never ranked as timing-critical):
#   reset  reset release / reset fan-out ports (gen_phys: set_false_path from arst_n; the synchronous release is a
#          reset tree with its own recovery check, not a data word)
#   strap  plan-declared ID / count straps (type id_straps / count_straps, hard_cores[].parent_id_straps:
#          straps.py set_false_path -from the strap ports)
#   dead   plan dead_inputs (module ports tied by proof)
RESET_PORT = re.compile(r'^(rs|rs_\w+|rst\w*|arst\w*|rsync\w*|reset\w*|\w*_rst|\w*_rst_n|\w*_rstn|rst_n\w*)$', re.I)
STATIC_COLOR = '#7c6fd6'


def stroke_px(bits, scale=0.7):
    """floor.js strokePx: log, capped, times the user scale (0.7 default)"""
    b = bits if isinstance(bits, (int, float)) and bits and bits > 0 else 1
    return scale * min(5.0, 0.45 + 0.32 * math.log2(max(1, b)))


def classify(rec, l):
    """model.js classify: 0 ok, 1 relay, 2 over, 3 unknown; 4 = quasi-static (reset / strap / dead input)"""
    if l.get('stat'):
        return 4
    reach = rec.get('reach_um') or 500.0
    L, mh = l.get('L'), l.get('mh')
    if L is None and mh is None:
        return 3
    hop = mh if mh is not None else L
    if rec.get('stages_explicit'):
        if hop > reach:
            return 2
        return 1 if (l.get('s') or 0) > 0 else 0
    return 1 if (L if L is not None else hop) > reach else 0


def segs_of(l):
    if l.get('h'):
        return [(h[0], h[1], h[2], h[3]) for h in l['h'] if None not in h[:4]]
    e = l['e']
    if not e or e[0][2] is None:
        return []
    return [(e[0][2], e[0][3], x[2], x[3]) for x in e[1:] if x[2] is not None]


def worst_key(rec, l):
    st = classify(rec, l)
    hop = l.get('mh') if l.get('mh') is not None else (l.get('L') or 0)
    if st == 4:
        return (False, -1.0, False, 0)
    return (st == 2, (l.get('b') or 1) * hop, (l.get('x') or 0) > 0, l.get('bu') or 0)


def load_json(p):
    return DL.load_json(p)


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------------------------------------------------------------- generic record drawing
def _px2pt(fig):
    return 72.0 / fig.dpi


def draw_record(ax, rec, opts):
    """the floor view of one links record on a matplotlib axis (µm, y up); returns the highlighted link ids"""
    fig = ax.figure
    k = _px2pt(fig) * opts.get('wmul', 1.6)
    W, H = rec['outline'][:2]
    ax.set_facecolor(BG)
    ax.add_patch(Rectangle((0, 0), W, H, facecolor=DIE, edgecolor=DIE_EDGE, lw=1.0, zorder=0))
    B = rec['blocks']
    nb = len(B['name'])
    fills = opts.get('block_fill') or {}
    rects = []
    cols = []
    for i in range(nb):
        if B['reg'][i] and not opts.get('show_regs'):
            continue
        rects.append(Rectangle((B['x'][i], B['y'][i]), B['w'][i], B['h'][i]))
        cols.append(fills.get(i, BLOCK))
    ax.add_collection(PatchCollection(rects, facecolor=cols, edgecolor=opts.get('block_edge', BLOCK_EDGE),
                                      linewidth=0.6 * _px2pt(fig) * 2, zorder=1))
    for i, txt in (opts.get('block_labels') or {}).items():
        ax.text(B['x'][i] + B['w'][i] / 2, B['y'][i] + B['h'][i] / 2, txt, color=LABEL, fontsize=opts.get('label_fs', 5),
                ha='center', va='center', zorder=6, clip_on=True)
    links = rec['links']
    worst = sorted(range(len(links)), key=lambda i: worst_key(rec, links[i]), reverse=True)[:opts.get('top', 15)]
    worst = [i for i in worst if links[i].get('L') and not links[i].get('stat')]
    wset = set(worst)
    groups = collections.defaultdict(list)
    for i, l in enumerate(links):
        st = classify(rec, l)
        byp = bool(l.get('x'))
        w = round(stroke_px(l.get('b')) * k, 2)
        if st == 4:
            w = round(min(w, 0.8 * k), 2)
            byp = 'static'
        for s in segs_of(l):
            groups[(st, byp, w)].append([(s[0], s[1]), (s[2], s[3])])
    # wide first so thin links stay visible on top
    for (st, byp, w), ss in sorted(groups.items(), key=lambda kv: -kv[0][2]):
        ax.add_collection(LineCollection(ss, colors=STATUS[st][2], linewidths=w,
                                         linestyles=(0, (1, 2)) if byp == 'static' else (0, (4, 3)) if byp else 'solid',
                                         alpha=0.6 if byp == 'static' else 0.9, zorder=2.8 if byp == 'static' else 3, capstyle='round'))
    # direction: arrow heads on directed links (all when few, else the highlighted ones)
    many = len(links) > opts.get('arrows_max', 400)
    for i, l in enumerate(links):
        if not l.get('d') or (many and i not in wset):
            continue
        ss = segs_of(l)
        if not ss:
            continue
        for s in (ss[-1:] if l.get('h') else ss):
            if abs(s[2] - s[0]) + abs(s[3] - s[1]) < 1e-6:
                continue
            ax.annotate('', xy=(s[2], s[3]), xytext=(s[0] + 0.82 * (s[2] - s[0]), s[1] + 0.82 * (s[3] - s[1])),
                        arrowprops=dict(arrowstyle='-|>', color=STATUS[classify(rec, l)][2], lw=0.5,
                                        mutation_scale=opts.get('arrow_ms', 6)), zorder=4)
    # stations / registers on hop chains
    if opts.get('show_hop_regs', True):
        xs, ys = [], []
        for l in links:
            h = l.get('h') or []
            for a in h[1:]:
                xs.append(a[0]); ys.append(a[1])
        if xs:
            ax.scatter(xs, ys, s=opts.get('reg_s', 2.5), c=REG, marker='s', linewidths=0, zorder=5, alpha=0.8)
    # worst links: white halo + rank label
    for r, i in enumerate(worst, 1):
        l = links[i]
        ss = segs_of(l)
        if not ss:
            continue
        w = stroke_px(l.get('b')) * k
        ax.add_collection(LineCollection([[(s[0], s[1]), (s[2], s[3])] for s in ss], colors='#ffffff',
                                         linewidths=w + 2.2 * k, alpha=0.35, zorder=2.9))
        mid = max(ss, key=lambda s: abs(s[2] - s[0]) + abs(s[3] - s[1]))
        ax.text((mid[0] + mid[2]) / 2, (mid[1] + mid[3]) / 2, '#%d' % r, color='#ffffff', fontsize=opts.get('rank_fs', 6),
                fontweight='bold', ha='center', va='center', zorder=7,
                path_effects=[PE.withStroke(linewidth=1.6, foreground='#000000')])
    ax.set_xlim(-0.02 * W, W * 1.02)
    ax.set_ylim(-0.02 * H, H * 1.02)
    ax.set_aspect('equal')
    ax.tick_params(colors=LABEL, labelsize=6)
    for sp in ax.spines.values():
        sp.set_color(DIE_EDGE)
    return [links[i]['i'] for i in worst], worst


def legend(fig, rec, extra=()):
    k = _px2pt(fig) * 1.6
    hs = []
    from matplotlib.lines import Line2D
    for sid, lab, col in STATUS:
        hs.append(Line2D([], [], color=col, lw=2, label=lab))
    hs.append(Line2D([], [], color=BYPASS if False else '#bbbbbb', lw=1.5, ls=(0, (4, 3)), label='dashed: crosses an unrelated block'))
    for b in (1, 64, 1024, 16384):
        hs.append(Line2D([], [], color='#9aa6c4', lw=stroke_px(b) * k, label='%s bit' % format(b, ',')))
    hs.append(Line2D([], [], color=REG, marker='s', ls='', ms=3, label='register stage / station'))
    for h in extra:
        hs.append(h)
    ncol = max(2, min(7, int(fig.get_figwidth() / 2.4)))
    lg = fig.legend(handles=hs, loc='lower center', ncol=ncol, fontsize=7, frameon=False, labelcolor=INK)
    return lg


def save(fig, out, name):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / (name + '.png'), facecolor=BG)
    fig.savefig(out / (name + '.svg'), facecolor=BG)
    plt.close(fig)
    return out / (name + '.png'), out / (name + '.svg')


def links_tsv(rec, path, worst_idx, extra_cols=None):
    B = rec['blocks']
    nm = lambda b: B['name'][b] if b is not None and b >= 0 else ''  # noqa: E731
    rank = {i: r for r, i in enumerate(worst_idx, 1)}
    order = sorted(range(len(rec['links'])), key=lambda i: worst_key(rec, rec['links'][i]), reverse=True)
    cols = ['worst_rank', 'id', 'class', 'bits', 'directed', 'driver', 'sinks', 'stages', 'length_um', 'max_hop_um',
            'bit_mm', 'status', 'static', 'bypass_n', 'bypassed', 'note'] + list((extra_cols or {}).keys())
    with open(path, 'w') as f:
        f.write('\t'.join(cols) + '\n')
        for i in order:
            l = rec['links'][i]
            e = l['e']
            drv = '%s.%s' % (nm(e[0][0]), e[0][1]) if e else ''
            sinks = ','.join('%s.%s' % (nm(x[0]), x[1]) for x in e[1:])
            row = [rank.get(i, ''), l['i'], l.get('c'), l.get('b'), l.get('d'), drv, sinks[:2000], l.get('s'), l.get('L'),
                   l.get('mh'), round((l.get('bu') or 0) / 1000, 1), STATUS[classify(rec, l)][0], l.get('stat'), l.get('x'),
                   ','.join(nm(b) for b in (l.get('xb') or [])), (l.get('n') or '').replace('\t', ' ')[:300]]
            for c, fn in (extra_cols or {}).items():
                row.append(fn(l))
            f.write('\t'.join('' if v is None else str(v) for v in row) + '\n')


def write_record(out, rid, meta, blocks, links, inputs):
    a = argparse.Namespace(candidate_of=None)
    DL.write(out, rid, meta, blocks, links, inputs, a)
    return load_json(Path(out) / (rid + '.links.json.gz'))


def summary(rec, links=None):
    links = rec['links'] if links is None else links
    reach = rec.get('reach_um') or 500
    st = collections.Counter(classify(rec, l) for l in links)
    return dict(links=len(links), bit_mm=round(sum((l.get('bu') or 0) for l in links) / 1000, 1),
                over=st[2], relayed=st[1], static=st[4], bypass=sum(1 for l in links if l.get('x') and not l.get('stat')),
                max_hop=max([l.get('mh') or l.get('L') or 0 for l in links] or [0]),
                over_reach_bits=sum(l.get('b') or 0 for l in links if not l.get('stat') and (l.get('mh') if l.get('mh') is not None else (l.get('L') or 0)) > reach))


def summary_text(s, sep=', '):
    return ('%(links)d links, %(bit_mm).1f bit-mm, max hop %(max_hop).0f um' % s + sep +
            '%(over)d hop>reach, %(relayed)d relayed, %(bypass)d cross unrelated blocks' % s +
            (', %(static)d quasi-static (not ranked)' % s if s.get('static') else ''))


# ---------------------------------------------------------------- plan helpers
def orient_rect(w, h, o):
    return (h, w) if o in ('R90', 'R270', 'MXR90', 'MYR90') else (w, h)


def orient_xy(o, w, h, x, y):
    """type-frame point -> placed frame offset (route_supply.orient_pt convention)"""
    X = w - x if o in ('MY', 'R180') else x
    Y = h - y if o in ('MX', 'R180') else y
    return X, Y


def face_pt(W, H, face, win):
    m = (win[0] + win[1]) / 2 if win else None
    if face == 'W':
        return (0.0, m if m is not None else H / 2)
    if face == 'E':
        return (W, m if m is not None else H / 2)
    if face == 'S':
        return (m if m is not None else W / 2, 0.0)
    return (m if m is not None else W / 2, H)


# ================================================================ DIE VIEW
def ft_slot_stages(f, extra=0):
    """an ft slot's stations the way the kit builds them (gen_rtl: a chain of `stations` ot_dp_st, default 1, plus the
    plan's built_station_extra; face_flops.tcl: station 0 is the in-port face flop, station j = 1..k-1 sits at
    regs_um[j] when regs_um has >= k sites, else at the bit_sites_um stage j-1 (stations-1 internal stages, centroid
    here), else at L*j/k along the slot route; the out port is not registered (the neighbour's station 0 is)).
    Returns (k, interior sites in the type frame or None = spread along the route, provenance reg/site/spread/none)."""
    k = int(f.get('stations', 1) if f.get('stations') is not None else 1) + int(extra or 0)
    if k <= 0:
        return 0, [], 'none'
    regs = [tuple(r[:2]) for r in f.get('regs_um') or []]
    if len(regs) >= k:
        return k, regs[1:k], 'reg'
    out = []
    for site in f.get('bit_sites_um') or []:
        pts = [q for q in site if isinstance(q, (list, tuple)) and len(q) >= 2 and isinstance(q[0], (int, float))]
        if pts:
            out.append((sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts)))
    if out and len(out) == k - 1:
        return k, out, 'site'
    return k, None, 'spread'


def slot_route(a, b, fin, fout):
    """face_flops.tcl ff_zroute: Z through the midpoint for a straight slot, L for a turning one"""
    if fin in ('N', 'S') and fout in ('N', 'S'):
        ym = (a[1] + b[1]) / 2
        return [a, (a[0], ym), (b[0], ym), b]
    if fin in ('E', 'W') and fout in ('E', 'W'):
        xm = (a[0] + b[0]) / 2
        return [a, (xm, a[1]), (xm, b[1]), b]
    return [a, (a[0], b[1]), b] if fin in ('N', 'S') else [a, (b[0], a[1]), b]


def point_at(pts, d):
    for p, q in zip(pts, pts[1:]):
        L = abs(q[0] - p[0]) + abs(q[1] - p[1])
        if d <= L + 1e-9 and L > 0:
            t = d / L
            return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
        d -= L
    return pts[-1]


def spread_on(pts, k):
    """the k-1 interior stations at L*j/k along a polyline"""
    L = sum(abs(q[0] - p[0]) + abs(q[1] - p[1]) for p, q in zip(pts, pts[1:]))
    return [point_at(pts, L * j / k) for j in range(1, k)]


def station_extra(P, tn):
    """schema.built_station_extra: stations already built beyond ft_slots[].stations, {slot: n}"""
    return dict(((P.get('built_station_extra') or {}).get(tn) or {}))


def bus_station_entries(t):
    """kit_istations.bus_entries: one station chain per bus conn.  Several entries on one bus (capture groups) merge
    to the deepest depth, stage j at the bits-weighted centroid of the deepest entries; bit_route / exact-site entries
    stay as written; core<->core entries stay one per entry"""
    by, out = collections.OrderedDict(), []
    for e in t.get('internal_stations') or []:
        if (e.get('conn') or '').startswith('bus:'):
            by.setdefault(e['conn'], []).append(e)
        else:
            out.append(e)
    for conn, es in by.items():
        if len(es) == 1 or any(e.get('bit_route') or 'bit_sites_um' in e or 'face_bit_sites_um' in e for e in es):
            out.extend(es)
            continue
        n = max(len(e.get('regs_um') or []) for e in es)
        deep = [e for e in es if len(e.get('regs_um') or []) == n]
        w = sum(int(e.get('bits', 1)) for e in deep) or 1
        regs = [[sum(e['regs_um'][j][c] * int(e.get('bits', 1)) for e in deep) / w for c in (0, 1)] for j in range(n)]
        out.append(dict(deep[0], regs_um=regs, bits=sum(int(e.get('bits', 1)) for e in es), merged_entries=len(es)))
    return out


def build_die(P, reach=None):
    T = P['partition_types']
    B = DL.Builder()
    parts = {}
    for p in P['partitions']:
        t = T.get(p['type']) or {}
        if not t.get('outline_um'):
            continue
        o = p.get('orient', 'R0')
        w, h = orient_rect(*t['outline_um'][:2], o)
        parts[p['name']] = (p, w, h, B.block(p['name'], p['type'], 'partition', p['name'], p['origin_um'][0], p['origin_um'][1], w, h))
    ports = {q['id']: q for q in P.get('ports') or []}

    def to_die(pn, xy):
        p, w, h, _ = parts[pn]
        tw, th = (T[p['type']]['outline_um'])[:2]
        X, Y = orient_xy(p.get('orient', 'R0'), tw, th, xy[0], xy[1])
        return (p['origin_um'][0] + X, p['origin_um'][1] + Y)

    def tbus_seg(pn, bus):
        """the plan type's own bus window (face + window_um, type frame) as a die-frame segment"""
        if pn not in parts or not bus:
            return None
        p, w, h, _ = parts[pn]
        tw, th = T[p['type']]['outline_um'][:2]
        for b in T[p['type']].get('buses') or []:
            if b.get('name') == bus and b.get('window_um') and b.get('face') in ('N', 'S', 'E', 'W'):
                lo, hi = b['window_um'][:2]
                f = b['face']
                a_, b_ = {'W': ((0, lo), (0, hi)), 'E': ((tw, lo), (tw, hi)), 'S': ((lo, 0), (hi, 0)), 'N': ((lo, th), (hi, th))}[f]
                return to_die(pn, a_), to_die(pn, b_)
        return None

    def face_seg(pn, face, win):
        p, w, h, _ = parts[pn]
        tw, th = T[p['type']]['outline_um'][:2]
        lo, hi = win[:2]
        a_, b_ = {'W': ((0, lo), (0, hi)), 'E': ((tw, lo), (tw, hi)), 'S': ((lo, 0), (hi, 0)), 'N': ((lo, th), (hi, th))}[face]
        return to_die(pn, a_), to_die(pn, b_)

    def slot_seg(pn, bus, side):
        """the ft slot's own in / out window (in_face + in_window_um, type frame) as a die-frame segment: where the
        kit puts that partition's pin and, on the in side, its station 0 (face_flops.tcl)"""
        if pn not in parts or not bus:
            return None
        base = re.sub(r'_(i|o|in|out)$', '', bus)
        for f in T[parts[pn][0]['type']].get('ft_slots') or []:
            if f.get('name') == base and f.get(side + '_window_um') and f.get(side + '_face') in ('N', 'S', 'E', 'W'):
                return face_seg(pn, f[side + '_face'], f[side + '_window_um'])
        return None

    def crossing(q):
        """die-frame segment where the port crosses src -> dst, and its provenance:
        pin  = the port's own face window (exact);  slot = the ft slot's in/out window (exact: the kit's pin and
        station 0);  tbus = the src (else dst) type bus window of that bus name (exact);
        edge = the shared edge of two abutting partitions (stand-in);  box = the src outline point nearest dst"""
        s_, t_ = parts.get(q['src']['part']), parts.get(q['dst']['part'])
        if not s_:
            return None, None
        p, w, h, bi = s_
        x0, y0 = p['origin_um']
        if q.get('window_um') and q.get('face') in ('N', 'S', 'E', 'W'):
            lo, hi = min(q['window_um'][:2]), max(q['window_um'][:2])
            f = q['face']
            if f in 'EW':
                x = x0 + (w if f == 'E' else 0)
                return ((x, lo), (x, hi)), 'pin'
            y = y0 + (h if f == 'N' else 0)
            return ((lo, y), (hi, y)), 'pin'
        si = slot_seg(q['dst']['part'], q['dst'].get('bus'), 'in')      # dst slot in window: its station 0 sits here
        so = slot_seg(q['src']['part'], q['src'].get('bus'), 'out')
        if si and so:            # both sides name a window: their overlap (they abut), else the station-0 side
            ov = [(max(min(si[0][d], si[1][d]), min(so[0][d], so[1][d])), min(max(si[0][d], si[1][d]), max(so[0][d], so[1][d]))) for d in (0, 1)]
            if all(a_ <= b_ + 0.01 for a_, b_ in ov):
                return ((ov[0][0], ov[1][0]), (ov[0][1], ov[1][1])), 'slot'
            return si, 'slot'
        if si or so:
            return si or so, 'slot'
        sg = tbus_seg(q['src']['part'], q['src'].get('bus')) or tbus_seg(q['dst']['part'], q['dst'].get('bus'))
        if sg:
            return sg, 'tbus'
        if not t_:
            return None, None
        a = (x0, y0, x0 + w, y0 + h)
        tp, tw, th, ti = t_
        b = (tp['origin_um'][0], tp['origin_um'][1], tp['origin_um'][0] + tw, tp['origin_um'][1] + th)
        ox0, ox1, oy0, oy1 = max(a[0], b[0]), min(a[2], b[2]), max(a[1], b[1]), min(a[3], b[3])
        if (abs(a[2] - b[0]) < 0.01 or abs(a[0] - b[2]) < 0.01) and oy1 >= oy0:
            x = a[2] if abs(a[2] - b[0]) < 0.01 else a[0]
            return ((x, oy0), (x, oy1)), 'edge'
        if (abs(a[3] - b[1]) < 0.01 or abs(a[1] - b[3]) < 0.01) and ox1 >= ox0:
            y = a[3] if abs(a[3] - b[1]) < 0.01 else a[1]
            return ((ox0, y), (ox1, y)), 'edge'
        c = B.clip(bi, B.centre(ti))
        return (c, c), 'box'

    def t_name(pn):
        return parts[pn][0]['type']

    def ft_regs(pn, bus):
        """(regs in die frame | station count | None, provenance): reg = plan regs_um, site = bit_sites_um centroids,
        spread = a station count without sites, none = the slot has no stations, noslot = no ft slot of that name"""
        if pn not in parts:
            return None, 'nopart'
        t = T[parts[pn][0]['type']]
        base = re.sub(r'_(i|o|in|out)$', '', bus or '')
        for f in t.get('ft_slots') or []:
            if f.get('name') == base:
                k, r, kd = ft_slot_stages(f, station_extra(P, t_name(pn)).get(f['name']))
                if r is None:
                    return (k, 'spread')        # k stages: station 0 at the in crossing, k-1 spread to the out crossing
                return [to_die(pn, x) for x in r], kd
        return None, 'noslot'

    via_of = {}
    for lane in P.get('lanes') or []:
        qs = [ports[i] for i in lane.get('ports', []) if i in ports]
        qs = [q for q in qs if q['src']['part'] in parts and q['dst']['part'] in parts]
        if not qs:
            continue
        cr = [crossing(q) for q in qs]
        keep = [k for k, c in enumerate(cr) if c[0] is not None]
        if not keep:
            continue
        qs = [qs[k] for k in keep]
        segw = [cr[k][0] for k in keep]
        pts = [((g[0][0] + g[1][0]) / 2, (g[0][1] + g[1][1]) / 2) for g in segw]
        pkind = [cr[k][1] for k in keep]
        stages, known, via, segs_regs, spread, skind = 0, True, [], [], [], []
        for k in range(len(qs) - 1):
            pn = qs[k]['dst']['part']
            via.append(pn)
            regs, kd = ft_regs(pn, qs[k]['dst']['bus'])
            if qs[k + 1]['src']['part'] != pn:
                kd = 'break'          # the next port does not leave the partition this one entered
            skind.append(kd)
            if regs is None:
                known = False
                regs = []
            if isinstance(regs, int):     # the slot names a station count but no sites: k-1 spread evenly
                spread.append(k)
                stages += regs
                segs_regs.append(regs - 1)
                continue
            # station 0 is the in-face flop at the in crossing (kit face_flops.tcl), then the k-1 interior sites
            stages += len(regs) + (1 if kd in ('reg', 'site') else 0)
            segs_regs.append(regs)
        # a wide window (or shared edge) carries the bus bits spread along it: each crossing sits at the point of its
        # window that minimises the longer of its two hops (else the projection of its one neighbour): a best case /
        # lower bound on the hops, never the window centre
        for k in range(len(qs)):
            g = segw[k]
            nb = []
            if k > 0 and isinstance(segs_regs[k - 1], list):
                nb.append(segs_regs[k - 1][-1] if segs_regs[k - 1] else pts[k - 1])
            if k < len(qs) - 1 and isinstance(segs_regs[k], list):
                nb.append(segs_regs[k][0] if segs_regs[k] else pts[k + 1])
            if not nb:
                continue
            if len(nb) == 2:      # best case: the window point that minimises the longer of its two hops
                best = None
                for i in range(201):
                    c = (g[0][0] + (g[1][0] - g[0][0]) * i / 200, g[0][1] + (g[1][1] - g[0][1]) * i / 200)
                    v = max(abs(nb[0][0] - c[0]) + abs(nb[0][1] - c[1]), abs(nb[1][0] - c[0]) + abs(nb[1][1] - c[1]))
                    if best is None or v < best[0] - 1e-9:
                        best = (v, c)
                pts[k] = best[1]
                continue
            mx, my = sum(x[0] for x in nb) / len(nb), sum(x[1] for x in nb) / len(nb)
            pts[k] = (min(max(mx, min(g[0][0], g[1][0])), max(g[0][0], g[1][0])),
                      min(max(my, min(g[0][1], g[1][1])), max(g[0][1], g[1][1])))
        hops, chain = [], [pts[0]]
        hk = [pkind[0]]          # provenance per chain point
        sg = lambda k: [round(v, 1) for v in (segw[k][0][0], segw[k][0][1], segw[k][1][0], segw[k][1][1])]
        hg = [sg(0)]             # per chain point: the crossing's window / edge segment (None for a station)
        hp, hs = [], []          # per hop: the partition it runs in, the provenance of that partition's stations
        for k in range(len(qs) - 1):
            sr = segs_regs[k]
            if isinstance(sr, int):
                a_, b_ = pts[k], pts[k + 1]
                sr = [(a_[0] + (b_[0] - a_[0]) * j / (sr + 1), a_[1] + (b_[1] - a_[1]) * j / (sr + 1)) for j in range(1, sr + 1)]
            elif len(sr) > 1:
                d0 = abs(sr[0][0] - pts[k][0]) + abs(sr[0][1] - pts[k][1])
                d1 = abs(sr[-1][0] - pts[k][0]) + abs(sr[-1][1] - pts[k][1])
                if d0 > d1 + 1.0:
                    skind[k] = skind[k] + '+reversed'     # sites listed out->in relative to this lane's entry
            chain += sr + [pts[k + 1]]
            hk += [skind[k]] * len(sr) + [pkind[k + 1]]
            hg += [None] * len(sr) + [sg(k + 1)]
            hp += [via[k]] * (len(sr) + 1)
            hs += [skind[k]] * (len(sr) + 1)
        for a, b in zip(chain, chain[1:]):
            hops.append((a[0], a[1], b[0], b[1], max(q.get('width') or 0 for q in qs)))
        bits = max(q.get('width') or 0 for q in qs) or None
        s0, d0 = qs[0]['src'], qs[-1]['dst']
        ends = [(parts[s0['part']][3], s0['bus'], pts[0], 'pin' if pkind[0] in ('pin', 'tbus', 'slot') else 'box'),
                (parts[d0['part']][3], d0['bus'], pts[-1], 'pin' if pkind[-1] in ('pin', 'tbus', 'slot') else 'box')]
        B.link(lane['id'], qs[0].get('kind') or 'data', bits, ends, True, hops=hops if hops else None,
               stages=stages if known else None,
               note=(((lane.get('note') or '')[:200]) + (' | stations spread evenly in %s (slot has a count, no sites)' % ','.join(via[k] for k in spread) if spread else '')).strip(' |') or None,
               extra=dict(cyc=lane.get('fixed_cycles'), via=via or None, hk=hk if len(qs) > 1 else None, hg=hg if len(qs) > 1 else None,
                          hp=hp or None, hs=hs or None))
        if hops:
            B.links[-1]['path_um'] = sum(abs(h[2] - h[0]) + abs(h[3] - h[1]) for h in hops)
        via_of[lane['id']] = via
    blocks, links = B.finish()
    # bypass: a lane's own ft partitions are not bypasses (the plan routes it through them)
    grid = B._grid(250.0)
    for l in links:
        own = {e[0] for e in l['e'] if e[0] >= 0} | {parts[v][3] for v in (l.get('via') or []) if v in parts}
        crossed = set()
        for s in segs_of(l):
            a, b = (s[0], s[1]), (s[2], s[3])
            n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) // 125) + 1)
            cand = set()
            for kk in range(n + 1):
                t = kk / n
                cand.update(grid.get((int((a[0] + (b[0] - a[0]) * t) // 250), int((a[1] + (b[1] - a[1]) * t) // 250)), ()))
            for i in cand:
                if i not in own and i not in crossed and B._crosses(i, a, b):
                    crossed.add(i)
        l['x'] = len(crossed)
        l['xb'] = sorted(crossed, key=lambda i: -B.w[i] * B.h[i])[:12]
    return blocks, links


def cmd_die(a):
    P = load_json(a.plan)
    die = P.get('die') or {}
    reach = a.reach or die.get('reach_um') or 500.0
    blocks, links = build_die(P, reach)
    name = a.name or ('die_%s' % (die.get('name') or Path(a.plan).stem))
    meta = dict(label=die.get('label') or name, design=die.get('name') or name, token_designs=[], revision=a.revision or Path(a.plan).name,
                role='inspection', scope='die plan %s (partitions + lanes/ports + ft-slot stations)' % a.plan, reach_um=reach,
                reach_source='die.reach_um of the plan', outline=die.get('outline_um'), stages_explicit=True,
                registers='ft_slots regs_um of the partitions each lane passes, placed with the partition orient',
                direction='port src -> dst (plan lanes)', pins='port face windows (exact, die frame) where the plan gives them, else the shared edge middle of the abutting partitions (edge), else the src outline point nearest dst (box); ends inside the end partitions unknown (lower bound)')
    rec = write_record(a.out, name, meta, blocks, links, [dict(path=str(a.plan), sha256=sha256(a.plan), role='die plan')])
    W, H = rec['outline']
    asp = H / W
    fw = a.width
    fig = plt.figure(figsize=(fw, fw * asp * 0.92 + 1.4), dpi=a.dpi)
    ax = fig.add_axes([0.04, 0.09, 0.92, 0.84])
    tlab = {}
    for i, n in enumerate(rec['blocks']['name']):
        if rec['blocks']['w'][i] * rec['blocks']['h'][i] > 0.002 * W * H:
            tlab[i] = '%s\n%s' % (n, rec['blocks']['master'][i])
    hl = set(a.highlight_type or [])
    fills = {i: '#2a2350' for i, m in enumerate(rec['blocks']['master']) if m in hl}
    ids, worst = draw_record(ax, rec, dict(top=a.top, block_labels=tlab, block_fill=fills, label_fs=a.label_fs, arrows_max=0, reg_s=1.2))
    s = summary(rec)
    fig.text(0.04, 0.965, '%s  |  %s sha256 %s  |  reach %.0f um  |  plan die.label: %s' % (
        die.get('name'), Path(a.plan).name, sha256(a.plan)[:12], reach, (die.get('label') or '')[:48]), color=INK, fontsize=11, fontweight='bold')
    fig.text(0.04, 0.945, summary_text(s) + '  |  #N = worst links (hop>reach first, then bits x hop): see %s.links.tsv' % name,
             color=LABEL, fontsize=8)
    legend(fig, rec)
    png, svg = save(fig, a.out, name)
    links_tsv(rec, Path(a.out) / (name + '.links.tsv'), worst,
              dict(cycles=lambda l: l.get('cyc'), via=lambda l: ','.join(l.get('via') or [])))
    print('DIE %s: %s\n  %s\n  %s\n  %s' % (name, summary_text(s), png, svg, Path(a.out) / (name + '.links.tsv')))


# ================================================================ TYPE VIEW
_LEF_DIR = {}


def lef_dirs(path):
    if path in _LEF_DIR:
        return _LEF_DIR[path]
    d, pin = {}, None
    try:
        txt = Path(path).read_text(errors='replace')
    except OSError:
        _LEF_DIR[path] = d
        return d
    for ln in txt.splitlines():
        w = ln.split()
        if not w:
            continue
        if w[0] == 'PIN' and len(w) > 1:
            pin = re.sub(r'\[\d+\]$', '', w[1])
        elif w[0] == 'DIRECTION' and pin:
            d.setdefault(pin, w[1].rstrip(';').upper())
        elif w[0] == 'END' and len(w) > 1 and w[1] == pin:
            pin = None
    _LEF_DIR[path] = d
    return d


def name_dir(port):
    p = port.lower()
    if re.search(r'(^|_)(o|out|dout|q|res|resp|rsp|wr|tx)(\d*)$', p) or re.search(r'(^o_|^out_|_out_)', p):
        return 'OUTPUT'
    if re.search(r'(^|_)(i|in|din|d|req|rd|rx)(\d*)$', p) or re.search(r'(^i_|^in_|_in_)', p):
        return 'INPUT'
    return None


class RS:
    """route_supply.py as a library: the scorer's own pin, partner and delta model"""

    def __init__(self, path):
        import importlib.util
        spec = importlib.util.spec_from_file_location('route_supply_er', path)
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)
        self.path = path


def _merge(base, patch):
    """route_supply._merge (plan-route-5) for route_supply versions without --delta: dicts merge; a dict patch onto a
    list of dicts merges by inst/name (null deletes, new keys append); anything else replaces"""
    if isinstance(base, dict) and isinstance(patch, dict):
        out = dict(base)
        for k, v in patch.items():
            if v is None:
                out.pop(k, None)
            else:
                out[k] = _merge(base.get(k), v) if k in base else v
        return out
    if isinstance(base, list) and isinstance(patch, dict) and all(isinstance(x, dict) for x in base):
        key = 'inst' if any('inst' in x for x in base) else 'name'
        out, seen = [], set()
        for x in base:
            kx = x.get(key)
            if kx in patch:
                seen.add(kx)
                if patch[kx] is not None:
                    out.append(_merge(x, patch[kx]))
            else:
                out.append(x)
        for kx, v in patch.items():
            if kx not in seen and v is not None:
                out.append(dict(v, **{key: kx}) if isinstance(v, dict) else v)
        return out
    return patch


def apply_delta(T, D):
    T2 = copy.deepcopy(T)
    if isinstance(D, list):
        rows, D = D, {}
        for r in rows:
            r = dict(r)
            tn, ins = r.pop('type'), r.pop('inst', None)
            if ins is None:
                D.setdefault(tn, {}).update(r)
            else:
                D.setdefault(tn, {}).setdefault('hard_cores', {})[ins] = r
    else:
        D = D.get('partition_types') or D.get('types') or {}
    for tn, p in D.items():
        T2[tn] = _merge(T2.get(tn, {}), p) if tn in T2 else p
    return T2


def norm_delta(D, base_types):
    """-> (partition_types patch for route_supply.apply_delta | None, full type replacements {type: dict}, note)"""
    if isinstance(D, dict) and D.get('schema') == 'opentallas.core_place.v1':
        po = D.get('plan_output')
        if po and Path(po).is_file():
            T2 = load_json(po).get('partition_types', {})
            names = [r['type'] for r in D.get('rows', [])]
            return None, {n: T2[n] for n in names if n in T2}, 'core_place.v1 plan_output %s' % po
        patch = {}
        for r in D.get('rows', []):
            ca = r.get('cores_after') or {}
            patch[r['type']] = {'hard_cores': {k: {kk: vv for kk, vv in v.items() if kk in ('origin_um', 'orient')} for k, v in ca.items()}}
        return {'partition_types': patch}, {}, 'core_place.v1 cores_after (stations not re-sited in this view)'
    if isinstance(D, list) or (isinstance(D, dict) and ('types' in D or 'partition_types' in D)):
        return D, {}, 'route_supply delta'
    if isinstance(D, dict):
        patch = {}
        for tn, v in D.items():
            if tn not in base_types or not isinstance(v, dict):
                continue
            hc = {}
            for inst, pos in v.items():
                if isinstance(pos, (list, tuple)) and len(pos) >= 2 and all(isinstance(z, (int, float)) for z in pos[:2]):
                    hc[inst] = dict(origin_um=[pos[0], pos[1]], **({'orient': pos[2]} if len(pos) > 2 and isinstance(pos[2], str) else {}))
                elif isinstance(pos, dict) and ('origin_um' in pos or 'orient' in pos):
                    hc[inst] = {k: pos[k] for k in ('origin_um', 'orient') if k in pos}
            if hc:
                patch[tn] = {'hard_cores': hc}
        if patch:
            return {'partition_types': patch}, {}, 'CLEANSLATE positions delta {type: {inst: [x, y, orient]}}'
    raise SystemExit('delta format not recognised (core_place.v1, route_supply types/partition_types/rows, or {type: {inst: [x,y,o]}})')


def split_ip(s, idx):
    """'inst.port' where inst names may contain dots: the longest prefix that is a hard-core instance"""
    if s in idx:
        return s, ''
    k = len(s)
    while True:
        k = s.rfind('.', 0, k)
        if k < 0:
            return s.partition('.')[0], s.partition('.')[2]
        if s[:k] in idx:
            return s[:k], s[k + 1:]


def pipeline_rank(n, succ, fed):
    """pipeline stage of each core: strongly connected groups (feedback loops) share one rank; rank = longest path
    from a core fed by an input face (or with no directed predecessor) over the condensed DAG"""
    index, low, on, st, comp, cnt = {}, {}, set(), [], {}, [0]
    for root in range(n):
        if root in index:
            continue
        work = [(root, iter(sorted(succ.get(root, ()))))]
        index[root] = low[root] = cnt[0]; cnt[0] += 1; st.append(root); on.add(root)
        while work:
            v, it = work[-1]
            adv = False
            for w in it:
                if w not in index:
                    index[w] = low[w] = cnt[0]; cnt[0] += 1; st.append(w); on.add(w)
                    work.append((w, iter(sorted(succ.get(w, ())))))
                    adv = True
                    break
                if w in on:
                    low[v] = min(low[v], index[w])
            if adv:
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[v])
            if low[v] == index[v]:
                c = len(set(comp.values()))
                while True:
                    w = st.pop(); on.discard(w); comp[w] = c
                    if w == v:
                        break
    csucc = collections.defaultdict(set)
    indeg = collections.Counter()
    for u, vs in succ.items():
        for v in vs:
            if comp[u] != comp[v] and comp[v] not in csucc[comp[u]]:
                csucc[comp[u]].add(comp[v]); indeg[comp[v]] += 1
    nc = len(set(comp.values()))
    lvl = {c: 0 for c in range(nc)}
    q = collections.deque(c for c in range(nc) if indeg[c] == 0)
    while q:
        c = q.popleft()
        for d in csucc[c]:
            lvl[d] = max(lvl[d], lvl[c] + 1)
            indeg[d] -= 1
            if indeg[d] == 0:
                q.append(d)
    return {i: lvl[comp[i]] for i in range(n)}


def build_type(tname, t, rs, die_dir, repo, conns_t, reach, base=None, per_port=False, st_extra=None):
    """links record (blocks = hard cores) + overlay data for one partition type"""
    m = rs.m
    W, H = t['outline_um'][:2]
    B = DL.Builder()
    cores = t.get('hard_cores') or []
    pins, idx, cdir, rects = {}, {}, {}, {}
    for h in cores:
        o = h.get('orient', 'R0')
        w, hh = orient_rect(*h['outline_um'][:2], o)
        idx[h['inst']] = B.block(h['inst'], h.get('module'), 'core', h['inst'], h['origin_um'][0], h['origin_um'][1], w, hh)
        rects[h['inst']] = (h['origin_um'][0], h['origin_um'][1], h['origin_um'][0] + w, h['origin_um'][1] + hh)
        d = collections.defaultdict(list)
        for bus, x, y in m.core_pins(h, die_dir, repo):
            d[bus].append((x, y))
        pins[h['inst']] = d
        lp = h.get('lef')
        cdir[h['inst']] = lef_dirs(str(Path(repo) / lp)) if lp else {}
    buses = {b['name']: b for b in t.get('buses') or []}

    def cen(pts):
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

    def pdir(inst, port):
        return cdir.get(inst, {}).get(port) or name_dir(port)

    seen, links, unres, glue, stn_keys = {}, [], collections.Counter(), collections.Counter(), set()
    strap_ports = collections.defaultdict(set)      # inst -> ports;  '' -> type face bus names
    for sp in (t.get('id_straps') or []) + (t.get('count_straps') or []):
        strap_ports[''].add(sp.get('name'))
    for h in cores:
        strap_ports[h['inst']].update((h.get('parent_id_straps') or {}).keys())
        strap_ports[h['inst']].update((h.get('straps') or {}).keys() if isinstance(h.get('straps'), dict) else [])
    dead_mod = collections.defaultdict(set)
    for di in t.get('dead_inputs') or []:
        dead_mod[di.get('module')].update((di.get('ports') or {}).keys())
    mod_of = {h['inst']: h.get('module') for h in cores}

    def stat_of(inst, port):
        if not port:
            return None
        if RESET_PORT.match(port):
            return 'reset'
        if port in strap_ports.get(inst, ()) or (inst is None and port in strap_ports.get('', ())):
            return 'strap'
        if port in dead_mod.get(mod_of.get(inst), ()):
            return 'dead'
        return None
    for st in t.get('internal_stations') or []:
        la, ca = st.get('launch') or st.get('conn', '|').split('|')[0], st.get('capture') or st.get('conn', '|').split('|')[-1]
        li, lpn = split_ip(la, idx)
        ci, cpn = split_ip(ca, idx)
        stn_keys.add((li, lpn, ci))
        stn_keys.add((ci, cpn, li))
    for A, ports in (conns_t or {}).items():
        if A not in idx:
            continue
        for p, dests in ports.items():
            if CONTROL_PORT.match(p) or p not in pins[A] and not dests:
                continue
            nA = len(pins[A].get(p, [])) or None
            cd = [x for x in dests if isinstance(x, str) and x.startswith('core:')]
            for dst in dests:
                if not isinstance(dst, str):
                    continue
                kind, _, rest = dst.partition(':')
                if dst == 'glue' or kind == 'glue':
                    glue[A] += nA or 1
                    continue
                if kind == 'tap':
                    continue
                pa = cen(pins[A][p]) if pins[A].get(p) else None
                if kind == 'core':
                    Bn, q = split_ip(rest, idx)
                    if Bn not in idx or Bn == A:
                        unres[A] += 1
                        continue
                    if not q:
                        rq = [qq for qq, ds in (conns_t.get(Bn) or {}).items() if any(x in ('core:' + A, 'core:%s.%s' % (A, p)) for x in ds)]
                        q = rq[0] if len(rq) == 1 else ''
                    if q and CONTROL_PORT.match(q):
                        continue
                    pb = cen(pins[Bn][q]) if q and pins[Bn].get(q) else None
                    nB = len(pins[Bn].get(q, [])) if q else 0
                    bits = min(nA, nB) if nA and nB else (nA if len(cd) <= 1 else max(1, round((nA or 1) / len(cd))))
                    key = frozenset([(A, p), (Bn, q or '*')])
                    if key in seen:
                        continue
                    if (A, p, Bn) in stn_keys or (Bn, q, A) in stn_keys:
                        continue      # the plan's internal stations carry this pair: drawn from internal_stations
                    da, db = pdir(A, p), (pdir(Bn, q) if q else None)
                    drv_first = not (da == 'INPUT' or (da is None and db == 'OUTPUT'))
                    directed = da in ('INPUT', 'OUTPUT') or db in ('INPUT', 'OUTPUT')
                    eA = (idx[A], p, pa, 'pin' if pa else None)
                    eB = (idx[Bn], q or '', pb, 'pin' if pb else None)
                    ends = [eA, eB] if drv_first else [eB, eA]
                    seen[key] = len(links)
                    links.append(dict(id='%s.%s>%s.%s' % (A, p, Bn, q or '*') if drv_first else '%s.%s>%s.%s' % (Bn, q or '*', A, p),
                                      cls='core-core', bits=bits, ends=ends, directed=directed,
                                      stat=stat_of(A, p) or stat_of(Bn, q)))
                elif kind in ('bus', 'face', 'ft'):
                    if kind == 'bus' and rest in buses:
                        bb = buses[rest]
                        fp, bdir, cls = face_pt(W, H, bb.get('face'), bb.get('window_um')), bb.get('dir'), 'core-face'
                    elif kind == 'face' and rest[:1] in 'NSEW':
                        fp, bdir, cls = face_pt(W, H, rest[:1], None), None, 'core-face'
                    else:
                        unres[A] += 1
                        continue
                    key = frozenset([(A, p), (dst, '')])
                    if key in seen:
                        continue
                    seen[key] = len(links)
                    da = pdir(A, p)
                    inward = bdir == 'in' or (bdir is None and da == 'INPUT')
                    eA = (idx[A], p, pa, 'pin' if pa else None)
                    eF = (None, dst, fp, 'pin')
                    links.append(dict(id=('%s>%s.%s' % (dst, A, p)) if inward else ('%s.%s>%s' % (A, p, dst)), cls=cls,
                                      bits=(bb.get('width') if kind == 'bus' and not nA else nA),
                                      ends=[eF, eA] if inward else [eA, eF], directed=bdir in ('in', 'out') or da is not None,
                                      stat=stat_of(A, p) or (stat_of(None, rest) if kind == 'bus' else None)))
                else:
                    unres[A] += 1
    if not per_port:      # one link per (driver core, sink core | face): bits summed, ends = bit-weighted pin centroids
        grp = collections.OrderedDict()
        for L in links:
            e0, e1 = L['ends']
            k_ = (e0[0] if e0[0] is not None else e0[1], e1[0] if e1[0] is not None else e1[1], L['directed'], L['cls'], L.get('stat'))
            grp.setdefault(k_, []).append(L)
        agg = []
        for k_, Ls in grp.items():
            if len(Ls) == 1:
                agg.append(Ls[0])
                continue

            def wc(j):
                pts = [(L['ends'][j][2], L['bits'] or 1) for L in Ls if L['ends'][j][2] is not None]
                if not pts:
                    return None
                sw = sum(w for _, w in pts)
                return (sum(p[0] * w for p, w in pts) / sw, sum(p[1] * w for p, w in pts) / sw)
            e0, e1 = Ls[0]['ends']
            ports0 = sorted({L['ends'][0][1] for L in Ls})
            ports1 = sorted({L['ends'][1][1] for L in Ls})
            p0, p1 = wc(0), wc(1)
            agg.append(dict(id='%s>%s' % (B.names[e0[0]] if e0[0] is not None else e0[1], B.names[e1[0]] if e1[0] is not None else e1[1]),
                            cls=Ls[0]['cls'], bits=sum(L['bits'] or 0 for L in Ls) or None, directed=Ls[0]['directed'], stat=Ls[0].get('stat'),
                            ends=[(e0[0], '+'.join(ports0)[:120], p0, 'pin' if p0 else None), (e1[0], '+'.join(ports1)[:120], p1, 'pin' if p1 else None)],
                            note='%d port links bundled: %s' % (len(Ls), ', '.join('%s>%s' % (L['ends'][0][1], L['ends'][1][1]) for L in Ls)[:280])))
        links = agg
    for L in links:
        B.link(L['id'], L['cls'], L['bits'], L['ends'], L['directed'], note=L.get('note'), extra=dict(stat=L.get('stat')))
    nst = 0
    for st in bus_station_entries(t):
        fr, to, regs = st.get('from_um'), st.get('to_um'), st.get('regs_um') or []
        if not fr or not to:
            continue
        la, ca = st.get('launch') or st.get('conn', '|').split('|')[0], st.get('capture') or st.get('conn', '|').split('|')[-1]
        li, lpn = split_ip(la, idx)
        ci, cpn = split_ip(ca, idx)
        if CONTROL_PORT.match(lpn or '') or CONTROL_PORT.match(cpn or ''):
            continue
        sst = stat_of(li if li in idx else None, lpn) or stat_of(ci if ci in idx else None, cpn)
        note = None
        if base:      # after a positions delta: station ends follow their cores, the plan's regs stay where they were
            fr, to = list(fr), list(to)
            for inst, pt in ((li, fr), (ci, to)):
                b0, h1 = base.get(inst), next((h for h in t.get('hard_cores') or [] if h['inst'] == inst), None)
                if b0 and h1 and tuple(b0['origin_um']) != tuple(h1['origin_um']):
                    pt[0] += h1['origin_um'][0] - b0['origin_um'][0]
                    pt[1] += h1['origin_um'][1] - b0['origin_um'][1]
                    note = 'core moved by the delta: station regs not re-sited (stale)'
        chain = [tuple(fr)] + [tuple(r) for r in regs] + [tuple(to)]
        hops = [(a[0], a[1], b[0], b[1], st.get('bits') or 0) for a, b in zip(chain, chain[1:])]
        B.link('stn:%s' % st.get('conn'), 'internal-station', st.get('bits'),
               [(idx.get(li), lpn, tuple(fr), 'pin'), (idx.get(ci), cpn, tuple(to), 'pin')], True, hops=hops, stages=len(regs),
               note=note, extra=dict(stat=sst))
        B.links[-1]['path_um'] = sum(abs(h[2] - h[0]) + abs(h[3] - h[1]) for h in hops)
        nst += 1
    for f in t.get('ft_slots') or []:
        a0 = face_pt(W, H, f.get('in_face'), f.get('in_window_um'))
        b0 = face_pt(W, H, f.get('out_face'), f.get('out_window_um'))
        k, r, kd = ft_slot_stages(f, (st_extra or {}).get(f['name']))
        if kd == 'reg' and not f.get('in_window_um'):
            a0 = tuple(f['regs_um'][0][:2])          # no in window: the plan's station 0 site stands for the in pin
        if r is None:
            r = spread_on(slot_route(a0, b0, f.get('in_face'), f.get('out_face')), k)
        chain = [a0] + list(r) + [b0]
        hops = [(p[0], p[1], q[0], q[1], f.get('width') or 0) for p, q in zip(chain, chain[1:])]
        B.link('ft:%s' % f['name'], 'ft', f.get('width'), [(None, 'ft_in', a0, 'pin'), (None, 'ft_out', b0, 'pin')], True,
               hops=hops, stages=k, note='%d stations (station 0 = in-face flop), interior sites: %s' % (k, kd))
        B.links[-1]['path_um'] = sum(abs(h[2] - h[0]) + abs(h[3] - h[1]) for h in hops)
    blocks, recs = B.finish()
    # pipeline rank over directed core links (inputs first); cycles broken in DFS order
    succ = collections.defaultdict(set)
    fed = set()
    for l in recs:
        e = l['e']
        if not l['d'] or len(e) < 2:
            continue
        a_, b_ = e[0][0], e[1][0]
        if a_ >= 0 and b_ >= 0 and a_ != b_:
            succ[a_].add(b_)
        elif a_ < 0 and b_ >= 0:
            fed.add(b_)
    rank = pipeline_rank(len(blocks['name']), succ, fed)
    pf = {}
    for inst, d in pins.items():
        x0, y0, x1, y1 = rects[inst]
        c = collections.Counter()
        for bus, pts in d.items():
            if CONTROL_PORT.match(bus):
                continue
            for (x, y) in pts:
                dd = {'W': x - x0, 'E': x1 - x, 'S': y - y0, 'N': y1 - y}
                c[min(dd, key=dd.get)] += 1
        pf[inst] = dict(c)
    ov = dict(W=W, H=H, rank={blocks['name'][i]: r for i, r in rank.items()}, pins_per_face=pf, glue=dict(glue), unresolved=dict(unres),
              pins={k: [p for bus, v in d.items() if not CONTROL_PORT.match(bus) for p in v] for k, d in pins.items()},
              orient={h['inst']: h.get('orient', 'R0') for h in cores}, buses=list(buses.values()), ft=t.get('ft_slots') or [],
              clock=t.get('clock') or {}, n_stations=nst, cores=len(cores))
    return blocks, recs, ov


def fam_colour(module):
    hsh = int(hashlib.md5((module or '').encode()).hexdigest()[:6], 16)
    h = (hsh % 360) / 360.0
    r, g, b = colorsys.hls_to_rgb(h, 0.17, 0.35)
    return '#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255))


def draw_type(ax, rec, ov, opts, moved=(), supply=None):
    W, H = ov['W'], ov['H']
    B = rec['blocks']
    fills = {i: fam_colour(B['master'][i]) for i in range(len(B['name']))}
    labels = {}
    for i, n in enumerate(B['name']):
        if B['w'][i] * B['h'][i] > opts.get('label_area', 0.004) * W * H:
            r = ov['rank'].get(n)
            labels[i] = '%s%s\n%s' % ('#%d ' % r if r is not None and opts.get('ranks', True) else '', n.split('.')[-1] if opts.get('short') else n,
                                      (B['master'][i] or '')[:28])
    o2 = dict(opts, block_fill=fills, block_labels=labels, block_edge='#3a4a78')
    ids, worst = draw_record(ax, rec, o2)
    fig = ax.figure
    k = _px2pt(fig)
    # moved cores (delta): accent outline
    for i, n in enumerate(B['name']):
        if n in moved:
            ax.add_patch(Rectangle((B['x'][i], B['y'][i]), B['w'][i], B['h'][i], fill=False, edgecolor=MOVED, lw=1.4, zorder=6))
    # orient marker: the R0 origin corner, transformed
    for i, n in enumerate(B['name']):
        o = ov['orient'].get(n, 'R0')
        x0, y0, w, h = B['x'][i], B['y'][i], B['w'][i], B['h'][i]
        s = min(min(w, h) * 0.18, 0.025 * min(W, H))
        cx = x0 + w if o in ('MY', 'R180') else x0
        cy = y0 + h if o in ('MX', 'R180') else y0
        dx = -s if o in ('MY', 'R180') else s
        dy = -s if o in ('MX', 'R180') else s
        ax.add_patch(Polygon([(cx, cy), (cx + dx, cy), (cx, cy + dy)], closed=True, facecolor='#b8c4e6', edgecolor='none', alpha=0.7, zorder=2))
    # pins per face, as small counts inside each face
    if opts.get('face_counts', True):
        for i, n in enumerate(B['name']):
            c = ov['pins_per_face'].get(n) or {}
            x0, y0, w, h = B['x'][i], B['y'][i], B['w'][i], B['h'][i]
            if w * h < opts.get('label_area', 0.004) * W * H * 0.5:
                continue
            fs = opts.get('face_fs', 3.5)
            for f, (x, y, ha, va) in dict(N=(x0 + w / 2, y0 + h, 'center', 'top'), S=(x0 + w / 2, y0, 'center', 'bottom'),
                                         W=(x0, y0 + h / 2, 'left', 'center'), E=(x0 + w, y0 + h / 2, 'right', 'center')).items():
                if c.get(f):
                    ax.text(x, y, '%s%d' % (f, c[f]), fontsize=fs, color='#9fb0dd', ha=ha, va=va, zorder=6, clip_on=True)
    # pins
    if opts.get('pins', True):
        xs = [p[0] for v in ov['pins'].values() for p in v]
        ys = [p[1] for v in ov['pins'].values() for p in v]
        if xs:
            ax.scatter(xs, ys, s=0.15, c='#8fa3d9', linewidths=0, zorder=2.5, alpha=0.7)
    # face windows
    lw = 3.2 * k * 1.6
    tops = sorted(ov['buses'], key=lambda b: -(b.get('width') or 0))[:opts.get('bus_labels', 14)]
    for b in ov['buses']:
        win, f = b.get('window_um'), b.get('face')
        if not win or f not in 'NSEW':
            continue
        col = FACE_IN if b.get('dir') == 'in' else FACE_OUT
        if f in 'EW':
            x = 0 if f == 'W' else W
            ax.plot([x, x], [win[0], max(win[1], win[0] + 0.004 * H)], color=col, lw=lw, solid_capstyle='butt', zorder=5)
        else:
            y = 0 if f == 'S' else H
            ax.plot([win[0], max(win[1], win[0] + 0.004 * W)], [y, y], color=col, lw=lw, solid_capstyle='butt', zorder=5)
        if b in tops:
            m = (win[0] + win[1]) / 2
            xy = {'W': (0, m), 'E': (W, m), 'S': (m, 0), 'N': (m, H)}[f]
            off = {'W': (-4, 0), 'E': (4, 0), 'S': (0, -4), 'N': (0, 4)}[f]
            ax.annotate('%s %db' % (b['name'], b.get('width') or 0), xy=xy, xytext=off, textcoords='offset points', fontsize=4.2,
                        color=col, ha={'W': 'right', 'E': 'left'}.get(f, 'center'), va={'S': 'top', 'N': 'bottom'}.get(f, 'center'),
                        rotation=90 if f in 'NS' else 0, zorder=7)
    # clock tap + core taps
    ck = ov['clock']
    if ck.get('tap_um'):
        ax.scatter([ck['tap_um'][0]], [ck['tap_um'][1]], s=60, marker='*', c=TAP, edgecolors='#000000', linewidths=0.4, zorder=8)
    tx = [tp['xy'] for tp in ck.get('taps') or [] if tp.get('xy')]
    if tx:
        ax.scatter([p[0] for p in tx], [p[1] for p in tx], s=6, marker='x', c=TAP, linewidths=0.5, zorder=8)
    # route_supply overlay
    if supply is not None:
        import numpy as np
        r = np.maximum(supply['rH'], supply['rV'])
        bu = float(supply['bin_um'])
        ny, nx = r.shape
        im = ax.imshow(r, origin='lower', extent=[0, nx * bu, 0, ny * bu], cmap='magma', vmin=0.0, vmax=2.0, alpha=1.0,
                       zorder=0.5, interpolation='nearest')
        return ids, worst, im
    return ids, worst, None


def run_supply(a, plan_path, P, tname, t_after, tag, tmp):
    """route_supply.py --maps for one type (before = the plan as is; after = the plan with this type replaced)"""
    rsp = a.route_supply
    out = Path(tmp) / tag
    plan_arg = plan_path
    ref = [str(Path(plan_path).resolve().parent)] + list(a.ref_dirs or [])
    if t_after is not None:
        P2 = {k: v for k, v in P.items() if k != 'partition_types'}
        P2['partition_types'] = {tname: t_after}
        plan_arg = str(Path(tmp) / ('plan_%s.json' % tag))
        Path(plan_arg).write_text(json.dumps(P2))
    cmd = [sys.executable, '-I', rsp, '--plan', str(plan_arg), '--repo', str(a.repo), '--types', tname, '--maps', '--out', str(out),
           '--ref-dirs'] + ref
    if a.die:
        cmd += ['--die', a.die]
    if a.release_cache:
        cmd += ['--release-cache', a.release_cache]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, cwd=str(a.repo))
    import numpy as np
    f = list(out.glob('*__%s.npz' % tname))
    if p.returncode or not f:
        print('route_supply %s failed (rc %s): %s' % (tag, p.returncode, (p.stderr or p.stdout)[-800:]), file=sys.stderr)
        return None
    z = np.load(f[0])
    d = dict(rH=z['rH'], rV=z['rV'], bin_um=float(z['bin_um']))
    row = None
    for j in out.glob('*.json'):
        try:
            x = json.loads(j.read_text())
            rows = x.get('rows') if isinstance(x, dict) else x
            for r in rows or []:
                if isinstance(r, dict) and r.get('type') == tname:
                    row = r
        except (ValueError, OSError):
            pass
    d['row'] = row
    rr = np.maximum(d['rH'], d['rV'])
    d['max'] = float(rr.max())
    d['p99'] = float(np.percentile(rr, 99))
    return d


def type_meta(a, tname, t, reach, note):
    return dict(label='%s (%s)' % (tname, t.get('module')), design=tname, token_designs=[], revision=Path(a.plan).name, role='inspection',
                scope='partition type %s of %s%s' % (tname, a.plan, ('; ' + note) if note else ''), reach_um=reach,
                reach_source='die.reach_um of the plan (or --reach)', outline=t['outline_um'][:2], stages_explicit=True,
                registers='internal_stations regs_um (core links the plan stations) and ft_slots regs_um', direction=
                'LEF DIRECTION of the core port, else type bus dir, else port-name suffix; undirected when unknown',
                pins='pins_file centroids per bus (route_supply.core_pins, orient applied); face ends = bus window centre')


def cmd_type(a):
    rs = RS(a.route_supply)
    m = rs.m
    repo = Path(a.repo).resolve()
    plan = Path(a.plan)
    if not plan.is_absolute():
        plan = repo / plan
    P = load_json(plan)
    T = P['partition_types']
    tname = a.type
    if tname not in T:
        raise SystemExit('type %s not in plan (%d types)' % (tname, len(T)))
    m.REF_DIRS[:] = [str(plan.parent)] + [str(repo / 'physical' / 'die_plan' / r) for r in (a.ref_dirs or [])]
    die = a.die or (P.get('die') or {}).get('name') or plan.parent.name
    die_dir = repo / 'physical' / 'die_plan' / die
    if not die_dir.is_dir():
        die_dir = plan.parent
    conns = m.load_conns(die_dir, a.core_conns, plan.parent, m.REF_DIRS[1:])
    reach = a.reach or (P.get('die') or {}).get('reach_um') or 500.0
    t0 = T[tname]
    t1, note = None, ''
    if a.delta or a.after_plan:
        if a.after_plan:
            t1 = load_json(a.after_plan)['partition_types'][tname]
            note = 'after = %s' % a.after_plan
        else:
            D = load_json(a.delta)
            patch, full, note = norm_delta(D, T)
            if tname in full:
                t1 = full[tname]
            elif patch is not None:
                T2 = (m.apply_delta if hasattr(m, 'apply_delta') else apply_delta)({tname: t0}, patch)
                t1 = T2[tname]
            if t1 is None or t1 == t0:
                raise SystemExit('delta %s does not change type %s' % (a.delta, tname))
    name = a.name or ('type_%s' % tname)
    out = Path(a.out)
    views = [('before' if t1 is not None else 'plan', t0)] + ([('after', t1)] if t1 is not None else [])
    built = []
    # same core_conns key resolution as route_supply (exact type, then __clXXXXXXXX stripped, then family before '__')
    cc_key = next((k for k in (tname, re.sub(r'__cl[0-9a-f]{8}.*$', '', tname), re.sub(r'__.*$', '', tname))
                   if conns.get(k)), None)
    cc = conns.get(cc_key) if cc_key else None
    for tag, t in views:
        blocks, links, ov = build_type(tname, t, rs, die_dir, repo, cc, reach,
                                       base={h['inst']: h for h in t0.get('hard_cores') or []} if tag == 'after' else None,
                                       per_port=a.per_port, st_extra=station_extra(P, tname))
        rid = name + ('' if tag == 'plan' else '__' + tag)
        rec = write_record(out, rid, type_meta(a, tname, t, reach, note if tag == 'after' else ''), blocks, links,
                           [dict(path=str(plan), sha256=sha256(plan), role='plan')] +
                           ([dict(path=str(a.delta or a.after_plan), sha256=sha256(a.delta or a.after_plan), role='delta')] if tag == 'after' else []) +
                           ([dict(path=m._CONNS_SRC.get(cc_key), sha256=sha256(m._CONNS_SRC[cc_key]), role='core_conns:' + str(cc_key))] if cc_key and m._CONNS_SRC.get(cc_key) else []))
        built.append((tag, t, rec, ov, rid))
    moved = set()
    if t1 is not None:
        o0 = {h['inst']: (tuple(h['origin_um']), h.get('orient', 'R0')) for h in t0.get('hard_cores') or []}
        moved = {h['inst'] for h in t1.get('hard_cores') or [] if o0.get(h['inst']) != (tuple(h['origin_um']), h.get('orient', 'R0'))}
    sup = {}
    if a.supply:
        with tempfile.TemporaryDirectory(prefix='er_rs_') as tmp:
            for tag, t, rec, ov, rid in built:
                sup[tag] = run_supply(a, str(plan), P, tname, None if tag in ('plan', 'before') else t, tag, tmp)
    W, H = t0['outline_um'][:2]
    panels = [(v, False) for v in built] + ([(v, True) for v in built if sup.get(v[0])] if sup else [])
    n = len(panels)
    pw = a.width
    asp = H / W
    if pw * asp > a.max_height:      # tall types: keep the page readable and the PNG small
        pw = a.max_height / asp
    fig = plt.figure(figsize=(max(pw, 6.5) * n, pw * asp + 2.6), dpi=a.dpi)
    lines = []
    worst_by = {}
    for j, ((tag, t, rec, ov, rid), is_sup) in enumerate(panels):
        ax = fig.add_axes([0.05 / n + j / n, 0.09, 0.92 / n, 0.74])
        if is_sup:      # route_supply panel: ratio map, cores, face windows, no links
            rec_nl = dict(rec, links=[])
            draw_type(ax, rec_nl, ov, dict(top=0, label_fs=a.label_fs, short=True, pins=False, face_counts=False, ranks=False),
                      moved if tag == 'after' else (), sup.get(tag))
            for c_ in ax.collections:
                if isinstance(c_, PatchCollection):
                    c_.set_facecolor('none')
            sp = sup[tag]
            rw = sp.get('row') or {}
            ax.set_title('%s route_supply (demand/supply, max of H and V; magma 0..2)\nratio max %.2f | %s worst %s_%s p99 %s\nflag %s' % (
                tag.upper(), sp['max'], rw.get('verdict'), (rw.get('worst') or {}).get('region'), (rw.get('worst') or {}).get('dir'),
                (rw.get('worst') or {}).get('p99'), ', '.join('%s %.2f' % (f_[0], f_[1]) for f_ in (rw.get('flag_regions') or [])[:4])),
                color=INK, fontsize=7.5, loc='left')
            continue
        ids, worst, im = draw_type(ax, rec, ov, dict(top=a.top, label_fs=a.label_fs, short=a.short_labels, wmul=a.wmul,
                                                     arrows_max=a.arrows_max, rank_fs=7), moved if tag == 'after' else (), None)
        worst_by[tag] = worst
        s = summary(rec)
        sp = sup.get(tag)
        stx = ''
        if sp:
            stx = '\nroute_supply ratio max %.2f' % sp['max']
            if sp.get('row'):
                w_ = sp['row'].get('worst') or {}
                stx += ' | %s worst %s_%s p99 %s' % (sp['row'].get('verdict', ''), w_.get('region'), w_.get('dir'), w_.get('p99'))
        cc = collections.Counter(l.get('c') for l in rec['links'])
        ax.set_title('%s: %s\n%s\ncores %d, links %s\nstations %d, glue pins %d, unresolved conns %d%s%s' % (
            tag.upper(), tname, summary_text(s, '\n'), ov['cores'], dict(cc), ov['n_stations'], sum(ov['glue'].values()),
            sum(ov['unresolved'].values()), (', moved %d' % len(moved)) if tag == 'after' else '', stx),
            color=INK, fontsize=7.5, loc='left')
        lines.append((tag, s, sp))
        links_tsv(rec, out / (rid + '.links.tsv'), worst, dict(pipeline=lambda l, ov=ov, rec=rec: '>'.join(
            str(ov['rank'].get(rec['blocks']['name'][e[0]], '')) if e[0] >= 0 else 'face' for e in l['e'])))
    from matplotlib.lines import Line2D
    extra = [Line2D([], [], color=FACE_IN, lw=3, label='face window in'), Line2D([], [], color=FACE_OUT, lw=3, label='face window out'),
             Line2D([], [], color=TAP, marker='*', ls='', ms=7, label='clock tap / x core taps'),
             Line2D([], [], color='#b8c4e6', marker='<', ls='', ms=5, label='orient: R0 origin corner')]
    if moved:
        extra.append(Line2D([], [], color=MOVED, lw=1.5, label='moved by the delta'))
    if sup:
        extra.append(Line2D([], [], color='#f89540', lw=4, label='route_supply panel: ratio, magma 0 (black) .. 2 (white)'))
    legend(fig, built[0][2], extra)
    fig.text(0.02, 0.975, '%s | %s | reach %.0f um\n#N worst links (hop>reach first, then bits x hop); #k in a core = pipeline rank'
             % (tname, plan.name, reach), color=INK, fontsize=8.5, fontweight='bold')
    png, svg = save(fig, out, name)
    print('TYPE %s %s' % (tname, plan))
    for tag, s, sp in lines:
        rw = (sp or {}).get('row') or {}
        print('  %-6s %s%s' % (tag, summary_text(s), (' | route_supply %s worst %s %s p99 %s, flag %s' % (
            rw.get('verdict'), (rw.get('worst') or {}).get('region'), (rw.get('worst') or {}).get('dir'),
            (rw.get('worst') or {}).get('p99'), rw.get('flag_regions'))) if sp else ''))
    print('  %s\n  %s' % (png, svg))
    for tag, t, rec, ov, rid in built:
        print('  %s' % (out / (rid + '.links.tsv')))


# ================================================================ HOP AUDIT (die records)
def seg_gap(a, b):
    """Manhattan lower bound between two chain points, each a point (x,y) or an axis-aligned segment [x0,y0,x1,y1]:
    the hop is at least this long wherever on its window / shared edge the crossing really sits"""
    def iv(p):
        return ((min(p[0], p[2]), max(p[0], p[2])), (min(p[1], p[3]), max(p[1], p[3]))) if len(p) == 4 else ((p[0], p[0]), (p[1], p[1]))
    A, B_ = iv(a), iv(b)
    return sum(max(0.0, B_[d][0] - A[d][1], A[d][0] - B_[d][1]) for d in (0, 1))


def minimax_cross(p, g, n, steps=400):
    """best case for a crossing that may sit anywhere on segment g between fixed chain points p and n:
    min over c on g of max(|p-c|, |c-n|) (Manhattan). Even with a flop exactly at the crossing, one of the
    two hops is at least this long; without one, the hop p->n is longer still"""
    best = None
    for i in range(steps + 1):
        c = (g[0] + (g[2] - g[0]) * i / steps, g[1] + (g[3] - g[1]) * i / steps)
        v = max(abs(p[0] - c[0]) + abs(p[1] - c[1]), abs(n[0] - c[0]) + abs(n[1] - c[1]))
        best = v if best is None or v < best else best
    return best


def hop_verdict(kind_a, kind_b, seg, length, reach, lower=None):
    """REAL = the over-reach hop runs between plan facts (port windows, regs_um, bit_sites, or a slot with no stations);
    MODEL = it depends on a geometry stand-in of this tool. An evenly spread station count is the best case for that
    count (even spacing minimises the longest hop), so a hop still over reach there is REAL (lower bound)."""
    if length <= reach:
        return 'ok', ''
    why = []
    if lower is not None and lower > reach and (kind_a in ('edge', 'box') or kind_b in ('edge', 'box')):
        return 'REAL', ('crossing is an edge stand-in, but its best point anywhere on that shared edge still leaves a hop '
                        'of %.0f um > reach (lower bound, independent of the stand-in)' % lower)
    for k in (kind_a, kind_b):
        if k in ('edge', 'box'):
            why.append('crossing point is a %s stand-in (no port window and no type bus window in the plan)' % k)
    for flag, txt in (('noslot', 'no ft slot of that bus name in the via partition: its stations are not modelled'),
                      ('nopart', 'via partition not placed'),
                      ('break', 'port chain break: next port does not leave this partition'),
                      ('reversed', 'slot sites listed out->in for this lane: order assumed')):
        if flag in (seg or ''):
            why.append(txt)
    if why:
        return 'MODEL', '; '.join(why)
    if (seg or '').startswith('spread'):
        return 'REAL', 'slot declares a station count but no sites; even spacing is the best case and is still over reach (lower bound)'
    if (seg or '').startswith('none'):
        return 'REAL', 'the plan ft slot through this partition has NO stations'
    src = {'reg': 'plan regs_um', 'site': 'plan bit_sites_um'}.get((seg or '').split('+')[0], seg)
    return 'REAL', 'between plan sites (%s; crossings at their best window point = lower bound)' % src


def cmd_audit(a):
    rec = load_json(a.record)
    reach = a.reach or rec.get('reach_um') or 500.0
    links = rec['links']
    order = sorted(range(len(links)), key=lambda i: worst_key(rec, links[i]), reverse=True)[:a.top]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    name = a.name or re.sub(r'\.links\.json(\.gz)?$', '', Path(a.record).name) + '__hop_audit'
    rows, verdicts = [], collections.Counter()
    for r_, i in enumerate(order, 1):
        l = links[i]
        h, hk, hp, hs, hg = l.get('h') or [], l.get('hk') or [], l.get('hp') or [], l.get('hs') or [], l.get('hg') or []
        lv = []
        for j, x in enumerate(h):
            ln = abs(x[2] - x[0]) + abs(x[3] - x[1])
            ka = hk[j] if j < len(hk) else None
            kb = hk[j + 1] if j + 1 < len(hk) else None
            ga = (hg[j] if j < len(hg) else None) or x[:2]
            gb = (hg[j + 1] if j + 1 < len(hg) else None) or x[2:4]
            lb = seg_gap(ga, gb)
            # an edge crossing between two fixed points: the best crossing point on the edge bounds this hop pair
            for c, (pp, nn) in ((j, (h[j - 1][:2] if j > 0 else None, x[2:4])), (j + 1, (x[:2], h[j + 1][2:4] if j + 1 < len(h) else None))):
                fixed = lambda k: 0 <= k < len(hg) and not hg[k]          # a station / site, not another window
                if (pp is not None and nn is not None and c < len(hg) and hg[c] and c < len(hk)
                        and hk[c] in ('edge', 'box') and fixed(c - 1) and fixed(c + 1)):
                    lb = max(lb, minimax_cross(pp, hg[c], nn))
            v, why = hop_verdict(ka, kb, hs[j] if j < len(hs) else None, ln, reach, lower=lb)
            if v == 'ok':
                continue
            lv.append(v)
            rows.append([r_, l['i'], l.get('b'), j, hp[j] if j < len(hp) else '', round(ln, 1), round(lb, 1), ka, kb, hs[j] if j < len(hs) else '', v, why,
                         '%.1f,%.1f -> %.1f,%.1f' % tuple(x[:4])])
        lane_v = 'REAL' if lv and all(v == 'REAL' for v in lv) else 'MODEL' if lv and all(v == 'MODEL' for v in lv) else 'MIXED' if lv else 'ok'
        verdicts[lane_v] += 1
        rows.append([r_, l['i'], l.get('b'), 'LANE', ','.join(l.get('via') or []), l.get('mh'), '', '', '', '', lane_v,
                     '%d over-reach hops: %s' % (len(lv), dict(collections.Counter(lv))), ''])
    with open(out / (name + '.tsv'), 'w') as f:
        f.write('\t'.join(['worst_rank', 'lane', 'bits', 'hop', 'partition', 'hop_um', 'hop_lower_um', 'from_kind', 'to_kind', 'slot_kind', 'verdict',
                           'why', 'hop_xy']) + '\n')
        for r in rows:
            f.write('\t'.join('' if v is None else str(v) for v in r) + '\n')
    print('AUDIT %s top %d lanes (reach %.0f): %s -> %s' % (Path(a.record).name, len(order), reach, dict(verdicts), out / (name + '.tsv')))


# ================================================================ RECORD VIEW
def cmd_record(a):
    rec = load_json(a.record)
    name = a.name or re.sub(r'\.links\.json(\.gz)?$', '', Path(a.record).name)
    W, H = rec['outline'][:2]
    fig = plt.figure(figsize=(a.width, a.width * H / W * 0.92 + 1.4), dpi=a.dpi)
    ax = fig.add_axes([0.04, 0.09, 0.92, 0.84])
    ids, worst = draw_record(ax, rec, dict(top=a.top, arrows_max=0))
    s = summary(rec)
    fig.text(0.04, 0.965, '%s  |  %s' % (rec.get('label'), rec.get('revision')), color=INK, fontsize=11, fontweight='bold')
    fig.text(0.04, 0.945, summary_text(s), color=LABEL, fontsize=8)
    legend(fig, rec)
    png, svg = save(fig, a.out, name)
    links_tsv(rec, Path(a.out) / (name + '.links.tsv'), worst)
    print('RECORD %s: %s\n  %s\n  %s' % (name, summary_text(s), png, svg))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    def common(p):
        p.add_argument('--out', required=True)
        p.add_argument('--name')
        p.add_argument('--top', type=int, default=15, help='worst links highlighted (#1..#N)')
        p.add_argument('--dpi', type=int, default=170)
        p.add_argument('--width', type=float, default=11.0, help='inches per panel')
        p.add_argument('--label-fs', type=float, default=4.5)
    p = sub.add_parser('die')
    common(p)
    p.add_argument('--plan', required=True)
    p.add_argument('--reach', type=float)
    p.add_argument('--revision')
    p.add_argument('--highlight-type', nargs='*')
    p = sub.add_parser('type')
    common(p)
    p.add_argument('--plan', required=True)
    p.add_argument('--type', required=True)
    p.add_argument('--repo', default='.')
    p.add_argument('--die')
    p.add_argument('--ref-dirs', nargs='*', default=[])
    p.add_argument('--core-conns')
    p.add_argument('--delta', help='core_place.v1 | route_supply delta | CLEANSLATE {type: {inst: [x, y, orient]}}')
    p.add_argument('--after-plan', help='a whole plan to take the after type from')
    p.add_argument('--supply', action='store_true', help='overlay route_supply ratio maps (runs route_supply.py --maps)')
    p.add_argument('--route-supply', help='route_supply.py (default <repo>/tools/die_plan/route_supply.py)')
    p.add_argument('--release-cache')
    p.add_argument('--reach', type=float)
    p.add_argument('--short-labels', action='store_true')
    p.add_argument('--wmul', type=float, default=1.6)
    p.add_argument('--arrows-max', type=int, default=400)
    p.add_argument('--per-port', action='store_true', help='one link per core port (default: one per core pair, bits summed)')
    p.add_argument('--max-height', type=float, default=13.0, help='inches: tall types shrink to this panel height')
    p = sub.add_parser('record')
    common(p)
    p.add_argument('--record', required=True)
    p = sub.add_parser('audit', help='REAL / MODEL per over-reach hop of the top worst lanes of a die record')
    p.add_argument('--record', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--name')
    p.add_argument('--top', type=int, default=30)
    p.add_argument('--reach', type=float)
    a = ap.parse_args(argv)
    if a.cmd == 'type' and not a.route_supply:
        a.route_supply = str(Path(a.repo).resolve() / 'tools' / 'die_plan' / 'route_supply.py')
    dict(die=cmd_die, type=cmd_type, record=cmd_record, audit=cmd_audit)[a.cmd](a)


if __name__ == '__main__':
    main()
