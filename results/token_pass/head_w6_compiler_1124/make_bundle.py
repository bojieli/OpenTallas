#!/usr/bin/env python3
"""Build the HEAD W6 compiler source witness bundle (HEAD-R18, COORD ruling 11-24).

Inputs (none of them on main; their sha256 are recorded in the manifest and pinned by head_root_boot.py):
  PLAN      live W6 source plan b3507e628de6 (HEAD-WEST prep_r18w6)
  SIDECAR   W6 sidecar with the lep0N_w status-network fix (HEAD-WEST w6_live/sidecar_w6_coll.json)
  STAGES    START tree re-sited on the W6 type raw exports (HEAD-R18 start_w6_1124/provider_w6: unpatch of
            provider_e1br, start_reset.py + relay_over.py, SETTLE 88, 9 relays, span 72)
root88_report.json and boot88_account.json are recomputed with the arithmetic of the 10-30 accountant
(results/codex_head_1030/legal88_source/account_boot88_v2.py), as in head_l48uo_compiler_1107/make_bundle.py,
read-only.  Source witness only: frozen false, physical admission false, no START/HOST/PMA/mission date.

  make_bundle.py PLAN SIDECAR STAGES_DIR OUT
"""
import hashlib
import json
import sys
from pathlib import Path

PLAN_EVENT = 'w6'
N4 = ('coll_WN1_u__1', 'coll_WN2_u__3', 'coll_WN1_d__0', 'coll_WN2_d__0')


def account(raw, side, stages, all_part_max, span, settle, prev_settle):
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
    return dict(schema='HEAD_ROOT88_BOOT_ACCOUNT_1', plan_event=PLAN_EVENT, root_settle_cycles=settle,
                previous_settle_cycles=prev_settle, delta_boot_cycles=settle - prev_settle, added_steady_cycles=0,
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
    plan, sidecar, sd, out = (Path(a) for a in sys.argv[1:5])
    out.mkdir(parents=True, exist_ok=False)
    copies = {'source_plan.json': plan, 'source_sidecar.json': sidecar,
              'start_stages.json': sd / 'start_stages.json', 'start_stages.sv': sd / 'start_stages.sv'}
    for name, src in copies.items():
        (out / name).write_bytes(src.read_bytes())
    raw = json.loads((out / 'source_plan.json').read_text())
    side = json.loads((out / 'source_sidecar.json').read_text())
    stages = json.loads((out / 'start_stages.json').read_text())
    settle = int(stages['root_settle'])
    prev_settle = settle - int(stages['root_settle_guard']['added_boot_cycles'])
    if side['count_aligned']['root_settle_cycles'] != settle:
        raise ValueError('sidecar root settle differs from the START tree')
    regions = {r for r in side['count_aligned']['regions'] if r.startswith('st:')}
    if regions != {s['region'] for s in stages['stages']}:
        raise ValueError('START tree stages differ from the sidecar st: regions')
    parts = side['collector']['parts']
    loose = sorted({x for e in side['collector']['edges'] for x in (e['src'], e['dst'])} - set(parts))
    if loose:
        raise ValueError('collector edges name parts it does not declare: ' + ', '.join(loose))
    all_part_max = side['collector']['boot_budget']['raw_reset_release_max_cycles']
    rows = [s for s in stages['stages'] if s.get('reset_source')]
    root = next(s for s in stages['stages'] if s['root'])
    releases = [s['reset_source']['raw_release'] for s in rows]
    span = max(v - root['reset_source']['raw_release'] for v in releases)
    span_relays = stages['root_settle_guard'].get('raw_relative_span_with_relays', span)
    report = dict(schema='HEAD_ROOT88_REPORT_W6', root_settle_cycles=settle, raw_relative_span=span,
                  raw_relative_span_with_relays=span_relays, guard_cycles=4, previous_settle_cycles=prev_settle,
                  delta_boot_cycles=settle - prev_settle, added_steady_cycles=0, raw_release_absolute_min=min(releases),
                  raw_release_absolute_max=max(releases), all_part_raw_release_max=all_part_max,
                  stages=len(stages['stages']), reset_ports=len(stages['reset_ports']), reset_relays=stages.get('reset_relays', 0),
                  settle_covers_span_plus_guard=max(span, span_relays) + 4 <= settle)
    if not report['settle_covers_span_plus_guard'] or settle < 64:
        raise ValueError('root settle does not cover span + guard (or is below the rst_n >= 64 rule)')
    (out / 'root88_report.json').write_text(json.dumps(report, indent=1) + '\n')
    acc = account(raw, side, stages, all_part_max, span, settle, prev_settle)
    (out / 'boot88_account.json').write_text(json.dumps(acc, indent=1) + '\n')
    files = {n: hashlib.sha256((out / n).read_bytes()).hexdigest() for n in
             ['source_plan.json', 'source_sidecar.json', 'start_stages.json', 'start_stages.sv',
              'root88_report.json', 'boot88_account.json']}
    cap = side['count_aligned']['ports']
    n4 = {p: dict(added_cycles=next(r for r in side['ports'] if r['port'] == p)['added_cycles'], sched_lat=cap[p]['sched_lat'])
          for p in N4}
    manifest = dict(schema='opentallas.head_current_source.w6.v1', frozen=False, physical_admission=False,
                    plan_event=PLAN_EVENT, root_settle_cycles=settle, delta_boot_cycles=settle - prev_settle,
                    added_steady_cycles=0, n4_ports=n4,
                    inputs={n: str(p) for n, p in copies.items()},
                    qualification='SOURCE witness; parent bind on W6 is HEAD-WEST bind_r18w6(c); no '
                                  'physical START/HOST/KS/PMA/mission dates', files=files)
    (out / 'current_source_manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    b = side['collector']['boot_budget']
    print(json.dumps(dict(files={k: v[:12] for k, v in files.items()},
                          manifest=hashlib.sha256((out / 'current_source_manifest.json').read_bytes()).hexdigest(),
                          span=span, span_relays=span_relays, all_part_max=all_part_max, n4=n4,
                          recomputed=dict(root_raw_release=acc['root_raw_release_cycle'], root_start_upper=acc['root_start_upper_cycle'],
                                          part_start_max=acc['part_start_max_cycle'],
                                          ready_upper=acc['status_ready_or_fault_at_glue_upper_cycle']),
                          sidecar_budget=dict(raw_max=b['raw_reset_release_max_cycles'], root_start_upper=b['root_start_upper_cycle'],
                                              part_start_max=b['part_start_max_cycle'], ready_upper=b['control_ready_or_fault_upper_cycle'])), indent=1))


if __name__ == '__main__':
    main()
