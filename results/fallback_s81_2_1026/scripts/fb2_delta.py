#!/usr/bin/env python3
"""FALLBACK-S81-2 plan delta on the composed G=2 plan (no early taps, COORD RULING 10-26 17:49):
clock.core_taps 'early' removed (schema enum has only early) on every legacy-core type (the die tree feeds only partition entries; the legacy core
clock pin is a partition-CTS sink whose data ports are landed (+3, priced) or the core is rebuilt to 12.3).
The latency table is regenerated afterwards with gen.py latency --inplace.  usage: fb2_delta.py IN OUT"""
import json, sys
raw = json.load(open(sys.argv[1]))
n = 0
for tn, t in raw['partition_types'].items():
    ck = t.get('clock') or {}
    if ck.get('core_taps') == 'early':
        del ck['core_taps']
        n += 1
raw['note'] = (raw.get('note', '') + '; FALLBACK-S81-2 10-26: core_taps early removed on %d types (no early taps)' % n).strip('; ')
json.dump(raw, open(sys.argv[2], 'w'), indent=1)
print(json.dumps(dict(types_core_taps_off=n)))
