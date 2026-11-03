from pathlib import Path
from collections import deque,Counter
import sys,json,math
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design('/srv/opentallas-scratch/claude/head-wave-path-query-1102/hd_st_n3_turn/geom5/geom.tsv');by={c[6].replace(chr(92),''):i for i,c in D.cells.items()};i=by['u_cland_u1_i/_09236_'];roots=[s[1]for n in D.drives[i]for s in D.nets[n][2]if s[0]=='i'and D.cells[s[1]][1].startswith('OR3')];out=[]
for root in roots:
 q=deque(D.drives[root]);seen=set();buf=set();leaves=[];ports=[]
 while q:
  n=q.popleft()
  if n in seen:continue
  seen.add(n)
  for s in D.nets[n][2]:
   if s[0]=='p':ports.append(D.pin_by_k[s[1]]['name']);continue
   k=s[1];c=D.cells[k];ins=[nn for nn,ck in D.cell_in.get(k,[])if not ck]
   if not s[2]and c[1].startswith('BUFx')and len(ins)==1and ins[0]==n:buf.add(k);q.extend(D.drives.get(k,[]))
   else:leaves.append(dict(instance=c[6],id=k,clock=s[2],old_net_id=n,xy=list(g.ctr(c))))
 leaves.sort(key=lambda z:(z['xy'][0],z['xy'][1],z['instance']));groups=[]
 for j in range(0,len(leaves),16):
  a=leaves[j:j+16];xy=[sum(z['xy'][0]for z in a)/len(a),570.24];groups.append(dict(index=len(groups),xy=xy,fanout=len(a),max_leaf_centre_l1_um=max(abs(z['xy'][0]-xy[0])+abs(z['xy'][1]-xy[1])for z in a),members=a))
 upper=[]
 for j in range(0,len(groups),8):
  a=groups[j:j+8];xy=[sum(z['xy'][0]for z in a)/len(a),566.46];upper.append(dict(index=len(upper),xy=xy,fanout=len(a),children=[z['index']for z in a],max_child_centre_l1_um=max(abs(z['xy'][0]-xy[0])+abs(z['xy'][1]-xy[1])for z in a)))
 out.append(dict(root=D.cells[root][6],root_master=D.cells[root][1],root_xy=list(g.ctr(D.cells[root])),root_inputs=[dict(net=n,driver=str(D.nets[n][1]))for n,ck in D.cell_in[root]if not ck],existing_buffers=[D.cells[k][6]for k in sorted(buf)],leaf_sink_pins=len(leaves),clock_sinks=sum(z['clock']for z in leaves),public_ports=ports,leaf_groups=groups,upper_groups=upper,model_buffer_count=len(groups)+len(upper),reusable_existing_buffers=len(buf),additional_buffers_if_all_reused=max(0,len(groups)+len(upper)-len(buf)),root_fanout=len(upper),max_leaf_fanout=max((z['fanout']for z in groups),default=0),max_upper_fanout=max((z['fanout']for z in upper),default=0)))
res=dict(scope='CONDITIONAL SOURCE-ONLY DATA BUF-tree pricing; upstream frame/profile not qualified; no native creation/rewire/STA/clock/FF/cycle edits',roots=out,total_existing_buffers=sum(z['reusable_existing_buffers']for z in out),model_buffer_count=sum(z['model_buffer_count']for z in out),additional_buffers_if_all_reused=sum(z['additional_buffers_if_all_reused']for z in out),leaf_sink_pins=sum(z['leaf_sink_pins']for z in out),unique_leaf_instances=len({q['instance']for z in out for a in z['leaf_groups']for q in a['members']}),holds=['Original five OR3 gates and ALL their existing inputs remain untouched; no upstream ORclone loading invented','All leaf sink pins must be resolved by exact original native ITerm, not just instance name or dump net index','Proposed buffer centres are schematic guide locations only; no native ROW/TAP/body/PG/master sizing or pairTTFF calibration','No timing gain assumed and exact B remaining-202 result is not qualified physical failure before forwarded-frame authority','No publicpins, FFs, clock/reset tree or cycles change; only identified internal non-inverting DATA BUF forest could be replaced after proof/scope'])
(P/'balanced_prep.json').write_text(json.dumps(res,indent=1)+'\n');print({k:v for k,v in res.items()if k not in['roots','holds']})
for z in out:print(z['root'],z['leaf_sink_pins'],'BUF',z['reusable_existing_buffers'],'->',z['model_buffer_count'],'rootF',z['root_fanout'],'leafF',z['max_leaf_fanout'])
