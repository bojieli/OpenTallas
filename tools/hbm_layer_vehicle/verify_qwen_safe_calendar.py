#!/usr/bin/env python3
"""Verify repaired Qwen reader calendars preserve actual operand images and numerical checks (no simulation)."""
import argparse
import hashlib
import json
from pathlib import Path
from native_su_calendar import reserve_component, compact_holds


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline', type=Path, required=True)
    ap.add_argument('--candidate', type=Path, required=True)
    ap.add_argument('--boundary', type=Path, required=True)
    ap.add_argument('--capacity', type=int, default=11651)
    a = ap.parse_args()
    boundary = json.loads(a.boundary.read_text())
    rows = []
    for stage in ('L0', 'chain'):
        for rank in (0, 5):
            rel = Path(stage)/f'r{rank}'
            new = json.loads((a.candidate/rel/'replay.json').read_text())
            old = json.loads((a.baseline/rel/'replay.json').read_text())
            man = json.loads((a.candidate/rel/'manifest.json').read_text())
            before = json.loads((a.baseline/rel/'manifest.json').read_text())
            def numerical(events, kind):
                return sorted(json.dumps({k:v for k,v in e.items() if k != 'cyc'}, sort_keys=True)
                              for e in events if e['k'] == kind)
            assert numerical(new['events'], 'M') == numerical(old['events'], 'M'), f'operand images changed: {rel}'
            assert numerical(new['events'], 'C') == numerical(old['events'], 'C'), f'numerical checks changed: {rel}'
            assert man['counts'] == before['counts'], f'node scope changed: {rel}'
            assert [(r['i'],r['status'],r.get('golden_vs_hgi')) for r in man['records']] == [
                (r['i'],r['status'],r.get('golden_vs_hgi')) for r in before['records']], f'arithmetic changed: {rel}'
            assert all(r.get('golden_vs_hgi',{}).get('mismatch',0) == 0 for r in man['records'] if r['status']=='emitted')
            assert not [reason for r in man['records'] for reason in r['reasons'] if 'raw_hazard' in reason]
            reserved = reserve_component(new, boundary)
            emitted_nev = 1 + sum(e['k'] != 'M' for e in reserved['events'])
            if emitted_nev > a.capacity:
                # This removes only redundant same-value D holds, preserving
                # every input transition, preload, check and record event.
                reserved = compact_holds(reserved, a.capacity)
            dest = a.candidate/'reserved'/f'qw_{stage.lower()}_r{rank}.json'
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(reserved)+'\n')
            non_m = sum(e['k'] != 'M' for e in reserved['events'])
            assert non_m+1 <= a.capacity, f'new capacity required: {rel}, NEV={non_m+1}'
            rows.append(dict(case=str(rel),preloads_identical=True,expectations_identical=True,
                             math_nodes_unchanged=True,status_counts=man['counts'],
                             excluded_chain_stale=[r['i'] for r in man['records'] if r['status']=='chain_stale'],
                             emitted_NEV=emitted_nev,
                             lossless_hold_compaction=reserved.get('hold_compaction'),
                             required_NEV=non_m+1,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),replay=str(dest)))
    receipt = dict(status='PASS_EMISSION_ONLY',scope='same partial Qwen SU nodes; actual RTL execution pending',
                   reader_contract='unused roles read live A own-bank; inactive scalar lane address identity; unchanged arithmetic',
                   drain_guard_serial=1,fixed_record_serialization=True,no_runtime_wait=True,capacity=a.capacity,
                   hardware_executed=False,qualifies_native_layer=False,qualifies_native_chain=False,
                   qualifies_full_token=False,cases=rows)
    (a.candidate/'safe_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
