# Per-band TRAIN_EDGES route ages from a homes file (Q-VMWB route profile for tools/qwen_vmwb/wb_calendar.route_binding).
# Ages count added relay edges at the ideal 500 um/stage reach on actual per-bit pin pairs (+ optional routed detour);
# capture = 13-edge measured component path + relay edges on tag(tt_ctlm c-bundle -> port tiles) + rq_b.
import sys,json,copy,re,math
sys.path.insert(0,'/home/ubuntu/artifacts/globalfp/qwen/recovery-1325/recovered-source');import gfp_core as C
from pathlib import Path
import numpy as np
C.REACH=500
die=C.Die(Path('/home/ubuntu/artifacts/globalfp/qwen/structural-1417/upper-specialized-routing-capacity-source.json'));C.attach_ports(die)
hp=sys.argv[1];det=json.load(open(sys.argv[2])) if len(sys.argv)>2 else {}
m=copy.deepcopy(die.base)
for n,v in json.load(open(hp))['homes'].items():
 for k in 'xyo':m[n][k]=v[k]
def pair(bus,a,b):
 r=next(r for r in die.recs+die.ctrl if r['b']==bus);g=C.bus_geom(r,m);pts=g[4];names=[e[0] for e in r['ends']]
 i,j=names.index(a),names.index(b);L=float(np.abs(pts[i]-pts[j]).sum(-1).max())+det.get(bus,0.)
 return L,max(1,math.ceil(L/500))-1
recs={r['b']:r for r in die.recs+die.ctrl}
def worst(prefix_re,a,b):
 best=(0,0,None)
 for bus,r in recs.items():
  if re.match(prefix_re,bus) and a in [e[0] for e in r['ends']] and b in [e[0] for e in r['ends']]:
   L,e=pair(bus,a,b)
   if (e,L)>(best[1],best[0]):best=(L,e,bus)
 return best
iss=worst(r'^tt_c1__rsi_','tt_ctlm','res_train_issue')
bands=[]
for b in range(3):
 tag=worst(rf'^tt_c{b}(__|$)','tt_ctlm',f'sp_port_tiles_{b}');rq=pair(f'rq_{b}',f'sp_port_tiles_{b}',f'sp_res_ser_{b}');fo=worst(r'^rsi_','res_train_issue',f'sp_res_ser_{b}')
 bands.append({'band':b,'tag_relay_edges':tag[1],'tag_um':round(tag[0],1),'tag_worst_bus':tag[2],'rq_relay_edges':rq[1],'rq_um':round(rq[0],1),
  'tag_to_capture_edges':13+tag[1]+rq[1],'train_fanout_edges':fo[1],'fanout_um':round(fo[0],1),'fanout_worst_bus':fo[2]})
issue=iss[1]
delays=[x['tag_to_capture_edges']-issue-x['train_fanout_edges'] for x in bands]
TE=max(delays);pad=[TE-d for d in delays]
out={'schema':'opentallas.qwen.globalfp-train-edges.v1','homes':hp,'qualified':False,'reach_um':500,
 'tag_to_issue_edges':issue,'tag_to_issue_um':round(iss[0],1),'tag_to_issue_bus':iss[2],'bands':bands,
 'unpadded_delays':delays,'TRAIN_EDGES':TE,'fanout_pad_edges_per_band':pad,
 'binding_note':'wb_calendar.route_binding requires equal delays; bands with pad>0 need that many explicit extra fanout relay edges (train_fanout_edges += pad) so one TRAIN_EDGES aligns all captures.',
 'scope':'Ideal 500 um geometric relay ages on actual pin pairs; measured reach, relay frames and native clocks remain OPEN.'}
for x,p in zip(bands,pad):x['train_fanout_edges_padded']=x['train_fanout_edges']+p
print(json.dumps(out,indent=1))
