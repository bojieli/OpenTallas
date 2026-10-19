#!/usr/bin/env python3
"""HKV-DIE2 10-19: the static KV die's stage-derived parameters, recomputed from the ACTUAL die netlist table.

kv_static_die prices several static parameters from the plan's relay_stages at generation time:
  ahub_ages      qkd_ahub_static_dw AP_OFS_s / FR_OFS (+ am_lag_edges for the compiler's EXP_START)
  astk_eread     e_after_header per V port (the pair takes in_e that many edges after its V header vh)
  attn_fault     per fault leaf / lane the edges to attn_face.unit_fault (the compiler prices the lane max)
  seq_kvn        the seq KVN-arrival bundle: S_kw == S_rx + S_prg + LAND (qkd_seq_core_st_s KVN_A0 is fixed)
After generation the die changes those stage counts: forwarded lanes (landed age = ceil(landed - 1), not the relay
count), bundle pads, pin-repair relays and the kv_lane_stations relay stations (HKV-STATIONS: +1/+2 edges on 128 buses).
This module recomputes every one of them from the die-run netlist table (tools/qwen_layerbench/netlist_relay_stages.py:
per bus src_nets -> generator bid, age_edges per destination pin; a landed lane n>1 takes its fwd_lanes.json age) with
the SAME kv_static_die formulas, and FAILS when:
  * a bus a parameter depends on is not found in the table (unresolved: fail closed);
  * the seq KVN bundle is torn on the actual netlist (S_kw != S_rx + S_prg + LAND -> f_arr at the first KVN word);
  * the hub binds AP_OFS / FR_OFS other than the recomputed values (die.v instance parameter, else the hardened kit's
    spec params, else the RTL default {4{16'd2}} / 0);
  * the generator's recorded (plan) parameters differ from the recomputed ones (the plan record is stale: consumers
    must take static_params.json, never the plan record).

    generator:  kv_die.py case writes CASE/static_model.json (model_lite(m): relay/fork stages, forks, bids, plan params)
    die chain:  kv_static_params.py --model CASE/static_model.json --table RUN/relay_stages_netlist.json.gz
                    [--fwd-lanes RUN/fwd_lanes.json] [--die-v die.v] --out RUN/static_params.json   (exit 1 on FAIL)
    compiler:   layer_compile.py --kv-static-model CASE/static_model.json [--kv-fwd-lanes ...] (same compute + check on
                the table it compiles with; failures become findings, the parameters go into the manifest)
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'tools'))

SCHEMA_MODEL = 'opentallas.qwen_kv.static_model.v1'
SCHEMA = 'opentallas.qwen_kv.static_params.v1'
AHUB_DEFAULT = dict(AP_OFS=[2, 2, 2, 2], FR_OFS=0)          # rtl/hdc/nearhbm/qkd_ahub_static_dw.sv parameter defaults
AHUB_KIT_SPEC = 'tools/ref_tile/specs_kvahubdw/qkd_ahub_sdw.json'


def _ksd():
    import kv_static_die as KSD
    return KSD


# ------------------------------------------------------------------------------------------------ generator side
def _first_hop_bid(m, inst, port):
    for b in m['buses']:
        if b is not None and b[3] and tuple(b[3][0]) == (inst, port):
            return b[0]
    return None


def model_lite(m):
    """the generator facts the post-station recompute needs (kv_die.py case -> CASE/static_model.json)"""
    KSD = _ksd()
    by = {i.name: i for i in m['insts']}
    rs = dict(m.get('relay_stages') or {})
    fs = dict(m.get('fork_stages') or {})
    forks = {b: [list(x) for x in v] for b, v in (m.get('forks') or {}).items()}
    plan = dict(ahub_ages=KSD.ahub_ages(m) if KSD.AHUB_STATIC and 'ks_ahs' in rs else None,
                astk_eread=KSD.astk_eread(m) if KSD.ASTK_ST else None,
                attn_fault=KSD.afault_latency(m))
    seq = None
    if all(i in by for i in ('seq', 'kvs_attn', 'd2d_kv')):
        seq = dict(rx=_first_hop_bid(m, 'd2d_kv', 'srx'), prg=_first_hop_bid(m, 'kvs_attn', 'prg'),
                   kw=_first_hop_bid(m, 'd2d_kv', 'skw'), dst=dict(rx='kvs_attn', prg='seq', kw='seq'), land=int(KSD.ATTN_LAND),
                   bundle=(m.get('bundle_eq') or {}).get('bundles', {}).get('S.seq_kvn'))
    hub = None
    if 'ahub' in by:
        hub = dict(inst='ahub', master=by['ahub'].master,
                   parameters=(KSD.bindings().get('qkd_ahub') or {}).get('parameters'))
    dsts = {}                                     # bid -> its non-relay destination pins (expanded sources: dst fallback)
    for b in m['buses']:
        if b is None or not b[3]:
            continue
        base = re.sub(r'__r\d+$', '', b[0])
        if base in rs:
            for e in b[3][1:]:
                if not str(e[0]).startswith('rly_'):
                    dsts.setdefault(base, []).append(list(e))
    # KVR-DERIVE 10-19: the plan's attention-path schedule, the tile ages, what the generator binds per instance, and the
    # chain sources / masters for the relay-domain audit
    pp = plan_paths(m)
    fl_fin = (KSD.FACE_LAND_TILES.get('kvs_attn') or {}).get('fin', 0) if 'kvs_attn' in KSD.FACE_LAND_SEL else 0
    bus_src, sinks = {}, {}
    for b in m['buses']:
        if b is not None and b[1] not in ('clock_trunk', 'reset', 'constant') and len(b[3]) >= 2:
            base = re.sub(r'(__(r\d+|pinfix\d+|beq\d+))+$', '', b[0])
            if base == b[0]:
                bus_src[base] = [b[3][0][0], b[3][0][1].lstrip('*')]
            for e in b[3][1:]:                          # the chain's first non-relay sink (the launch domain fallback)
                if not str(e[0]).startswith('rly_') and base not in sinks:
                    sinks[base] = [e[0], e[1].lstrip('*')]
    for base, v in bus_src.items():
        v += sinks.get(base, [])
    return dict(schema=SCHEMA_MODEL, relay_stages=rs, fork_stages=fs, forks=forks, seq_kvn=seq, hub=hub, plan=plan, dsts=dsts,
                static_schedule=dict(paths=pp, schedule=schedule(pp, face_land_fin=fl_fin)), tile_ages=KSD.tile_ages(),
                bindings=m.get('static_bindings') or {}, bus_src=bus_src,
                masters={i.name: i.master for i in m['insts']},
                face_land=dict(enabled=KSD.FACE_LAND, selected=sorted(KSD.FACE_LAND_SEL), tiles=KSD.FACE_LAND_TILES,
                               fin_edges=fl_fin),
                flags=dict(attn_land=KSD.ATTN_LAND, astk_expand=KSD.ASTK_EXPAND, astk_rl=KSD.ASTK_RL,
                           astk_erl=KSD.ASTK_ERL, afault=KSD.AFAULT, ahub_static=KSD.AHUB_STATIC))


# ------------------------------------------------------------------------------------------------ table side
def _bid_of(net):
    n = net[2:] if net.startswith('n_') else net
    return n


def _inst_is(name, inst):
    return name == inst or name.startswith(inst + '__') or name.startswith(inst + '/')


def lane_ages(fwd):
    """bid -> landed core-edge age of its worst lane (kv_static_ages.fwd_overlay rule: ceil(landed - 1))"""
    if not fwd:
        return {}
    import kv_static_ages as KSA
    out = {}
    for L in fwd.get('lanes', []):
        st = L['stations'] if isinstance(L['stations'], list) else eval(L['stations'])  # noqa: S307 (json list repr)
        b = KSA.lane_bid(st[-1])
        out[b] = max(out.get(b, 0), math.ceil(L['landed'] - 1))
    return out


def post_stages(model, doc, fwd=None):
    """per generator bid (and fork bid__f<i>) the ACTUAL age in core edges on the die netlist: max over the table
    records the bid's source net drives into its destination instance; age_edges when known, else the bid's landed lane
    age from fwd_lanes.json; None (unresolved) when neither exists"""
    by_bid = {}
    for b in doc['buses']:
        keys = set()
        for n in b.get('src_nets') or ():
            parts = _bid_of(n).split('__')
            keys |= {'__'.join(parts[:i]) for i in range(1, len(parts) + 1)}
        for k in keys:
            by_bid.setdefault(k, []).append(b)
    if not by_bid:
        raise SystemExit('kv_static_params: the netlist table carries no src_nets (re-export with '
                         'tools/qwen_layerbench/netlist_relay_stages.py at HKV-DIE2 or later)')
    la = lane_ages(fwd)
    forks = model.get('forks') or {}

    def age(recs, bid):
        vals = []
        for r in recs:
            a = r.get('age_edges', r['stages'])
            if a is None:
                a = la.get(bid)
                if a is None:
                    return None, f'{r["id"]}: landed lane age unknown (no fwd_lanes.json lane for {bid})'
            vals.append(a)
        return (max(vals), None) if vals else (None, f'{bid}: no table record')

    rs, fs, unresolved, src = {}, {}, [], {}
    deps = set(_deps(model))
    by_dst = {}
    for b in doc['buses']:
        by_dst.setdefault((b['dst']['inst'], b['dst']['port'].split('__')[0]), []).append(b)

    def dst_recs(eps):
        out = []
        for inst, port in eps:
            out += by_dst.get((inst, port), [])
        return out
    for bid in model['relay_stages']:
        if bid not in deps and bid.split('__')[0] not in deps:
            continue
        recs = by_bid.get(bid, [])
        if not recs:                              # source expanded (e.g. pvfork children): the bid's destination pins
            recs = dst_recs([tuple(e) for e in (model.get('dsts') or {}).get(bid, [])]
                            + [tuple(f) for f in forks.get(bid, [])])
        fdst = {f[0] for f in forks.get(bid, [])}
        main = [r for r in recs if not any(_inst_is(r['dst']['inst'], d) for d in fdst)] or recs
        v, why = age(main, bid)
        rs[bid] = v
        src[bid] = sorted({r['id'] for r in main})[:4]
        if v is None:
            unresolved.append(why)
        for i, (finst, _fport) in enumerate(forks.get(bid, [])):
            fb = f'{bid}__f{i}'
            frecs = [r for r in recs if _inst_is(r['dst']['inst'], finst)]
            fv, fwhy = age(frecs, fb)
            fs[fb] = fv
            src[fb] = sorted({r['id'] for r in frecs})[:4]
            if fv is None:
                unresolved.append(fwhy)
    sq = model.get('seq_kvn') or {}
    for k, d in (sq.get('dst') or {}).items():      # seq bundle members: the age INTO the named instance only
        bid = sq.get(k)
        recs = [r for r in by_bid.get(bid, []) if _inst_is(r['dst']['inst'], d)]
        v, why = age(recs, bid)
        rs[f'{bid}@{d}'] = v
        if v is None:
            unresolved.append(why)
    return rs, fs, unresolved, src


# ------------------------------------------------------------------------------------------------ parameters + check
def params(model, rs, fs):
    """the kv_static_die formulas on a stage table (rs / fs may hold None: a dependent value is then None)"""
    KSD = _ksd()
    mm = dict(relay_stages={k: v for k, v in rs.items() if v is not None},
              fork_stages={k: v for k, v in fs.items() if v is not None},
              forks={k: [tuple(x) for x in v] for k, v in (model.get('forks') or {}).items()})
    out = dict(ahub_ages=KSD.ahub_ages(mm) if model['flags'].get('ahub_static') and 'ks_ahs' in mm['relay_stages'] else None,
               astk_eread=KSD.astk_eread(mm) if model.get('plan', {}).get('astk_eread') is not None else None,
               attn_fault=KSD.afault_latency(mm) if model['flags'].get('afault') else None)
    sq = model.get('seq_kvn')
    if sq and all(sq.get(k) for k in ('rx', 'prg', 'kw')):
        dd = sq.get('dst') or {}
        S = {k: rs.get(f'{sq[k]}@{dd[k]}', rs.get(sq[k])) if k in dd else rs.get(sq[k]) for k in ('rx', 'prg', 'kw')}
        ok = None if None in S.values() else S['kw'] == S['rx'] + S['prg'] + sq['land']
        out['seq_kvn'] = dict(S_rx=S['rx'], S_prg=S['prg'], S_kw=S['kw'], LAND=sq['land'], aligned=ok,
                              rule='S_kw == S_rx + S_prg + LAND (qkd_seq_core_st_s KVN_A0 fixed after the CMD decode)')
    return out


def hub_bound(model, die_v=None):
    """every place the die's hub AP_OFS / FR_OFS is fixed: the hardened kit the die binds (OT_KV_AHUB_KIT_SPEC, default
    the qkd_ahub_sdw spec; its params, else the RTL defaults = what the view was hardened at) and, when present, the
    die.v instance parameters (+ the generator's binding).  Each must equal the table's values."""
    import os
    out = []
    spec = os.environ.get('OT_KV_AHUB_KIT_SPEC', AHUB_KIT_SPEC)
    try:
        kp = json.loads((ROOT / spec).read_text()).get('params') or {}
    except FileNotFoundError:
        kp = None
    if kp is not None:
        out.append((f'hardened kit {spec}', _vals(kp)))
    gp = (model.get('hub') or {}).get('parameters') or {}
    if 'AP_OFS' in gp or 'FR_OFS' in gp:
        out.append(('generator binding (static_model.json)', _vals(gp)))
    if die_v and Path(die_v).exists():
        m = re.search(r'qkd_ahub_static_dw\s*#\s*\((.*?)\)\s*ahub\s*\(', Path(die_v).read_text(errors='replace'), re.S)
        if m:
            pr = dict(re.findall(r'\.(\w+)\(([^()]*)\)', m.group(1)))
            if 'AP_OFS' in pr or 'FR_OFS' in pr:
                out.append((f'die.v {die_v}', _vals(pr)))
    return out


def _vals(pr):
    got = dict(AHUB_DEFAULT)
    if 'AP_OFS' in pr:
        got['AP_OFS'] = _ap_list(pr['AP_OFS'])
    if 'FR_OFS' in pr:
        got['FR_OFS'] = int(str(pr['FR_OFS']), 0)
    return got


def _ap_list(v):
    if isinstance(v, list):
        return [int(x) for x in v]
    s = str(v)
    fs = re.findall(r"16'h([0-9a-fA-F]+)", s)
    if fs:                                           # {s3, s2, s1, s0} MSB first
        vals = [int(x, 16) for x in reversed(fs)]
        return [x - 0x10000 if x & 0x8000 else x for x in vals]
    x = int(s, 0)
    return [((x >> (16 * k)) & 0xffff) - (0x10000 if (x >> (16 * k)) & 0x8000 else 0) for k in range(4)]


def _diff(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b), key=str):
            if k in ('schema', 'module', 'file', 'bench', 'rtl', 'note', 'AP_OFS_hex', 'buses'):
                continue
            out += _diff(a.get(k), b.get(k), f'{path}.{k}' if path else str(k))
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in _diff(x, y, f'{path}[{i}]')]
    return [] if a == b else [dict(param=path, plan=a, actual=b)]


def check(model, rs, fs, unresolved, actual, die_v=None):
    fails, info = [], []
    for u in unresolved:
        fails.append(dict(id='UNRESOLVED_STAGE', what=u))
    sq = actual.get('seq_kvn')
    if sq is not None and sq['aligned'] is not True:
        fails.append(dict(id='SEQ_KVN_TORN', what=f"S_kw {sq['S_kw']} != S_rx {sq['S_rx']} + S_prg {sq['S_prg']} + LAND "
                          f"{sq['LAND']}: qkd_seq_core_st_s faults f_arr at the first KVN word",
                          fix='re-equalise S.seq_kvn on the post-station netlist (pad skw or shorten prg/rx)'))
    ah = actual.get('ahub_ages')
    if ah is not None:
        for how, got in hub_bound(model, die_v):
            if got['AP_OFS'] != ah['AP_OFS'] or got['FR_OFS'] != ah['FR_OFS']:
                fails.append(dict(id='AHUB_OFS_BOUND', what=f'hub AP_OFS {got["AP_OFS"]} FR_OFS {got["FR_OFS"]} ({how}); '
                                  f'the die stage table needs AP_OFS {ah["AP_OFS"]} ({ah["AP_OFS_hex"]}) FR_OFS {ah["FR_OFS"]}',
                                  fix='harden the hub kit (and bind the die instance) at the static_params.json values'))
    fl = model.get('face_land') or {}
    if die_v and Path(die_v).exists() and fl.get('tiles'):
        txt = Path(die_v).read_text(errors='replace')
        sel = set(fl.get('selected', fl['tiles'] if fl.get('enabled') else ()))
        for tl, t in (fl.get('all_tiles') or fl['tiles']).items():
            # HKV-DIE3 10-19: per tile, by master (expanded children such as the ASTK strip's rly_296 relays included)
            ms = re.findall(r'^\s*(' + re.escape(t['master']) + r'(?:_fl)?)\s+(?:#\s*\(.*?\)\s*)?\w+\s*\(', txt, re.M | re.S)
            if not ms:
                continue
            landed = {m.endswith('_fl') for m in ms}
            want = tl in sel
            if landed != {want}:
                fails.append(dict(id='FACE_LAND_BINDING', what=f'{tl}: die.v binds {sorted(set(ms))} ({len(ms)} instances) but '
                                  f'the tile is {"" if want else "NOT "}selected (OT_KV_FACE_LAND): the compiler ages / '
                                  'startup calendar disagree with the tile',
                                  fix='bind the _fl view (CLOSED only) together with the tile in OT_KV_FACE_LAND, or neither'))
    plan = model.get('plan') or {}
    stale = []
    for k in ('ahub_ages', 'astk_eread', 'attn_fault'):
        if plan.get(k) is not None and actual.get(k) is not None:
            stale += [dict(record=k, **d) for d in _diff(plan[k], actual[k])]
    if stale:
        fails.append(dict(id='PLAN_PARAMS_STALE', what=f'{len(stale)} generator-recorded parameters differ from the '
                          'post-station die table (consumers must take static_params.json)', diffs=stale[:200]))
    changed = sorted(b for b, v in rs.items() if v is not None and b in model['relay_stages'] and v != model['relay_stages'][b])
    info.append(dict(id='STAGES_CHANGED', buses=len(changed), examples=[(b, model['relay_stages'].get(b), rs[b])
                                                                        for b in changed[:40]]))
    return fails, info


def attn_calendar_check(actual, rs, Ts=range(1, 8193)):
    """HKV-DIE3 10-19 (coordinator (b)): the compiled attention calendar of EVERY context against the bound hub / pvfin
    refusals, with the table's actual FR_OFS and pvw -> pvfin pair ages (kv_static_programme.attention_checks)"""
    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)
    from tools.qwen_kv_die import kv_static_programme as KP
    pr = KP.profile('die', json.loads((KP.ROOT / KP.AGES).read_text()))
    fr = (actual.get('ahub_ages') or {}).get('FR_OFS')
    d0, d1 = rs.get('ks_pvp0'), rs.get('ks_pvp1')
    delta = (d0 - d1) if d0 is not None and d1 is not None else 0
    return KP.attention_checks(pr, KP.service_end_of(pr), fr, pair_delta=delta, Ts=Ts)


# ------------------------------------------------------------------------------------------------ KVR-DERIVE 10-19
# The static-schedule ages of the attention path, derived from the relay plan (generator: plan_paths) or the post-station
# netlist table (table_paths) with ONE formula (schedule), checked against the ages the closed tiles hard-code
# (kv_static_die.tile_ages) and against what the die BINDS (die_bound.v / sidecar / generated tile text).  Every
# mismatch FAILS (coordinator 10-19: pad the faster side up to the tile value where legal, bind exactly the tile value,
# fail what cannot be padded; the later re-harden makes these ages boot-programmable registers).
def path_keys():
    KSD = _ksd()
    out = {}
    for st in KSD.STACKS:
        for g in range(8):
            e = f'ectl_{st}_{KSD.ectl_frame(g)}'
            out[f'krq_{st}_{g}'] = (f'krq_{st}_{g}', f'slg_{st}_{g}', None)
            out[f'krs_{st}_{g}'] = (f'krs_{st}_{g}', e, None)
        for k in range(4):
            for g in (0, 1):
                out[f'pvvq_{st}_{k}_{g}'] = (f'pvvq_{st}_{k}_{g}', f'slg_{st}_{2 * k + g}', None)
                out[f'pvrs_{st}_{k}_{g}'] = (f'pvrs_{st}_{k}_{g}', f'vport_{st}_{k}', None)
            out[f'pvrq_{st}_{k}'] = (f'pvrq_{st}_{k}', f'vport_{st}_{k}', None)
            out[f'O_{st}_{k}'] = (f'pvin_{st}_{k}', 'pvw_', '__u_ctl')        # V header vport.vo -> pair ctl (via the fork)
    for p in (0, 1):
        out[f'pvst_{p}'] = ('ks_pvst', f'pvw_{p}', None)
        out[f'pvp_{p}'] = (f'ks_pvp{p}', 'pvfin', None)
    out['pvfst'] = ('ks_pvfst', 'pvfin', None)
    out['fin'] = ('ks_pvfin', 'kvs_attn', None)
    return out


def table_paths(doc, fwd=None):
    """{path key: age} on the die netlist table (age_edges, landed lanes from fwd_lanes.json) + problems (unresolved / torn)"""
    by = {}
    for b in doc['buses']:
        for n in b.get('src_nets') or ():
            by.setdefault(_bid_of(n), []).append(b)
    la = lane_ages(fwd)
    out, probs = {}, []
    for key, (bid, dst, must) in path_keys().items():
        recs = [r for r in by.get(bid, []) if _inst_is(r['dst']['inst'], dst) or (dst.endswith('_') and
                                                                                  r['dst']['inst'].startswith(dst))]
        if must:
            recs = [r for r in recs if must in r['dst']['inst']]
        if bid == 'ks_pvfin':
            recs = [r for r in recs if r['dst']['port'].startswith('fin')]
        ages = set()
        for r in recs:
            a = r.get('age_edges', r['stages'])
            ages.add(la.get(bid) if a is None else a)
        if not ages or None in ages:
            probs.append(dict(id='UNRESOLVED_PATH', path=key, bid=bid, dst=dst))
            out[key] = None
        elif len(ages) > 1:
            probs.append(dict(id='TORN_PATH', path=key, bid=bid, dst=dst, ages=sorted(ages)))
            out[key] = max(ages)
        else:
            out[key] = ages.pop()
    return out, probs


def plan_paths(m):
    """the same path ages on the generator's relay plan (relay_stages / fork_stages after every generator pass)"""
    rs, fs, fk = m.get('relay_stages') or {}, m.get('fork_stages') or {}, m.get('forks') or {}
    out = {}
    for key, (bid, dst, _m) in path_keys().items():
        if key.startswith('O_'):
            sk = key[2:]
            out[key] = rs.get(f'pvin_{sk}', 0) + 1 + rs.get(f'pvh_{sk}', 0)
        elif key == 'pvst_1' and ('pvw_1', 'st') in [tuple(x) for x in fk.get('ks_pvst', [])]:
            out[key] = fs.get(f'ks_pvst__f{[tuple(x) for x in fk["ks_pvst"]].index(("pvw_1", "st"))}', 0)
        else:
            out[key] = rs.get(bid, 0)
    return out


def schedule(paths, face_land_fin=0):
    """paths -> the static ages each element needs (None where a path is unresolved)"""
    KSD = _ksd()
    P = paths

    def s(*ks):
        return None if any(P.get(k) is None for k in ks) else sum(P[k] for k in ks)
    ectl, vport = {}, {}
    for st in KSD.STACKS:
        for g in range(8):
            r = s(f'krq_{st}_{g}', f'krs_{st}_{g}')
            ectl[f'ectl_{st}_{KSD.ectl_frame(g)}'] = dict(group=g, krq=P.get(f'krq_{st}_{g}'), krs=P.get(f'krs_{st}_{g}'),
                                                          RESPONSE_LAT=None if r is None else KSD.LANDING_SEG + r)
        for k in range(4):
            sides = [s(f'pvvq_{st}_{k}_{g}', f'pvrs_{st}_{k}_{g}') for g in (0, 1)]
            rt = None if None in sides else KSD.VPORT_RT_SEG + max(sides)
            w = s(f'pvrq_{st}_{k}', f'O_{st}_{k}')
            vport[f'vport_{st}_{k}'] = dict(sides=sides, sides_equal=None if None in sides else sides[0] == sides[1],
                                            RT=rt, WP=P.get(f'pvrq_{st}_{k}'), O=P.get(f'O_{st}_{k}'), W=w,
                                            RL0=None if None in (w, rt) else 4 + w + rt)
    rl0 = [v['RL0'] for v in vport.values()]
    RL = None if None in rl0 else max(rl0)
    for v in vport.values():
        v['DQ'] = None if RL is None else RL - v['RL0']
    lead = [P.get('pvst_0'), P.get('pvst_1')]
    PL = None if None in lead else max(lead)
    fd = None if None in (PL, P.get('pvfst'), P.get('fin')) else 1 + (P['pvfst'] - PL) + P['fin'] + face_land_fin
    return dict(ectl=ectl, vport=vport,
                pv=dict(RL=RL, FIRST_INPUT_AGE=None if RL is None else RL + 1, W=sorted({v['W'] for v in vport.values()
                                                                                         if v['W'] is not None})),
                attn=dict(PV_LEAD_by_pair=lead, PV_LEAD=PL, pvfst=P.get('pvfst'), pvp=[P.get('pvp_0'), P.get('pvp_1')],
                          pvfin_start_align=[None if None in (P.get('pvfst'), PL, P.get(f'pvp_{p}')) else
                                             P['pvfst'] - PL - P[f'pvp_{p}'] for p in (0, 1)],
                          fin=P.get('fin'), face_land_fin=face_land_fin, F_DLY=fd),
                rule='RESPONSE_LAT = 8 + krq + krs; vport RT = 9 + pvvq_g + pvrs_g (both sides equal); RL = 4 + W + DQ + RT '
                     'with W = pvrq + O equal on all 16 ports, pair FIRST_INPUT_AGE = RL + 1; PV_LEAD = D(ks_pvst) to both '
                     'pairs; pvfin start aligned: D(ks_pvfst) - PV_LEAD == D(ks_pvp_p); F_DLY = 1 + (D(ks_pvfst) - PV_LEAD) + '
                     'D(ks_pvfin) [+ face land]')


def bound_ages(die_v=None, sidecar=None, model=None):
    """what the die binds: per instance from die_bound.v #(...) (else the die.v.params.json sidecar, else the generator
    binding recorded in the model), the pair ctl kit age, the attention tile text"""
    KSD = _ksd()
    gb = (model or {}).get('bindings') or {}
    out = dict(ectl={}, vport={}, pv_ctl_age=gb.get('pv_ctl_age'), attn=KSD.attn_tile_params(), source={})
    txt = Path(die_v).read_text(errors='replace') if die_v and Path(die_v).exists() else ''
    sc = json.loads(Path(sidecar).read_text()) if sidecar and Path(sidecar).exists() else {}
    for kind, mod, keys in (('ectl', 'qkd_ectl3_kiss_st', ('RESPONSE_LAT', 'QK_ISSUE_AGE')), ('vport', 'qkd_pv16_vport(?:_b)?', ('RT', 'DQ'))):
        for prm, inst in re.findall(mod + r'\s*#\s*\(([^;]*?)\)\s*(\w+)\s*\(', txt):
            pr = dict(re.findall(r'\.(\w+)\(\s*(\d+)\s*\)', prm))
            out[kind][inst] = {k: int(pr[k]) for k in keys if k in pr}
        for inst, pr in sc.items():
            if inst.startswith(kind + '_') and inst not in out[kind]:
                out[kind][inst] = {k: int(v) for k, v in pr.items() if k in keys}
        for inst, pr in (gb.get(kind) or {}).items():
            out[kind].setdefault(inst, {k: int(v) for k, v in pr.items() if k in keys})
        out['source'][kind] = 'die_bound.v' if txt else ('sidecar' if sc else 'generator binding')
    m = re.search(r'ot_qwen_tp8_pv_wide_ctl_tb?\s*#\s*\(([^;]*?)\)\s*pvw_\d__u_ctl\s*\(', txt)   # KV-BOOTAGE: _tb
    if m and re.search(r'\.FIRST_INPUT_AGE\((\d+)\)', m.group(1)):
        out['pv_ctl_age'] = int(re.search(r'\.FIRST_INPUT_AGE\((\d+)\)', m.group(1)).group(1))
        out['source']['pv_ctl_age'] = 'die_bound.v'
    return out


def schedule_check(sched, tile, bound=None, plan_paths_=None, table_paths_=None, boot=None):
    """FAIL ids (each with the numbers): every derived age must equal the hard tile age, and the die must bind the tile age.
    KV-BOOTAGE 10-19: with boot (the generator's boot-age image, kv_bootage.image_ages; OT_KV_BOOT_AGES=1) the V port RT / DQ,
    pair FIRST_INPUT_AGE, PV_LEAD and F_DLY are boot-programmable: they are checked as boot image == the ages derived on
    THIS schedule (+ hardware bounds, kv_bootage.check_image) instead of against hard tile values."""
    fails = []

    def F(id_, what, rows, fix):
        if rows:
            fails.append(dict(id=id_, what=f'{len(rows)} {what}', rows=rows[:64], fix=fix))
    E = sched['ectl']
    F('ECTL_RESPONSE_LAT', f'ECTL frames: 8 + krq + krs != the hardened RESPONSE_LAT {tile["ECTL_RESPONSE_LAT"]}',
      [dict(inst=i, **v) for i, v in E.items() if v['RESPONSE_LAT'] != tile['ECTL_RESPONSE_LAT']],
      'kv_k_rt_eq pads krq up to the budget; a longer frame (or a post-station stage) needs the re-harden / re-place')
    V = sched['vport']
    F('VPORT_SIDES', 'V ports: vq0/i0 and vq1/i1 round trips differ (one RT per port)',
      [dict(inst=i, sides=v['sides']) for i, v in V.items() if v['sides_equal'] is not True],
      'kv_die vport side pads (pvvq, 15 b) at generation; a post-station change needs re-equalising')
    F('VPORT_RT', f'V ports: die round trip 9 + relays != the hardened RT {tile["VPORT_RT"]}',
      [dict(inst=i, RT=v['RT'], sides=v['sides']) for i, v in V.items() if v['RT'] != tile['VPORT_RT']],
      'unpaddable (the landing seg alone is 9): boot-programmable RT at the next re-harden (lanes/KVR-DERIVE.md)')
    want_rl = None if tile.get('PV_FIRST_INPUT_AGE') is None else tile['PV_FIRST_INPUT_AGE'] - 1
    F('PV_FIRST_INPUT_AGE', f'V ports: 4 + W + DQ + RT_die + 1 != the pair ctl FIRST_INPUT_AGE {tile.get("PV_FIRST_INPUT_AGE")} '
      f'(derived {sched["pv"]["FIRST_INPUT_AGE"]}, W {sched["pv"]["W"]})',
      [dict(inst=i, W=v['W'], RT=v['RT'], RL=v['RL0']) for i, v in V.items()
       if want_rl is None or v['RL0'] is None or v['RL0'] + tile['VPORT_DQ'] != want_rl],
      'W padding cannot shorten a path: re-harden the ctl leaf (boot-programmable age) or re-place the ports')
    A = sched['attn']
    F('PV_LEAD', f'PV pairs: D(ks_pvst) {A["PV_LEAD_by_pair"]} != the attention tile PV_LEAD {tile["PV_LEAD"]}',
      [dict(pair=p, edges=v) for p, v in enumerate(A['PV_LEAD_by_pair']) if v != tile['PV_LEAD']],
      'a path longer than the tile value cannot be padded to it: boot-programmable PV_LEAD (+ equal pair starts)')
    F('PVFIN_START_ALIGN', 'pvfin start vs pair result trunks: D(ks_pvfst) - PV_LEAD - D(ks_pvp_p) != 0',
      [dict(pair=p, skew=v, pvfst=A['pvfst'], pvp=A['pvp'][p], PV_LEAD=A['PV_LEAD'])
       for p, v in enumerate(A['pvfin_start_align']) if v != 0],
      'pad the shorter side (pvfst 65 b or the 534-b pvp trunk) once PV_LEAD is met; moot while PV_LEAD fails')
    F('F_DLY', f'attention face: 1 + (D(ks_pvfst) - PV_LEAD) + D(ks_pvfin) = {A["F_DLY"]} != the tile F_DLY {tile["F_DLY"]}',
      [dict(F_DLY=A['F_DLY'], fin=A['fin'], pvfst=A['pvfst'], PV_LEAD=A['PV_LEAD'])] if A['F_DLY'] != tile['F_DLY'] else [],
      'unpaddable (path longer than the tile value): boot-programmable F_DLY at the re-harden')
    if bound is not None:
        F('ECTL_BOUND', f'ECTL instances bind RESPONSE_LAT != {tile["ECTL_RESPONSE_LAT"]} (or not bound)',
          [dict(inst=i, bound=bound['ectl'].get(i)) for i in E if (bound['ectl'].get(i) or {}).get('RESPONSE_LAT')
           != tile['ECTL_RESPONSE_LAT']], 'bind the tile value per instance (kv_die case: die.v.params.json)')
        F('VPORT_BOUND', f'V ports bind RT/DQ != the kit {tile["VPORT_RT"]}/{tile["VPORT_DQ"]}',
          [dict(inst=i, bound=bound['vport'].get(i)) for i in V
           if (bound['vport'].get(i) or {}).get('RT') != tile['VPORT_RT'] or (bound['vport'].get(i) or {}).get('DQ', 0) != tile['VPORT_DQ']],
          'bind the kit RT (never a die-derived value the kit does not implement)')
        if bound.get('pv_ctl_age') is not None and bound['pv_ctl_age'] != tile.get('PV_FIRST_INPUT_AGE'):
            F('PV_AGE_BOUND', f'pair ctl binds FIRST_INPUT_AGE {bound["pv_ctl_age"]} != kit {tile.get("PV_FIRST_INPUT_AGE")}',
              [dict(bound=bound['pv_ctl_age'], kit=tile.get('PV_FIRST_INPUT_AGE'))], 'bind the kit value')
        for k in ('PV_LEAD', 'F_DLY'):
            if bound['attn'].get(k) != tile.get(k):
                F(f'{k}_BOUND', f'attention tile text {k} {bound["attn"].get(k)} != {tile.get(k)}', [dict(bound=bound['attn'].get(k))],
                  'regenerate the tile (kv_static_die --rtl)')
    if plan_paths_ is not None and table_paths_ is not None:
        F('PATH_STALE', 'path ages the generator planned differ on the post-station netlist',
          [dict(path=k, plan=plan_paths_.get(k), netlist=v) for k, v in table_paths_.items() if plan_paths_.get(k) != v],
          'the schedule is taken from the netlist table (this record); re-pad / re-GEN the changed paths')
    if boot is not None:
        import kv_bootage as KB
        fails = [f for f in fails if f['id'] not in KB.REPLACED_CHECKS]
        fails = KB.check_image(boot, sched, tile) + fails
        if bound is not None:
            F('BOOT_AGE_HW_BOUND', 'V ports / pair ctl not bound at the boot-age successors\' hardware bounds',
              [dict(inst=i, bound=bound['vport'].get(i)) for i in V if (bound['vport'].get(i) or {}).get('RT')
               != KB.BOUNDS['VPORT_RT'] or (bound['vport'].get(i) or {}).get('DQ', 0) != KB.BOUNDS['VPORT_DQ']]
              + ([dict(pv_ctl_age=bound['pv_ctl_age'])] if bound.get('pv_ctl_age') not in (None, KB.BOUNDS['PV_FIRST_INPUT_AGE'])
                 else []), 'kv_die binds qkd_pv16_vport_b / qkd_pvw_die_tb at kv_bootage.BOUNDS (OT_KV_BOOT_AGES=1)')
    return fails


def slg_identity(die_v):
    """slg_<st>_<g> landing identity straps (kvsid_*__cfg_stack / cfg_group die-top constants) -> FAILs: each must be
    (stack index, g) -- the VMAP / K-row checks in qkd_static_kv_landing_pc compare t[8:7] / group against them -- and no
    two groups may share an identity"""
    KSD = _ksd()
    txt = Path(die_v).read_text(errors='replace')
    bits = {}
    for n, i, b in re.findall(r"assign\s+n_(kvsid_slg_\w+?)\[(\d+)\]\s*=\s*1'b([01])\s*;", txt):
        bits.setdefault(n, {})[int(i)] = int(b)
    val = {n: sum(b << i for i, b in d.items()) for n, d in bits.items()}
    # the strict-bind netlist (die_bound.v) folds the straps into the connection: .slg__cfg_stack({1'b0, 1'b1})
    for inst, body in re.findall(r'^\s*\w+\s+(?:#\s*\(.*?\)\s*)?(slg_\w+?)\s*\((.*?)\);', txt if not val else '', re.M | re.S):
        for f in ('cfg_stack', 'cfg_group'):
            mm = re.search(r'\.slg__' + f + r"\(\s*\{?([^)]*?)\}?\s*\)", body)
            if mm:
                bs = re.findall(r"1'b([01])", mm.group(1))
                if bs:
                    val[f'kvsid_{inst}__slg__{f}'] = int(''.join(bs), 2)
    rows, seen, fails = {}, {}, []
    for st in KSD.STACKS:
        for g in range(8):
            d = f'slg_{st}_{g}'
            got = tuple(next((v for n, v in val.items() if n.startswith(f'kvsid_{d}__') and n.endswith(f)), None)
                        for f in ('cfg_stack', 'cfg_group'))
            want = (KSD.STACKS.index(st), g)
            rows[d] = dict(bound=list(got), want=list(want))
            if None in got or got != want:
                fails.append(dict(inst=d, bound=list(got), want=list(want)))
            seen.setdefault(got, []).append(d)
    dup = {str(k): v for k, v in seen.items() if len(v) > 1}
    out = []
    if fails:
        out.append(dict(id='SLG_IDENTITY', what=f'{len(fails)} landing groups strap a wrong / missing (cfg_stack, cfg_group)',
                        rows=fails[:32], fix='kv_static_die strap emission (kvsid_*): tie (STACKS index, g)'))
    if dup:
        out.append(dict(id='SLG_IDENTITY_DUP', what=f'{len(dup)} identities shared by several landing groups', rows=dup,
                        fix='every group needs its own identity'))
    return out, rows


def relay_domains(die_v, model):
    """every relay instance on die.v whose clock trunk domain differs from the launching pin domain of its chain (the
    chain's generator bid -> source pin from the model).  Mixed bundles are listed, not failed (open: split by domain)."""
    import kv_pin_repair as KPR
    src = model.get('bus_src') or {}
    masters = model.get('masters') or {}
    txt = Path(die_v).read_text(errors='replace')
    bad, mixed, n = [], {}, 0
    for mst, inst, body in re.findall(r'^\s*(qkd_rly\w*|qkd_rlys_\d+)\s+(\w+)\s*\((.*?)\);', txt, re.M | re.S):
        ck = re.search(r'\.ck\(\s*n_(clk_(?:core|hbm)\w*)', body)
        a = re.search(r'\.a\(\s*(?:\{[^}]*?)?n_(\w+?)(?:\[|\s|\))', body)
        if not ck or not a:
            continue
        bid = a.group(1)
        while re.search(r'__(r\d+|pinfix\d+|beq\d+|s\d+\w*|f\d+)$', bid):
            bid = re.sub(r'__(r\d+|pinfix\d+|beq\d+|s\d+\w*|f\d+)$', '', bid)
        sp = src.get(bid)
        if not sp:
            continue
        n += 1
        dom = KPR.port_domain(masters.get(sp[0]), sp[1]) or (KPR.port_domain(masters.get(sp[2]), sp[3]) if len(sp) > 2 else None) or 'core'
        cd = KPR.trunk_domain(ck.group(1))
        if dom == 'mixed':
            mixed.setdefault(bid, set()).add(cd)
        elif cd != dom:
            bad.append(dict(relay=inst, bus=bid, clock=ck.group(1), launch=dom, src=sp[:2]))
    fails = [dict(id='RELAY_DOMAIN', what=f'{len(bad)} relays clocked off their launching pin domain', rows=bad[:64],
                  fix='kv_pin_repair.relay_trunk (pin repair + bundle / K_RT_EQ pads)')] if bad else []
    return fails, dict(relays_checked=n, mixed_domain_buses={k: sorted(v) for k, v in sorted(mixed.items())})


def run(model, doc, fwd=None, die_v=None, attn=False, case_die_v=None, sidecar=None):
    rs, fs, unresolved, src = post_stages(model, doc, fwd)
    actual = params(model, rs, fs)
    fails, info = check(model, rs, fs, unresolved, actual, die_v)
    # KVR-DERIVE 10-19: the attention-path static schedule on THIS table vs the tile ages and the die's bindings
    tp, probs = table_paths(doc, fwd)
    KSD = _ksd()
    tile = model.get('tile_ages') or KSD.tile_ages()
    flf = ((model.get('face_land') or {}).get('fin_edges') or 0)
    sched = schedule(tp, face_land_fin=flf)
    actual['static_schedule'] = dict(paths=tp, schedule=sched, tile_ages=tile)
    for p_ in probs:
        fails.append(dict(id=p_['id'], what=json.dumps(p_)))
    bound = bound_ages(die_v, sidecar or (str(case_die_v) + '.params.json' if case_die_v else None), model)
    actual['static_schedule']['bound'] = bound
    fails += schedule_check(sched, tile, bound, (model.get('static_schedule') or {}).get('paths'), tp,
                            boot=model.get('boot_ages'))     # KV-BOOTAGE: the GEN's boot image vs THIS table
    dv = case_die_v or die_v
    if dv and Path(dv).exists():
        f_, rows = slg_identity(dv)
        fails += f_
        actual['slg_identity'] = rows
        if model.get('bus_src'):
            f_, inf = relay_domains(dv, model)
            fails += f_
            info.append(dict(id='RELAY_DOMAIN', **inf))
    if attn:
        ac = attn_calendar_check(actual, rs)
        actual['attention_checks'] = ac
        for f in ac['fails']:
            fails.append(dict(id=f'ATTN_CALENDAR {f["id"]}', what=f'{f["contexts"]} of {ac["contexts"]} contexts: '
                              + json.dumps(f['examples'][:3]),
                              fix={'PVFIN_PAIR_SKEW': 'RTL: the pair skew 0/16/32 is set by the pair issue count (w16_nq); '
                                   'qkd_pv_fin_s SKEW 1 cannot absorb it -- a 32-beat pair-1 deskew line in pvfin or a '
                                   'pair end floor (decision, lanes/HKV-DIE.md); no compiled field moves it',
                                   'HUB_FR_EXPORT': 'compiler: the minimal R / PV_START use max(RZ_MARGIN, 3 - FR_OFS) with '
                                   'the BOUND FR_OFS (OT_KV_AHUB_OFS); re-GEN with the table value',
                                   'CALENDAR_UNMEETABLE': 'the link RESULT slot is too early for this context',
                                   'PVFIN_CAL_RANGE': 'calendar field outside qkd_pv_fin_s range'}.get(f['id'])))
    return dict(schema=SCHEMA, status='FAIL' if fails else 'PASS', table_digest=doc.get('digest'),
                table_plan=doc.get('plan', {}).get('id'), params=actual, fails=fails, info=info,
                dependent_stages={k: rs.get(k, fs.get(k)) for k in _deps(model)},
                rule='parameters recomputed by kv_static_params.py from the die netlist table; never from the plan record')


def _deps(model):
    """the bids the parameters read (for the record)"""
    keys = [k for k in model['relay_stages'] if re.match(r'^(ks_ah|ks_pvfst|ap_|am_|pve_|pvh_|ks_af|af_|hf$)', k)]
    sq = model.get('seq_kvn') or {}
    keys += [sq[k] for k in ('rx', 'prg', 'kw') if sq.get(k)]
    keys += [k for k in model.get('fork_stages', {}) if re.match(r'^(pvh_|ks_afv_|af_|hf__)', k)]
    return sorted(set(keys))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--model', type=Path, required=True, help='CASE/static_model.json (kv_die.py case)')
    ap.add_argument('--table', type=Path, required=True, help='die netlist relay table (netlist_relay_stages.py)')
    ap.add_argument('--fwd-lanes', type=Path)
    ap.add_argument('--die-v', type=Path)
    ap.add_argument('--case-die-v', type=Path, help='the case die.v (kvsid straps, relay clocks, die.v.params.json sidecar)')
    ap.add_argument('--no-attn', action='store_true', help='skip the ATTN_CALENDAR sweep (unit use only)')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    import die_relay_stages as DRS
    model = json.loads(a.model.read_text())
    if model.get('schema') != SCHEMA_MODEL:
        raise SystemExit(f'kv_static_params: {a.model} is not {SCHEMA_MODEL}')
    rec = run(model, DRS.load(a.table), json.loads(a.fwd_lanes.read_text()) if a.fwd_lanes else None, a.die_v,
              attn=not a.no_attn, case_die_v=a.case_die_v)
    a.out.write_text(json.dumps(rec, indent=1, default=str) + '\n')
    print(f"KV_STATIC_PARAMS {rec['status']}: " + '; '.join(f"{f['id']}: {f['what'][:200]}" for f in rec['fails'])
          + (f" | AP_OFS {rec['params']['ahub_ages']['AP_OFS']} FR_OFS {rec['params']['ahub_ages']['FR_OFS']}"
             if rec['params'].get('ahub_ages') else '') + f" -> {a.out}")
    return 1 if rec['fails'] else 0


if __name__ == '__main__':
    sys.exit(main())
