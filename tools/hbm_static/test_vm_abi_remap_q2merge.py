#!/usr/bin/env python3
"""Calendar bench for the NW write merge (vm_abi_remap_q2merge): compiler-only proof that the migrated NW calendar
serves every write of the OLD (WG3) schedule on the new q0-master bank behind hfd_vms_wq2_merge, edge for edge.

Model (the RTL facts the equivalence bench tb_vms_wq2_merge proved bit-exact on real RTL, 0 mismatches):
  * producers unchanged: an old-schedule write of owner k at edge t has its source valid at the bank's ports at t
    (owners 0, >=3) or at the leaf's inputs at t (owners 1, 2 -> the leaf presents it at the bank's wq1 at t + 2);
  * the bank (ot_vms_bank_*: w_active / wslot compare) writes iff the edge's slot names the ONE active source, and
    flags w_bad if any source is active without its slot.
The random old schedules are legal WG3 calendars (<= 1 write a bank an edge).  The migrated calendar must serve
every write with no w_bad and compile into the universal NW programme word.  OT_Q2MERGE_EDGES != 2 is the mutant.
"""
import copy, json, os, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hbm_vm_static_calendar import layout, compile_schedule, ROOT
import vm_abi_remap_q2merge as M

LEAF = 2  # the RTL leaf: two edges (hfd_vms_wq2_merge pin flop + merge flop)
abi = json.loads((ROOT / 'results/arch/hbm_vm_static_1014/quadrant_abi.json').read_text())
new = copy.deepcopy(abi)
new['quadrants']['NW']['params'].update(NC=0, CW=1, RG=5, WG=2)
for port in new['quadrants']['NW']['ports']:
    n = port['name']
    if n in ('client_seq', 'response_seq'): port['bits'] = 2
    elif n == 'response_enable': port['bits'] = 1
    elif n == 'bank_client': port['bits'] = 8
    elif n == 'hub_ring_client': port['bits'] = 2
spec = layout(new, 'NW', True)
errors = served = total = 0
rng = random.Random(1016)
for trial in range(200):
    n = 64
    # legal-by-construction WG3 calendar: each bank's write edges on the NEW bank port are unique
    # (owners 1/2 land at t + LEAF, all others at t), as the compiler must place them
    claimed = set(); per = [[0] * 8 for _ in range(n)]; vv = [0] * n
    for tt in range(n):
        for b in range(8):
            if rng.random() >= 0.7:
                continue
            k = rng.randrange(8)
            at = tt + LEAF if k in (1, 2) else tt
            if (at, b) in claimed or at >= n:
                continue
            claimed.add((at, b)); vv[tt] |= 1 << b; per[tt][b] = k
    old = [dict(wslot_v=vv[tt], wslot=M.packed(per[tt], 3)) for tt in range(n)]
    sched = dict(cycles=old)
    try:
        mig = M.migrate(sched)
    except ValueError:
        errors += 1  # the schedule is legal by construction: a migration error is a failure
        continue
    # source activity at the bank ports, from the OLD schedule + the real leaf delay
    act = {}
    for t, c in enumerate(old):
        codes = M.chunks(c['wslot'], 3, 8)
        for b in range(8):
            if (c['wslot_v'] >> b) & 1:
                k = codes[b]; total += 1
                if k in (1, 2): act.setdefault((t + LEAF, b), []).append(1)
                else: act.setdefault((t, b), []).append(0 if k == 0 else k - 1)
    cyc = mig['cycles']
    for (t, b), owners in act.items():
        c = cyc[t] if t < len(cyc) else {}
        slot_v = (c.get('wslot_v', 0) >> b) & 1
        slot = M.chunks(c.get('wslot', 0), 3, 8)[b]
        if len(owners) != 1 or not slot_v or slot != owners[0]:
            errors += 1
        else:
            served += 1
    for t, c in enumerate(cyc):
        for b in range(8):
            if (c.get('wslot_v', 0) >> b) & 1 and (t, b) not in act:
                errors += 1  # a reserved slot with no source: a schedule the compiler did not intend
    compile_schedule(spec, dict(cycles=[dict(wslot_v=c.get('wslot_v', 0), wslot=c.get('wslot', 0)) for c in cyc]))
# negatives: collision and loop wrap are rejected
neg = 0
try:
    M.migrate(dict(cycles=[dict(wslot_v=1, wslot=1), {}, dict(wslot_v=1, wslot=0)]))
except ValueError:
    neg += 1
try:
    M.migrate(dict(loops=4, cycles=[{}, {}, dict(wslot_v=1, wslot=2)]))
except ValueError:
    neg += 1
edges = M.MERGE_EDGES
if errors == 0 and neg == 2 and served > 1000:
    print(f'VM_Q2MERGE_CALENDAR PASS edges={edges} served={served} of {total} writes, 2 negatives rejected, NW universal word compiles')
else:
    print(f'VM_Q2MERGE_CALENDAR FAIL edges={edges} errors={errors} served={served} negatives={neg}')
    sys.exit(1)
