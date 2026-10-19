#!/usr/bin/env python3
"""Audit source-pinned SS sensitivity coverage of a d4g view plan without substituting TT.

SS coverage is independent of source/native qualification: a complete SS inventory alone cannot qualify a die.
Use --source-root for the archived source snapshot actually consumed by the running die chain.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def audit(plan, source_root, views):
    records = {}
    for cell, v in sorted(plan.items()):
        synth = v['kind'] == 'SYNTH'
        if synth:
            top = v.get('synth_top', v.get('wrapper', cell))
            candidates = [views / 'synth' / cell / f'{top}_synth_ss.lib']
        else:
            tt = source_root / v['tt']
            candidates = [source_root / v['ss']] if v.get('ss') else []
            # Stay in the selected TT view directory and preserve the rest of its variant filename.
            name, count = re.subn(r'(?i)(?<![A-Za-z])tt(?![A-Za-z])', 'ss', tt.name)
            if count == 1:
                candidates.append(tt.with_name(name))
        candidates = list(dict.fromkeys(candidates))
        present = [p for p in candidates if p.is_file()]
        record = dict(master=v['master'], kind=v['kind'], instances=len(v['instances']),
                      source_lineage_verified=v.get('source_lineage_verified', False),
                      native_qualified=v.get('native_qualified', False), candidates=[str(p) for p in candidates])
        if len(present) == 1:
            path = present[0]
            record.update(status='AVAILABLE_UNQUALIFIED', path=str(path),
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        else:
            record.update(status='MISSING' if not present else 'AMBIGUOUS',
                          reason='No SS library for the exact selected view; TT substitution is forbidden.' if not present else
                                 'Multiple distinct candidate SS files; require explicit selected ss path.')
        records[cell] = record
    counts = Counter(x['status'] for x in records.values())
    return dict(schema='opentallas.hbm.ss_sensitivity_inventory.v1', role='SS sensitivity only',
                can_run_complete_ss=bool(records) and counts['AVAILABLE_UNQUALIFIED'] == len(records),
                native_release_qualified=False, cells=len(records), by_status=dict(counts), records=records)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--view-plan', required=True, type=Path)
    ap.add_argument('--source-root', required=True, type=Path)
    ap.add_argument('--views', required=True, type=Path, help='the local view plan directory containing synth/<cell>')
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    out = audit(json.loads(a.view_plan.read_text()), a.source_root, a.views)
    out.update(view_plan=str(a.view_plan), source_root=str(a.source_root), views=str(a.views),
               view_plan_sha256=hashlib.sha256(a.view_plan.read_bytes()).hexdigest())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'records'}))


if __name__ == '__main__':
    main()
