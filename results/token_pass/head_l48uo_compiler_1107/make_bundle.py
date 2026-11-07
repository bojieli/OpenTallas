#!/usr/bin/env python3
"""Build the HEAD l48uo compiler source witness bundle from a checkout of main.

Inputs are the plan_of_record/l48uo files only: l48uo plan, sidecar 90d006, the
START stage tree and its SV. root88_report.json and boot88_account.json are
recomputed here, with the same arithmetic as the 10-30 accountant
(results/codex_head_1030/legal88_source/account_boot88_v2.py), but read-only:
nothing in the sidecar is rewritten. Source witness only, as in 10-30: frozen
false, physical admission false, no START/HOST/PMA/mission date.

  make_bundle.py REPO OUT
"""
import gzip
import hashlib
import json
import sys
from pathlib import Path

N4 = {'coll_WN1_u__1': 4, 'coll_WN2_u__3': 4, 'coll_WN1_d__0': 2, 'coll_WN2_d__0': 2}


def account(raw, side, stages, all_part_max, span):
    ca, c, types = side['count_aligned'], side['collector'], raw['partition_types']
    root = next(x for x in stages['stages'] if x['root'])
    base = root['reset_source']['raw_release'] + root['settle'] + 1
    delays = {}

    def delay(n):
        if n not in delays:
            r = ca['regions'][n]
            delays[n] = 0 if r['parent'] is None else delay(r['parent']) + 3 + int(r['pad']) + int(r['edge_fall'])
        return delays[n]

    for n in ca['regions']:
        delay(n)
    start = {pn: base + delays[v['region']] + int(v.get('stages', 0)) for pn, v in ca['parts'].items()}
    rw, depths = {}, {}
    for tn, t in types.items():
        ck = t.get('clock', {})
        z = lambda k: int(ck.get(k, {}).get('depth', 0))
        rw[tn] = max(z('landing_reader_start'), z('landing_writer_start'))
        inf = c['types'].get(tn, {})
        sd = ck.get('landing_status_input_stages', {})
        extra = lambda target: max((len(v) for v in sd.get(target, {}).values()), default=0)
        ls = inf.get('local_status_depth', 1)
        ls = max(ls.values(), default=1) if isinstance(ls, dict) else ls
        depths[tn] = dict(aggregate=int(inf.get('local_registered_depth', 0)) + extra('agg'),
                          local=int(ls) + max([extra(k) for k in sd if k != 'agg'] or [0]))
    train = 171  # D8 strap TIMEOUT, as 10-30
    localboot = {pn: max(all_part_max, start.get(pn, base)) + rw[v['type']] + train for pn, v in c['parts'].items()}
    loc = {pn: localboot[pn] + depths[v['type']]['local'] for pn, v in c['parts'].items()}
    incoming = {pn: [] for pn in c['parts']}
    for e in c['edges']:
        incoming[e['dst']].append(e)
    agg = {}

    def status(pn):
        if pn not in agg:
            a = [localboot[pn]]
            for e in incoming[pn]:
                src = status(e['src']) if e['carries'] == 'aggregate' else loc[e['src']]
                a.append(src + (train if e.get('seam') else int(e['boot_transport_extra_cycles'])))
            agg[pn] = max(a) + depths[c['parts'][pn]['type']]['aggregate']
        return agg[pn]

    sys.setrecursionlimit(10000)
    ready = status(c['observer']['part']) + 1
    return dict(schema='HEAD_ROOT88_BOOT_ACCOUNT_1', plan_event='l48uo', root_settle_cycles=88,
                previous_settle_cycles=74, delta_boot_cycles=14, added_steady_cycles=0,
                root_raw_release_cycle=root['reset_source']['raw_release'], root_start_upper_cycle=base,
                raw_relative_span=span, raw_guard_cycles=4, all_part_raw_release_max_cycles=all_part_max,
                start_transport_max_cycles=max(delays.values()), part_start_max_cycle=max(start.values()),
                local_reset_start_stage_max=max(rw.values()), strap_ready_or_fault_timeout_cycles=train,
                status_ready_or_fault_at_glue_upper_cycle=ready, observer_capture_cycles=1,
                per_type_start_stages=rw, per_type_status_depths=depths,
                mission_admission='actual registered root ready && !actual sticky fault && actual host boot_done; '
                                  'a numeric bound never asserts mission',
                physical_clock_phase_qualified=False, actual_external_host_event_cycle=None,
                actual_physical_full_array_boot_receipt=None,
                qualification='conditional generated START/CA/status-network bound only; native PMA/PHY, external '
                              'host events and full-array mission readiness are excluded.')


def main():
    repo, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=False)
    por = repo / 'physical/die_plan/s81_head/plan_of_record/l48uo'
    copies = {'source_plan.json': por / 'source_plan.json.gz', 'source_sidecar.json': por / 'source_sidecar.json.gz',
              'start_stages.json': por / 'source/start_stages.json.gz', 'start_stages.sv': por / 'source/start_stages.sv.gz'}
    for name, src in copies.items():
        (out / name).write_bytes(gzip.open(src, 'rb').read())
    raw = json.loads((out / 'source_plan.json').read_text())
    side = json.loads((out / 'source_sidecar.json').read_text())
    stages = json.loads((out / 'start_stages.json').read_text())
    for port, cycles in N4.items():
        row = next(p for p in side['ports'] if p['port'] == port)
        if row['added_cycles'] != cycles or side['count_aligned']['ports'][port]['sched_lat'] != cycles:
            raise ValueError('sidecar does not carry the n4 event: ' + port)
    # Release bound as the sidecar declares it. The plan-vs-tree reset check is G0C, which DIE-HEAD-81 runs.
    all_part_max = side['collector']['boot_budget']['raw_reset_release_max_cycles']
    rows = [s for s in stages['stages'] if s.get('reset_source')]
    root = next(s for s in stages['stages'] if s['root'])
    releases = [s['reset_source']['raw_release'] for s in rows]
    span = max(v - root['reset_source']['raw_release'] for v in releases)
    report = dict(schema='HEAD_ROOT88_REPORT_L48UN', root_settle_cycles=88, raw_relative_span=span, guard_cycles=4,
                  delta_boot_cycles=14, added_steady_cycles=0, raw_release_absolute_min=min(releases),
                  raw_release_absolute_max=max(releases), all_part_raw_release_max=all_part_max,
                  stages=len(stages['stages']), settle_covers_span_plus_guard=span + 4 <= 88)
    (out / 'root88_report.json').write_text(json.dumps(report, indent=1) + '\n')
    acc = account(raw, side, stages, all_part_max, span)
    (out / 'boot88_account.json').write_text(json.dumps(acc, indent=1) + '\n')
    files = {n: hashlib.sha256((out / n).read_bytes()).hexdigest() for n in
             ['source_plan.json', 'source_sidecar.json', 'start_stages.json', 'start_stages.sv',
              'root88_report.json', 'boot88_account.json']}
    manifest = dict(schema='opentallas.head_current_source.l48uo.v1', frozen=False, physical_admission=False,
                    plan_event='l48uo', root_settle_cycles=88, delta_boot_cycles=14, added_steady_cycles=0,
                    n4_data_cycles_added_per_link=1, n4_ports=N4,
                    qualification='SOURCE witness; parent bind on l48uo owned by DIE-HEAD-81, not run here; no '
                                  'physical START/HOST/KS/PMA/mission dates', files=files)
    (out / 'current_source_manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    b = side['collector']['boot_budget']
    print(json.dumps(dict(files={k: v[:12] for k, v in files.items()},
                          manifest=hashlib.sha256((out / 'current_source_manifest.json').read_bytes()).hexdigest(),
                          span=span, all_part_max=all_part_max,
                          recomputed=dict(root_start_upper=acc['root_start_upper_cycle'], part_start_max=acc['part_start_max_cycle'],
                                          ready_upper=acc['status_ready_or_fault_at_glue_upper_cycle']),
                          sidecar_budget=dict(raw_max=b['raw_reset_release_max_cycles'], root_start_upper=b['root_start_upper_cycle'],
                                              part_start_max=b['part_start_max_cycle'], ready_upper=b['control_ready_or_fault_upper_cycle'])), indent=1))


if __name__ == '__main__':
    main()
