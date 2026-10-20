#!/usr/bin/env python3
"""Die-run relay stages vs the compiled static schedule (ROOT RELAY-SCHEMA 10-16): FAIL on any difference.

    die_relay_check.py DIE_RUN_STAGES SCHEDULE_STAGES [--json REPORT.json] [--max-list 40]

DIE_RUN_STAGES   opentallas.die_relay_stages.v1 exported from the die run (role die_plan), e.g.
                 tools/hbm_die_v15/relay_stages_export.py on the GEN case, tools/s81/relay_stages_export.py,
                 tools/qwen_split/relay_stages_export.py, tools/qwen_kv_die/relay_stages_export.py
SCHEDULE_STAGES  the table the compiler / timing model scheduled with (role compiled_schedule, written by the
                 consumer's --compiled-out), or another die_plan export (plan vs relayed run)
FAIL (exit 1) on: invalid file / bad digest, design mismatch, compiled table built from a different plan digest,
incomplete coverage or unresolved exports, unknown domains, any bus missing on either side, any bus whose stages / width / clock domain differ, any diagnostic override in the
schedule, and (QXF-SEAMK 10-18) any TORN RECORD BUNDLE of the die run (tools/die_record_bundles.py: the members of one
static record reach their consumer on different ages -- a consumer captures a torn record whatever the schedule says;
--no-bundles skips it for designs without a bundle table).  eq_age_group differences are warnings.  PASS (exit 0) prints
the shared digest.  A die run whose bus table is bit-identical to the compiled schedule (same digest) PASSES although the
schedule was compiled from an earlier plan (compiled.loaded_digest): the die now builds exactly what was scheduled (e.g. a
generator fix that equalised the bundles the compiler had already scheduled at their max).

Die chains: run it as the last step after the die GEN export, e.g.
    python3 tools/die_relay_check.py $RUN/relay_stages.json $SCHED/relay_stages_compiled.json --json $RUN/relay_check.json
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_relay_stages as DRS  # noqa: E402
import die_record_bundles as DRB  # noqa: E402


def check(run, sched, max_list=40, bundles=True):
    fails, warns = [], []
    for label, doc in (('die run', run), ('schedule', sched)):
        if doc.get('coverage') != 'complete':
            fails.append(f"{label} coverage {doc.get('coverage')!r} is incomplete; direct and multicast buses required")
        if doc.get('problem_count', 0) or doc.get('problems'):
            fails.append(f"{label} reports unresolved export problems")
        unknown = [b['id'] for b in doc['buses'] if not b.get('domain')]
        if unknown:
            fails.append(f"{label} has {len(unknown)} buses with unknown clock domains, e.g. {unknown[:3]}")
    if run['design'] != sched['design']:
        fails.append(f"design {run['design']} != {sched['design']}")
    if sched['role'] == 'compiled_schedule':
        c = sched['compiled']
        if c['loaded_digest'] != run['digest'] and run['digest'] != sched['digest']:
            fails.append(f"schedule compiled from plan digest {c['loaded_digest']} (plan {sched['plan']['id']}), "
                         f"die run digest {run['digest']} (plan {run['plan']['id']}): re-compile against this die")
        for o in c.get('overrides') or []:
            fails.append(f"diagnostic override in schedule: {o['bus']} plan {o['plan_stages']} -> used {o['used_stages']}")
    if abs(run['clock_period_ps'] - sched['clock_period_ps']) > 1e-3:
        fails.append(f"clock period {run['clock_period_ps']} != {sched['clock_period_ps']} ps")
    R = {b['id']: b for b in run['buses']}
    S = {b['id']: b for b in sched['buses']}
    only_r = sorted(set(R) - set(S)); only_s = sorted(set(S) - set(R))
    diff, wdiff, ddiff, gdiff, adiff = [], [], [], [], []
    for k in sorted(set(R) & set(S)):
        r, s = R[k], S[k]
        if r['stages'] != s['stages']:
            diff.append(dict(bus=k, die_run=r['stages'], schedule=s['stages']))
        if 'age_edges' in r or 'age_edges' in s:
            ra, sa = r.get('age_edges', '<absent>'), s.get('age_edges', '<absent>')
            if ra is None or sa is None or ra != sa:
                adiff.append(dict(bus=k, die_run=ra, schedule=sa))
        if r['width'] != s['width']:
            wdiff.append(dict(bus=k, die_run=r['width'], schedule=s['width']))
        if r.get('domain') != s.get('domain'):
            ddiff.append(dict(bus=k, die_run=r.get('domain'), schedule=s.get('domain')))
        if r.get('eq_age_group') != s.get('eq_age_group'):
            gdiff.append(k)
    if only_r:
        fails.append(f'{len(only_r)} buses in the die run missing from the schedule, e.g. {only_r[:3]}')
    if only_s:
        fails.append(f'{len(only_s)} scheduled buses missing from the die run, e.g. {only_s[:3]}')
    if diff:
        fails.append(f'{len(diff)} buses with different relay stage counts, e.g. ' +
                     ', '.join(f"{d['bus']}: die {d['die_run']} vs sched {d['schedule']}" for d in diff[:3]))
    if wdiff:
        fails.append(f'{len(wdiff)} buses with different width')
    if adiff:
        fails.append(f'{len(adiff)} buses with different or unresolved effective source-to-pin ages')
    if ddiff:
        fails.append(f'{len(ddiff)} buses with different clock domain')
    if gdiff:
        warns.append(f'{len(gdiff)} buses with a different eq_age_group, e.g. {gdiff[:3]}')
    torn = DRB.torn(run) if bundles else []
    for n_, r_ in torn:
        fails.append('torn record bundle ' + DRB.describe(n_, r_))
    if not fails and run['digest'] != sched['digest']:
        fails.append(f"digest {run['digest']} != {sched['digest']} with no bus difference found (internal error)")
    return dict(schema='opentallas.die_relay_check.v1', verdict='FAIL' if fails else 'PASS',
                design=run['design'], die_run=dict(plan=run['plan'], digest=run['digest'], buses=run['bus_count']),
                schedule=dict(plan=sched['plan'], role=sched['role'], digest=sched['digest'], buses=sched['bus_count'],
                              consumer=(sched.get('compiled') or {}).get('consumer')),
                fails=fails, warnings=warns, only_in_die_run=only_r[:max_list], only_in_schedule=only_s[:max_list],
                stage_diffs=diff[:max_list], age_diffs=adiff[:max_list], width_diffs=wdiff[:max_list], domain_diffs=ddiff[:max_list],
                torn_bundles={n_: r_ for n_, r_ in torn}, bundles_checked=bool(bundles))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('die_run'); ap.add_argument('schedule'); ap.add_argument('--json'); ap.add_argument('--max-list', type=int, default=40)
    ap.add_argument('--no-bundles', action='store_true', help='skip the record-bundle rule (designs without a bundle table)')
    a = ap.parse_args(argv)
    try:
        run, sched = DRS.load(a.die_run), DRS.load(a.schedule)
    except (DRS.RelayStagesError, json.JSONDecodeError, OSError) as e:
        print(f'DIE_RELAY_CHECK FAIL: {e}')
        return 1
    rep = check(run, sched, a.max_list, bundles=not a.no_bundles)
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1) + '\n')
    if rep['verdict'] == 'PASS':
        print(f"DIE_RELAY_CHECK PASS design={run['design']} buses={run['bus_count']} digest={run['digest']} "
              f"plan={run['plan']['id']} schedule={sched['role']}:{(sched.get('compiled') or {}).get('consumer')}")
    else:
        print(f"DIE_RELAY_CHECK FAIL design={run['design']} " + ' | '.join(rep['fails']))
    for w in rep['warnings']:
        print('  warning:', w)
    return 0 if rep['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
