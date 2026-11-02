from pathlib import Path
import sys,json
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design('/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338/geom.tsv');O=g.Design(str(P/'geom.tsv'));old={c[6]:c for c in O.cells.values()if c[0]=='S'};matched=[];missing=[];mismatch=[];moves=[]
for k,c in list(D.cells.items()):
 if c[0]!='S':continue
 z=old.get(c[6])
 if z is None:missing.append(c[6]);continue
 if c[1]!=z[1] or abs(c[4]-c[2]-(z[4]-z[2]))>1e-5 or abs(c[5]-c[3]-(z[5]-z[3]))>1e-5:mismatch.append({'name':c[6],'current_master':c[1],'old_master':z[1]})
 matched.append(c[6]);a,b=g.ctr(c);x,y=g.ctr(z);dx,dy=x-a,y-b;cc=list(c);cc[2]+=dx;cc[4]+=dx;cc[3]+=dy;cc[5]+=dy;D.cells[k]=tuple(cc)
 if abs(dx)+abs(dy)>1e-5:moves.append({'name':c[6],'old':[a,b],'new':[x,y],'l1':abs(dx)+abs(dy)})
bad=[];met=g.r2r_metrics(D,capture_pairs=bad)
r=dict(scope='STATIC whole name+master+size matched COUNTB FF centres on CURRENT graph only; unmatched current FFs preserved at current poses; no source/proof/occupancy/pin/clock adoption',current_ff=sum(c[0]=='S'for c in D.cells.values()),old_ff=len(old),matched=len(matched),changed=len(moves),missing_current=missing,master_size_mismatch=mismatch,old_only=sorted(set(old)-{c[6]for c in D.cells.values()if c[0]=='S'}),metrics=met,remaining_bad=bad,moves=moves)
(P/'whole_countb_centres_current_masters.json').write_text(json.dumps(r,indent=1)+'\n');print({k:r[k]for k in['current_ff','old_ff','matched','changed','metrics']});print('mastermismatch',len(mismatch),'missing',len(missing))
