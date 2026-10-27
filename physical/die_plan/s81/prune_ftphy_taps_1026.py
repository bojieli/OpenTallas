#!/usr/bin/env python3
"""PATH-S81-PD4: drop explicit clock taps that the 10-26 PHY-fit regen APPENDED for ft_phy stations and that are now
EMPTY because PD4 removed those ft_phy slots. Only taps listed as 'added' in the PHY-fit taps ledger are candidates
(original endpoints are never touched); a candidate is removed only when taps.assign gives it zero load.
usage: prune_ftphy_taps_1026.py SRC_ROOT PLAN_IN PLAN_OUT OLD_TAPS_LEDGER[,LEDGER2...] REPORT"""
import json, os, re, sys
root, pin, pout, led, rep = sys.argv[1:6]
sys.path.insert(0, os.path.join(root, 'tools/die_plan')); import schema, taps
raw = json.load(open(pin)); out = {}; old = {}
for lp in led.split(','):           # several regen ledgers (PHY-fit 10-26 + PD4 re-runs): union of APPENDED taps
    for tn, ent in json.load(open(lp))['types'].items():
        old.setdefault(tn, {'added': []})['added'] += list(ent.get('added') or [])
for tn, ent in old.items():
    cand = set(ent.get('added') or [])
    if tn not in raw['partition_types'] or not cand: continue
    while True:
        P = schema.Plan(raw)
        try: taps.explicit_taps(P, tn); break
        except ValueError as e:
            m = re.search(r'explicit tap (\S+) load=0/', str(e))
            if not m or m.group(1) not in cand or 'empty=True' not in str(e): break
            ck = raw['partition_types'][tn]['clock']; ck['taps'] = [p for p in ck['taps'] if p.get('name') != m.group(1)]
            out.setdefault(tn, []).append(m.group(1))
ren = {}
for tn in out:      # keep the local tap names contiguous (taps.explicit_taps order rule): only APPENDED taps are renamed
    ck = raw['partition_types'][tn]['clock']; loc = [p for p in ck['taps'] if p.get('kind') != 'core']
    cand = set(old[tn].get('added') or [])
    for i, p in enumerate(loc):
        want = 'clk' if i == 0 else f'clk_t{i}'
        if p['name'] != want:
            assert p['name'] in cand, (tn, p['name'], want)
            ren.setdefault(tn, []).append([p['name'], want]); p['name'] = want
json.dump(raw, open(pout, 'w')); json.dump(dict(removed=out, renamed=ren, count=sum(map(len, out.values()))), open(rep, 'w'), indent=1)
print('pruned', sum(map(len, out.values())), 'taps in', len(out), 'types')
