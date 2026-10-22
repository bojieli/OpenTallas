#!/usr/bin/env python3
"""STW-S81c-DIE3-C28 GEN gates: c28_gen_gate.py GEN_DIR REF_CASE_JSON -> one line, exit 0 only when every gate passes.
Gates: DIE_GEN_SAFETY PASS, strict port bind PASS, ROUTE_DONE failed 0, hops_over 0, census == reference (cap26 same
variant) for every non-std master (closed + stand-in; std cells may differ: entry buffers / ties), dieclk split/reserve facts."""
import json, sys, re
G, ref = sys.argv[1], sys.argv[2]
c = json.load(open(f'{G}/case/case.json')); r = json.load(open(ref))
gs = json.load(open(f'{G}/case/gen_safety.json')); pb = json.load(open(f'{G}/bind/bind/port_bind.json'))
route = open(f'{G}/route.log').read()
m = re.search(r'ROUTE_DONE failed (\d+)', route)
fails = []
if gs['verdict'] != 'PASS': fails.append(f"gen_safety {gs['verdict']}")
if pb['verdict'] != 'PASS': fails.append(f"port_bind {pb['verdict']}")
if not m or m.group(1) != '0': fails.append('route failed ' + (m.group(1) if m else '?'))
if gs['counts'].get('hops_over'): fails.append(f"hops_over {gs['counts']['hops_over']}")
fn = lambda cen: {k: v for k, v in cen.items() if not k.startswith('std:')}
a, b = fn(c['census']), fn(r['census'])
diff = {k: (b.get(k, 0), a.get(k, 0)) for k in set(a) | set(b) if a.get(k, 0) != b.get(k, 0)}
if diff: fails.append(f'census diff vs cap26 {len(diff)}: ' + ', '.join(f'{k} {x}->{y}' for k, (x, y) in sorted(diff.items())[:8]))
dk = c.get('dieclk') or {}
print(('C28_GEN_GATE PASS' if not fails else 'C28_GEN_GATE FAIL: ' + '; '.join(fails)) +
      f" | gen_safety {gs['verdict']} hops_over {gs['counts'].get('hops_over')} max_hop {gs.get('max_hop_um')} | port_bind {pb['verdict']}"
      f" | route failed {m.group(1) if m else '?'} | census non-std masters {len(a)} (cap26 {len(b)}) same={not diff}"
      f" | dieclk roots {dk.get('roots')} split {dk.get('roots_split')} entries {dk.get('entries')} iters {dk.get('iters')}"
      f" split_um {dk.get('split_um')} pin_split {dk.get('pin_split')} ckr_reserve {json.dumps(dk.get('ckr_reserve'))}")
sys.exit(1 if fails else 0)
