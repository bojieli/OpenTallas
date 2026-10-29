"""SPB0 exact reviewed bank geometry after c25c_phy_street.py, no placement/route.
usage: build_sites.py PLAN_DIR PIN_FILES_DIR ACTUAL_SPB_GRAPH.json OUT_DIR
"""
import hashlib,json,re,sys
from pathlib import Path
D,PD,GF,O=map(Path,sys.argv[1:5]);P=json.load(open(D/'die_plan.json'));G=json.load(open(GF));O.mkdir(parents=True,exist_ok=True)
t=P['partition_types']['q_spb0'];cores={c['inst']:c for c in t['hard_cores']};lk,ep=cores['u_lk_S0'],cores['u_ep_S0'];assert lk['origin_um']==[103.68,34.56]
def points(c,port):
 q=json.load(open(PD/c['pins_file']));v={}
 for p in q:
  m=re.fullmatch(re.escape(port)+r'\[(\d+)\]',p['name'])
  if m:v[int(m[1])]=[round(c['origin_um'][0]+p['x'],6),round(c['origin_um'][1]+p['y'],6)]
 return [v[i] for i in range(len(v))]
def dist(a,b):return sum(abs(x-y) for x,y in zip(a,b))
def intersects(a,b):return a[0]<b[2]-1e-8 and b[0]<a[2]-1e-8 and a[1]<b[3]-1e-8 and b[1]<a[3]-1e-8
boxes={'PHY':[103.68,0,703.728,1050],'EP':[181.44,1088.64,423.36,1486.08]}
RX=[[51.84,669.6],[51.84,1043.28],[397.44,1069.2],[440.64,1320.84]]
TX=[[155.52,1123.2],[470.88,1069.2],[786.24,1013.04],[786.24,639.36]]
entries=[];summ=[]
for inst,width,control,centres,src,dst in [('u_hbm_spb0_rx',514,2,RX,points(lk,'rx')+points(lk,'st'),points(ep,'sd_rx')+points(ep,'sd_st')),('u_hbm_spb0_tx',512,0,TX,points(ep,'sd_tx'),points(lk,'tx'))]:
 assert len(src)==len(dst)==width
 banks=[];actual=[]
 for stage,(cx,cy) in enumerate(centres):
  # Allocation envelope1.35x0.27, sitepitch0.054,rowpitch0.27,16columns; no extra epoch.
  sites=[[round(cx-10.8+(bit%16)*1.35,6),round(cy-4.32+(bit//16)*.27,6)] for bit in range(width)]
  rects=[[x,y,x+1.35,y+.27] for x,y in sites]
  assert all(not intersects(r,box) for r in rects for box in boxes.values())
  assert all(abs(x/.054-round(x/.054))<1e-6 and abs(y/.27-round(y/.27))<1e-6 for x,y in sites)
  entries.append({'instance':inst,'module':'ot_hbm_spb0_regs','width':width,'control_bits':control,'stage':stage,'flop_net':f'g_stage[{stage}].rd','cell_envelope_um':[1.35,.27],'sites_um':sites})
  banks.append(sites);actual.append([[x+.675,y+.135] for x,y in sites])
  assert all(not intersects(r,r2) for j,r in enumerate(rects) for r2 in rects[j+1:])
 hops=[]
 seq=[src]+actual+[dst]
 for a,b in zip(seq,seq[1:]):hops.append(max(dist(x,y) for x,y in zip(a,b)))
 assert max(hops)<=405,(inst,hops)
 summ.append({'instance':inst,'width':width,'stages':4,'max_per_bit_hops_um':[round(v,6) for v in hops],'maximum_um':round(max(hops),6)})
# Banks may not overlap one another across either direction.
allboxes=[]
for e in entries:
 for x,y in e['sites_um']:allboxes.append((e['instance'],e['stage'],[x,y,x+1.35,y+.27]))
for i,(a,j,r) in enumerate(allboxes):
 for b,k,z in allboxes[i+1:]:
  if (a,j)!=(b,k):assert not intersects(r,z),(a,j,b,k)
R={'schema':'opentallas.hbm.spb0_sites.v1','status':'PLAN CANDIDATE; real FF masters/rows, core clock and G2 remain required','plan_sha256':hashlib.sha256((D/'die_plan.json').read_bytes()).hexdigest(),'actual_graph_sha256':hashlib.sha256(GF.read_bytes()).hexdigest(),'physical_envelopes_um':boxes,'summary':summ,'entries':entries,'actual_new_ff_per_partition':4104,'model_extra_ff_per_partition':1028,'latency':{'actual_RTL_rx_st_added':4,'actual_RTL_tx_added':4,'model_rx_st_added':2,'model_tx_added':0}}
(O/'placement.json').write_text(json.dumps(R,indent=1)+'\n');print(json.dumps(summ,indent=1))
