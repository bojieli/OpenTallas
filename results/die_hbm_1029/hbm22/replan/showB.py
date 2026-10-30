import sys, json
V=json.loads(sys.argv[1]); B=sys.argv[2]=='B'; sys.argv=['x','lanes.json','rows103.json','rows_h8b.json']
import replan_est as R
if B: R.SIZE.update({'NW_spu0':466.56,'NW_spu1':1468.8+1218.24})
rect=R.apply_rows({'A':V[0],'C':V[1]})
for (a,b),(pb,nb) in sorted(R.pairs.items(),key=lambda kv:-kv[1][1]):
    if nb==0 or a.startswith('NE') or b.startswith('NE'): continue
    e,g=R.rel(rect[a],rect[b]); 
    print('  %-9s %-9s new %5d plan %5d %s'%(a,b,nb,pb,'ADJ edge %.0f'%e if e>=50 else ('NEAR' if g<=1200 else 'FAR')+' gap %.0f'%g))
