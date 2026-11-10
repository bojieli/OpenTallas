#!/usr/bin/env python3
"""S81-PLAN-1 (COORD 11-09 02:33, ONE FINAL SWITCH PER DIE): the compiler map of a relay/type-safe event's PIN CYCLES.

A relay event (tools/die_plan/ts_relay_event.py) adds register stages to plan lanes; the RTL side is proven by
ts_relay_miter.py (per lane: new == old delayed by exactly the declared k).  What is left is the compiler: every
quantity the S81 compiler reads for a lane must move by exactly that lane's pin_cycle_delta, or the compiler schedules
against the old depth.  This tool is the golden-model check of that, lane by lane, for every compiler input that
carries a lane depth:

  golden  G[lane] = base plan latency.lanes[lane].cycles + event.pin_cycle_deltas.get(lane, 0)   (independent of the
          event plan: only the base plan and the event's declaration)
  C0 plan    event plan latency.lanes[lane].cycles == G                      (gen.py latency regen of the event plan)
  C1 table   compiler latency table lanes[lane].cycles == G, plan_digest == event plan's digest
             (readers: tokfunc/compose_tok_ds.lane_table, layer_prog/norm_q_plan)
  C2 bind    bind_latency.json buses[lane].bound_stages == plan_cycles == G  (readers: layer_prog/bound_data.rebind_links
             -> dv_layer_compile --bound-data; layer_prog/bound_die.BoundDie.route reads the same bind per bit)
  C3 leaf    leaf offsets (layer_prog/leaf_transport.report_from_offsets -> lower_vpx LO / entry_norm / lower_vs):
             dn[i] == G[dn_<s>_L<i>] + local_command_edges, up[i] == G[up_<s>_L<i>] + local_partial_edges (local
             edges from an emitted_leaf_routes report, which the event does not change)
  C4 frame   frame_int (fi_*) lanes: the as-built frame schedule (frame_schedule_asb.py -> lower_xs.source_frame_schedule)
             times every r_i -> r_j band crossing from its traced RTL; per (master, crossing) the event lanes must be ONE
             value (one schedule per master) and the schedule's traced value must equal it, else the frame compiler
             does not schedule around the stations (NOT_SCHEDULED, a FAIL)
  C5 terms   compose_tok_ds._lane_terms on the table == the same terms on G (perf model terms: field_round,
             leaf_hub_rt, svc_to_hub, link_end, ring_link)

Every lane carrying a delta is also listed with its class and its compiler consumer path (CLASS_MAP) so the map is
complete: a class without a row FAILS (an event lane nothing would schedule).

  pin_cycle_consumers.py --base-plan B.json --plan P.json --event E.json [--table T.json] [--bind DIR]
        [--leaf-offsets O.json --leaf-routes R.json] [--frame-check M=CHECK.json ...] [--repo ROOT] --out OUT.json
  exit 0 when every requested check passes, 1 otherwise.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

# class regex -> (compiler consumer path, how it reads the depth)
CLASS_MAP = [
    (r'dn_s_\d[NS]_L\d', 'layer_prog/leaf_transport (TS4 leaf offsets) -> lower_vpx LO, entry_norm, lower_vs; '
                         'compose leaf_hub_rt', 'C3 leaf offsets + C1 table'),
    (r'up_s_\d[NS]_L\d', 'layer_prog/leaf_transport (TS4 leaf offsets) -> lower_vpx LO, entry_norm, lower_vs; '
                         'compose leaf_hub_rt', 'C3 leaf offsets + C1 table'),
    (r'fi_[EW]\d_p\d_r\dr\d', 'frame_schedule_asb.py (traced as-built band frame) -> lower_xs.source_frame_schedule; '
                              'compose field_round', 'C4 frame schedule + C1 table'),
    (r'rt_[EW]\d_(in|out)_\d', 'dv_layer_compile --bound-data (bound_data.rebind_links, frame return links); compose '
                               'field_round', 'C2 bind + C1 table'),
    (r'x_[EW]\d_(in|out)', 'dv_layer_compile --bound-data (x chain head links); compose field_round',
     'C2 bind + C1 table'),
    (r'xo_[EW]\d_(in|out)_[ab]', 'frame phase programme (ot_s81_cfg7_seq x forward; no compiler module names these '
                                 'lanes); compose field_round', 'C2 bind + C1 table'),
    (r'coll__.*', 'link end LP<->link (xdie co-sim lane legs); compose link_end (bound only); rebind_links',
     'C2 bind + C1 table'),
    (r'lpc__.*', 'slice hub C -> LP control (no tools/s81_dv reader; rebind_links / BoundDie.route)', 'C2 bind'),
    (r'attn__s_\d[NS]_C__svc_\d+', 'hub C -> svc attention (lower_svc via BoundDie.route / rebind_links)', 'C2 bind'),
    (r'(unit|flt)__eng__svc_\d+', 'Engram unit / fault to svc (lower_eng LAT via rebind_links; flt is a sticky '
                                  'fault level)', 'C2 bind'),
    (r'xtier__.*', 'layer_prog/norm_q_plan (V route over xtier lanes from the latency table)', 'C1 table'),
    # S81-PLAN-1 11-10: the static control lanes (TYPE-SAFE-5 06:25: 30 lanes with no row); all read through
    # layer_prog/bound_ctl_lanes.load (bound_stages == plan_cycles, fail closed) from the dv_layer_compile --bound-data bind
    (r'(tl|ca|cb)__(bk_sel|s_0N_LP)__(bk_sel|s_0N_LP)', 'bound_ctl_lanes.idxnet tree_legs -> lower_bk job_rank_tree_rd '
                                                        'leg (child arrival)', 'C2 bind'),
    (r'(qc__iqf__s_0N_LP|ql__s_0N_LP__iqf)', 'bound_ctl_lanes.query_offset -> lower_bk job_rank_tree_rd e0 (query '
                                             'fan-out per depth)', 'C2 bind'),
    (r'tp__(bk_sel|s_\d[NS]_LP)__(bk_sel|s_\d[NS]_LP)', 'bound_ctl_lanes.tp4_on_die -> lower_bk topk_final t0 (TP4 '
                                                       'all-gather on-die hops)', 'C2 bind'),
    (r'idx__(svc_\d+__bk_sel|s_\d[NS]_C__iqf)', 'bound_ctl_lanes.idxnet idx_chain (score-chain / iq arrival; the IDX_S '
                                              'job is not lowered: lower_bk GAPS producer)', 'C2 bind'),
    (r'(unit__seqhost__s_\d[NS]_LP|ctrl__s_\d[NS]_LP__seqhost|unit__s_\d[NS]_LP__seqhost)',
     'MU HWIN: bound_ctl_lanes.hwin_bound_transport -> native_hwin_calendar.check_consumer_book(bound_transport); '
     'dv_layer_compile --bound-data re-ages mu_*/rt_0N/ht_7N/hf_7N', 'C2 bind'),
    (r'(unit__seqhost__s_\d[NS]_C|ctrl__s_\d[NS]_C__seqhost|unit__seqhost__(gunit|eng))',
     'dv_layer_compile --bound-data (rebind_links hbc_*, cw_seqhost, eks_7N; a BLOCKED link raises on read)', 'C2 bind'),
    (r'unit__(seqhost__svc_\d+|svc_\d+__seqhost)', 'lower_svc _ages j_w/j_e/jd_w/jd_e from the re-aged jw_*/jd_* links '
                                                 '(bound_ctl_lanes.svc_cross_check in dv_layer_compile)', 'C2 bind'),
    (r'attn__svc_\d+__s_\d[NS]_C', 'svc -> hub C pv (pv_v valid-qualified at the hub; compose svc_to_hub)', 'C2 bind'),
    (r'flt__gunit__s_\d[NS]_C', 'sticky fault level (no date)', 'C2 bind'),
    (r'vid_(seqhost__svc_\d+|svc_\d+__seqhost)', 'fault relay / alive level (no date)', 'C2 bind'),
]


def lane_class(lid):
    for rx, path, how in CLASS_MAP:
        if re.fullmatch(rx, lid):
            return rx, path, how
    return None, None, None


def plan_digest(raw):
    r = json.loads(json.dumps(raw))
    r.pop('latency', None)
    return hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()[:16]


def golden(base, event):
    pcd = event['pin_cycle_deltas']
    bl = base['latency']['lanes']
    unknown = sorted(set(pcd) - set(bl))
    if unknown:
        raise ValueError(f'event declares pin cycles on lanes the base plan does not have: {unknown[:5]}')
    return {k: v['cycles'] + pcd.get(k, 0) for k, v in bl.items()}, pcd


def cmp_lanes(name, G, got, lanes):
    bad = [dict(lane=k, golden=G[k], got=got.get(k)) for k in lanes if got.get(k) != G[k]]
    return dict(check=name, lanes=len(lanes), mismatches=len(bad), first=bad[:8], verdict='FAIL' if bad else 'PASS')


def check_plan(G, plan):
    pl = plan['latency']['lanes']
    r = cmp_lanes('C0 plan latency', G, {k: v['cycles'] for k, v in pl.items()}, sorted(G))
    extra = sorted(set(pl) - set(G))
    if extra:
        r.update(verdict='FAIL', extra_lanes=extra[:8])
    return r


def check_table(G, table, plan):
    r = cmp_lanes('C1 latency table', G, {k: v['cycles'] - v.get('r8_pad', 0) for k, v in table['lanes'].items()},
                  sorted(G))
    dig = plan_digest(plan)
    r['plan_digest'] = dict(table=table.get('plan_digest'), plan=dig)
    if table.get('plan_digest') != dig:
        r['verdict'] = 'FAIL'
    return r


def check_bind(G, bind_latency, pcd):
    buses = {}
    for b in bind_latency['buses']:
        if b.get('lane') is not None:
            if b['lane'] in buses:
                raise ValueError('bind repeats a lane identity: ' + b['lane'])
            buses[b['lane']] = b
    bound = {k: b['bound_stages'] for k, b in buses.items()}
    planc = {k: b['plan_cycles'] for k, b in buses.items()}
    r = cmp_lanes('C2 bind bound_stages', G, bound, sorted(G))
    rp = cmp_lanes('C2 bind plan_cycles', G, planc, sorted(G))
    r['plan_cycles'] = dict(mismatches=rp['mismatches'], first=rp['first'])
    r['event_lanes_checked'] = sum(1 for k in pcd if k in bound)
    if rp['verdict'] == 'FAIL':
        r['verdict'] = 'FAIL'
    return r


def check_leaf(G, offsets, routes):
    loc = {(x['slice'], x['leaf']): x for x in routes['leaves']}
    bad, n = [], 0
    for s, v in sorted(offsets['slices'].items()):
        sl = s[2:]
        for kind, lk in (('dn', 'local_command_edges'), ('up', 'local_partial_edges')):
            for i, got in enumerate(v[kind]):
                lane = f'{kind}_{sl}_L{i}'
                want = G[lane] + loc[(s, i)][lk]
                n += 1
                if got != want:
                    bad.append(dict(lane=lane, slice=s, leaf=i, offsets=got, golden=want))
    return dict(check='C3 leaf offsets', entries=n, mismatches=len(bad), first=bad[:8], plan=offsets.get('plan'),
                verdict='FAIL' if bad else 'PASS')


def fi_groups(plan, G, pcd):
    """{(master, 'rI->rJ'): {cycles}} from the plan's fi lanes, golden cycles, plus which carry event deltas"""
    pt = {p['name']: p['type'] for p in plan['partitions']}
    ports = {p['id']: p for p in plan['ports']} if isinstance(plan['ports'], list) else plan['ports']
    g = collections.defaultdict(lambda: dict(golden=set(), delta=set(), lanes=0))
    for ln in plan['lanes']:
        if not ln['id'].startswith('fi_'):
            continue
        st = pt[ports[ln['ports'][0]]['src']['part']]
        dt = pt[ports[ln['ports'][-1]]['dst']['part']]
        ms, md = re.match(r'(col_h\d+)_(r\d)', st), re.match(r'(col_h\d+)_(r\d)', dt)
        if not (ms and md and ms.group(1) == md.group(1)):
            raise ValueError(f'fi lane {ln["id"]} does not join two bands of one master: {st} -> {dt}')
        e = g[(ms.group(1), f'{ms.group(2)}->{md.group(2)}')]
        e['golden'].add(G[ln['id']])
        e['delta'].add(pcd.get(ln['id'], 0))
        e['lanes'] += 1
    return g


def check_frame(plan, G, pcd, frame_checks):
    """frame_checks: {master_var: check json of frame_schedule_asb.py}; its plan_consistency rows carry the traced
    rtl_asbuilt value of every 'frame_int rI->rJ' crossing"""
    groups = fi_groups(plan, G, pcd)
    rows, fails = [], []
    for (m, x), e in sorted(groups.items()):
        uniform = len(e['golden']) == 1
        row = dict(master=m, crossing=x, lanes=e['lanes'], golden=sorted(e['golden']), deltas=sorted(e['delta']),
                   uniform_per_master=uniform, schedules={})
        if not uniform:
            fails.append(f'{m} {x}: event depths differ between frame instances {sorted(e["golden"])} '
                         '(one schedule per master cannot carry them)')
        for mv, chk in sorted(frame_checks.items()):
            if not mv.startswith(m + '_'):
                continue
            traced = [r['rtl_asbuilt'] for r in chk.get('plan_consistency', [])
                      if r['link'].startswith(f'frame_int {x} ')]
            ok = uniform and traced == [sorted(e['golden'])]
            row['schedules'][mv] = dict(traced=traced, verdict='PASS' if ok else 'NOT_SCHEDULED')
            if not ok:
                fails.append(f'{mv} frame_int {x}: schedule traced {traced} vs bound {sorted(e["golden"])}')
        rows.append(row)
    return dict(check='C4 frame schedule (fi)', groups=rows, fails=fails, verdict='FAIL' if fails else 'PASS')


def check_terms(G, table, repo):
    spec = importlib.util.spec_from_file_location('ctd_pcc', Path(repo) / 'tools/s81_dv/tokfunc/compose_tok_ds.py')
    M = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M)

    def lanes_of(tab):
        def f(p):
            rx = re.compile(p)
            return {k: v for k, v in tab.items() if rx.fullmatch(k)}
        return f
    T = {k: v['cycles'] for k, v in table['lanes'].items()}
    a, b = M._lane_terms(lanes_of(T)), M._lane_terms(lanes_of(G))
    bad = [dict(term=k, table=a[k]['cycles'], golden=b[k]['cycles']) for k in a if a[k]['cycles'] != b[k]['cycles']]
    return dict(check='C5 compose lane terms', terms={k: v['cycles'] for k, v in b.items()}, mismatches=bad,
                verdict='FAIL' if bad else 'PASS')


def class_map(pcd):
    by = collections.defaultdict(lambda: dict(lanes=0, pin_cycles=0, deltas=set()))
    unmapped = []
    for k, d in pcd.items():
        rx, path, how = lane_class(k)
        if rx is None:
            unmapped.append(k)
            continue
        e = by[rx]
        e.update(consumer=path, checked_by=how)
        e['lanes'] += 1
        e['pin_cycles'] += d
        e['deltas'].add(d)
    rows = [dict(cls=k, **{**v, 'deltas': sorted(v['deltas'])}) for k, v in sorted(by.items())]
    return dict(check='class map', classes=rows, unmapped=unmapped, verdict='FAIL' if unmapped else 'PASS')


def run(a):
    base, plan, event = (json.loads(Path(p).read_text()) for p in (a.base_plan, a.plan, a.event))
    G, pcd = golden(base, event)
    out = dict(schema='opentallas.s81.pin_cycle_consumers.v1', tool='tools/s81_dv/pin_cycle_consumers.py',
               base_plan=a.base_plan, plan=a.plan, event=a.event,
               plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),
               event_lanes=len(pcd), event_pin_cycles=sum(pcd.values()), checks=[])
    out['checks'].append(class_map(pcd))
    out['checks'].append(check_plan(G, plan))
    table = None
    if a.table:
        table = json.loads(Path(a.table).read_text())
        out['checks'].append(check_table(G, table, plan))
    if a.bind:
        out['checks'].append(check_bind(G, json.loads((Path(a.bind) / 'bind_latency.json').read_text()), pcd))
    if a.leaf_offsets:
        out['checks'].append(check_leaf(G, json.loads(Path(a.leaf_offsets).read_text()),
                                        json.loads(Path(a.leaf_routes).read_text())))
    if a.frame_check:
        fc = {kv.split('=', 1)[0]: json.loads(Path(kv.split('=', 1)[1]).read_text()) for kv in a.frame_check}
        out['checks'].append(check_frame(plan, G, pcd, fc))
    if a.repo and table is not None:
        out['checks'].append(check_terms(G, table, a.repo))
    out['verdict'] = 'FAIL' if any(c['verdict'] != 'PASS' for c in out['checks']) else 'PASS'
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base-plan', required=True)
    ap.add_argument('--plan', required=True)
    ap.add_argument('--event', required=True)
    ap.add_argument('--table')
    ap.add_argument('--bind')
    ap.add_argument('--leaf-offsets')
    ap.add_argument('--leaf-routes')
    ap.add_argument('--frame-check', action='append', default=[], metavar='MASTER_VAR=CHECK.json')
    ap.add_argument('--repo', help='source root for compose_tok_ds (C5)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    if bool(a.leaf_offsets) != bool(a.leaf_routes):
        ap.error('--leaf-offsets needs --leaf-routes (local edges)')
    out = run(a)
    Path(a.out).write_text(json.dumps(out, indent=1, default=sorted) + '\n')
    for c in out['checks']:
        print(c['check'], c['verdict'], {k: c[k] for k in ('mismatches', 'lanes', 'entries') if k in c})
    print('PIN_CYCLE_CONSUMERS', out['verdict'], out['event_lanes'], 'lanes', out['event_pin_cycles'], 'pin cycles')
    return 0 if out['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
