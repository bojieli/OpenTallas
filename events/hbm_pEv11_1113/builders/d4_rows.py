"""pEv11 delta 4 (DIE-HBM-102): pEv10 fabric rows over 1.0 (DIE-LAYOUT-HBM 00:57 RESULT), named from fabric.guide (rownets.py):
  B  y 12019.2 M6 1.181 / M8 1.059 (x 5 mm): NW_b113 L8350x3 0.68 + L1271x7 0.38;  y 11971.2 M6 1.054 (x 4 mm): L8350x3 0.71.
  AW y 10416.0 M8 1.025 (x 10 mm): NW_hub L1219x1 0.975 (one 1527-bit turnaround line).
Both slots have no bit_sites_um, so their kit station banks sit on those rows too (real demand, not a fabric artefact).
The rows just below are empty (B 11750-11900 <= 0.11; AW below 10358 = 0 at x 9-12 mm), so:
  (a) q_b113 L1271x7: its 1532.53 legs (stations 13-16, x 1149-1726) -> local y 1562.0 (die row 12048: 0.38/0.54 before), so
      the two lanes' banks no longer share row 12019.2 (model: 12019.2 -> M6 0.80 / M8 0.71, 12048 -> 0.76 / 0.89).  The only
      free x span over u_sfucore_Q_opstore_a__g0 is the top strip y 1533.6-1571.4, so L8350x3 itself cannot move down.
  (b) q_hub_nw L1219x1: the turnaround line (stations 1-4, local y 4247.64) -> y 4182.0 (die 10350.96, row 10348.8), stations respaced evenly
      x 4875.0-5890.0 so every hop (in 358, line 338, out 358) stays <= 0.9 x reach 405 = 364 (G0C reach).  0 cycles.
Not changed (fabric model artefact: fabric.py stacks every bit of a station on regs_um and ignores bit_sites_um): DE y 4800
L5071 (bit sites span y 174-486 in NE_b103/NE_b111), DW y 4560 L3005 (bit sites span 80 um).  Under 1.0 -> open list:
AE y 10483.2 0.927 (mixed), DW y 5539.2 M6 (L1265 bit-sited + L1278x6 0.28)."""
import json, sys, hashlib
src, dst, tools = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
from placement_obstacles import placement_boxes
D = json.load(open(src)); pt = D['partition_types']
hop = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
def slot(tn, sn): return [s for s in pt[tn]['ft_slots'] if s['name'] == sn][0]
def win_mid(t, s, face_key, win_key):
    W, H = t['outline_um']; f = s[face_key]; m = sum(s[win_key]) / 2
    return {'N': (m, H), 'S': (m, 0.0), 'E': (W, m), 'W': (0.0, m)}[f]
def check(tn, s):
    t = pt[tn]; boxes = list(placement_boxes(t, halo=1.08).values())
    p = [win_mid(t, s, 'in_face', 'in_window_um')] + [r[:2] for r in s['regs_um']] + [win_mid(t, s, 'out_face', 'out_window_um')]
    h = [round(hop(a, b), 1) for a, b in zip(p, p[1:])]
    inside = [r[:2] for r in s['regs_um'][1:] if any(a < r[0] < c and b < r[1] < d for a, b, c, d in boxes)]
    return h, inside
rep = {}
s = slot('q_b113', 'L1271x7'); before = check('q_b113', s)[0]
for j in (13, 14, 15, 16): assert abs(s['regs_um'][j][1] - 1532.53) < 0.01; s['regs_um'][j][1] = 1562.0
s['note'] = s.get('note', '') + ' | pEv11 DIE-HBM-102 rows: legs 13-16 y 1532.53 -> 1562.0 (die row 12048, off the L8350x3 row 12019.2), 0 cycles'
rep['q_b113:L1271x7'] = (before, check('q_b113', s))
# (b) q_hub_nw L1219x1 WITHDRAWN (pEv11c): fabEv10_AW already spreads the 1527-bit line over rows 10387-10425
# (0.5-0.98 each, one bus); moving the line only moves that peak, and a drop >87 um below the N pins breaks the
# real-bit in/out hop budget (G0 hops/stations ERROR at 138 um). pEv10 geometry kept; AW 10416 -> open list.
for k, (b, (h, ins)) in rep.items():
    print(k, 'hops before', b, 'after', h, 'regs in cores', ins); assert max(h) <= (364.0 if 'L1219' in k else 405.0) and not ins, k
out = json.dumps(D, indent=1); open(dst, 'w').write(out); print('sha', hashlib.sha256(out.encode()).hexdigest()[:12])
