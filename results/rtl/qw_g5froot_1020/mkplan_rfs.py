"""QW-G5FROOT 10-20 reserved-fault-site plan: regenerate the fault-emit plan from the EXACT base GEN the fault run sits on
(the cfc5a82ac data-only GEN dv2f20g5r2).  reserved = every relay / landing box (rly_*) that base placed, so fault roots
placed before _relays never take a site the data relays use (the old plan came from the pre-reach-fix dv2f20g5 base: 594 of
the 1080 cfc5a82ac relay/landing boxes were NOT reserved -> group roots sat on them -> 9 data nets over 405 in dv2f20g5rf).
owners[o].pts = landing CENTRES (the fault pin sits at the landing centre, next to ck/rs).
    python3 mkplan_rfs.py CASE_DIR OUT.json"""
import json, re, sys, statistics, collections
case, out = sys.argv[1], sys.argv[2]
fl = json.load(open(case + '/fwd_lanes.json'))
pl = {mm[1]: (float(mm[2]), float(mm[3])) for mm in
      re.finditer(r'findInst (\S+)\] ([\d.]+) ([\d.]+) (\S+)', open(case + '/place.tcl').read())}
dv = open(case + '/die.v').read()
lef = open(case + '/elements.lef').read()
sz = {mm[1]: (float(mm[2]), float(mm[3])) for mm in
      re.finditer(r'MACRO (\S+)\n(?:.*\n){0,3}?\s*SIZE ([\d.]+) BY ([\d.]+)', lef)}
landm = {n: ms for ms, n in re.findall(r'^\s*(qfd_landh\w*)\s+(\w+)\s*\(', dv, re.M)}
own, miss = collections.defaultdict(list), []
for r in fl['lanes']:
    L = r.get('landing')
    if L in landm:
        if L not in pl or landm[L] not in sz:
            miss.append(L); continue
        (x, y), (w, h) = pl[L], sz[landm[L]]
        own[r['dst']].append((x + w / 2, y + h / 2))
o = {k: dict(xy=[round(statistics.median(p[0] for p in v), 3), round(statistics.median(p[1] for p in v), 3)],
             landings=len(v), pts=[[round(p[0], 3), round(p[1], 3)] for p in sorted(v)]) for k, v in sorted(own.items())}
mst = {n: ms for ms, n in re.findall(r'^\s*(qfd_\w+)\s+(rly_\w+)\s*\(', dv, re.M)}
res = []
for n, ms in sorted(mst.items()):
    if n in pl and ms in sz:
        x, y = pl[n]; w, h = sz[ms]
        res.append([x, y, round(x + w, 3), round(y + h, 3)])
print('landings', len(landm), 'in lanes', sum(len(v) for v in own.values()), 'owners', len(own), 'miss', miss[:5],
      'reserved', len(res), 'of', len(mst))
json.dump(dict(reserved=res, schema='opentallas.qwen.fault-emit-plan.v1', source=case, pts_are='landing centres',
               owners=o, landings=len(landm)), open(out, 'w'), indent=1)
