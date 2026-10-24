#!/usr/bin/env python3
"""KV-P7-HUB 10-23: R4 tap GRID at <= 400 um for the four hub singletons (COORD 10-23 21:26 CP1 r8 RULING: the R4 clock
method is a grid of taps at <= 400 um pitch covering all sinks, balanced to the die common latency 250 ps; sink-anchored
taps only as extras for face clusters; hubs and every large kit use the grid).  hub_Ei on the default 600-um grid
(9 taps) measured face-flop spread TT 342 / FF 288 ps (tap means 290-482 ps, all over 250, so tap_balance could not pad),
> the owner 80-ps rule.  Sets partition_types.<hub>.clock.tap_pitch_um = 400 (ceil(1278.72/400) x ceil(1676.16/400) =
4 x 5 = 20 taps at the cell centres, every sink <= ~370 um Manhattan from its tap).  Touches the four hubs' clock only.
usage: post_v38t.py die_plan.json > die_plan.json"""
import json
import sys

HUBS = ('kv3_hub_Ei', 'kv3_hub_Eo', 'kv3_hub_Wo', 'kv3_hub_Wi')
p = json.load(open(sys.argv[1]))
for tn in HUBS:
    ck = p['partition_types'][tn].setdefault('clock', {})
    for k in ('tap_mode', 'tap_radius_um', 'tap_max_sinks'):
        ck.pop(k, None)
    ck['tap_pitch_um'] = 400.0
p['note'] = p.get('note', '') + ' | v3.8t (KV-P7-HUB 10-23, COORD 21:26 R4 grid): clock.tap_pitch_um 400 on hub_Ei/Eo/Wo/Wi'
json.dump(p, sys.stdout, indent=1)
sys.stdout.write('\n')
