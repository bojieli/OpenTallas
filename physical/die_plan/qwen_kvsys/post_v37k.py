#!/usr/bin/env python3
"""KV-P6 10-23: COORD 19:55 R4 corrected to the owner clock rule -> ONE die-wide common clock latency target for every KV
partition.  The per-type clock.insertion_ps values (250..500) were the legacy one-interior-tap estimates (retired by R4 tap
grids; KV IO kits9 measured 239..267 ps at the face flops).  Every type's clock.insertion_ps (and the die clock) is set to
the die target COMMON_PS; tap_balance pads each partition's face-flop insertion to it, and the IO SDC proxy uses it as the
vclk latency.  Hard checks (owner 10-17): face-flop spread <= 80 ps TT+FF on RC, seam skew to the common target <= 80 ps.

    python3 post_v37k.py die_plan_in.json [COMMON_PS=250] > die_plan.json
"""
import json
import sys

p = json.load(open(sys.argv[1]))
common = float(sys.argv[2]) if len(sys.argv) > 2 else float(p['clock'].get('insertion_ps', 250))
p['clock']['insertion_ps'] = common
p['clock']['common_latency_ps'] = common          # G0C die-level key (plan-tool4)
old = {}
for n, t in p['partition_types'].items():           # G0C: new top-down cores are built on the plan tracks
    for hc in t.get('hard_cores', []):
        hc.setdefault('track_offset_um', [0.0, 0.0])
for n, t in p['partition_types'].items():
    c = t.setdefault('clock', {})
    old[n] = c.get('insertion_ps')
    c['insertion_ps'] = common
p['note'] = p.get('note', '') + f' | v3.7 (KV-P6 10-23): one common die clock latency {common:.0f} ps for all types (COORD 19:55: hard = face-flop spread <= 80 ps TT+FF + seam skew to it <= 80; insertion/sink/tap checks WARN)'
sys.stderr.write(f'post_v37k: {sum(1 for v in old.values() if v != common)} of {len(old)} types re-targeted to {common:.0f} ps\n')
json.dump(p, sys.stdout, indent=1)
sys.stdout.write('\n')
