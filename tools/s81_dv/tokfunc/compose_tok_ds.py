#!/usr/bin/env python3
"""TOK-DS/COMPOSE (2026-10-24): single-user DeepSeek-V4.1 token latency (AR + MTP) on the S81 array for the CURRENT die
plan (v4.8, physical/die_plan/s81/die_plan.json, latency table physical/die_plan/s81/lat/s81_latency.json, 833 ps), then
the multi-user calendar on the same inputs.  Analytical only (AGENTS.md: simulate the minimum component, compose
system timing analytically).

Composition
  T = max(sum over the committed critical path, longest path of the re-solved DAG) + per-token extra terms
  on the static token DAG (results/arch/token_path_20261009/ds_rom{,_mtp}.json) with the measured element records of
  results/token_pass/measured_s81_1019/elements (tools/toksim_s81_compose.py admission rules, reused, not re-priced).
  Every node is a list of COMPONENTS (cycles, grade, kind, source).  This tool then:
   1. REGRADE: a measured component is `measured-current-RTL` only if every RTL module its record names is
      blob-identical between the record's source revision and this tree's HEAD (rtl/); otherwise `measured-old-RTL`
      (the record and the differing modules are listed).  A priced / old / PHY component is never promoted.
   2. LANES: the on-die wire terms the DAG carries for the old p4l plan are replaced by plan-v4.8 latency-table lanes,
      with an explicit DAG-term -> lane mapping (LANE_MAP below; every term that could not be mapped is listed).
   3. OFF-CHIP: each crossing's 453-cycle switched leg -> the class's direct-cabling D_cycles_max
      (results/arch/release_rack_1021/hop_latency.json; ladder.json off_chip_legs), grade modelled-PHY.
   4. RELEASE NODE TERMS (as tools/s81_dv/dv_mu_calendar_phys.py --release241): attention variant (default G4, the
      release die72 slot), index reader +40, Engram RETURN_AGE 640 -- all graded priced.
   5. --layer-cycles F: measured single-die layer replays {"L0": {"cycles", "verdict", "receipt", ...}}; only verdict
      PASS is admitted; it replaces that layer's on-die node cycles (scaled onto the layer's non-xdie nodes) and its p4l
      DV delta term, grade measured-current-RTL with the receipt path.
   6. --components DIR: component receipts (*.json, schema in README); only verdict PASS with every mutant CAUGHT is
      admitted, as measured-current-RTL.

Multi-user: the 241-stage release calendar (dv_mu_calendar_phys.py --release241 --alap, map f72r224gpq_241) is run on
these node cycles (off-chip still switched; the calendar applies direct cabling itself), plus the formula table
aggregate = users x f / max(T_user, period) at the requested user counts.

  python3 tools/s81_dv/tokfunc/compose_tok_ds.py                 # writes results/token_pass/tokds_compose_1024/*
  python3 tools/s81_dv/tokfunc/compose_tok_ds.py --check         # recompute and compare
  python3 tools/s81_dv/tokfunc/compose_tok_ds.py --selftest
  python3 tools/s81_dv/tokfunc/compose_tok_ds.py --layer-cycles L.json [--components DIR] --out DIR
"""
from __future__ import annotations

import argparse
import collections
import copy
import functools
import glob
import hashlib
import importlib.util
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'results/token_pass/tokds_compose_1024'
PLAN = ROOT / 'physical/die_plan/s81/die_plan.json'
LAT = LAT_OF_RECORD = ROOT / 'physical/die_plan/s81/lat/s81_latency.json'
LAT_R8 = ROOT / 'physical/die_plan/s81/r8/s81_latency.json'
PLAN_VERSIONS = {'b4ac6d49d5198cd0': 'v4.8 (847f8568f, sha ea36999b, G0 PASS; G2 PASS 3be3c7df1)',
                 '87f0256809a93f1e': 'v4.8 + 26-slot frame FT405 per-bit-site plan (90fd169e9) + leaf/svc/eng hard cores '
                                     '(e94d9bb32, G0 PASS + G0C PASS 174/174)'}
HOPLAT = ROOT / 'results/arch/release_rack_1021/hop_latency.json'
LADDER = ROOT / 'results/token_pass/tokfunc3_s81_1021/ladder.json'
MAP241 = ROOT / 'results/arch/s81_map72_1021/r2_241/stage_map_f72r224gpq_241.json'
F_CLK = 1.2e9
PERIOD_PS = 833
SCHEMA = 'opentallas.tokds_compose.v1'
MEASURED_IN = ('measured-release-RTL', 'measured-newest-element-RTL', 'measured-current-RTL')
CUR, OLD, PRICED, EDGE, LANE, PHY = ('measured-current-RTL', 'measured-old-RTL', 'priced', 'priced-edge',
                                     'plan-v4.8-lane', 'modelled-PHY')
SWITCHED = 453
LEG_P4L_PER_CROSSING = 134.0     # base "on-die leg farthest slice <-> end slice, both ends (p4l plan, 67 an end)"
LEG_LINKS = 7                    # farthest slice -> end slice ring links (LEG definition; v4.8 ends at slice 0 and 7,
#                                  a TP4 broadcast needs both the E and the W links -> 7 links worst case)
RSTOP_EDGES = 5                  # LEG law: each ring link + the stop it enters = k_link + 5 edges (rstop logic)
FRAME_FI_HOPS = 4                # frame-internal b0->b1->b2 out + b2->b1->b0 back (fi lanes) a field round

# ---------------------------------------------------------------------------------------------- module loading
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


C = load(ROOT / 'tools/toksim_s81_compose.py', 'toksim_s81_compose_tokds')
ELEM = C.OUT / 'elements'


def rel(p):
    p = Path(p).resolve()
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------- plan v4.8 lanes
def plan_digest(raw):
    r = dict(raw)
    r.pop('latency', None)
    return hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()[:16]


@functools.lru_cache(None)
def lane_table():
    lat = json.loads(LAT.read_text())
    dig = plan_digest(json.loads(PLAN.read_text()))
    return lat, dig


def lanes(pattern, base=False):
    """{lane: cycles}; base=True: without the R8 landing pad (gen.py latency --fold-r8: cycles = base + r8_pad)"""
    lat, _ = lane_table()
    rx = re.compile(pattern)
    return {k: v['cycles'] - (v.get('r8_pad', 0) if base else 0) for k, v in lat['lanes'].items() if rx.fullmatch(k)}


def lane_terms():
    """the plan lane quantities used by the mapping, each with the lanes that define it; with an R8-folded table each
    term also carries its value without the R8 landing pads (`base_cycles`) and the pad lanes it picked up"""
    L = _lane_terms(lambda p: lanes(p))
    B = _lane_terms(lambda p: lanes(p, base=True))
    lat, _ = lane_table()
    for k, v in L.items():
        v['base_cycles'] = B[k]['cycles']
        v['r8_pad_cycles'] = v['cycles'] - B[k]['cycles']
        v['r8_pad_lanes'] = {l: lat['lanes'][l]['r8_pad'] for l in v['lanes'] if lat['lanes'][l].get('r8_pad')}
    return L


def _lane_terms(lanes):
    L = {}
    xr = lanes(r'xring__s_\d[NS]_C__s_\d[NS]_C')
    L['ring_link'] = dict(cycles=max(xr.values()), lanes=sorted(xr), rule='max xring lane (slice hub C -> neighbour hub C)')
    # field round: hub C -> x lane -> frame pos (p1/p4) -> xo chain -> farthest pos (p3/p6) -> fi b0->b1->b2 and back
    #              -> rt lane frame pos b0 -> hub C; max over the 12 columns and 6 positions
    best = None
    for side in 'EW':
        for col in range(6):
            for grp, base in (('in', 1), ('out', 4)):
                x = lanes(rf'x_{side}{col}_{grp}')
                if not x:
                    continue
                xo = [lanes(rf'xo_{side}{col}_{grp}_a'), lanes(rf'xo_{side}{col}_{grp}_b')]
                for k in range(3):
                    pos = base + k
                    rt = lanes(rf'rt_{side}{col}_{grp}_{k}')
                    fi = lanes(rf'fi_{side}{col}_p{pos}_r\d r\d'.replace(' ', ''))
                    fi_c = sorted(fi.values(), reverse=True)[:FRAME_FI_HOPS]
                    chain = sum(list(d.values())[0] for d in xo[:k])
                    tot = sum(x.values()) + chain + sum(fi_c) + sum(rt.values())
                    used = list(x) + [list(d)[0] for d in xo[:k]] + sorted(fi)[:FRAME_FI_HOPS] + list(rt)
                    if best is None or tot > best[0]:
                        best = (tot, used)
    L['field_round'] = dict(cycles=best[0], lanes=best[1],
                            rule='max over columns/positions of x + xo chain + 4 fi + rt (one hub->frame->hub round)')
    dn, up = lanes(r'dn_s_\d[NS]_L\d'), lanes(r'up_s_\d[NS]_L\d')
    L['leaf_hub_rt'] = dict(cycles=max(dn.values()) + max(up.values()),
                            lanes=[max(dn, key=dn.get), max(up, key=up.get)],
                            rule='max dn (hub C -> leaf) + max up (leaf -> hub C)')
    so = lanes(r'attn__svc_\d+__s_\d[NS]_C')
    L['svc_to_hub'] = dict(cycles=max(so.values()), lanes=[max(so, key=so.get)],
                           rule='max attn lane svc -> slice hub C (SO -> XS)')
    coll = lanes(r'coll__.*')
    kd = lanes(r'k[du]_s_\d[NS]')
    L['link_end'] = dict(cycles=max(coll.values()) + max(kd.values()), lanes=[max(coll, key=coll.get), max(kd, key=kd.get)],
                         rule='end slice hub C <-> LP (kd/ku) + LP <-> link (coll); NOT substituted (inside the '
                              'measured xdie co-sim lane legs), reported as a bound')
    return L


# ---------------------------------------------------------------------------------------------- regrade (blob check)
def git(*a):
    return subprocess.run(['git', '-C', str(ROOT), *a], capture_output=True, text=True).stdout


@functools.lru_cache(None)
def tree_blobs(rev):
    """basename(.sv/.v) -> {path: blob} under rtl/ at rev ('' when the rev is unknown)"""
    out = collections.defaultdict(dict)
    txt = git('ls-tree', '-r', rev, 'rtl/')
    for line in txt.splitlines():
        meta, path = line.split('\t', 1)
        blob = meta.split()[2]
        b = path.rsplit('/', 1)[-1]
        if b.endswith(('.sv', '.v', '.svh')):
            out[b.rsplit('.', 1)[0]][path] = blob
    return dict(out)


MOD_RX = re.compile(r'\b((?:ot|dsdv|dsfd|col|rly)_[A-Za-z0-9_]+)')
REV_RX = re.compile(r'@([0-9a-f]{9,40})\b|\b([0-9a-f]{9,40})\b')


@functools.lru_cache(None)
def blob_verdict(source, module_text):
    """(grade, detail) of a measured record against HEAD rtl/"""
    revs = [a or b for a, b in REV_RX.findall(source or '')]
    revs = [r for r in revs if git('cat-file', '-t', r).strip() == 'commit']
    mods = sorted(set(m for m in MOD_RX.findall(module_text or '') if not m.endswith('_')))
    if not revs or not mods:
        return OLD, dict(why='unverifiable: no resolvable source revision or no RTL module named', source=source,
                         modules=mods)
    rev = revs[0]
    head, then = tree_blobs('HEAD'), tree_blobs(rev)
    same, diff, missing = [], [], []
    for m in mods:
        h, t = head.get(m), then.get(m)
        if not h or not t:
            missing.append(m)
            continue
        common = set(h) & set(t)
        if common and all(h[p] == t[p] for p in common):
            same.append(m)
        else:
            diff.append(m)
    found = same + diff
    if not found:
        return OLD, dict(why='unverifiable: no named module found under rtl/', rev=rev, missing=missing)
    if diff:
        return OLD, dict(why='RTL changed since the measurement', rev=rev, changed=diff, same=same, missing=missing)
    return CUR, dict(why='every found module blob-identical to HEAD', rev=rev, same=same, missing=missing)


@functools.lru_cache(None)
def rtl_by_op():
    """op -> rtl of the non-curation element record that measured it bit-exact (zz_curation maps carry no rtl)"""
    out = {}
    for f in sorted(glob.glob(str(ELEM / '*.json'))):
        if Path(f).name.startswith('zz_'):
            continue
        for o in json.loads(Path(f).read_text()).get('ops', []):
            if o.get('rtl') and o.get('grade') in MEASURED_IN and o.get('bit_exact') is True:
                out.setdefault(o['op'], dict(rtl=o['rtl'], file=rel(f)))
    return out


def regrade(grade, rec):
    """measured grade + record -> current / old; everything else unchanged (never promoted)"""
    if grade not in MEASURED_IN and grade != 'measured-scaled':
        return grade, None
    if grade == 'measured-scaled':
        return OLD, dict(why='measured-scaled (shape not measured) is not a measurement of this node')
    via = None
    if rec and not rec.get('rtl') and rec.get('op') in rtl_by_op():
        via = rtl_by_op()[rec['op']]
        rec = dict(rec, rtl=via['rtl'])
    r = (rec or {}).get('rtl') or {}
    if isinstance(r, str):
        r = dict(module=r)
    text = ' '.join(str(r.get(k) or '') for k in ('module', 'blob'))
    g, det = blob_verdict(str(r.get('source') or ''), text)
    if via:
        det = dict(det, rtl_from=via['file'])
    return g, det


# The xdie co-sim (base term grade measured-current-RTL) ran on the G8R2 p4m die: rstop + lep + lane legs + lane tiles.
XDIE_RTL = dict(source='tb_xdie_s81_2 G8R2 @0e6b9b710', module='ot_s81sl_rstop ot_s81sl_lep_mu ot_s81_land ot_s81_rly')

# ---------------------------------------------------------------------------------------------- lane map
# DAG on-die wire term -> plan-v4.8 lanes.  'old_wire' = the p4l wire cycles inside the record's number (split out);
# 'logic' = priced non-wire part of a record tail that stays priced; rounds = hub->frame->hub traversals.
FIELD_WIRE = {
    'attn.wq_b': dict(where='tail', old_wire=143, logic=52, rounds=1,
                      src='WQBG tail 195 = CAP EDLY 24 + VP hand-off 28 + die wire 143'),
    'ffn.down': dict(where='main', old_wire=143, logic=52, rounds=1,
                     src='FDOWN/FSDN 3084 = frame 2889 + priced tail 195 (as wq_b); the 195 was counted as measured'),
    'ffn.router': dict(where='main', old_wire=150, logic=0, rounds=1, src='FSEQ 1419 = 1269 + r8 die wire 122 + tiles 28'),
    'attn.a_proj': dict(where='main', old_wire=170, logic=0, rounds=1,
                        src='FSMALL 531 = 361 + r8 142 + tiles 28; APSP per-layer values include the same +170'),
    'attn.wo_b': dict(where='main', old_wire=174, logic=26, rounds=1, src='FWOA 1464 = 1264 + r8 146 + tiles 28 + 26 CAP edges'),
    'attn.wo_a': dict(where='main', old_wire=612, logic=26, rounds=4,
                      src='FWOA 4862 = 4224 + r8 584 (= 4 x 146) + tiles 28 + 26 CAP edges'),
    'ffn.experts_gu': dict(where='add', old_wire=0, logic=0, rounds=1,
                           src='FGU/FSGU 3680: die wire / hub return NOT included -> v4.8 round added (was missing)'),
    'ffn.shared_gu': dict(where='add', old_wire=0, logic=0, rounds=1,
                          src='FGU 798: die wire / hub return NOT included -> v4.8 round added (was missing)'),
}
HUB_TAIL = {   # SU leaf-op tails that are hub / die-tile station wire -> leaf<->hub round trip
    'attn.hc_post': 'zz_curation: old hub in/out stations 33 + 23',
    'ffn.hc_post': 'zz_curation: as attn.hc_post',
    'ffn.softplus_sqrt': 'zz_curation: +2 in +2 out wire stages',
    'attn.z_quant': 'zz_curation: +1 hub-slab +3 die-tile stations',
    'ffn.bias': 'zz_curation: +4 hub-slab +3 die-tile',
    'attn.q_rope': 'zz_curation: +4 hub-slab +3 die-tile',
}
SVC_TAIL = {'attn.normalize': 'SMX tail 132 = SMWIRE priced edge last SO write -> last XS arrival (115 E / 132 W)'}
UNMAPPED_TAIL = {
    'head.lm_head': 'head die wire +34 (head die is not on the S81 layer-die plan; no head plan of record)',
    'draft.head': 'head die wire +34 (head die, no plan of record)',
    'embed': 'embed priced 751.3 (TP4 owner->4 ranks all_gather + SU expand + board leg; not a layer-die lane)',
}
ATTN = {'G16': None, 'G8': {'attn.scores': 449.0, 'attn.pv': 756.0}, 'G4': {'attn.scores': 769.0, 'attn.pv': 1076.0}}
TP_X = {'attn.a_allgather': 1, 'attn.out_allreduce': 2, 'ffn.router_allgather': 1, 'ffn.combine_allreduce': 2,
        'attn.idx.topk_merge': 1, 'attn.rows_allgather': 1, 'attn.cand.merge': 1, 'head.argmax_merge': 1}
HOP_X = {'substage_hop0': 1, 'substage_hop1': 1, 'unplaced_hops': 62, 'hop_in': 1, 'wave.hop': 1}
IDX_LAT, ENG_AGE = 40, 640

# ladder gaps (results/token_pass/tokfunc3_s81_1021/ladder.json) that block a re-measurement on the current die
BLOCKERS = [
    (r'attn\.kv_norm|attn\.kv_rope_qdq', 'G-KV-LEAF'),
    (r'attn\.normalize', 'G-NORMALIZE-SO'),
    (r'attn\.cmp\.|compress|eng\.knorm|attn\.idx\.l20', 'G-L2-L20-HW'),
    (r'attn\.idx\.score|attn\.gather|attn\.scores|attn\.pv|eng\.gate|attn\.idx\.newkey|attn\.out_allreduce|wkv',
     'G-COMPILER-ROWS'),
    (r'^head\.|^draft\.|mtp\.|^mc\.', 'G-HEAD-DIE-TB'),
    (r'embed|hop_in|token\.return', 'G-HOST-CONTEXT'),
]


def blockers(op):
    return sorted({g for rx, g in BLOCKERS if re.search(rx, op or '')})


# ---------------------------------------------------------------------------------------------- components
def comp(c, g, k, src, rec=None):
    return dict(c=float(c), g=g, k=k, src=src, rec=rec)


def build_components(wl, base, dag, ops, slots, xparts):
    """C.compose() rewritten to keep per-node component lists (parity with C.compose is a selftest)."""
    gk = {g['id']: g['kind'] for g in dag['groups']}
    xd = {}
    for t in base['workloads'][wl]['terms']:
        if t['kind'] == 'xdie':
            xd.setdefault(t['slot'], []).append(t)
    nodes, comps, overrides = {n['id']: n for n in dag['nodes']}, {}, {}
    for n in dag['nodes']:
        L = C.lkey(n, gk)
        old = float(n['cycles'])
        if n.get('cls') in ('coll', 'hop'):
            parts = xd.get(f'{L}.xdie.{n["id"]}', [])
            cl = []
            for p in parts:
                c, g = C.xdie_part(p, xparts)
                pn = str(p.get('part') or '')
                if g == PHY or pn.startswith('PMA'):
                    cl.append(comp(c, g, 'offchip', pn, dict(base_total=p['total'])))
                elif pn.startswith('on-die leg'):
                    x = xparts.get(pn)
                    cl.append(comp(c, g, 'leg', pn, dict(base_total=p['total'], file=(x or {}).get('file'))))
                else:
                    cl.append(comp(c, g, 'xdie', pn[:80], dict(rtl=XDIE_RTL)))
            if not parts:
                cl.append(comp(old, PRICED, 'logic', 'coll/hop node without xdie term (priced DAG number)'))
            comps[n['id']] = cl
            continue
        g = {'measured': OLD, 'measured+vendor': OLD}.get((n.get('src') or {}).get('grade'), PRICED)
        new, tail, rec = old, 0.0, None
        ov = ops.get((n.get('cls'), n.get('op'))) or ops.get((None, n.get('op')))
        if ov and not ov.get('compose_hook'):
            c, how = C.node_cycles(n, ov)
            if c is not None:
                new = c
                g = ov['grade'] if how == 'exact' else 'measured-scaled'
                tail = float(ov.get('tail_priced') or 0.0)
                rec = ov
                overrides[n['id']] = ov
        cl = [comp(new, g, 'logic', (rec or {}).get('file') or 'DAG ' + str((n.get('src') or {}).get('record')), rec)]
        if tail:
            cl.append(comp(tail, PRICED, 'tail', 'priced tail of ' + str(rec.get('file')), rec))
        comps[n['id']] = cl
    for n in dag['nodes']:
        ov = ops.get((n.get('cls'), n.get('op'))) or ops.get((None, n.get('op')))
        if ov and not ov.get('compose_hook') and C.node_cycles(n, ov)[0] is None:
            ov = None
        delta, _ = C.edge_delta(n, ov)
        for k, v in delta.items():
            comps[n['id']].append(comp(v, EDGE, 'edge', 'source-age edge ' + k))
    hooks = []
    for n in dag['nodes']:
        ov = ops.get((n.get('cls'), n.get('op'))) or ops.get((None, n.get('op')))
        if ov and ov.get('compose_hook'):
            hooks.append((n, ov))
    extra = []
    E = C.EDGES or {}
    for key, cycles in E.get('per_token', {}).items():
        extra.append(dict(slot='edges.' + key, kind='edge', cycles=float(cycles), grade=EDGE, rec=None))
    for t in base['workloads'][wl]['terms']:
        if t['kind'] == 'xdie' or t['slot'].endswith('.die'):
            continue
        o = slots.get(t['slot'])
        c, g = (float(o['cycles']), o['grade']) if o else (t['total'], t['grade'])
        extra.append(dict(slot=t['slot'], kind=t['kind'], cycles=c, grade=g, rec=o, note=t.get('note')))
    seen = {t['slot'] for t in base['workloads'][wl]['terms']}
    for sl, o in sorted(slots.items()):
        if sl in seen or o.get('workloads', [wl]) and wl not in o.get('workloads', [wl]):
            continue
        extra.append(dict(slot=sl, kind='element', cycles=float(o['cycles']) * float(o.get('n', 1)),
                          grade=o.get('term_grade', o['grade']), rec=o))
    return comps, hooks, extra, overrides


def apply_hooks(dag, comps, hooks, ops):
    """composite wave positions: sum of the group's (already transformed) components + the measured handoff"""
    for n, ov in hooks:
        hook = ov['compose_hook']
        group = [x for x in dag['nodes'] if x.get('group') == hook['group'] and x['id'] not in hook.get('exclude', [])]
        cl = [dict(c_, src='composite ' + n['id'] + ' <- ' + c_['src']) for x in group for c_ in comps[x['id']]]
        proof = next((o for o in [ops.get(k) for k in ops] if o and o.get('op') == 'wave.handoff'), None)
        cl.append(comp(hook['handoff_cycles'], 'measured-release-RTL', 'logic', 'wave.handoff ' + ov['file'], proof or ov))
        comps[n['id']] = cl


# ---------------------------------------------------------------------------------------------- transforms
def transform_lanes(dag, comps, LT, log, unmapped):
    W = LT['field_round']['cycles']
    leg_end = LEG_LINKS * (LT['ring_link']['cycles'] + RSTOP_EDGES)
    for n in dag['nodes']:
        i, op, cl = n['id'], n.get('op') or '', comps[n['id']]
        crit = bool(n.get('critical'))
        out = []
        for c_ in cl:
            if c_['k'] == 'leg':
                xs = c_['rec']['base_total'] / LEG_P4L_PER_CROSSING
                wire = xs * 2 * LEG_LINKS * LT['ring_link']['cycles']
                stop = xs * 2 * LEG_LINKS * RSTOP_EDGES
                leg_rec = json.loads((ROOT / c_['rec']['file']).read_text())['ops'][0] if c_['rec'].get('file') else None
                out.append(comp(wire, LANE, 'wire', f'v4.8 ring: {xs:g} crossings x 2 ends x {LEG_LINKS} xring lanes'))
                out.append(comp(stop, 'measured-release-RTL' if leg_rec else PRICED, 'logic',
                                f'rstop logic {RSTOP_EDGES} edges a stop (LEG law)', leg_rec))
                log['leg'][('crit' if crit else 'off')] += 1
                log['leg_delta'] += (wire + stop - c_['c']) * crit
                continue
            out.append(c_)
        cl = out
        if op in FIELD_WIRE and n.get('cls') == 'field':
            fw = FIELD_WIRE[op]
            main = cl[0]
            measured = main['g'] in MEASURED_IN
            if not measured:
                unmapped.add(('field-node-old', op, 'node keeps its old DAG number (old r8 wire + tiles embedded, '
                              'not separable)'))
            else:
                if fw['where'] == 'main':
                    main['c'] -= fw['old_wire'] + fw['logic']
                    main['src'] += f' (minus p4l wire {fw["old_wire"]}' + (f' + priced {fw["logic"]}' if fw['logic'] else '') + ')'
                    if fw['logic']:
                        cl.append(comp(fw['logic'], PRICED, 'tail', 'priced non-wire tail: ' + fw['src']))
                elif fw['where'] == 'tail':
                    t = next(x for x in cl if x['k'] == 'tail')
                    t['c'] -= fw['old_wire']
                    t['src'] += ' (die wire split out)'
                cl.append(comp(W * fw['rounds'], LANE, 'wire', f'v4.8 field round x{fw["rounds"]}: ' + fw['src']))
                log['field'][op] += 1
                log['field_delta'] += (W * fw['rounds'] - fw['old_wire']) * crit
        elif n.get('cls') == 'field' and cl[0]['g'] not in MEASURED_IN:
            unmapped.add(('field-node-old', op, 'node keeps its old DAG number (old r8 wire + tiles embedded)'))
        if op in HUB_TAIL or op in SVC_TAIL:
            t = next((x for x in cl if x['k'] == 'tail'), None)
            if t:
                key = 'leaf_hub_rt' if op in HUB_TAIL else 'svc_to_hub'
                new = LT[key]['cycles']
                log['tail'][op] += 1
                log['tail_delta'] += (new - t['c']) * crit
                t.update(c=float(new), g=LANE, k='wire', src=f'v4.8 {key}: ' + (HUB_TAIL.get(op) or SVC_TAIL[op]))
        if op in UNMAPPED_TAIL and any(x['k'] == 'tail' for x in cl):
            unmapped.add(('tail', op, UNMAPPED_TAIL[op]))
        comps[i] = cl


def transform_offchip(dag, comps, log, direct=True):
    if not direct:
        return
    hl = json.loads(HOPLAT.read_text())['systems']['S81']
    D = {k: hl[k]['D_cycles_max'] for k in ('tp_mesh', 'stage_hop', 'head_hop')}
    for n in dag['nodes']:
        op = n.get('op') or ''
        if op in TP_X:
            sv, cls = TP_X[op] * (SWITCHED - D['tp_mesh']), 'tp_mesh'
        elif op in HOP_X:
            sv, cls = HOP_X[op] * (SWITCHED - D['stage_hop']), 'stage_hop'
        elif op == 'head.hop':
            sv, cls = SWITCHED - D['head_hop'], 'head_hop'
        else:
            continue
        cl = comps[n['id']]
        phy = [x for x in cl if x['k'] == 'offchip']
        if phy:
            phy[0]['c'] -= sv
            phy[0]['src'] += f' -> direct {cls} D_cycles_max {D[cls]}'
        else:   # node priced without an xdie term: the calendar tool subtracts from the node; do the same, priced
            cl.append(comp(-sv, PHY, 'offchip', f'direct {cls} (node without xdie term)'))
        log['offchip'][cls] += sv * bool(n.get('critical'))


def transform_release(dag, comps, log, attn='G4'):
    av = ATTN.get(attn) or {}
    for n in dag['nodes']:
        op, cl = n.get('op') or '', comps[n['id']]
        if op in av:
            old = sum(x['c'] for x in cl)
            comps[n['id']] = [comp(av[op], PRICED, 'logic', f'attention variant {attn} (S81-SVCFIT, dv_mu_calendar_phys ATTN)')]
            log['release'][op] += (av[op] - old) * bool(n.get('critical'))
        elif op == 'attn.idx.score':
            cl.append(comp(IDX_LAT, PRICED, 'logic', 'index reader by the HBM PHY +40 (REL241 idx_lat)'))
            log['release'][op] += IDX_LAT * bool(n.get('critical'))
        elif op == 'eng.hbm_read':
            c = sum(x['c'] for x in cl)
            if c < ENG_AGE:
                cl.append(comp(ENG_AGE - c, PRICED, 'logic', 'Engram RETURN_AGE 640 (REL241 eng_age)'))
                log['release'][op] += (ENG_AGE - c) * bool(n.get('critical'))


def transform_components(dag, comps, receipts, log):
    """admitted component receipts (verdict PASS, every mutant CAUGHT) -> measured-current-RTL on the op's nodes"""
    for r in receipts:
        if r.get('leg_rstop_edges') is not None:
            for cl in comps.values():
                for x in cl:
                    if x['src'].startswith('rstop logic'):
                        per = x['c'] / RSTOP_EDGES
                        x.update(c=per * float(r['leg_rstop_edges']), g=CUR, src=f'rstop {r["leg_rstop_edges"]} edges '
                                 f'a stop: receipt {r["_file"]}', rec=None, receipt=r['_file'])
            log['components'].append(dict(file=r['_file'], applied='leg_rstop_edges'))
        ops_ = r.get('op')
        if not ops_ or r.get('cycles') is None and not r.get('per_layer'):
            continue
        ops_ = [ops_] if isinstance(ops_, str) else ops_
        hit = 0
        for n in dag['nodes']:
            if (n.get('op') or '') not in ops_:
                continue
            ref = r.get('old_cycles_per_instance')
            if ref is not None and abs(float(n['cycles']) - float(ref)) > 0.6:
                continue
            L = n.get('layer')
            c = (r.get('per_layer') or {}).get(f'L{L}', r.get('cycles'))
            if c is None:
                continue
            cl = comps[n['id']]
            keep = [x for x in cl if x['k'] in ('wire', 'edge', 'offchip', 'xdie', 'leg')] if r.get('replaces') != 'node' else []
            comps[n['id']] = [dict(comp(c, CUR, 'logic', 'component receipt ' + r['_file']), receipt=r['_file'])] + keep
            hit += 1
        log['components'].append(dict(file=r['_file'], ops=ops_, nodes=hit))


def transform_layers(dag, comps, extra, layer_rx, log):
    """admitted single-die layer replays: the layer's non-xdie nodes scaled to the measured cycles (critical-path sum
    = measured), grade measured-current-RTL; the layer's p4l DV delta term is dropped (the replay ran on the die)."""
    for key, r in sorted(layer_rx.items()):
        targets = [key] + list(r.get('applies_to') or [])
        for lk in targets:
            L = int(lk[1:])
            ids = [n['id'] for n in dag['nodes'] if n.get('layer') == L and n.get('cls') not in ('coll', 'hop')
                   and not n['id'].startswith('V.')]
            crit = [i for i in ids if dag_crit(dag, i)]
            old = sum(sum(x['c'] for x in comps[i]) for i in crit)
            if old <= 0:
                log['layers'].append(dict(layer=lk, applied=False, why='no critical on-die nodes'))
                continue
            f = float(r['cycles']) / old
            for i in ids:
                tot = sum(x['c'] for x in comps[i])
                comps[i] = [dict(comp(tot * f, CUR, 'logic', f'layer replay {key} ({r["receipt"]}) scaled x{f:.4f}'),
                                 receipt=r['receipt'])]
                if dag['nodes_by_id'][i]['id'].startswith('V.'):
                    pass
            for e in extra:
                if e['slot'] == f'{lk}.dv_p4l':
                    e.update(cycles=0.0, note='dropped: layer replay on the die covers the p4l DV deltas')
            log['layers'].append(dict(layer=lk, from_replay=key, applied=True, critical_nodes=len(crit),
                                      old_critical_cycles=round(old, 1), measured=float(r['cycles']),
                                      factor=round(f, 6), receipt=r['receipt']))


def dag_crit(dag, i):
    return bool(dag['nodes_by_id'][i].get('critical'))


# ---------------------------------------------------------------------------------------------- inputs (admission)
def load_layer_cycles(path):
    """schema: {"L0": {"cycles": int, "verdict": "PASS"|..., "receipt": "path or host:path", optional "die",
    "rtl", "applies_to": ["L3", ...] (explicit, never implied)}}; only verdict PASS is admitted"""
    if not path:
        return {}, []
    d = json.loads(Path(path).read_text())
    ok, rej = {}, []
    for k, v in d.items():
        if k.startswith('_'):
            continue
        if not re.fullmatch(r'L\d+', k) or not isinstance(v, dict):
            rej.append(dict(layer=k, why='bad key/entry'))
        elif v.get('verdict') != 'PASS':
            rej.append(dict(layer=k, why=f'verdict {v.get("verdict")!r} != PASS'))
        elif not isinstance(v.get('cycles'), (int, float)) or v['cycles'] <= 0 or not v.get('receipt'):
            rej.append(dict(layer=k, why='missing cycles or receipt'))
        else:
            ok[k] = v
    return ok, rej


def mutant_caught(r):
    m = r.get('mutant', r.get('mutants'))
    if isinstance(m, str):
        return m.upper() == 'CAUGHT'
    if isinstance(m, dict):
        return bool(m) and all(str(v).upper() == 'CAUGHT' for v in m.values())
    if isinstance(m, list):
        return bool(m) and all(str(x.get('result') if isinstance(x, dict) else x).upper() == 'CAUGHT' for x in m)
    return False


def load_components(d):
    if not d:
        return [], []
    ok, rej = [], []
    for f in sorted(glob.glob(str(Path(d) / '*.json'))):
        try:
            r = json.loads(Path(f).read_text())
        except Exception as e:  # noqa: BLE001
            rej.append(dict(file=f, why=f'unreadable: {e}'))
            continue
        name = rel(f) if Path(f).resolve().is_relative_to(ROOT) else f
        if r.get('verdict') != 'PASS':
            rej.append(dict(file=name, why=f'verdict {r.get("verdict")!r}'))
        elif not mutant_caught(r):
            rej.append(dict(file=name, why='no mutant CAUGHT'))
        else:
            ok.append(dict(r, _file=name))
    return ok, rej


# ---------------------------------------------------------------------------------------------- compose
def node_total(cl):
    return sum(x['c'] for x in cl)


def finalize_grades(comps, extra, regrade_on=True):
    reg = {}
    for cl in comps.values():
        for x in cl:
            if regrade_on and x['g'] in MEASURED_IN + ('measured-scaled',) and not x.get('receipt'):
                rec = x['rec'] or {}
                g, det = regrade(x['g'], rec)
                key = rec.get('file') or x['src'][:60]
                reg.setdefault(f'{key} :: {rec.get("op", "")}', dict(from_grade=x['g'], to=g, detail=det))
                x['g0'], x['g'] = x['g'], g
    for e in extra:
        if regrade_on and e['grade'] in MEASURED_IN:
            g, det = regrade(e['grade'], e.get('rec'))
            if not e.get('rec'):
                det = dict(why='base layer term, no element record: not verifiable against HEAD')
            reg.setdefault('extra ' + e['slot'], dict(from_grade=e['grade'], to=g, detail=det))
            e['g0'], e['grade'] = e['grade'], g
    return reg


def compose(wl, opts, layer_rx=None, receipts=None):
    base = json.loads(C.BASE.read_text())
    ops, slots, xparts, files, excluded, inserts = C.load_elements(ELEM)
    for o in inserts:
        ops[(o.get('dag_cls'), o['op'])] = o
    dag = C.insert_nodes(json.loads(C.DAGS[wl].read_text()), inserts)
    dag['nodes_by_id'] = {n['id']: n for n in dag['nodes']}
    comps, hooks, extra, _ = build_components(wl, base, dag, ops, slots, xparts)
    log = dict(leg=collections.Counter(), leg_delta=0.0, field=collections.Counter(), field_delta=0.0,
               tail=collections.Counter(), tail_delta=0.0, offchip=collections.Counter(),
               release=collections.Counter(), components=[], layers=[])
    unmapped = set()
    LT = lane_terms()
    if opts.get('lanes', True):
        transform_lanes(dag, comps, LT, log, unmapped)
    if opts.get('release', True):
        transform_release(dag, comps, log, opts.get('attn', 'G4'))
    if receipts:
        transform_components(dag, comps, receipts, log)
    if layer_rx:
        transform_layers(dag, comps, extra, layer_rx, log)
    apply_hooks(dag, comps, hooks, ops)
    # off-chip after the composite so a wave composite inherits the switched legs exactly as the calendar sees them
    pre_offchip = {i: node_total(cl) for i, cl in comps.items()}
    if opts.get('offchip', True):
        transform_offchip(dag, comps, log, True)
        apply_hooks(dag, comps, hooks, ops)   # recompute composites from offchip-adjusted members
        # composite members adjusted twice? apply_hooks rebuilds from members -> idempotent
    reg = finalize_grades(comps, extra, opts.get('regrade', True))
    cyc = {i: node_total(cl) for i, cl in comps.items()}
    crit = [n['id'] for n in dag['nodes'] if n.get('critical')]
    ex = sum(e['cycles'] for e in extra)
    fixed = sum(cyc[i] for i in crit) + ex
    T_s, path = C.solve(dag, cyc)
    T_s += ex
    sel = crit if fixed >= T_s else path
    T = max(fixed, T_s)
    by = collections.Counter()
    for i in sel:
        for x in comps[i]:
            by[x['g']] += x['c']
    for e in extra:
        by[e['grade']] += e['cycles']
    if fixed < T_s:   # explicit edge latency on the solved path (none in this DAG) stays priced
        by[PRICED] += T_s - sum(cyc[i] for i in path) - ex
    tau = base['workloads'][wl].get('tau') or 1.0
    return dict(wl=wl, dag=dag, comps=comps, extra=extra, cyc=cyc, pre_offchip=pre_offchip, crit=crit, path=path,
                sel=sel, T=T, fixed=fixed, solved=T_s, by=by, tau=tau, log=log, unmapped=unmapped, regrade=reg,
                LT=LT, excluded=excluded, files=files)


def four_way(by):
    tot = sum(by.values())
    q = lambda *ks: sum(by.get(k, 0.0) for k in ks)
    return dict(measured_current_rtl=round(100 * q(CUR) / tot, 2), measured_old_rtl=round(100 * q(OLD) / tot, 2),
                priced=round(100 * q(PRICED, EDGE, LANE) / tot, 2), modelled_phy=round(100 * q(PHY) / tot, 2),
                priced_split=dict(priced=round(100 * q(PRICED) / tot, 2), priced_edge=round(100 * q(EDGE) / tot, 2),
                                  plan_v48_lane=round(100 * q(LANE) / tot, 2)))


def stage_table(r, top=40):
    rows = {}
    for i in r['sel']:
        n = r['dag']['nodes_by_id'][i]
        key = (n.get('cls'), n.get('op') or i)
        row = rows.setdefault(key, dict(cls=key[0], op=key[1], n=0, cycles=0.0, grades=collections.Counter(),
                                        kinds=collections.Counter(), sources=set()))
        row['n'] += 1
        for x in r['comps'][i]:
            row['cycles'] += x['c']
            row['grades'][x['g']] += x['c']
            row['kinds'][x['k']] += x['c']
            if x['g'] in (CUR, OLD) and x.get('rec') and x['rec'].get('file'):
                row['sources'].add(x['rec']['file'])
            if x.get('receipt'):
                row['sources'].add(x['receipt'])
    for e in r['extra']:
        key = ('extra', re.sub(r'^L\d+\.', 'L*.', e['slot']))
        row = rows.setdefault(key, dict(cls='extra', op=key[1], n=0, cycles=0.0, grades=collections.Counter(),
                                        kinds=collections.Counter(), sources=set()))
        row['n'] += 1
        row['cycles'] += e['cycles']
        row['grades'][e['grade']] += e['cycles']
        row['kinds'][e['kind']] += e['cycles']
    T = r['T']
    out = []
    for row in sorted(rows.values(), key=lambda x: -x['cycles']):
        if abs(row['cycles']) < 0.05:
            continue
        nm = sum(v for k, v in row['grades'].items() if k != CUR)
        out.append(dict(cls=row['cls'], op=row['op'], count=row['n'], cycles=round(row['cycles'], 1),
                        share_pct=round(100 * row['cycles'] / T, 2),
                        grades={k: round(v, 1) for k, v in sorted(row['grades'].items()) if abs(v) > 0.05},
                        kinds={k: round(v, 1) for k, v in sorted(row['kinds'].items()) if abs(v) > 0.05},
                        not_measured_current=round(nm, 1), blocked_by=blockers(row['op']),
                        sources=sorted(row['sources'])[:4]))
    return out[:top], out


def lane_map_table(r):
    LT = r['LT']
    lg = r['log']
    return [
        dict(dag_term='xdie on-die leg (priced 134 / LEG p4l 140 a crossing)', lane_quantity='ring_link',
             lanes=LT['ring_link']['lanes'][:4] + ['...'], per_unit=LT['ring_link']['cycles'],
             formula=f'crossings x 2 ends x {LEG_LINKS} x (ring_link + {RSTOP_EDGES} rstop edges)',
             per_crossing=2 * LEG_LINKS * (LT['ring_link']['cycles'] + RSTOP_EDGES),
             nodes=dict(lg['leg']), critical_delta=round(lg['leg_delta'], 1)),
        dict(dag_term='field op p4l die wire (r8 wire + s81 die tiles) / missing hub return', lane_quantity='field_round',
             lanes=LT['field_round']['lanes'], per_unit=LT['field_round']['cycles'],
             formula='rounds x field_round (FIELD_WIRE table)', ops={k: dict(FIELD_WIRE[k], nodes=v) for k, v in lg['field'].items()},
             critical_delta=round(lg['field_delta'], 1)),
        dict(dag_term='SU leaf-op hub / die-tile station tails', lane_quantity='leaf_hub_rt',
             lanes=LT['leaf_hub_rt']['lanes'], per_unit=LT['leaf_hub_rt']['cycles'], ops=sorted(HUB_TAIL),
             critical_delta=None),
        dict(dag_term='softmax normalize SO -> XS tail', lane_quantity='svc_to_hub', lanes=LT['svc_to_hub']['lanes'],
             per_unit=LT['svc_to_hub']['cycles'], ops=sorted(SVC_TAIL), critical_delta=None,
             tail_nodes=dict(lg['tail']), tail_critical_delta_total=round(lg['tail_delta'], 1)),
        dict(dag_term='end slice <-> link (kd/ku + coll lanes)', lane_quantity='link_end', lanes=LT['link_end']['lanes'],
             per_unit=LT['link_end']['cycles'], formula='NOT substituted: inside the measured(-old) xdie co-sim lane legs',
             critical_delta=0),
    ]


def unmapped_list(r):
    u = sorted(r['unmapped'])
    rows = [dict(kind=k, op=o, why=w) for k, o, w in u]
    rows.append(dict(kind='extra', op='L*.dv_p4l (41 layer terms)', why='p4l DV die deltas (landing, half-cycle hops, '
                     'pin registers) on the critical nodes; per-layer sums only, no per-node split -> kept priced '
                     '(partly double counts the v4.8 lanes above: an upper bound)'))
    rows.append(dict(kind='extra', op='price_of_record_residual / scan_d legs / reindex', why='ledger terms with no '
                     'lane content of their own; kept priced'))
    rows.append(dict(kind='xdie', op='measured xdie co-sim part (rstop + lep + lane legs, G8R2 p4m)', why='lane legs are '
                     'inside a measured span; v4.8 end-slice<->link lanes (kd/ku + coll) not separable; kept'))
    rows.append(dict(kind='xdie', op='token.return (modelled-PHY 2194)', why='no per-crossing split in the base record; '
                     'kept as modelled-PHY (ladder token_return D = 251 a crossing)'))
    rows.append(dict(kind='node', op='SU / select / hbm measured spans', why='spans measured on p4l RTL include p4l '
                     'on-die stations internally; not re-timed to v4.8 (needs the v4.8 die = layer replays)'))
    return rows


def summarize(r, top=40):
    tbl, full = stage_table(r, top)
    blocked = collections.Counter()
    for row in full:
        for g in row['blocked_by'] or ['(no ladder gap: needs a v4.8-die bench)']:
            blocked[g] += row['not_measured_current']
    nm_ops = sorted((x for x in full if x['not_measured_current'] > 0), key=lambda x: -x['not_measured_current'])[:15]
    tau = r['tau']
    return dict(
        workload=r['wl'], tau=tau if r['wl'] == 'mtp' else None,
        T_cycles=round(r['T'], 1), T_cycles_fixed=round(r['fixed'], 1), T_cycles_solved=round(r['solved'], 1),
        rate_basis='max(committed critical path, re-solved DAG) + extra terms (as toksim_s81_compose)',
        per_accepted_cycles=round(r['T'] / tau, 1) if r['wl'] == 'mtp' else None,
        tok_s=round(F_CLK * (tau if r['wl'] == 'mtp' else 1.0) / r['T'], 1),
        by_grade={k: round(v, 1) for k, v in sorted(r['by'].items()) if abs(v) > 0.05},
        pct=four_way(r['by']),
        transforms=dict(leg_nodes=dict(r['log']['leg']), leg_critical_delta=round(r['log']['leg_delta'], 1),
                        field_critical_delta=round(r['log']['field_delta'], 1),
                        tail_critical_delta=round(r['log']['tail_delta'], 1),
                        offchip_saved_critical={k: round(v, 1) for k, v in r['log']['offchip'].items()},
                        release_critical={k: round(v, 1) for k, v in r['log']['release'].items()},
                        components=r['log']['components'], layers=r['log']['layers']),
        critical_stage_table=tbl,
        top_not_measured_current=[dict(op=x['op'], cls=x['cls'], cycles=x['not_measured_current'],
                                       grades=x['grades'], blocked_by=x['blocked_by']) for x in nm_ops],
        not_measured_current_by_blocker={k: round(v, 1) for k, v in blocked.most_common()},
    )


# ---------------------------------------------------------------------------------------------- calendar
def calendar(res, layer_rx_extra=None, attn='G4'):
    """dv_mu_calendar_phys --release241 --alap on THESE node cycles (switched off-chip legs; the tool applies direct
    cabling + G4 + idx + eng itself, so the inputs are the pre-offchip, pre-release node cycles)."""
    K = load(ROOT / 'tools/s81_dv/dv_mu_calendar_phys.py', 'dv_mu_calendar_phys_tokds')
    K.REL.update(K.REL241)
    K.REL['attn'] = attn

    def composed(_mode='record'):
        r, dags = {}, {}
        for wl in ('ar', 'mtp'):
            x = res[wl]
            ex = sum(e['cycles'] for e in x['extra'])
            T = max(sum(x['cyc'][i] for i in x['crit']) + ex, C.solve(x['dag'], x['cyc'])[0] + ex)
            tau = x['tau']
            r[wl] = dict(T_cycles=T, tok_s=round(F_CLK * (tau if wl == 'mtp' else 1) / T, 1),
                         pct_measured=four_way(x['by'])['measured_current_rtl'],
                         extra_terms=[dict(slot=e['slot'], kind=e['kind'], cycles=e['cycles']) for e in x['extra']])
            dags[wl] = (x['dag'], dict(x['cyc']))
        return dict(workloads=r), dags
    K.composed = composed
    recs = K.build(str(MAP241), 'record', True, False, 1)
    return recs


# ---------------------------------------------------------------------------------------------- build / outputs
def build(layer_path=None, comp_dir=None, attn='G4'):
    layer_rx, layer_rej = load_layer_cycles(layer_path)
    receipts, comp_rej = load_components(comp_dir)
    res = {wl: compose(wl, dict(attn=attn), layer_rx, receipts) for wl in ('ar', 'mtp')}
    # calendar inputs: same transforms except off-chip direct + release node terms (the calendar applies them)
    cal_in = {wl: compose(wl, dict(attn=attn, offchip=False, release=False, regrade=False), layer_rx, receipts)
              for wl in ('ar', 'mtp')}
    recs = calendar(cal_in, attn=attn)
    lat, dig = lane_table()
    r8 = json.loads(LAT_R8.read_text())
    r8f = lat.get('r8', {})
    padded = {k: dict(r8_pad=v['r8_pad'], base=v['base'], cycles=v['cycles'], r8_pad_min=v.get('r8_pad_min'))
              for k, v in sorted(lat['lanes'].items()) if v.get('r8_pad')}
    one = {wl: summarize(res[wl]) for wl in res}
    for wl in res:   # consistency: the calendar's composer T after its node override == this tool's T
        ov = recs['ar']['composition']['release241']['node_override'][wl]
        one[wl]['calendar_cross_check'] = dict(calendar_T_after_override=ov['T_after'], this_T=one[wl]['T_cycles'],
                                               diff=round(ov['T_after'] - one[wl]['T_cycles'], 1))
    reg = {}
    for wl in res:
        reg.update(res[wl]['regrade'])
    head = git('rev-parse', 'HEAD').strip()
    compose_1u = dict(
        schema=SCHEMA, lane='TOK-DS/COMPOSE', design='ds_rom (DeepSeek-V4.1) on the S81 array', head=head,
        die_plan=dict(plan=rel(PLAN), version=PLAN_VERSIONS.get(dig, f'plan of record at this HEAD (digest {dig})'),
                      latency_table=rel(LAT), latency_table_sha256=sha(LAT), plan_digest_in_table=lat['plan_digest'],
                      plan_digest_of_plan=dig, table_of_record=lat['plan_digest'] == dig, period_ps=lat['period_ps'],
                      lanes=len(lat['lanes']),
                      r8_fold=dict(folded=bool(r8f.get('fold', {}).get('folded')), fold=r8f.get('fold'),
                                   summary=r8f.get('summary'), landing=r8f.get('landing'),
                                   bus_groups_digest=r8f.get('bus_groups_digest'), landed=r8f.get('landed'),
                                   rebase=r8f.get('rebase'), padded_lanes=padded),
                      r8_variant=dict(table=rel(LAT_R8), plan_digest=r8['plan_digest'], lanes=len(r8['lanes']),
                                      verdict='NOT of record: BINDER4-S81 as-built bind on plan v4.6 (474d1c07a) + R8 '
                                              'landing pads on v4.7b bus groups; 13 shared lanes 1..2 cycles longer, '
                                              '18 v4.8 lanes absent')),
        clock_hz=F_CLK,
        inputs=dict(dags={k: rel(v) for k, v in C.DAGS.items()}, base=rel(C.BASE), elements=rel(ELEM),
                    hop_latency=rel(HOPLAT), ladder=rel(LADDER), toksim=rel(ROOT / 'tools/toksim_s81_compose.py'),
                    layer_cycles=layer_path, components=comp_dir),
        admission=dict(layer_cycles_admitted=sorted(layer_rx), layer_cycles_rejected=layer_rej,
                       components_admitted=[r['_file'] for r in receipts], components_rejected=comp_rej,
                       element_rules='toksim_s81_compose strict admission (measured grade AND bit_exact); excluded: '
                                     + ', '.join(sorted({e['op'] for e in res['ar']['excluded']}))),
        grades={CUR: 'measured on RTL whose every named module is blob-identical to this tree (or a PASS receipt '
                     'with mutant CAUGHT / a PASS layer replay)',
                OLD: 'measured, but on RTL that has since changed (or not verifiable): does NOT count',
                PRICED: 'analytic price / DAG number / release model term', EDGE: 'priced source-age edge',
                LANE: 'plan v4.8 latency-table lanes (register stages from the plan; a model of record, not measured)',
                PHY: 'off-chip leg, direct cabling D_cycles_max (modelled)'},
        lane_terms={k: dict(v, lanes=v['lanes'][:12]) for k, v in res['ar']['LT'].items()},
        lane_map=lane_map_table(res['ar']), unmapped=unmapped_list(res['ar']),
        regrade={k: v for k, v in sorted(reg.items())},
        workloads=one)
    cal = calendar_summary(recs, one)
    return compose_1u, cal


def calendar_summary(recs, one):
    F = F_CLK
    ar, mtp = recs['ar'], recs['mtp']
    ca, cm = ar['composition']['ar'], ar['composition']['mtp']
    T_ar = ca['T']
    T_mtp = cm.get('T') or cm.get('unqualified_original_T')
    tau = 4.159

    def formula(users, T_user, period, mtp_=False):
        eff = max(T_user, period)
        per = F * (tau if mtp_ else 1.0) / eff
        return dict(users=users, T_user=round(T_user, 1), period=period, bound='per-user token' if T_user >= period else
                    'calendar period', per_user_tok_s=round(per, 1), aggregate_tok_s=round(users * per))
    out = dict(
        schema=SCHEMA + '.calendar', tool='tools/s81_dv/dv_mu_calendar_phys.py build(map241, record-mode on THESE '
        'node cycles, alap, 1 job context) with REL241 (direct cabling, LINK5, land 0, G4, idx +40, Engram 640/II704, '
        'MTP causal six-position pipeline)', map=rel(MAP241), map_sha256=sha(MAP241),
        grade='MODEL: exact calendar arithmetic on composed node cycles; node cycles carry compose_1u grades; the '
              'stage split, forward-x chain, stage-hop law (HOP 821 incl. 266 direct PHY + 652 link serialisation) and '
              'MTP law are MODEL; the multi-user RTL calendar programme has not run (MU.TOK)',
        single_user_on_map=dict(
            ar=dict(T_composer=ca['T_composer'], T_after_release_node_terms=ar['composition']['release241']['node_override']['ar']['T_after'],
                    cal2_structural=ca['cal2_structural'], added_hops=ca['added_hops'],
                    forward_x_chain_delta=ca['forward_x_chain_delta'], T=T_ar, tok_s=round(F / T_ar, 1)),
            mtp=dict(T_composer=cm['T_composer'], T_step=T_mtp, tok_s=cm.get('tok_s'),
                     law_of_record='causal six-position pipeline (owner decision15)',
                     stretch_sensitivity=dict(T_step=mtp['pipeline_graph']['T_mtp_law_6f'],
                         tok_s=round(tau * F / mtp['pipeline_graph']['T_mtp_law_6f'], 1))
                         if mtp.get('pipeline_graph') else None,
                     schedule_verdict=cm.get('schedule_verdict', 'PASS'))),
        qualified=dict(
            ar=dict(users=ar['users'], period=ar['period'], per_user_tok_s=ar['per_user_tok_s'],
                    aggregate_tok_s=ar['aggregate_tok_s'], checker=ar['checker'], binding_next_user=ar.get('binding_next_user'),
                    bound_window=ar['bound_window'], binding_link=ar.get('binding_link')),
            mtp=dict(users=mtp['users'], period=mtp['period'], per_user_tok_s=mtp['per_user_tok_s'],
                     aggregate_tok_s=mtp['aggregate_tok_s'], checker=mtp['checker'],
                     binding_next_user=mtp.get('binding_next_user'), bound_window=mtp['bound_window'])),
        formula_table=dict(
            note='aggregate = users x f / max(T_user, period) (1019 README); T_user = per-user token (AR) / verify step '
                 '(MTP) on the 241-stage map; period = the calendar period that admits that many users',
            ar_50=formula(50, T_ar, ar['period']), ar_46=formula(46, T_ar, ar['period']),
            mtp_10=dict(formula(10, T_mtp, mtp['period'], True),
                        qualified=False, why='the 10-user MTP calendar (mucal241 6f law) FAULTS the same-user check '
                        '(calendar_sameuser_s81_1021 exit 2); the causal pipeline admits ' + str(mtp['users']) + ' users'),
            mtp_qualified=formula(mtp['users'], T_mtp, mtp['period'], True),
            dag_1u_only=dict(ar=one['ar']['tok_s'], mtp=one['mtp']['tok_s'],
                             note='DAG composition without the 241-stage map hops (compose_1u); not the release '
                                  'single-user figure')),
        measured_inputs=dict(
            per_user_cycles='compose_1u node cycles: AR measured-current-RTL ' + str(one['ar']['pct']['measured_current_rtl'])
                            + ' %, MTP ' + str(one['mtp']['pct']['measured_current_rtl']) + ' % (of the DAG composition)',
            slot_issue='measured-old-RTL: HEADMU seq_host/fixed_issue slot issue (10-19, 19bf4121e); dsdv_seq_host '
                       'changed on main since (blob 1c7a86d31 -> HEAD differs)',
            mu_collectives='measured-old-RTL: XDIE u5 46/10-user collectives on MU die ceaed19c4 (WIN/INV PASS)',
            not_measured='the 241-stage map calendar itself, stage-hop chain, forward-x, copy-B colouring, MTP pipeline '
                         'law (MODEL); no multi-user RTL token pass'),
        reference=dict(romopt_calendar='results/token_pass/calendar_pipeline_s81_1021 (G4: AR 50 x 952.8 = 47,642; MTP '
                                       '6 x 2,963.4 = 17,780) used --compose romopt = CALPIPE + ROMOPT PROPOSED spans '
                                       '(not measured); this file uses the release-partial measured composition'))
    return out


def write_readme(c1, cal, out):
    a, m = c1['workloads']['ar'], c1['workloads']['mtp']
    qa, qm = cal['qualified']['ar'], cal['qualified']['mtp']
    sa, sm = cal['single_user_on_map']['ar'], cal['single_user_on_map']['mtp']
    L = []
    L.append('# TOK-DS/COMPOSE: DeepSeek S81 token latency on the S81 die plan of record (2026-10-24)\n')
    L.append('Analytical composition (AGENTS.md rule: simulate the minimum component, compose system timing). '
             'Tool: `tools/s81_dv/tokfunc/compose_tok_ds.py` (`--selftest`, `--check`). Clock 1.2 GHz (833 ps).\n')
    L.append('**Verdict: NOT MEASURED ON THE CURRENT DIE.** No stage was measured on the v4.8 die, which has not been '
             'assembled. The component numbers below were measured on p4l (10-19/20) RTL. Each one counts as '
             '`measured-current-RTL` only if every RTL module its record names is blob-identical on this tree\'s HEAD.'
             ' That check is necessary but not sufficient: submodules a record does not name are not checked, and a die-level '
             'context change (stations, landing) is covered only by the lane substitution.\n')
    L.append('## Latency table of record\n')
    d = c1['die_plan']
    L.append(f'- `{d["latency_table"]}`: plan_digest `{d["plan_digest_in_table"]}` = digest of `die_plan.json` '
             f'(`{d["plan_digest_of_plan"]}`), {d["lanes"]} lanes, {d["period_ps"]} ps. **This table is of record.**')
    L.append(f'- Plan: {d["version"]}.')
    f = d.get('r8_fold') or {}
    if f.get('folded'):
        fo, su = f['fold'], f['summary']
        L.append(f'- R8 landing pads PRICED in the table (`gen.py latency --fold-r8`, `physical/die_plan/s81/lat/run_lat_r8.sh`): '
                 f'per lane `cycles` = `base` + `r8_pad` (largest R8 landing pad of the lane\'s members). Bus groups '
                 f'`{f["bus_groups_digest"]}` (BINDER4 b3r8 as-built bind, plan v4.7b; bound depths rebased by lane onto this '
                 f'plan: {f["rebase"]["moved"]} of {f["rebase"]["members"]} members moved), landed rule {f["landed"]}. '
                 f'{su["pad_flops"]:,} pad flops, {su["padded_members"]} padded members, {su["landed_bundles"]} landed '
                 f'bundles ({su["landed_over_margin"]} over the margin, kept per-lane). {fo["lanes_padded"]} lanes padded, '
                 f'max {fo["max_pad"]}, mean {fo["mean_pad"]} cycles, sum {fo["sum_pad"]}; bind paths outside the plan '
                 f'lanes: {fo["not_plan_lanes"]}.')
        L.append('')
        L.append('| lane | base | R8 pad | cycles | min member pad |')
        L.append('|---|---:|---:|---:|---:|')
        for k, v in sorted(f['padded_lanes'].items(), key=lambda x: (-x[1]['r8_pad'], x[0])):
            L.append(f'| {k} | {v["base"]} | {v["r8_pad"]} | {v["cycles"]} | {v["r8_pad_min"]} |')
        L.append('')
        L.append('Lane terms the composition uses (the pads they picked up):\n')
        L.append('| term | cycles | without R8 pads | R8 pad | padded lanes in the term |')
        L.append('|---|---:|---:|---:|---|')
        for k, v in sorted(c1['lane_terms'].items()):
            L.append(f'| {k} | {v["cycles"]} | {v["base_cycles"]} | {v["r8_pad_cycles"]} | '
                     f'{", ".join(f"{a} +{b}" for a, b in v["r8_pad_lanes"].items()) or "-"} |')
        L.append('')
    else:
        L.append('- The R8 landed-bundle pads are NOT folded into this table (no `r8.fold` block).')
    L.append(f'- `{d["r8_variant"]["table"]}`: digest `{d["r8_variant"]["plan_digest"]}`, {d["r8_variant"]["lanes"]} '
             f'lanes. {d["r8_variant"]["verdict"]}.\n')
    for name, cmp_ in c1.get('compare', {}).items():
        if name == 'table':
            continue
        L.append(f'### Delta vs {name} (`{cmp_["dir"]}`)\n')
        L.append('| quantity | then | now | delta |')
        L.append('|---|---:|---:|---:|')
        for q, (o, n) in cmp_['rows'].items():
            L.append(f'| {q} | {o:,} | {n:,} | {round(n - o, 1):+,} |' if isinstance(o, (int, float)) and isinstance(n, (int, float))
                     else f'| {q} | {o} | {n} | - |')
        L.append('')
        for wl, dd in cmp_['critical_stage_delta'].items():
            top = sorted(dd.items(), key=lambda x: (-abs(x[1]), x[0]))[:12]
            L.append(f'Critical-stage table delta ({wl.upper()}, top-40 stages, cycles): '
                     + (', '.join(f'{k} {v:+,}' for k, v in top) or 'none') + '\n')
    L.append('## Single user\n')
    L.append('| workload | DAG composition cycles | tok/s (DAG) | on the 241-stage map: cycles | tok/s (map) | '
             'measured-current | measured-old | priced (incl. plan lanes) | PHY |')
    L.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|')
    L.append(f'| AR | {a["T_cycles"]:,.0f} | {a["tok_s"]:,.1f} | {sa["T"]:,.0f} | {sa["tok_s"]:,.1f} | '
             f'{a["pct"]["measured_current_rtl"]} % | {a["pct"]["measured_old_rtl"]} % | {a["pct"]["priced"]} % | '
             f'{a["pct"]["modelled_phy"]} % |')
    mt = sm['T_step']
    L.append(f'| MTP (tau 4.159) | {m["T_cycles"]:,.0f} / step = {m["per_accepted_cycles"]:,.0f} / token | '
             f'{m["tok_s"]:,.1f} | {mt:,.0f} / step | {4.159 * F_CLK / mt:,.1f} | {m["pct"]["measured_current_rtl"]} % | '
             f'{m["pct"]["measured_old_rtl"]} % | {m["pct"]["priced"]} % | {m["pct"]["modelled_phy"]} % |\n')
    sensitivity = sm.get('stretch_sensitivity')
    if sensitivity:
        L.append(f'Owner decision15 uses the checker-qualified six-position pipeline above. The prior stretch law '
                 f'remains a sensitivity: {sensitivity["T_step"]:,.0f} cycles/step, '
                 f'{sensitivity["tok_s"]:,.1f} tok/s. It does not bound the rate of record.\n')
    L.append('The grade percentages are shares of the DAG composition. "Priced" splits as AR '
             f'{a["pct"]["priced_split"]} and MTP {m["pct"]["priced_split"]}.')
    L.append('The 241-stage map figure is the dv_mu_calendar_phys single-user timeline on the same node cycles. On top of '
             f'the DAG composition it adds the release node terms (G4 attention, idx +40, Engram 640), {sa["added_hops"]:,} '
             f'cycles of stage hops on the map, a forward-x chain of {sa["forward_x_chain_delta"]:,} cycles and '
             f'{sa["cal2_structural"]:,} structural cycles (all MODEL). It is the release-shaped single-user number.\n')
    cc = m['calendar_cross_check']
    L.append(f'Cross-check: the calendar tool, given the same node cycles, re-derives AR T after its node override = '
             f'{a["calendar_cross_check"]["calendar_T_after_override"]:,.1f} (this tool {a["T_cycles"]:,.1f}). For MTP the '
             f'difference is {cc["diff"]:+,.0f} cycles. This tool rebuilds the MTP wave composites from their members after '
             'direct cabling and G4. The calendar overrides only member nodes and keeps the composite at its input value. '
             'The calendar replaces the composer wave with its own physical wave term anyway.\n')
    L.append('## Multi-user (241-stage calendar, same inputs)\n')
    ft = cal['formula_table']
    L.append('| case | users | T_user | period | per user tok/s | aggregate tok/s | status |')
    L.append('|---|---:|---:|---:|---:|---:|---|')
    L.append(f'| AR, qualified calendar | {qa["users"]} | {sa["T"]:,.0f} | {qa["period"]:,} | {qa["per_user_tok_s"]} | '
             f'{qa["aggregate_tok_s"]:,} | checker {qa["checker"]["result"]}, N+1 {qa["checker"]["negative_n_plus_1"]["result"]} |')
    x = ft['ar_46']
    L.append(f'| AR at 46 users (formula) | 46 | {x["T_user"]:,.0f} | {x["period"]:,} | {x["per_user_tok_s"]} | '
             f'{x["aggregate_tok_s"]:,} | subset of the 50-user calendar |')
    L.append(f'| MTP, qualified causal pipeline | {qm["users"]} | {mt:,.0f} | {qm["period"]:,} | {qm["per_user_tok_s"]} | '
             f'{qm["aggregate_tok_s"]:,} | checker {qm["checker"]["result"]} (same-user included) |')
    x = ft['mtp_10']
    L.append(f'| MTP at 10 users (formula) | 10 | {x["T_user"]:,.0f} | {x["period"]:,} | {x["per_user_tok_s"]} | '
             f'{x["aggregate_tok_s"]:,} | **NOT qualified**: {x["why"]} |\n')
    L.append('Measured inputs: ' + '; '.join(f'{k}: {v}' for k, v in cal['measured_inputs'].items()) + '.\n')
    L.append('The earlier 47,642 / 17,780 calendar (calendar_pipeline_s81_1021) ran on `--compose romopt`, which is the '
             'CALPIPE + ROMOPT PROPOSED compiled spans and not measured. This calendar uses the measured release-partial '
             'composition plus the v4.8 lanes.\n')
    L.append('## What is NOT measured (AR critical path, cycles not measured-current, by blocking ladder gap)\n')
    L.append('| blocker | AR cycles | MTP cycles |')
    L.append('|---|---:|---:|')
    keys = list(dict.fromkeys(list(a['not_measured_current_by_blocker']) + list(m['not_measured_current_by_blocker'])))
    for k in keys:
        L.append(f'| {k} | {a["not_measured_current_by_blocker"].get(k, 0):,.0f} | '
                 f'{m["not_measured_current_by_blocker"].get(k, 0):,.0f} |')
    L.append('\nTop AR stages that are not measured-current:\n')
    L.append('| op | cycles | grades | blocked by |')
    L.append('|---|---:|---|---|')
    for x in a['top_not_measured_current'][:12]:
        L.append(f'| {x["op"]} | {x["cycles"]:,.0f} | {", ".join(f"{k} {v:,.0f}" for k, v in x["grades"].items())} | '
                 f'{", ".join(x["blocked_by"]) or "-"} |')
    L.append('\n## Critical-path stage table (AR, top 20)\n')
    L.append('| op | n | cycles | share | grades |')
    L.append('|---|---:|---:|---:|---|')
    for x in a['critical_stage_table'][:20]:
        L.append(f'| {x["op"]} | {x["count"]} | {x["cycles"]:,.0f} | {x["share_pct"]} % | '
                 f'{", ".join(f"{k} {v:,.0f}" for k, v in x["grades"].items())} |')
    L.append('\n## Lane mapping (DAG term -> plan v4.8 lanes)\n')
    for x in c1['lane_map']:
        L.append(f'- **{x["dag_term"]}** -> `{x["lane_quantity"]}` = {x["per_unit"]} cycles '
                 f'({", ".join(map(str, x["lanes"][:5]))}{" ..." if len(x["lanes"]) > 5 else ""})'
                 + (f'; {x["formula"]}' if x.get('formula') else '')
                 + (f'; AR critical delta {x["critical_delta"]:+,.0f}' if x.get('critical_delta') else ''))
    tr = a['transforms']
    L.append(f'- Off-chip: switched 453 -> direct D_cycles_max (tp_mesh 251 / stage_hop 266 / head_hop 257). AR critical '
             f'cycles saved: {tr["offchip_saved_critical"]}.')
    L.append(f'- Release node terms (priced), AR critical delta: {tr["release_critical"]}.\n')
    L.append('Edges and terms that could not be mapped (kept with their old grade):\n')
    for x in c1['unmapped']:
        L.append(f'- {x["kind"]}: `{x["op"]}`. {x["why"]}')
    L.append('\n## Regrade (measured records vs HEAD rtl/)\n')
    L.append('| record :: op | from | to | why |')
    L.append('|---|---|---|---|')
    for k, v in c1['regrade'].items():
        det = v.get('detail') or {}
        why = det.get('why', '')
        if det.get('changed'):
            why += ': ' + ', '.join(det['changed'][:4])
        L.append(f'| {k} | {v["from_grade"]} | {v["to"]} | {why} |')
    L.append('\n## Inputs to come (re-run commands)\n')
    L.append('- `--layer-cycles F.json`. Schema: `{"L0": {"cycles": <int>, "verdict": "PASS", "receipt": "<host:path or '
             'repo path>", "die": "fc31 35ba1ef7", "rtl": "<rev>", "applies_to": ["L1", ...]}}`. Only `verdict == "PASS"` '
             'is admitted. The cycles are the single-die layer replay span. They replace that layer\'s on-die (non-xdie) '
             'node cycles, scaled so that the critical-path sum equals the measured value, and the layer\'s `dv_p4l` term '
             'is dropped. The grade is measured-current-RTL with the receipt. `applies_to` is explicit and never implied.')
    L.append('- `--components DIR` (COMP receipts `results/token_pass/tokds_comp_1024/*.json`). Each receipt holds '
             '`verdict` = "PASS", `mutant` = "CAUGHT" (or `mutants` {name: "CAUGHT"}), and `op` (DAG op or list) with '
             '`cycles` (or `per_layer`), optional `old_cycles_per_instance` (shape match), `replaces` "logic"|"node", '
             '`receipt`. A rstop receipt can instead carry `leg_rstop_edges` (edges a ring stop).')
    L.append('- Command: `python3 tools/s81_dv/tokfunc/compose_tok_ds.py --layer-cycles <F.json> --components '
             'results/token_pass/tokds_comp_1024 --out results/token_pass/tokds_compose_1024`.\n')
    cmd = (f'python3 tools/s81_dv/tokfunc/compose_tok_ds.py --out {rel(out)}'
           + (f' --lat {c1["die_plan"]["latency_table"]}' if Path(c1['die_plan']['latency_table']) != Path(rel(LAT_OF_RECORD)) else '')
           + ''.join(f" --compare '{n}={v['dir']}'" for n, v in c1.get('compare', {}).items()))
    L.append(f'- This run: `{cmd}` (`--check` with the same arguments re-derives both JSON files).\n')
    L.append('Files: `compose_1u.json` (all tables, lane map, unmapped list, regrade receipts) and `calendar_mu.json`.')
    (out / 'README.md').write_text('\n'.join(L) + '\n')


def headline(c1, cal):
    a, m = c1['workloads']['ar'], c1['workloads']['mtp']
    sa, sm = cal['single_user_on_map']['ar'], cal['single_user_on_map']['mtp']
    qa, qm = cal['qualified']['ar'], cal['qualified']['mtp']
    r = {'1u AR, 241-stage map: cycles/token': round(sa['T']), '1u AR, 241-stage map: tok/s': sa['tok_s'],
         '1u AR, DAG: cycles/token': round(a['T_cycles']), '1u AR, DAG: tok/s': a['tok_s'],
         '1u MTP, 241-stage map: cycles/step': round(sm['T_step']), '1u MTP, 241-stage map: tok/s': sm['tok_s'],
         '1u MTP, DAG: cycles/step': round(m['T_cycles']), '1u MTP, DAG: tok/s': m['tok_s'],
         'MU AR: users': qa['users'], 'MU AR: aggregate tok/s': qa['aggregate_tok_s'], 'MU AR: period cycles': qa['period'],
         'MU MTP: users': qm['users'], 'MU MTP: aggregate tok/s': qm['aggregate_tok_s'],
         'MU MTP: period cycles': qm['period']}
    for k, v in sorted(c1['lane_terms'].items()):
        r[f'lane term {k}'] = v['cycles']
    return r


def compare(d, c1, cal):
    """deltas vs an earlier compose output directory (same headline quantities)"""
    o1 = json.loads((d / 'compose_1u.json').read_text())
    oc = json.loads((d / 'calendar_mu.json').read_text())
    old, new = headline(o1, oc), headline(c1, cal)
    rows = {k: (old.get(k), new.get(k)) for k in new}
    ops = {}
    for wl in ('ar', 'mtp'):
        so = {r['op']: r['cycles'] for r in o1['workloads'][wl]['critical_stage_table']}
        sn = {r['op']: r['cycles'] for r in c1['workloads'][wl]['critical_stage_table']}
        ops[wl] = {k: round(sn.get(k, 0) - so.get(k, 0), 1) for k in sorted(set(so) | set(sn))
                   if sn.get(k, 0) != so.get(k, 0)}
    return dict(dir=rel(d), plan_digest=o1['die_plan']['plan_digest_in_table'], rows=rows,
                critical_stage_delta=ops)


def dumps(x):
    return json.dumps(x, indent=1, sort_keys=True, default=lambda o: sorted(o) if isinstance(o, set) else str(o)) + '\n'


# ---------------------------------------------------------------------------------------------- selftest
def selftest():
    ok = True

    def chk(name, cond, msg=''):
        nonlocal ok
        ok &= bool(cond)
        print(f'{"PASS" if cond else "FAIL"} {name} {msg}')
    # 1 parity with toksim_s81_compose (no transforms, no regrade) = committed cycles.json
    ref = json.loads((C.OUT / 'cycles.json').read_text())
    for wl in ('ar', 'mtp'):
        r = compose(wl, dict(lanes=False, release=False, offchip=False, regrade=False))
        w = ref['workloads'][wl]
        chk(f'parity {wl} T', abs(r['T'] - w['T_cycles']) < 0.5, f'{r["T"]:.1f} vs {w["T_cycles"]}')
        bg = {k: round(v, 1) for k, v in r['by'].items() if abs(v) > 0.05}
        d = max(abs(bg.get(k, 0) - w['by_grade'].get(k, 0)) for k in set(bg) | set(w['by_grade']))
        chk(f'parity {wl} grades', d < 1.0, f'max diff {d:.1f}')
    # 2 latency table of record
    lat, dig = lane_table()
    chk('latency table digest == plan v4.8 digest', lat['plan_digest'] == dig, f'{lat["plan_digest"]} / {dig}')
    chk('period 833 ps', lat['period_ps'] == PERIOD_PS)
    # 3 never promote: measured-current after regrade <= measured before; priced never measured
    r0 = compose('ar', dict(regrade=False))
    r1 = compose('ar', dict())
    m0 = sum(v for k, v in r0['by'].items() if k in MEASURED_IN)
    chk('no promotion (regrade)', r1['by'].get(CUR, 0) <= m0 + 0.5, f'{r1["by"].get(CUR, 0):.0f} <= {m0:.0f}')
    pr0 = sum(x['c'] for cl in r0['comps'].values() for x in cl if x['g'] in (PRICED, EDGE, PHY, LANE))
    pr1 = sum(x['c'] for cl in r1['comps'].values() for x in cl if x['g'] in (PRICED, EDGE, PHY, LANE))
    chk('regrade leaves non-measured cycles unchanged', abs(pr0 - pr1) < 0.5)
    # 4 layer admission
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / 'l.json'
        p.write_text(json.dumps({'L0': dict(cycles=20000, verdict='FAIL', receipt='x'),
                                 'L2': dict(cycles=30000, verdict='PASS', receipt='epyc3:/tmp/r')}))
        ok_, rej = load_layer_cycles(p)
        chk('layer admission: FAIL rejected, PASS admitted', list(ok_) == ['L2'] and rej and rej[0]['layer'] == 'L0')
        rl = compose('ar', dict(), ok_)
        l2 = [i for i in rl['crit'] if rl['dag']['nodes_by_id'][i].get('layer') == 2
              and rl['dag']['nodes_by_id'][i].get('cls') not in ('coll', 'hop')]
        s = sum(rl['cyc'][i] for i in l2)
        chk('layer replay sets L2 critical on-die sum', abs(s - 30000) < 1.0, f'{s:.1f}')
        chk('layer replay graded measured-current', all(rl['comps'][i][0]['g'] == CUR for i in l2))
        # 5 component admission
        dd = Path(td) / 'c'
        dd.mkdir()
        (dd / 'a.json').write_text(json.dumps(dict(verdict='PASS', mutant='MISSED', op='ffn.bias', cycles=1)))
        (dd / 'b.json').write_text(json.dumps(dict(verdict='PASS', mutants={'m1': 'CAUGHT'}, op='ffn.bias', cycles=100,
                                                   receipt='x')))
        (dd / 'c.json').write_text(json.dumps(dict(verdict='FAIL', mutant='CAUGHT', op='ffn.bias', cycles=1)))
        ok_, rej = load_components(dd)
        chk('component admission: only PASS + CAUGHT', len(ok_) == 1 and ok_[0]['_file'].endswith('b.json') and len(rej) == 2)
        rc = compose('ar', dict(), None, ok_)
        b = [i for i in rc['crit'] if rc['dag']['nodes_by_id'][i].get('op') == 'ffn.bias']
        chk('component receipt applied as measured-current', b and all(rc['comps'][i][0]['g'] == CUR and
                                                                     rc['comps'][i][0]['c'] == 100 for i in b))
    # 6 lane-map sanity: every substituted wire comes from the table
    LT = lane_terms()
    lat_l = lat['lanes']
    chk('lane terms reference only table lanes', all(l in lat_l for v in LT.values() for l in v['lanes']))
    print('SELFTEST', 'PASS' if ok else 'FAIL')
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--layer-cycles')
    ap.add_argument('--components')
    ap.add_argument('--attn', default='G4', choices=sorted(ATTN))
    ap.add_argument('--out', default=str(OUT))
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--lat', help='latency table to price (default: the table of record, physical/die_plan/s81/lat)')
    ap.add_argument('--compare', action='append', default=[], metavar='NAME=DIR',
                    help='earlier compose outputs (compose_1u.json + calendar_mu.json) to tabulate deltas against')
    a = ap.parse_args(argv)
    if a.lat:
        global LAT
        LAT = Path(a.lat).resolve()
        lane_table.cache_clear()
    if a.selftest:
        return 0 if selftest() else 1
    c1, cal = build(a.layer_cycles, a.components, a.attn)
    if a.compare:
        c1['compare'] = {n: compare(Path(d), c1, cal) for n, d in (x.split('=', 1) for x in a.compare)}
    out = Path(a.out)
    files = {'compose_1u.json': dumps(c1), 'calendar_mu.json': dumps(cal)}
    if a.check:
        rc = 0
        for f, s in files.items():
            same = (out / f).exists() and (out / f).read_text() == s
            print(f'{f}: {"SAME" if same else "DIFFERS"}')
            rc |= 0 if same else 1
        return rc
    out.mkdir(parents=True, exist_ok=True)
    for f, s in files.items():
        (out / f).write_text(s)
    write_readme(c1, cal, out)
    for wl, w in c1['workloads'].items():
        print(f'{wl}: T {w["T_cycles"]:,} cyc -> {w["tok_s"]:,} tok/s; {w["pct"]}; calendar check {w["calendar_cross_check"]}')
    print('calendar:', json.dumps(cal['qualified']['ar'] | {'checker': None}, default=str)[:300])
    print('calendar mtp:', json.dumps(cal['qualified']['mtp'] | {'checker': None}, default=str)[:300])
    print('single user on map:', json.dumps(cal['single_user_on_map']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
