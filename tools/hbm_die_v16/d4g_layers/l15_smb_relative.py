#!/usr/bin/env python3
"""Migrate CP/SVG/XC together to the resident relative-service contract.

Apply before relay planning. Reapplication to a fully migrated final contract is
idempotent and verifies actual bit paths. A legacy post-relay contract is rejected:
its packed narrow lanes must be regenerated, never widened at endpoints alone.
Missing router IDs are an explicit release gap for l17, never tied or made oracle inputs.
"""
import argparse
import collections
import copy
import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import die_port_bind as DPB

REGION = 'd4g_l15_smb_relative'
CP = 'ot_static_run_target'
SVG = 'ot_hbm_svc_sm_group_rel_id'
XC = 'ot_hbm_svc_sm_xcal_rel_t'
HOST = 'rtl/hbm_accel/host_static_20261015/'
SVC = 'rtl/hbm_accel/loader/service_native/'
SOURCES = {CP: HOST + CP + '.sv', SVG: SVC + SVG + '.sv', XC: SVC + XC + '.sv'}
PARAMS = {CP: dict(AWA=11, AWB=8, RBW=8, RCW=9, NA=2, NF=1, TGT_PIN=1, RSYNC=1),
          SVG: dict(LBANKS=4, NID=6, IDW=9, PAW=11, PREL=1, DD=256),
          XC: dict(PAW=11, PREL=1, DD=256)}
OLD = {CP: 'ot_static_cmd_target', SVG: 'ot_hbm_svc_sm_group_id', XC: 'ot_hbm_svc_sm_xcal_t'}
DEPS = [SVC + n + '.sv' for n in ['ot_hbm_svc_sm_feed_programmed_rel_id', 'ot_hbm_svc_sm4pc_cdc_rel_id',
        'ot_hbm_svc_prefetch_overlap_owner_rel_id', 'ot_hbm_svc_sm_issuer_rel', 'ot_hbm_svc_sm_xcal_rel']]
DEPS += ['rtl/hbm_accel/sm/static/ot_smh_calendar_static_x.sv', HOST + CP + '.sv']
LINKS = [('a_addr', 'program_cfg_addr', 10, 11), ('b_addr', 'desc_addr', 7, 8),
         ('run_base', 'run_base', 7, 8), ('run_count', 'run_count', 8, 9)]
IDS = {'ids_v': 1, 'ids_layer': 8, 'ids': 54}


def load(path):
    with gzip.open(path, 'rt') if str(path).endswith('.gz') else open(path) as f:
        return json.load(f)


def write(path, obj):
    raw = json.dumps(obj, separators=(',', ':'), sort_keys=False) + '\n'
    if str(path).endswith('.gz'):
        with gzip.open(path, 'wt') as f:
            f.write(raw)
    else:
        Path(path).write_text(raw)


def rtl_ports(root=ROOT):
    idx, amb = DPB.rtl_index([], [str(root / p) for p in SOURCES.values()], {}, [])
    if amb:
        raise ValueError(f'ambiguous relative masters: {amb}')
    out = {}
    for name, params in PARAMS.items():
        m = idx[name]
        env = m.env(params)
        out[name] = {p: dict(direction=m.ports[p][0], bits=m.width(p, env)) for p in m.order}
        if any(v['bits'] is None for v in out[name].values()):
            raise ValueError(f'{name}: unevaluated port width')
    return out


def edge(src, sink, name):
    assert src[3] - src[2] == sink[3] - sink[2]
    return dict(name=name, bits=src[3] - src[2], source=src, sink=sink, clock='stream',
                ready_or_credit=False, allowed_exception=None,
                basis='L15 resident relative service; real collar argument, no data cadence change', region=REGION)


def bit_paths(c, start, target):
    """Follow only actual contract edges and known transparent register lanes."""
    bysrc = collections.defaultdict(list)
    for e in c['edges']:
        bysrc[tuple(e['source'][:2])].append(e)
    todo = [(start, [])]
    seen = set()
    while todo:
        ep, via = todo.pop()
        key = tuple(ep)
        if key in seen:
            continue
        seen.add(key)
        if ep == target:
            return via
        for e in bysrc[tuple(ep[:2])]:
            s, t = e['source'], e['sink']
            if s[2] <= ep[2] < s[3]:
                nxt = [t[0], t[1], t[2] + ep[2] - s[2]]
                if nxt == target:
                    return via + [e['name']]
                inst = c['instances'].get(t[0], {})
                master = inst.get('master', '')
                ports = inst.get('ports', {})
                if (re.match(r'^hbfd_(rly_|land|pad)', master) and t[1] == 'd'
                        and 'q' in ports and ports['q']['bits'] > nxt[2]):
                    todo.append(([t[0], 'q', nxt[2]], via + [e['name'], t[0]]))
    return None


def apply(contract, root=ROOT):
    c = copy.deepcopy(contract)
    ports = rtl_ports(root)
    I = c['instances']
    names = sorted(n[7:] for n in I if re.fullmatch(r'cp_svg_(SW|NW)[0-7]', n))
    if len(names) != 16:
        raise ValueError(f'expected16 CP/SVG/XC triplets, found{len(names)}')
    states = []
    for suffix in names:
        for prefix, master in [('cp_svg_', CP), ('svg_', SVG), ('xc_', XC)]:
            n = prefix + suffix
            if n not in I:
                raise ValueError(f'missing triplet member {n}')
            v = I[n]
            if v['master'] == master:
                allowed_extra = ({'ID_COHORT'} if master == SVG and re.search(r'\bID_COHORT\s*=', (root / SOURCES[SVG]).read_text()) else set())
                actual_params = v.get('params', {})
                params_ok = (all(actual_params.get(k) == val for k, val in PARAMS[master].items())
                    and set(actual_params) <= set(PARAMS[master]) | allowed_extra
                    and actual_params.get('ID_COHORT', 0) in (0, 1))
                if not params_ok or v['ports'] != ports[master]:
                    raise ValueError(f'PARTIAL_MIGRATION {n}: relative master with stale parameters/ports')
                states.append('new')
            elif v['master'] == OLD[master]:
                if master in (CP, SVG):
                    expect = dict(a_addr=10, b_addr=7, run_base=7, run_count=8) if master == CP else dict(program_cfg_addr=10, desc_addr=7, run_base=7, run_count=8)
                    if any(v['ports'].get(k, {}).get('bits') != width for k, width in expect.items()):
                        raise ValueError(f'PARTIAL_MIGRATION {n}: legacy master with partially widened ports')
                states.append('old')
            else:
                raise ValueError(f'{n}: unexpected master {v["master"]}')
    if len(set(states)) != 1:
        raise ValueError('PARTIAL_MIGRATION: CP/SVG/XC must change together for every SM')
    fresh = states[0] == 'old'
    rep = dict(layer='l15_smb_relative', migrated=fresh, triplets=names, n=16,
               program_words=2048, descriptor_rows=256, added_data_edges=0, reset_settle_added_edges=2,
               new_links=[], unresolved_ids=[], bit_paths_verified=0, physical_adoption='OPEN_SVG_XC_HARDENING')
    if fresh:
        # Validate direct pre-relay links before making any mutation.
        changes = []
        for suffix in names:
            cp, svg = 'cp_svg_' + suffix, 'svg_' + suffix
            for sp, tp, oldw, neww in LINKS:
                match = [e for e in c['edges'] if e['source'] == [cp, sp, 0, oldw]
                         and e['sink'] == [svg, tp, 0, oldw] and e['bits'] == oldw]
                if len(match) != 1:
                    raise ValueError(f'STALE_NARROW_RELAY_CHAIN {cp}.{sp}->{svg}.{tp}: '
                                     'apply L15 before regenerating real relay/pin lanes')
                changes.append((match[0], neww))
        for e, width in changes:
            e['bits'] = width
            e['source'][3] = width
            e['sink'][3] = width
            e['basis'] = 'L15 coherent relative CP/SVG width; PRE-relay, lanes must be planned from this width'
        for suffix in names:
            cp, svg = 'cp_svg_' + suffix, 'svg_' + suffix
            for prefix, master in [('cp_svg_', CP), ('svg_', SVG), ('xc_', XC)]:
                v = I[prefix + suffix]
                v.update(master=master, source=SOURCES[master], params=copy.deepcopy(PARAMS[master]),
                         ports=copy.deepcopy(ports[master]), rtl_deps=[] if master == CP else list(DEPS))
                v['note'] = (v.get('note') or '') + (' | L15 resident relative service:2048programme/256descriptors; '
                        'same cfg/run +2edges; CP reset settle+2; router IDs require actual l17 producer')
            I[cp]['slot'] = cp
            e = edge([cp, 'run_arg', 0, 8], [svg, 'run_layer', 0, 8], 'l15_' + cp + '_run_layer')
            c['edges'].append(e)
            rep['new_links'].append(e['name'])
        for s in c.get('straps', []):
            if s.get('inst') in I:
                s['master'] = I[s['inst']]['master']
        c['open_outputs'] = [x for x in c.get('open_outputs', [])
                             if not (isinstance(x, list) and len(x) >= 2 and x[0].startswith('cp_svg_')
                                     and x[1] in {'cmd_v', 'cmd', 'cycle'})]
        c['masters'] = dict(sorted(collections.Counter(v['master'] for v in I.values()).items()))
    for suffix in names:
        cp, svg = 'cp_svg_' + suffix, 'svg_' + suffix
        if I[cp].get('slot') != cp:
            raise ValueError(f'{cp}: relative CP still aliases another instance slot')
        for sp, tp, _, width in LINKS + [('run_arg', 'run_layer', 0, 8), ('run_v', 'run_v', 0, 1)]:
            for bit in range(width):
                if bit_paths(c, [cp, sp, bit], [svg, tp, bit]) is None:
                    raise ValueError(f'FINAL_LANE_WIDTH_MISMATCH {cp}.{sp}[{bit}]->{svg}.{tp}[{bit}]')
                rep['bit_paths_verified'] += 1
        for p, width in {k: v['bits'] for k, v in I[svg]['ports'].items() if k.startswith('ids')}.items():
            driven = set()
            for e in c['edges']:
                if e['sink'][:2] == [svg, p]:
                    driven.update(range(e['sink'][2], e['sink'][3]))
            if driven != set(range(width)):
                rep['unresolved_ids'].append(dict(instance=svg, port=p, width=width,
                    missing_bits=sorted(set(range(width)) - driven), owner='HBM-ROUTER-IDS l17'))
    gapid = 'G-SMB-ROUTER-IDS'
    c['gaps'] = [x for x in c.get('gaps', []) if x.get('id') != gapid]
    if rep['unresolved_ids']:
        c['gaps'].append(dict(id=gapid, owner='HBM-ROUTER-IDS l17',
            missing_rtl='actual MoE TOPK VM result collector/broadcast, layer/cohort freshness; no host/oracle/ties',
            affects=[[x['instance'], x['port'], x['width']] for x in rep['unresolved_ids']]))
    rep['release_ready'] = not rep['unresolved_ids']
    rep['router_status'] = 'BLOCKED_IDS_PRODUCER' if rep['unresolved_ids'] else 'CONNECTED_NEEDS_LIFETIME_BENCH'
    return c, rep


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    ap.add_argument('--root', type=Path, default=ROOT); ap.add_argument('--require-ids', action='store_true')
    a = ap.parse_args()
    try:
        c, rep = apply(load(a.inp), a.root)
    except ValueError as exc:
        Path(a.report).write_text(json.dumps(dict(layer='l15_smb_relative', problems=[str(exc)]), indent=1) + '\n')
        print('L15_FAIL', exc); return 1
    write(a.out, c)
    Path(a.report).write_text(json.dumps(rep, indent=1) + '\n')
    print('L15_OK', 'migrated' if rep['migrated'] else 'idempotent', '16triplets', rep['router_status'])
    return 2 if a.require_ids and rep['unresolved_ids'] else 0


if __name__ == '__main__':
    sys.exit(main())
