"""DIE-LAYOUT-HBM F3 (11-11): q_su01 su-chan ft re-site, proposal (A) of the 05:52 su-chan-ft-resite handoff (COORD 04:09 (1)).
L8007x1 (641 b, S 297-351 -> E 759-813) and L8008x7 (632 b, E 826-879 -> S 353-405) leave the y~800-850 E-W street above
plain12_15 and the W column (x~315) and run through the empty S field (cores start at y ~340) and the empty E strip
(x > 1700 below the exp5/exp11 row). Same station count (7 each), regs re-spread at equal hops along the new route.
Positions only; windows, cores and other slots unchanged."""
import json, sys
cur, out = sys.argv[1], sys.argv[2]
P = json.load(open(cur)); t = P['partition_types']['q_su01']
def spread(path, k):
    seg = [(a, b) for a, b in zip(path, path[1:])]
    L = sum(abs(b[0]-a[0]) + abs(b[1]-a[1]) for a, b in seg); h = L / k; pts = [list(path[0])]
    for j in range(1, k):
        d = h * j
        for a, b in seg:
            l = abs(b[0]-a[0]) + abs(b[1]-a[1])
            if d <= l:
                f = d / l if l else 0; pts.append([round(a[0] + (b[0]-a[0]) * f, 3), round(a[1] + (b[1]-a[1]) * f, 3)]); break
            d -= l
    return pts, h
tag = ' | DIE-LAYOUT-HBM 11-11 F3 su-chan (A): re-sited through the empty S field / E strip, count kept'
for s in t['ft_slots']:
    if s['name'] == 'L8007x1':
        regs, h = spread([(324.0, 4.0), (324.0, 280.0), (1820.0, 280.0), (1820.0, 786.24), (1931.0, 786.24)], 7)
    elif s['name'] == 'L8008x7':
        regs, h = spread([(1931.0, 852.6), (1740.0, 852.6), (1740.0, 200.0), (379.0, 200.0), (379.0, 4.0)], 7)
    else:
        continue
    assert len(regs) == s['stations'] == 7
    s['regs_um'] = regs; s['note'] = s.get('note', '') + tag
    print(s['name'], round(h, 1), regs)
json.dump(P, open(out, 'w'), indent=1); open(out, 'a').write('\n')
