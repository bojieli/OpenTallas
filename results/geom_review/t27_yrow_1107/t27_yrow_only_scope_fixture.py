from pathlib import Path
import re,collections,sys
rows=[x.split('\t') for x in Path(sys.argv[1]).read_text().splitlines()]
roots={x[1]:(float(x[4]),float(x[5])) for x in rows if x[0]=='R'}
before={x[2]:x[1] for x in rows if x[0]=='S'};after=dict(before);groups=collections.defaultdict(list)
pat=re.compile(r'^u_bound[.]g_u_lf0_u_vp_yrow_d[.].*native_memory[^0-9]*[0-2][^0-9]+([0-9]+)[^0-9]')
for x in rows:
 if x[0]!='S':continue
 m=pat.search(x[2])
 if m:groups[m[1]].append(x)
assert len(groups)==128 and all(len(v)==3 for v in groups.values())
for v in groups.values():
 cx=sum(float(x[4]) for x in v)/3;cy=sum(float(x[5]) for x in v)/3
 rt=min(roots,key=lambda q:abs(cx-roots[q][0])+abs(cy-roots[q][1]))
 for x in v:after[x[2]]=rt
selected={x[2] for v in groups.values() for x in v}
untargeted=set(before)-selected
assert all(before[n]==after[n] for n in untargeted)
# Executable ct_follow skips every inst when ct_fre empty (line146).
fre='';followers=[n for n in before if fre and re.search(fre,n)];assert not followers
counts=collections.Counter(after.values());assert max(counts.values())<3000
print('PASS groups128x3, followers0, untargeted mapping equality',len(untargeted),'of',len(before),'baseline cells; maxrootload',max(counts.values()))
print('MODEL ONLY from existing CTS coordinates; actual new CTS membership must be compared again.')
