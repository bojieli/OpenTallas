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
    return dict(schema=SCHEMA_MODEL, relay_stages=rs, fork_stages=fs, forks=forks, seq_kvn=seq, hub=hub, plan=plan, dsts=dsts,
                face_land=dict(enabled=KSD.FACE_LAND, tiles=KSD.FACE_LAND_TILES),
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
        for inst, t in fl['tiles'].items():
            mm = re.search(r'^\s*(\w+)\s+(?:#\s*\(.*?\)\s*)?' + re.escape(inst) + r'\s*\(', txt, re.M | re.S)
            if not mm:
                continue
            landed = mm.group(1).endswith('_fl')
            if landed != bool(fl.get('enabled')):
                fails.append(dict(id='FACE_LAND_BINDING', what=f'{inst} binds {mm.group(1)} but OT_KV_FACE_LAND='
                                  f'{int(bool(fl.get("enabled")))}: the compiler ages / startup calendar disagree with the tile',
                                  fix='bind the _fl view (CLOSED only) together with OT_KV_FACE_LAND=1, or neither'))
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


def run(model, doc, fwd=None, die_v=None):
    rs, fs, unresolved, src = post_stages(model, doc, fwd)
    actual = params(model, rs, fs)
    fails, info = check(model, rs, fs, unresolved, actual, die_v)
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
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    import die_relay_stages as DRS
    model = json.loads(a.model.read_text())
    if model.get('schema') != SCHEMA_MODEL:
        raise SystemExit(f'kv_static_params: {a.model} is not {SCHEMA_MODEL}')
    rec = run(model, DRS.load(a.table), json.loads(a.fwd_lanes.read_text()) if a.fwd_lanes else None, a.die_v)
    a.out.write_text(json.dumps(rec, indent=1, default=str) + '\n')
    print(f"KV_STATIC_PARAMS {rec['status']}: " + '; '.join(f"{f['id']}: {f['what'][:200]}" for f in rec['fails'])
          + (f" | AP_OFS {rec['params']['ahub_ages']['AP_OFS']} FR_OFS {rec['params']['ahub_ages']['FR_OFS']}"
             if rec['params'].get('ahub_ages') else '') + f" -> {a.out}")
    return 1 if rec['fails'] else 0


if __name__ == '__main__':
    sys.exit(main())
