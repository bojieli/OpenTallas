#!/usr/bin/env python3
"""GLOBAL-FP-Q core: data-flow graph, traffic/criticality model and ONE floorplan objective for the Qwen compute die.

Every candidate floorplan is a full placement of the 1637 die instances (same masters, same per-bit assigned pins as
the current generated graph) plus an optional logical->physical tile permutation P (tree/bword endpoints only; the
broadcast reaches every tile identically).  The scorer is identical for every candidate:

  * sum width x length         per-bit pin-centre HPWL, summed over bits (bit-um)
  * sum traffic x length       bit-um x activations/token of the bus (bit-um/token)
  * bits over reach            bits of buses whose longest per-bit pin pair exceeds REACH (490 um pin-to-pin)
  * relay flops                sum bits x (ceil(longest/REACH) - 1)
  * critical loops (stages)    ME loop = broadcast depth (xs_tap -> farthest tile) + reduction (any tile -> VM)
                               + VM -> xs_tap; collective loop; KV loop; exposed stage-cycles per AR token
  * worst cut                  coarse global-route estimate: L-routes of pin centroids on a 250-um grid, demand /
                               track capacity (channel M4..M9, over hard macros M8/M9 only), threshold 0.60
  * long returns               buses whose longest per-bit pair > 5 mm, each with a reason class

Assignment-pin geometry only: no route, real cut, clock phi-R, halo/PDN or TT/FF qualification.
"""
import collections, gzip, hashlib, json, math, re, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from orientation_search import Graph, load  # noqa: E402

GEOM = Path('/home/ubuntu/claude-takeover-20261007/qwen-native-controller-geometry-1015.json')
REACH = 490.0
TILE_MASTERS = ('qfd_tile_nk',)
FIELD_MASTERS = ('qfd_tile_nk', 'qfd_xcst_s', 'qfd_xcst_n', 'qfd_xcol_w', 'qfd_xcol_e')
FIXED_PREFIX = ('io_',)            # S-edge IO band (bump/PHY map); ucie_kv keeps the N edge (x may follow the spine)

# ---------------------------------------------------------------- traffic / criticality (provenance in TRAFFIC_NOTE)
ME_OPS, SU_OPS, LAYERS, ARS = 217, 612, 36, 73
TRAFFIC_NOTE = {
    'ME_OPS': '217 ME ops per AR token (results/arch/qwen_split_compute_1014/pm_h_cycle_price: -1 stage = -217 cyc/AR token; '
              'layer_candidate_program.hex 5-6 ME/layer x 36 + LM head)',
    'SU_OPS': '17 SU ops/layer x 36 = 612 (natural_dataflow/programme_activity.json.gz layer_candidate_program totals)',
    'LAYERS': '36 decoder layers: one KV/attention round trip per layer',
    'ARS': '2 all-reduce per layer + argmax = 73 collective commands per token (Q-COLL r10 cycle profile)',
    'unit': 'activations/token = how many times the bus carries one compiler-scheduled transfer per token; words per '
            'transfer are NOT in any source artifact (programme_activity physical_scheduled_cycles=null), so '
            'traffic = bits x activations is a LOWER BOUND with an explicit unknown multiplier per class',
}


def activity(b):
    """(activations per token, criticality, reason) for one bus, from its class/name."""
    n, c = b['b'], b['c']
    if c in ('clock_trunk', 'reset'):
        return 0, 'control', 'clock/reset tree (not a data transfer)'
    if c in ('tap', 'corridor', 'head_chain'):
        return ME_OPS, 'me_loop', 'activation broadcast to every tile, once per ME op'
    if c == 'tree_block':
        return ME_OPS, 'me_loop', 'in-block ordered partial-sum tree, once per ME op'
    if n.startswith(('bword_', 'pfrag_', 'slab_', 'rq_', 'rs_', 'rc_', 'rk_', 'tw_', 'ty_')):
        return ME_OPS, 'me_loop', 'block result -> band port -> res_ser -> VM, once per ME op'
    if n.startswith(('tt_c', 'tt_f', 'tt_lc', 'tt_lf', 'pword_', 'tt_ty', 'o4_sel', 'o4_upf', 'up4_sel', 'tt_mx', 'tt_ib',
                     'xs_', 'o4_me_en', 'o4_meok', 'rs_fault', 'tt_land')):
        return ME_OPS, 'me_loop', 'ME issue / completion control or activation source, once per ME op'
    if n in ('x3', 'x3m', 'attn_ret', 'd2d_fdi', 'seq_d2d', 'd2d_seq', 'o4_kvd', 'o4_pw'):
        return LAYERS, 'layer_loop', 'KV/attention die round trip, once per layer'
    if n.startswith(('emb',)):
        return 1, 'token_once', 'embedding fetch, once per token'
    if n.startswith(('seq_coll', 'coll_seq', 'ucie_', 'serdes_')):
        return ARS, 'layer_loop', 'collective all-reduce command/data, per AR'
    if c == 'crom' or n in ('o4_su_iss', 'o4_su_st', 'vm_seq_q', 'seq_vwr'):
        return SU_OPS, 'su_loop', 'SU op issue / constants / VM access, once per SU op'
    if n in ('o4_me_snap', 'o4_su_snap', 'o4_me_start'):
        return ME_OPS + SU_OPS, 'su_loop', 'sequencer handshake, every ME and SU op'
    return 1, 'none', 'unclassified (default 1/token)'


LONG_REASON = {
    'bword': 'block-root result to its band port tile in the spine: reduction transport, bounded by field radius',
    'tree_block': 'in-block ordered tree leg (vertical leg = one tile pitch 1486 um)',
    'head_chain': 'activation root -> first head column across the spine half-width',
    'corridor': 'column broadcast hop between stations (one tile pitch)',
    'seq_coll': 'hub sequencer <-> collective at the S-edge IO band (IO edge fixed by bump map)',
    'coll_seq': 'collective -> hub sequencer return (IO edge fixed)',
    'attn_ret': 'KV die PHY (N edge) -> VM: attention result return',
    'x3': 'SU -> KV link query/KV-write path to the N-edge d2d',
    'emb': 'embedding return from the KV/system die link',
    'serdes': 'IO-band internal: serdes PHY <-> xfifo along the S edge',
    'tt_': 'tree-top control between ctlm and band ports / lanes',
    'rs_': 'res_ser -> VM band result word',
    'rc_': 'VM -> res_ser credit-free handshake bit', 'rk_': 'res_ser -> VM ok bit',
    'pword': 'band lanes -> tree-top up4 word', 'o4_': 'sequencer control word between hub blocks',
    'crom': 'SU <-> constant buffer groups', 'o4_cb': 'SU <-> constant buffer groups',
    'seq_d2d': 'sequencer <-> d2d (KV link) control', 'd2d_seq': 'd2d (KV link) -> sequencer status',
}


def long_reason(name, cls):
    for k, v in LONG_REASON.items():
        if name.startswith(k) or cls == k:
            return v
    return cls


# ---------------------------------------------------------------- graph
class Die:
    def __init__(self, path=GEOM):
        self.d, self.sha = load(path)
        self.path = path
        self.g = Graph(self.d, REACH)
        self.base = {n: dict(i) for n, i in self.g.inst.items()}
        self.recs = self.g.data           # data buses with per-bit pin arrays
        self.ctrl = self.g.ctrl
        for r in self.recs + self.ctrl:
            act, crit, why = activity(r)
            r['act'], r['crit'], r['why'] = act, crit, why
        self.byname = {r['b']: r for r in self.recs}
        self.die = self.d['die']

    # nodes of the data-flow graph
    def nodes(self, model):
        out = []
        for n, i in model.items():
            grp = group_of(n, i['m'])
            out.append(dict(id=n, master=i['m'], x_um=round(i['x'], 3), y_um=round(i['y'], 3), w_um=round(i['w'], 3),
                            h_um=round(i['h'], 3), orient=i['o'], group=grp, fixed=n.startswith(FIXED_PREFIX),
                            area_mm2=round(i['w'] * i['h'] / 1e6, 5)))
        return out


def group_of(n, m):
    if m == 'qfd_tile_nk': return 'tile'
    if m.startswith('qfd_xcst'): return 'station'
    if m.startswith('qfd_xcol'): return 'head_column'
    if n.startswith('io_'): return 'io_band'
    if n in ('ucie_kv', 'd2d_rom', 'ckb_rom', 'rs_bump', 'x3_mux'): return 'kv_link'
    if n.startswith(('sp_port', 'sp_res_ser', 'sp_band_lanes')): return 'band_port'
    return 'hub'


def place(rec_end, model):
    n, loc = rec_end
    i = model[n]; o = i['o']; x = loc[:, 0].copy(); y = loc[:, 1].copy()
    if o in ('MY', 'R180'): x = i['w'] - x
    if o in ('MX', 'R180'): y = i['h'] - y
    return np.stack([i['x'] + x, i['y'] + y], 1)


def remap_ends(rec, P):
    """P (logical tile -> physical tile) applies to the reduction only: tree legs and block words. The broadcast
    (tap) and every other bus bind to physical slots."""
    if not P or not (rec['c'] == 'tree_block' or rec['b'].startswith('bword_')): return rec['ends']
    return [(P.get(n, n), loc) for n, loc in rec['ends']]


def bus_geom(rec, model, P=None):
    ends = remap_ends(rec, P)
    pts = np.stack([place(e, model) for e in ends])
    hp = (pts.max(0) - pts.min(0)).sum(1)
    u = pts[..., 0] + pts[..., 1]; v = pts[..., 0] - pts[..., 1]
    far = np.maximum(u.max(0) - u.min(0), v.max(0) - v.min(0))
    L = float(far.max())
    cen = pts.mean(1)                        # per-end pin centroid
    return float(hp.sum()), L, cen, ends, pts


def stages(L):
    return max(1, math.ceil(L / REACH))


# ---------------------------------------------------------------- critical loops
ME_PATH = re.compile(r'^(head_\w+|cor_\d+_\d+|tap_\d+_\d+|tree_\d+_\d+_\d+[ab]|bword_\d+|pfrag_\d+_.*|slab_rq_\d+|rq_\d+|rs_\d+)$')


def node_key(n, port, model):
    if model[n]['m'] in TILE_MASTERS:
        return (n, 'leaf') if port in ('t_out', 'tap') else (n, 'node')
    return (n, '*')


def me_loop(die, model, ev, P=None):
    """Longest stage path xs_tap -> any tile leaf (bd) and any tile leaf -> VM (red); + xs_aw (VM -> xs_tap)."""
    adj = collections.defaultdict(list)
    for k, r in enumerate(die.recs):
        if not ME_PATH.match(r['b']) or r['n'] <= 1: continue
        ends = ev[k][3]
        s = node_key(ends[0][0], _port(r, 0), model)
        for j in range(1, len(ends)):
            t = node_key(ends[j][0], _port(r, j), model)
            adj[s].append((t, stages(ev[k][1]), r['b']))
    # tile leaf -> node inside the same tile is a real edge (own t_out feeds own n_a): already a bus (tree_*_0_*a)
    import functools
    sys.setrecursionlimit(100000)

    @functools.lru_cache(maxsize=None)
    def longest_from(s):
        best = (0, ())
        for t, w, b in adj.get(s, ()):
            if t == s: continue
            v, path = longest_from(t)
            if v + w > best[0]: best = (v + w, (b,) + path)
        return best
    # broadcast: xs_tap down to tiles, stop at tile leaves
    bc_adj = {s: [(t, w, b) for t, w, b in v if not b.startswith(('tree_', 'bword_', 'pfrag_', 'slab_', 'rq_', 'rs_'))] for s, v in adj.items()}

    @functools.lru_cache(maxsize=None)
    def bd_from(s):
        best = (0, ())
        for t, w, b in bc_adj.get(s, ()):
            v, path = bd_from(t)
            if v + w > best[0]: best = (v + w, (b,) + path)
        return best
    bd, bd_path = bd_from(('xs_tap', '*'))
    red_adj = {s: [(t, w, b) for t, w, b in v if b.startswith(('tree_', 'bword_', 'pfrag_', 'slab_', 'rq_', 'rs_'))] for s, v in adj.items()}

    @functools.lru_cache(maxsize=None)
    def red_from(s):
        best = (0, ())
        for t, w, b in red_adj.get(s, ()):
            if t == s: continue
            v, path = red_from(t)
            if v + w > best[0]: best = (v + w, (b,) + path)
        return best
    tiles = [n for n, i in model.items() if i['m'] in TILE_MASTERS]
    red, red_path, red_tile = 0, (), None
    tree_max = 0
    for t in tiles:
        v, path = red_from((t, 'leaf'))
        if v > red: red, red_path, red_tile = v, path, t
    # split red into in-block tree and transport for reporting
    k_aw = next(k for k, r in enumerate(die.recs) if r['b'] == 'xs_aw')
    aw = stages(ev[k_aw][1])
    tree_part = sum(stages(ev[die_index(die, b)][1]) for b in red_path if b.startswith('tree_'))
    return dict(bd=bd, red=red, red_tree=tree_part, red_transport=red - tree_part, vm_to_tap=aw, me_loop=bd + red + aw,
                bd_path_tail=list(bd_path[-4:]), bd_end=bd_path[-1] if bd_path else None, red_from_tile=red_tile,
                red_path=list(red_path))


_IDX = {}


def die_index(die, b):
    key = id(die.recs)
    if key not in _IDX:
        _IDX[key] = {r['b']: k for k, r in enumerate(die.recs)}
    return _IDX[key][b]


def _port(r, j):
    return r['port'][j]


def layer_loops(die, ev):
    st = {r['b']: stages(ev[k][1]) for k, r in enumerate(die.recs)}
    coll = sum(st.get(b, 0) for b in ('seq_coll', 'seq_coll_x', 'coll_seq', 'coll_seq_x'))
    kv = sum(st.get(b, 0) for b in ('x3', 'x3m', 'attn_ret'))
    su = max(st.get(f'o4_cb_a_{g}', 0) + st.get(f'o4_cb_q_{g}', 0) for g in range(8))
    return dict(coll_loop=coll, kv_loop=kv, su_const_loop=su)


# ---------------------------------------------------------------- congestion (coarse)
BIN = 250.0
CAP_CH, CAP_MAC = 1 / 0.048 + 1 / 0.064 + 1 / 0.080, 1 / 0.080     # tracks/um per direction (M4/M6/M8 | M8) etc.


def congestion(die, model, ev):
    W, H = die.die['w'], die.die['h']
    nx, ny = int(math.ceil(W / BIN)), int(math.ceil(H / BIN))
    occ = np.zeros((nx, ny))
    for i in model.values():
        x0, x1 = i['x'] / BIN, (i['x'] + i['w']) / BIN; y0, y1 = i['y'] / BIN, (i['y'] + i['h']) / BIN
        for ix in range(max(0, int(x0)), min(nx, int(math.ceil(x1)))):
            fx = min(x1, ix + 1) - max(x0, ix)
            if fx <= 0: continue
            for iy in range(max(0, int(y0)), min(ny, int(math.ceil(y1)))):
                fy = min(y1, iy + 1) - max(y0, iy)
                if fy > 0: occ[ix, iy] += fx * fy
    occ = np.clip(occ, 0, 1)
    cap = BIN * (occ * CAP_MAC + (1 - occ) * CAP_CH)          # tracks across one bin edge (either direction)
    dh = np.zeros((nx, ny)); dv = np.zeros((nx, ny))           # horizontal wires crossing bin (ix,iy) ; vertical
    for k, r in enumerate(die.recs):
        pts = ev[k][4]; n = r['n']                              # E x bits x 2 per-bit pins
        nb = pts.shape[1]; step = max(1, int(math.ceil(nb / 16)))
        for c0 in range(0, nb, step):                          # up to 16 bundles per bus, each at its own pin centroid
            sub = pts[:, c0:c0 + step].mean(1); w = min(step, nb - c0) * (n / nb)
            a = sub[0]
            for j in range(1, len(sub)):
                b = sub[j]
                ax, ay = int(a[0] // BIN), int(a[1] // BIN); bx, by = int(b[0] // BIN), int(b[1] // BIN)
                ax, bx = (min(max(q, 0), nx - 1) for q in (ax, bx)); ay, by = (min(max(q, 0), ny - 1) for q in (ay, by))
                if ax == bx and ay == by: continue
                xl, xh = sorted((ax, bx)); yl, yh = sorted((ay, by))
                dh[xl:xh + 1, ay] += w / 2; dv[bx, yl:yh + 1] += w / 2
                dv[ax, yl:yh + 1] += w / 2; dh[xl:xh + 1, by] += w / 2
    rh, rv = dh / cap, dv / cap
    r = np.maximum(rh, rv)
    flat = np.sort(r.ravel())[::-1]
    worst = np.unravel_index(np.argmax(r), r.shape)
    return dict(worst_cut=round(float(flat[0]), 3), worst_bin_um=[round(worst[0] * BIN), round(worst[1] * BIN)],
                p999=round(float(np.quantile(r, 0.999)), 3), bins_over_060=int((r > 0.60).sum()), bins=int(r.size),
                note='coarse L-route estimate of per-bus pin centroids on a 250-um grid vs M4..M9 channel / M8-M9 '
                     'over-macro tracks; NOT a GRT result'), r


# ---------------------------------------------------------------- one objective
def score(die, model, P=None, name='?', want_grid=False):
    ev = [bus_geom(r, model, P) for r in die.recs]
    tot = dict(bit_um=0.0, traffic_bit_um=0.0, bits_over_reach=0, relay_flops=0, worst_leg_um=0.0)
    fam = collections.defaultdict(lambda: dict(bits=0, bit_um=0.0, relay_flops=0))
    longs = []
    for k, r in enumerate(die.recs):
        hp, L, cen, ends = ev[k][:4]
        rl = stages(L) - 1
        tot['bit_um'] += hp; tot['traffic_bit_um'] += hp * r['act']
        tot['relay_flops'] += rl * r['n']; tot['worst_leg_um'] = max(tot['worst_leg_um'], L)
        if L > REACH: tot['bits_over_reach'] += r['n']
        f = fam[r['c']]; f['bits'] += r['n']; f['bit_um'] += hp; f['relay_flops'] += rl * r['n']
        if L > 5000 and r['n'] > 1:
            longs.append(dict(bus=r['b'], cls=r['c'], bits=r['n'], longest_um=round(L), stages=stages(L), reason=long_reason(r['b'], r['c'])))
    me = me_loop(die, model, ev, P)
    ll = layer_loops(die, ev)
    exposed = ME_OPS * me['me_loop'] + ARS * ll['coll_loop'] + LAYERS * ll['kv_loop']
    cong, grid = congestion(die, model, ev)
    longs.sort(key=lambda x: -x['longest_um'] * x['bits'])
    res = dict(name=name, bit_um=round(tot['bit_um']), traffic_bit_um_per_token=round(tot['traffic_bit_um']),
               bits_over_reach=tot['bits_over_reach'], relay_flops=tot['relay_flops'],
               relay_area_mm2=round(tot['relay_flops'] / 26 * 74.65 / 1e6, 3), worst_leg_um=round(tot['worst_leg_um']),
               **{k: me[k] for k in ('bd', 'red', 'red_tree', 'red_transport', 'vm_to_tap', 'me_loop')}, **ll,
               exposed_stage_cycles_per_token=exposed, me_detail=dict(bd_tail=me['bd_path_tail'], red_from=me['red_from_tile'], red_path=me['red_path']),
               congestion=cong, families={k: dict(bits=v['bits'], Mbit_um=round(v['bit_um'] / 1e6, 2), relay_flops=v['relay_flops']) for k, v in sorted(fam.items())},
               long_links=longs[:40], long_link_count=len(longs))
    if want_grid:
        return res, ev, grid
    return res, ev


def links_json(die, model, ev, name, metrics, P=None, unknowns=()):
    links = []
    for k, r in enumerate(die.recs + die.ctrl):
        if k < len(die.recs):
            hp, L, cen, ends = ev[k][:4]
        else:
            hp, L, cen, ends = bus_geom(r, model, P)[:4]
        ports = r['port']
        src = dict(node=ends[0][0], port=ports[0], x_um=round(float(cen[0][0]), 2), y_um=round(float(cen[0][1]), 2))
        dst = [dict(node=ends[j][0], port=ports[j], x_um=round(float(cen[j][0]), 2), y_um=round(float(cen[j][1]), 2)) for j in range(1, len(ends))]
        links.append(dict(id=r['b'], **{'class': r['c']}, bits=r['n'], src=src, dst=dst, activations_per_token=r['act'],
                          traffic_bits_per_token=r['n'] * r['act'], critical=r['crit'], length_um=round(L, 2),
                          hpwl_bit_um=round(hp, 1), stages=stages(L), relays=stages(L) - 1, over_reach=L > REACH,
                          provenance=f"{die.path.name} sha256 {die.sha[:12]} bus {r['b']}; activity: {r['why']}"))
    return dict(schema='opentallas.floorplan.links.v1', design='qwen_rom_compute', candidate=name, source_graph=str(die.path),
                source_graph_sha256=die.sha, die=dict(w_um=die.die['w'], h_um=die.die['h'], mm2=die.die['mm2']), reach_um=REACH,
                nodes=die.nodes(model), links=links, metrics={k: v for k, v in metrics.items() if k not in ('long_links',)},
                traffic_note=TRAFFIC_NOTE, logical_tile_map=P or {}, unknowns=list(unknowns), qualification=False)


def attach_ports(die):
    """Graph keeps (inst, loc) only; recover port names per end for node keys / links."""
    by = {b['b']: b for b in die.d['buses']}
    for r in die.recs + die.ctrl:
        r['port'] = [p for _, p in by[r['b']]['e']]


# ---------------------------------------------------------------- explorer record (opentallas.dataflow.links.v1)
CRIT_SCORE = dict(me_loop=1.0, su_loop=0.6, layer_loop=0.4, token_once=0.1, control=0.0, none=0.0)


def dataflow_record(die, model, ev, rid, label, P=None, note=''):
    """Record in the data-flow explorer schema (el1015-dataflow-viz.log): columnar blocks, compact links with
    t (traffic bits/token), cr (criticality 0..1: 1 = on the per-ME-op loop), lat/s (geometric stages at REACH)."""
    names = list(model)
    idx = {n: k for k, n in enumerate(names)}
    blocks = dict(name=names, master=[model[n]['m'] for n in names], kind=[model[n]['m'] for n in names],
                  group=[group_of(n, model[n]['m']) if group_of(n, model[n]['m']) not in ('tile', 'station') else
                         re.sub(r'(_\d+)+$', '', n) for n in names],
                  reg=[1 if model[n]['m'].startswith('qfd_rly') else 0 for n in names],
                  x=[round(model[n]['x'], 3) for n in names], y=[round(model[n]['y'], 3) for n in names],
                  w=[round(model[n]['w'], 3) for n in names], h=[round(model[n]['h'], 3) for n in names])
    links = []
    for k, r in enumerate(die.recs):
        hp, L, cen, ends = ev[k][:4]
        st = stages(L)
        e = [[idx[n], p, round(float(c[0]), 1), round(float(c[1]), 1), 'pin'] for (n, _), p, c in zip(ends, r['port'], cen)]
        links.append(dict(i=r['b'], c=r['c'], b=r['n'], d=1, e=e, s=st, t=r['n'] * r['act'], cr=CRIT_SCORE[r['crit']], lat=st,
                          n=f"activity {r['act']}/token ({r['why']}); stages = ceil(longest per-bit pin pair / {REACH:.0f} um)"))
    return dict(schema='opentallas.dataflow.links.v1', id=rid, label=label, design='qwen_rom', token_designs=['qwen_rom'],
                revision='globalfp-1015', role='candidate', scope='Qwen compute die, all data buses of the current generated graph',
                outline=[die.die['w'], die.die['h']], reach_um=REACH, reach_source='GLOBAL-FP brief: ~490 um pin-to-pin one-cycle reach',
                stages_explicit=False, registers='relay stages are geometric (ceil(L/490)); no relay instances placed',
                direction='first end drives (export order)', pins='per-bit assigned pin rectangles, centroid per port, orientation applied',
                note=note + ' cr: 1.0 = per-ME-op loop (217/token), 0.6 SU loop, 0.4 per-layer loop, 0.1 once/token; t = bits x activations/token (lower bound)',
                provenance=dict(inputs=[dict(path=str(die.path), sha256=die.sha, role='current generated system geometry + master pins')]),
                blocks=blocks, links=links)
