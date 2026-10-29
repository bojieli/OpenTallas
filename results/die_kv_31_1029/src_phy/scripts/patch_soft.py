# Patch the copied plan_access.py into plan_access_soft.py (DIE-KV-31 variant; Codex original untouched).
import sys,re
p=sys.argv[1];s=open(p).read()
s=s.replace('a=p.parse_args()','p.add_argument("--soft-block-layer",default="",help="DIE-KV-31 variant: BLOCK OBS on this layer (die_trial.band_share_obs capacity stripes) are NOT hard blockers; PG metal inside them is charged to the stripe capacity");p.add_argument("--y-reach",type=int,default=1400,help="DIE-KV-31 variant: M8 landing search half-range in DBU (original 1400)");a=p.parse_args()',1)
s=s.replace("for owner,ly,*r in g['obstructions']:\n","soft=[]\nfor owner,ly,*r in g['obstructions']:\n if owner=='BLOCK' and ly==a.soft_block_layer:soft.append(r);continue\n",1)
s=s.replace("y-1400-40-80*par","y-a.y_reach-40-80*par").replace("y+1400-40-80*par","y+a.y_reach-40-80*par")
charge='''
# DIE-KV-31: charge PG metal on the soft layer against each band-share stripe, per 10.8-um gcell segment.
if soft:
 G=10800;pitch={'M7':64,'M6':64,'M5':48,'M4':48}.get(a.soft_block_layer,64);st=STRtree([box(*r) for r in soft]);use=collections.defaultdict(set)
 for n,ly,*r in shapes:
  if ly!=a.soft_block_layer:continue
  for j in st.query(box(*r)):
   R=soft[j]
   if not hit(r,R):continue
   vert=(R[3]-R[1])>(R[2]-R[0])
   tr0,tr1=((r[0]//pitch,(r[2]-1)//pitch) if vert else (r[1]//pitch,(r[3]-1)//pitch))
   g0,g1=((max(r[1],R[1])//G,(min(r[3],R[3])-1)//G) if vert else (max(r[0],R[0])//G,(min(r[2],R[2])-1)//G))
   for gg in range(g0,g1+1):
    for t in range(tr0,tr1+1):use[j,gg].add(t)
 rows=[]
 for (j,gg),tt in use.items():
  R=soft[j];vert=(R[3]-R[1])>(R[2]-R[0]);cap=((R[2]-R[0]) if vert else (R[3]-R[1]))//pitch
  rows.append([j,gg,len(tt),cap,round(len(tt)/max(cap,1),4)])
 rows.sort(key=lambda q:-q[4])
 s['soft_charge']=dict(layer=a.soft_block_layer,soft_stripes=len(soft),charged_stripe_gcells=len(rows),max_use=rows[0][4] if rows else 0,over_0p6=sum(q[4]>0.6 for q in rows),tracks_used=sum(q[2] for q in rows),top=rows[:10],note='use = distinct PG tracks on the stripe within one 10.8-um gcell / stripe tracks')
'''
s=s.replace("json.dump(s,open(out/'summary.json','w'),indent=2)",charge+"json.dump(s,open(out/'summary.json','w'),indent=2)",1)
assert s.count('a.y_reach')==2 and 'soft.append' in s and 'soft_charge' in s
open(p,'w').write(s);print('patched')
