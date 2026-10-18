#!/usr/bin/env python3
"""S81-DV frame wrapper masters col_h9 / col_h10 / col_h9_MX (S81U-3F, 2026-10-17; stub audit finding S-1).

The S81-DV die (results/arch/s81_dv_1016, p4h/p4i) places 122 ROM-column frames as three masters: col_h9 (9 slots),
col_h10 (10 slots) and col_h9_MX (= col_h9 RTL, mirrored placement).  Until now no RTL existed for them.  This tool
emits them from the ROM-column frame that tools/dsrom_s81_fulldie.py builds per frame (build_r8 + buses, region
frame_<r>), as tools/s81/cluster_extract.py extracted it from the c26l GEN (results/arch/s81_dv_1016/frame/src):

  SOURCE  the c26l column cluster master of the class (one per (pairs, BF) class; the representative with the most
          roots): h9 = dsfd_column_h9_v10 (12 q + 3 BF pairs, 7 roots), h10 = dsfd_column_h10a_v17 (12 q + 4 BF, 3 roots;
          see DECISION in the record).  Every frame boundary net of that cluster goes through its column FIFO, so the
          frame is: x in (xd 566 / xd2 538 on xf / xf2), return out (rd 70), column clock, reset -- and nothing else.
          Every element input (cfg, go, f_prog, go_tag, ef, xs_*, BF xb, ROM q, status) is driven inside the frame
          by its real producer (cfg7 sequencers + cfg ROMs, qbank_S/N, slot stations, the cfifo lane words).

  DV CUT  (p4h links, ot_s81sl_slice x-chain word)
          x[1103:0]  in : 4 x 276-b lanes, lane k = x[276k +: 276]; x[565:0] = cfifo xd = {xw[564:0], marker},
                          x[1103:566] = cfifo xd2 = {xw[1100:565], xw[0], marker}
          xk[3:0]    in : the lanes' forwarded clocks (last die station ck_o); cfifo xf = xk[1] (xd = lanes 0-1 + 14 b
                          of lane 2), xf2 = xk[2] (xd2 = 262 b of lane 2 + lane 3)
          xo[1103:0] out: the x-chain forward to the next frame: one flop-first dsfd_dvrly_276_NS station per lane on
                          the lane's own forwarded clock (closed view, native PASS); xok[k] = its ck_o
          ret[69:0]  out: cfifo_crs rd = {rr[67:0], rr[0], rsync_s} (ot_s81sl_cap consumes 8 x 70)
          clk        in : frame column clock root (every leaf, cfg ROM, station, node, relay)
          cr, cr_s   in : dsfd_cfifo_crs north / south roots (same PLL clock, phase 0)
          rst_n      in : raw regional reset (cfifo rst: synchronised inside on cr; xo station rs)

  CHANGES vs the c26l frame (each one recorded in the JSON):
    * dsfd_cfifo (c26 glue, ck/co/rf pins) -> dsfd_cfifo_crs (main c2e5317db r5f, CLOSED, native PASS);
      the c26 co (= ck pass-through column root) becomes the frame clk port; rf (= cr) is not a frame pin: the die
      forwards the return lane clock from the region root (p4i fwd_* cells)
    * ot_s81_cfg7_seq_bfp LAYOUT 1 / PINREG 1 (p4g frame_bind.json; s81coll_cfg7_seq_bfp_pr-pr1-ef2866774 CLOSED) and
      ot_s81_cfg7_seq PQ 1 / LAYOUT 1 / PINREG 1 (s81coll_cfg7_seq_pr-pr3-f8e89fc72 CLOSED): both read il7 cfg images
    * no constant inputs: ot_s81_sstn_base566 (status <= e0|e1|c0|c1|si|{nf,0}) drives an unused OR input from the
      slot's own real status: e1 <- e0, c1 <- c0, si (top station) <- e0, nf (no tree fault here) <- e0[1]
      (OR-idempotent: status bit-identical, zero constants); relays fed constant pad bits whose padded outputs nobody reads become exact-width
      relay masters (dsfd_rly_<W>_<faces>, ot_s81_rly, same RSREG) in rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv
    * instance names frame-local (pair p -> e<p - p0>, root r dropped); ROM / element INSTANCE = {INSTANCE, "_<name>"}
    * return r1 skew (S81U-3F2, D2): one dsfd_rly_63_NS / _WE stage at every q leaf node's b (second-row) input, so an
      element's two rows reach its leaf on consecutive edges (ot_s81_retn_static F1); the row / slot placement that
      keeps every node fault-free is the compiler's frame return plan (tools/s81_dv/frame_return_plan.py)

    python3 tools/s81_dv/frame_wrap.py emit [--out-rtl rtl/dsrom_sys/s81_dv/frame] [--record results/arch/s81_dv_1016/frame]
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_port_bind as DPB  # noqa: E402
import dsrom_s81_fulldie as F  # noqa: E402

SCHEMA = 'opentallas.s81_dv.frame_wrap.v1'
SRC = ROOT / 'results/arch/s81_dv_1016/frame/src'
CLASSES = {
    # master: (source module file, module name, slots, q pairs, BF pairs)
    'col_h9': ('c26l_h9_v10.v.gz', 'dsfd_column_h9_v10', 9, 12, 3),
    'col_h10': ('c26l_h10a_v17.v.gz', 'dsfd_column_h10a_v17', 10, 12, 4),
}
MIRROR = {'col_h9_MX': 'col_h9'}
PROVENANCE = dict(
    generator='tools/dsrom_s81_fulldie.py (c26l, claude/sdie-1815 aacb894e4 + flags of S-DIE 1815 10-16) -> '
              'tools/s81/cluster_extract.py extract',
    plan_sha256='2275d00c9c7929c25aae7e72a8b4c4ce8955c29a1d3c933d59b616c169e26a6f',
    die_v_sha256='e0665824dd6cec413e7dbe1d3a6c53f6c3148e4d0a606900b67a8bcbaa644765',
    extract='ot-epyc4:/srv/opentallas-scratch/claude/s81dv/ref_c26l_extract (die_hier.v c01d3527..., clusters.json '
            '579e7370...; the c26l GEN scratch was deleted 10-17 with the hub trials, the extract is kept)')
LANE, NL = 276, 4
XD, XD2, RD = 566, 538, 70
XF_LANE, XF2_LANE = 1, 2
XO_MASTER = 'dsfd_dvrly_276_NS'
RTL_FILES = [
    'rtl/dsrom_sys/s81_glue/dsfd_rly_masters.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_536.sv',
    'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_266ew.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv',
    'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_c26l.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_gen18.sv',
    'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_v16.sv',
    'rtl/dsrom_sys/s81_static_net/ot_s81_sstn_base566.sv', 'rtl/dsrom_sys/s81_static_net/ot_s81_sstn_payload536.sv',
    'rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_crs.sv', 'rtl/dsrom_sys/s81_die_bind/dsfd_bf_col.sv',
    'rtl/dsrom_sys/s81_die_bind/dsfd_bf_front_static.sv', 'rtl/dsrom_sys/s81_die_bind/dsfd_bf_front_roots.sv',
    'rtl/v41die/ot_s81_cfg7_seq.sv',
    'rtl/v41die/ot_s81_cfg7_seq_bfp.sv', 'rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv',
    'physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v',
] + [f'rtl/dsrom_sys/s81_static_net/gen/{m}.sv' for m in
     ('dsfd_node_NNfu', 'dsfd_node_NNfd', 'dsfd_node_LLfu', 'dsfd_node_LLfd', 'dsfd_node_LLd', 'dsfd_rstg',
      'dsfd_sstn_e0e1c0c1_cp1')] + [f'rtl/dsrom_sys/s81_fill2/gen19b/{m}.sv' for m in ('dsfd_qbank_N', 'dsfd_qbank_S')]
EXACT_RLY = 'rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv'
CONST = re.compile(r"^\d+'[bhd][0-9a-fA-FxXzZ_]+$")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------ source netlist
def parse_column(text, name):
    m = re.search(r'\bmodule\s+%s\s*\((.*?)\);(.*?)\bendmodule' % re.escape(name), text, re.S)
    assert m, name
    body = m.group(2)
    ports = {}
    for d in re.finditer(r'^\s*(input|output)\s+(\w+)\s*;', body, re.M):
        ports[d.group(2)] = d.group(1)
    insts = []
    for im in re.finditer(r'^\s*(\w+)\s+(\w+)\s*\((\s*\..*?)\);\s*$', body, re.M | re.S):
        mst, iname, conns = im.groups()
        if mst in ('input', 'output', 'wire'):
            continue
        cs = collections.OrderedDict()
        for c in re.finditer(r'\.(\w+)\s*\(\s*(\{.*?\}|[^()]*?)\s*\)', conns, re.S):
            v = c.group(2).strip()
            cs[c.group(1)] = [b.strip() for b in v[1:-1].split(',')] if v.startswith('{') else ([v] if v else [])
        insts.append(dict(master=mst, name=iname, conns=cs))
    assert not re.search(r'\bassign\b', body), 'unexpected assign in the source cluster'
    return ports, insts


def rtl_index():
    idx = {}
    for f in RTL_FILES:
        t = DPB.preprocess(DPB.strip_comments((ROOT / f).read_text()), {})
        for mod in DPB.parse_modules(t, f):
            idx.setdefault(mod.name, mod)
    return idx


def port_dir(idx, mst, port):
    return idx[mst].ports[port][0]


# ------------------------------------------------------------------------------------------------ naming
def local_names(children, insts):
    """c26l child originals (pair ids / root ids) -> frame-local names"""
    orig = {c['instance']: c['original'] for c in children}
    pairs = sorted({int(m.group(1)) for o in orig.values() for m in [re.fullmatch(r'e(\d+)[we]?', o)] if m})
    p0 = pairs[0]
    assert pairs == list(range(p0, p0 + len(pairs))), pairs
    roots = {int(m.group(1)) for o in orig.values() for m in [re.fullmatch(r'n(\d+)_\d+', o)] if m}
    assert len(roots) == 1
    r = roots.pop()
    assert not (p0 <= r < p0 + len(pairs)), 'root id inside the pair range: names would be ambiguous'

    def loc(o):
        for pat, fn in ((r'e(\d+)([we]?)', lambda g: f'e{int(g[0]) - p0}{g[1]}'),
                        (r'c(\d+)_(\d+)', lambda g: f'c{int(g[0]) - p0}_{g[1]}'),
                        (r's(\d+)', lambda g: f's{int(g[0]) - p0}'),
                        (r'b([ns])(\d+)', lambda g: f'b{g[0]}{int(g[1]) - p0}'),
                        (r'n%d_(\d+)' % r, lambda g: f'n{g[0]}'),
                        (r'rg%d_(\d+)' % r, lambda g: f'rg{g[0]}'),
                        (r't%d_(\d+)(.*)' % r, lambda g: f't{g[0]}{g[1]}'),
                        (r'cf%d' % r, lambda g: 'cf')):
            m = re.fullmatch(pat, o)
            if m:
                return fn(m.groups())
        m = re.fullmatch(r'y_([a-z0-9]+)_(\d+)_(.*)', o)
        if m:
            k, n, rest = m.group(1), int(m.group(2)), m.group(3)
            if n == r:
                return f'y_{k}_{rest}'
            assert p0 <= n < p0 + len(pairs), o
            return f'y_{k}_p{n - p0}_{rest}'
        raise ValueError(f'unnamed child {o}')
    out = {}
    for it in insts:
        out[it['name']] = 'u_' + loc(orig[it['name']])
    assert len(set(out.values())) == len(out)
    return out, dict(root=r, pair0=p0, pairs=len(pairs))


# ------------------------------------------------------------------------------------------------ transform
def build(master, idx, params_q, rstp, bf_front='roots', r1_skew=True):
    fn, mod, slots, nq, nbf = CLASSES[master]
    text = gzip.decompress((SRC / fn).read_bytes()).decode()
    ports, insts = parse_column(text, mod)
    cl = json.loads(gzip.decompress((SRC / 'c26l_sel_clusters.json.gz').read_bytes()))
    cluster = next(c for c in cl['clusters'] if c['master'] == mod)
    names, frame_ids = local_names(cluster['children'], insts)
    cnt = collections.Counter(i['master'] for i in insts)
    assert cnt['ot_v41_rom_elem_q_qxpq_w10'] == nq and cnt['dsfd_bf_front_static'] == nbf, (master, cnt)
    rec = dict(master=master, source=dict(file=f'results/arch/s81_dv_1016/frame/src/{fn}', sha256=sha(SRC / fn),
                                          module=mod, roots=cluster['roots'], c26l_root=frame_ids['root'],
                                          pair0=frame_ids['pair0']),
               slots=slots, pairs=dict(q=nq, bf=nbf), changes=[])
    # ---- the column FIFO and the frame boundary
    cfs = [i for i in insts if i['master'] == 'dsfd_cfifo']
    assert len(cfs) == 1
    cf = cfs[0]
    c = cf['conns']
    bmap = {}                                   # source top bit -> new expression

    def bind_top(bits, port, width, off=0):
        assert len(bits) == width, (port, len(bits))
        for k, b in enumerate(bits):           # MSB first
            assert ports.get(b), (port, b)
            bmap[b] = f'{port}[{off + width - 1 - k}]'
    bind_top(c['xd'], 'x', XD, 0)
    bind_top(c['xd2'], 'x', XD2, XD)
    bind_top(c['rd'], 'ret', RD, 0)
    bmap[c['xf'][0]] = None
    bmap[c['xf2'][0]] = None
    bmap[c['rst'][0]] = 'rst_n'
    bmap[c['ck'][0]] = None
    bmap[c['rf'][0]] = None
    co = c['co'][0]
    assert set(ports) == set(bmap), sorted(set(ports) ^ set(bmap))[:8]
    uses = collections.Counter(b for i in insts for v in i['conns'].values() for b in v)
    for p in (c['xf'][0], c['xf2'][0], c['ck'][0], c['rf'][0]):
        assert uses[p] == 1, (p, uses[p])          # only the cfifo pin: safe to drop
    rec['changes'].append(dict(kind='cfifo_rebind', old='dsfd_cfifo (c26 glue: ck/co/rf pins, CFIFO_V2 + x2pair ingress)',
                               new='dsfd_cfifo_crs (main; r5f-507e1b0c3 CLOSED TT +71.04 / FF +17.32, native PASS)',
                               note=f'c26 co net {co} (= ck) -> frame port clk; rf (= cr) dropped (the die forwards the '
                                    'return clock from the region root); xf <- xk[%d], xf2 <- xk[%d]; cr, cr_s ports'
                                    % (XF_LANE, XF2_LANE)))
    newc = collections.OrderedDict()
    for p in ('cc', 'rd', 'ri', 'rs', 'rst', 'st', 'xa', 'xb', 'xd', 'x2', 'xd2'):
        newc[p] = c[p]
    newc['xf'] = [f'xk[{XF_LANE}]']
    newc['xf2'] = [f'xk[{XF2_LANE}]']
    newc['cr'] = ['cr']
    newc['cr_s'] = ['cr_s']
    cf['master'], cf['conns'] = 'dsfd_cfifo_crs', newc
    # ---- net renaming (top bits and the column clock)

    def ren(b):
        if b == co:
            return 'clk'
        if b in bmap:
            assert bmap[b] is not None, b
            return bmap[b]
        return b
    for it in insts:
        for p, v in it['conns'].items():
            it['conns'][p] = [ren(b) for b in v]
    # ---- drivers / readers
    drv, readers = {}, collections.defaultdict(list)
    for it in insts:
        for p, v in it['conns'].items():
            d = port_dir(idx, it['master'], p)
            for k, b in enumerate(v):
                if d == 'output':
                    assert b not in drv, ('multi-driven', b)
                    drv[b] = (it['name'], p, k)
                else:
                    readers[b].append((it['name'], p, k))
    # ---- constant inputs
    ties = collections.Counter()
    exact = {}
    for it in insts:
        cs = it['conns']
        consts = {p: [k for k, b in enumerate(v) if CONST.match(b)] for p, v in cs.items()}
        consts = {p: k for p, k in consts.items() if k}
        if not consts:
            continue
        if it['master'] == 'ot_s81_sstn_base566':
            # status <= e0 | e1 | c0 | c1 | si | {nf, 0}: an unused OR input takes the slot's own e0 / c0 (OR-idempotent)
            assert 'e0' not in consts and 'c0' not in consts, it['name']
            for p, src in (('e1', 'e0'), ('c1', 'c0'), ('si', 'e0')):
                if p in consts:
                    assert len(consts[p]) == len(cs[p]) == 2, (it['name'], p)
                    cs[p] = list(cs[src])
                    ties[f'base566.{p}<-{src}'] += 1
            if 'nf' in consts:
                cs['nf'] = [cs['e0'][0]]           # MSB first: e0[1]
                ties['base566.nf<-e0[1]'] += 1
            assert not [b for v in cs.values() for b in v if CONST.match(b)], it['name']
        elif re.fullmatch(r'dsfd_rly_\d+_[NSEW]{2}', it['master']):
            assert set(consts) == {'i'}, (it['name'], consts)
            pos = set(consts['i'])
            o = cs['o']
            dead = [o[k] for k in pos]
            assert all(not readers.get(b) for b in dead), (it['name'], 'padded relay output is read')
            w = len(cs['i']) - len(pos)
            face = it['master'].rsplit('_', 1)[1]
            body = idx[it['master']].body
            rsreg = int(re.search(r'RSREG\((\d+)\)', body).group(1)) if 'RSREG' in body else 0
            nm = f'dsfd_rly_{w}_{face}'
            exact[nm] = (w, rsreg, it['master'])
            ties[f'{it["master"]}->{nm} ({len(pos)} pad bits)'] += 1
            cs['i'] = [b for k, b in enumerate(cs['i']) if k not in pos]
            cs['o'] = [b for k, b in enumerate(o) if k not in pos]
            it['master'] = nm
        else:
            raise ValueError(f'constant input on {it["master"]} {it["name"]}: {consts}')
    rec['changes'].append(dict(kind='constants_removed', counts=dict(ties)))
    # ---- BF front: the closed physical ABI of the same front (h03-392d7efcb CLOSED, native PASS)
    if bf_front == 'roots':
        n_ = 0
        for it in insts:
            if it['master'] != 'dsfd_bf_front_static':
                continue
            cs = it['conns']
            xb = cs.pop('xb')                       # MSB first, 1068
            assert len(xb) == 1068 and cs['io_clk'] == ['clk'], it['name']
            new = collections.OrderedDict()
            for p, v in cs.items():
                new[p] = v
            new['xb_data'] = xb[:1024]               # xb[1067:44]
            new['xb_meta'] = xb[1024:]               # xb[43:0]
            for p in ('io_n', 'io_w', 'io_e'):
                new[p] = ['clk']
            it['master'], it['conns'] = 'dsfd_bf_front_roots', new
            n_ += 1
        rec['changes'].append(dict(kind='bf_front_roots', count=n_, note='dsfd_bf_front_static -> dsfd_bf_front_roots '
                                   '(same front, physical ABI: xb = {xb_data, xb_meta}; io_n / io_w / io_e face clock '
                                   'roots = the column clock); --bf-front static keeps the generator source'))
    # ---- x-chain forward stations
    for k in range(NL):
        insts.append(dict(master=XO_MASTER, name=f'xo{k}', conns=collections.OrderedDict(
            ck=[f'xk[{k}]'], rs=['rst_n'], i=[f'x[{LANE * k + LANE - 1 - j}]' for j in range(LANE)],
            o=[f'xo[{LANE * k + LANE - 1 - j}]' for j in range(LANE)], ck_o=[f'xok[{k}]'])))
        names[f'xo{k}'] = f'u_xo{k}'
    rec['changes'].append(dict(kind='x_forward', note=f'{NL} x {XO_MASTER} (one flop-first stage, own lane forwarded '
                                                      'clock in / ck_o out); +1 edge per frame on the x chain'))
    # ---- return-tree r1 skew (lane S81U-3F2, decision D2): one register stage on every q element's second-row leaf path
    if r1_skew:
        rec['changes'].append(add_r1_skew(insts, names, idx))
    # ---- parameters
    pmap = {}
    for it in insts:
        m_ = it['master']
        nm = names[it['name']][2:]
        ps = collections.OrderedDict()
        if m_ == 'ot_v41_rom_elem_q_qxpq_w10':
            ps.update(params_q)
            if rstp:
                ps['RSTP'] = 1
        elif m_ == 'ot_s81_cfg7_seq':
            ps['PQ'] = 1                            # closed view s81coll_cfg7_seq_pr-pr3-f8e89fc72 (spec params)
            ps['LAYOUT'] = 1
            ps['PINREG'] = 1
        elif m_ == 'ot_s81_cfg7_seq_bfp':
            ps['LAYOUT'] = 1
            ps['PINREG'] = 1
        if m_ in ('ot_v41_rom_elem_q_qxpq_w10', 'ot_rom_4096x72_m8', 'dsfd_bf_front_static', 'dsfd_bf_front_roots',
                  'dsfd_bf_col'):
            ps['INSTANCE'] = f'{{INSTANCE, "_{nm}"}}'
        pmap[it['name']] = ps
    rec['params'] = {m_: dict(next(pmap[i['name']] for i in insts if i['master'] == m_)) for m_ in
                     ('ot_v41_rom_elem_q_qxpq_w10', 'ot_s81_cfg7_seq', 'ot_s81_cfg7_seq_bfp')}
    rec['members'] = dict(sorted(collections.Counter(i['master'] for i in insts).items()))
    return insts, names, pmap, exact, rec


SKEW_MASTER = {'S': 'dsfd_rly_63_NS', 'E': 'dsfd_rly_63_WE'}     # by the output face of the stage it follows


def add_r1_skew(insts, names, idx):
    """D2 (static return tree, ot_s81_retn_static F1): an NB=2 element emits its two rows r0 / r1 (rows 2R, 2R+1, never
    golden siblings) on the SAME edge into ONE leaf node (a = r0, b = r1), so both would leave the sibling window on one
    edge.  One 63-b relay stage (closed dsfd_rly_63_NS / _WE, continuing the last stage's output face) at every leaf
    node's b input delays r1 by exactly one edge: the leaf then forwards r0 at t + 13 and r1 at t + 14, and every node
    above sees an element's two rows on consecutive edges (r0 merges with r0, r1 with r1).  Cost: +1 edge on odd rows
    only (the compiler's return calendar, tools/s81_dv/frame_return_plan.py, carries it as link_b + 1)."""
    drv = {}
    for it in insts:
        for p, v in it['conns'].items():
            m_ = it['master']
            d = ('output' if p in ('o', 'ck_o') else 'input') if m_ not in idx else port_dir(idx, m_, p)
            if d == 'output':
                for k, b in enumerate(v):
                    drv[b] = (it, p, k)

    def origin(net):
        last = None
        while net in drv:
            it, p, k = drv[net]
            m_ = it['master']
            if m_.startswith('dsfd_rly') or m_ == 'dsfd_rstg':
                last = last or it
                net = it['conns']['i'][k]
            elif m_.startswith('dsfd_qbank'):
                net = it['conns']['e_' + p[2:]][k]
            else:
                return it, p, k, last
        return None, None, None, last
    n_ = collections.Counter()
    for it in list(insts):
        if not it['master'].startswith('dsfd_node_LL'):
            continue
        src, p, k, last = origin(it['conns']['b'][-1])
        if src is None or src['master'] != 'ot_v41_rom_elem_q_qxpq_w10':
            continue
        assert p == 'pv' and k == 0 and last is not None, (names[it['name']], p, k)   # pv MSB first: k 0 = pv[1] (r1)
        face = last['master'].rsplit('_', 1)[1][1]
        mst = SKEW_MASTER[face]
        leaf = names[it['name']][2:]
        old = it['conns']['b']
        new = [f'sk_{leaf}_{j}' for j in range(len(old))]
        nm = f'sk_{leaf}'
        insts.append(dict(master=mst, name=nm, conns=collections.OrderedDict(
            i=list(old), o=new, ck=list(last['conns']['ck']), rs=list(last['conns']['rs']))))
        names[nm] = f'u_y_rt_{leaf[1:]}b_sk'
        it['conns']['b'] = new
        n_[mst] += 1
    assert sum(n_.values()) == sum(1 for i in insts if i['master'] == 'ot_v41_rom_elem_q_qxpq_w10'), n_
    return dict(kind='return_r1_skew', counts=dict(n_), note='one relay stage at every q leaf node b (r1) input: r1 '
                'reaches the leaf one edge after r0 (D2, ot_s81_retn_static F1); compiler calendar '
                'tools/s81_dv/frame_return_plan.py')


MUTANTS = ('xlane', 'marker', 'tree', 'cfgbank', 'noskew')


def apply_mutant(kind, insts, names):
    """bench negative controls (never emitted into rtl/): each must make tools/s81_dv/frame_bench.sh FAIL"""
    by = {names[i['name']]: i for i in insts}
    cf = next(i for i in insts if i['master'] == 'dsfd_cfifo_crs')
    if kind == 'xlane':            # x lanes 1 and 2 swapped at the column FIFO entry
        def sw(b):
            m = re.fullmatch(r'x\[(\d+)\]', b)
            if not m:
                return b
            i = int(m.group(1))
            return f'x[{i + LANE}]' if LANE <= i < 2 * LANE else (f'x[{i - LANE}]' if 2 * LANE <= i < 3 * LANE else b)
        for p in ('xd', 'xd2'):
            cf['conns'][p] = [sw(b) for b in cf['conns'][p]]
        return 'cfifo xd/xd2: lane 1 <-> lane 2'
    if kind == 'marker':           # the cfifo xd epoch marker taken from the word valid bit
        assert cf['conns']['xd'][-1] == 'x[0]'
        cf['conns']['xd'][-1] = 'x[1]'
        return 'cfifo xd[0] marker <- x[1] (valid)'
    if kind == 'tree':             # one return node reads its a child on both inputs (b subtree lost, a duplicated)
        for nm in sorted(by):
            it = by[nm]
            if it['master'].startswith('dsfd_node_NN') and len(it['conns']['a']) == len(it['conns']['b']):
                it['conns']['b'] = list(it['conns']['a'])
                return f'{nm}.b <- {nm}.a child'
    if kind == 'cfgbank':          # cfg ROM banks 1 and 2 of one q pair swapped at its sequencer
        for nm in sorted(by, key=lambda n: (len(n), n)):
            it = by[nm]
            if it['master'] == 'ot_s81_cfg7_seq':
                it['conns']['q1'], it['conns']['q2'] = it['conns']['q2'], it['conns']['q1']
                return f'{nm}: q1 <-> q2'
    raise ValueError(kind)


# ------------------------------------------------------------------------------------------------ emit
PORTS = [('input', 'clk', 1), ('input', 'cr', 1), ('input', 'cr_s', 1), ('input', 'rst_n', 1),
         ('input', 'x', NL * LANE), ('input', 'xk', NL), ('output', 'xo', NL * LANE), ('output', 'xok', NL),
         ('output', 'ret', RD)]


def emit(master, insts, names, pmap, rec):
    top = {n for _, n, _ in PORTS}
    nets = sorted({b for i in insts for v in i['conns'].values() for b in v
                   if b.split('[')[0] not in top}, key=lambda s: (len(s), s))
    L = [f'// GENERATED by tools/s81_dv/frame_wrap.py -- do not edit. S81-DV frame master {master}',
         f'// ({rec["slots"]} slots: {rec["pairs"]["q"]} q + {rec["pairs"]["bf"]} BF pairs) from the c26l column cluster '
         f'{rec["source"]["module"]} (sha256 {rec["source"]["sha256"][:16]}...).',
         '// Port cut: x[1103:0] = 4 x 276-b lanes (x[565:0] = cfifo xd, x[1103:566] = xd2), xk = lane forwarded clocks,',
         '// xo / xok = registered x-chain forward, ret = cfifo_crs rd, clk = column root, cr / cr_s = cfifo roots.',
         '`timescale 1ns/1ps', '`default_nettype none',
         f'module {master} #(parameter string INSTANCE = "{master}") ({", ".join(n for _, n, _ in PORTS)});']
    for d, n, w in PORTS:
        L.append(f'    {d} wire {"[%d:0] " % (w - 1) if w > 1 else ""}{n};')
    for k in range(0, len(nets), 16):
        L.append('    wire ' + ', '.join(nets[k:k + 16]) + ';')
    for it in insts:
        ps = pmap.get(it['name']) or {}
        par = (' #(' + ', '.join(f'.{k}({v})' for k, v in ps.items()) + ')') if ps else ''
        cs = []
        for p, v in it['conns'].items():
            cs.append(f'.{p}({v[0]})' if len(v) == 1 else f'.{p}({{{", ".join(v)}}})')
        L.append(f'    {it["master"]}{par} {names[it["name"]]} ({", ".join(cs)});')
    L.append('endmodule')
    L.append('`default_nettype wire')
    return '\n'.join(L) + '\n'


def emit_mirror(mx, base):
    return '\n'.join([
        f'// GENERATED by tools/s81_dv/frame_wrap.py -- do not edit. {mx}: the {base} RTL, mirrored placement (MX).',
        '`timescale 1ns/1ps', '`default_nettype none',
        f'module {mx} #(parameter string INSTANCE = "{mx}") ({", ".join(n for _, n, _ in PORTS)});',
        '\n'.join(f'    {d} wire {"[%d:0] " % (w - 1) if w > 1 else ""}{n};' for d, n, w in PORTS),
        f'    {base} #(.INSTANCE(INSTANCE)) u_f (' + ', '.join(f'.{n}({n})' for _, n, _ in PORTS) + ');',
        'endmodule', '`default_nettype wire', ''])


def emit_exact(exact):
    L = ['// GENERATED by tools/s81_dv/frame_wrap.py -- do not edit. Exact-width frame relays: the c26l frame fed these',
         '// relay stages constant pad bits (a narrower payload on a wider dedupe master, padded outputs unread); the',
         '// frame binds an exact-width master instead (owner 10-17 no-ties rule).  Same body as the wide master:',
         '// one ot_s81_rly stage, same reset pin register.', '`timescale 1ns/1ps', '`default_nettype none']
    for nm, (w, rsreg, src) in sorted(exact.items()):
        L.append(f'// from {src}')
        L.append(f'module {nm} (input wire ck, input wire rs, input wire [{w - 1}:0] i, output wire [{w - 1}:0] o);')
        L.append(f'    ot_s81_rly #(.W({w}), .RSREG({rsreg})) u (.ck(ck), .rs(rs), .i(i), .o(o));')
        L.append('endmodule')
    L.append('`default_nettype wire')
    return '\n'.join(L) + '\n'


def cmd_emit(a):
    idx = rtl_index()
    params_q = F._receipt_params(F.BOUND_VIEW_RECEIPTS['ot_v41_rom_elem_q_qxpq_w10'])
    out = Path(a.out_rtl) if Path(a.out_rtl).is_absolute() else ROOT / a.out_rtl
    out.mkdir(parents=True, exist_ok=True)
    recd = ROOT / a.record
    recd.mkdir(parents=True, exist_ok=True)
    exact_all, recs = {}, {}
    for master in CLASSES:
        insts, names, pmap, exact, rec = build(master, idx, params_q, a.rstp, a.bf_front, r1_skew=a.mutant != 'noskew')
        if a.mutant == 'noskew':
            rec['mutant'] = 'no r1 skew stage (the c26l leaf pairing: r0 / r1 on one edge)'
            print(f'{master}: MUTANT noskew')
        elif a.mutant:
            rec['mutant'] = apply_mutant(a.mutant, insts, names)
            print(f'{master}: MUTANT {a.mutant}: {rec["mutant"]}')
        for k, v in exact.items():
            assert exact_all.setdefault(k, v) == v
        txt = emit(master, insts, names, pmap, rec)
        (out / f'{master}.sv').write_text(txt)
        rec['rtl'] = dict(path=f'{a.out_rtl}/{master}.sv', sha256=sha(out / f'{master}.sv'))
        recs[master] = rec
        print(f'{master}: {len(insts)} instances, {txt.count(chr(10))} lines, members {rec["members"]}')
    for mx, base in MIRROR.items():
        (out / f'{mx}.sv').write_text(emit_mirror(mx, base))
        recs[mx] = dict(master=mx, rtl=dict(path=f'{a.out_rtl}/{mx}.sv', sha256=sha(out / f'{mx}.sv')), same_rtl_as=base,
                        placement='MX (mirrored); one child instance of the base master, ports pass through')
    if a.mutant:                   # bench negative control: wrappers only, into --out-rtl, no record
        return
    (ROOT / EXACT_RLY).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / EXACT_RLY).write_text(emit_exact(exact_all))
    doc = dict(schema=SCHEMA, provenance=PROVENANCE, sources={f: sha(ROOT / f) for f in RTL_FILES},
               ports=[dict(dir=d, name=n, width=w) for d, n, w in PORTS],
               lane_map=dict(x=f'lane k = x[276k +: 276]; x[565:0] = xd, x[1103:566] = xd2',
                             xf=f'xk[{XF_LANE}]', xf2=f'xk[{XF2_LANE}]', xo=f'{XO_MASTER} per lane, ck = xk[k], ck_o = xok[k]'),
               exact_relays={k: dict(width=v[0], rsreg=v[1], from_master=v[2]) for k, v in exact_all.items()},
               exact_relay_rtl=dict(path=EXACT_RLY, sha256=sha(ROOT / EXACT_RLY)),
               masters=recs, rstp=bool(a.rstp), bf_front=a.bf_front)
    (recd / 'frame_wrap.json').write_text(json.dumps(doc, indent=1) + '\n')
    print('record', recd / 'frame_wrap.json')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    e = sp.add_parser('emit')
    e.add_argument('--out-rtl', default='rtl/dsrom_sys/s81_dv/frame')
    e.add_argument('--record', default='results/arch/s81_dv_1016/frame')
    e.add_argument('--rstp', action='store_true', help='qxpq_w10 RSTP 1 (claude/qxpq-rst-1017; not on main yet)')
    e.add_argument('--bf-front', choices=('roots', 'static'), default='roots',
                   help='BF front master: roots = dsfd_bf_front_roots (closed view h03, native PASS; default), static = '
                        'dsfd_bf_front_static (the c26l source binding, no view)')
    e.add_argument('--mutant', choices=MUTANTS, help='bench negative control: emit mutated wrappers to --out-rtl only')
    a = ap.parse_args(argv)
    if a.cmd == 'emit':
        cmd_emit(a)


if __name__ == '__main__':
    main()
