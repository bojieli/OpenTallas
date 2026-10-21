import subprocess,json,hashlib,math,sys
from pathlib import Path
r=Path(__file__).resolve().parents[5];sys.path.insert(0,str(r/'tools'));import check_macro_track_alignment as C
out=r/'results/arch/s81_die72_1021/g9_assembly/ctrl_first_closed';out.mkdir(exist_ok=True)
ref='bbc9c9b13';source='22595e8993ac83c9293f59ffb5fe6b4d7914589c';vp='physical/ref_tile/s81ctrl_rg3s/views/dsfd_ctrl_rg3';get=lambda f,p:subprocess.check_output(['git','-C',str(r),'show',f+':'+p])
spec=json.loads(get(ref,'physical/ref_tile/s81ctrl_rg3s/spec.json'));assert spec['params']=={}and spec['outline']['w']==388.8 and spec['outline']['h']==324
sources={p:hashlib.sha256(get(source,p)).hexdigest()for p in spec['sources']};assert all(hashlib.sha256(get('HEAD',p)).hexdigest()==h for p,h in sources.items())
raw=get(ref,vp+'/dsfd_ctrl_rg3.lef');m=C.parse_lef(raw.decode())[0];assert(m['W'],m['H'])==(388800,324000)
constraints={'x':[],'y':[]}
for pin in m['pins']:
 if pin['use']in('POWER','GROUND'):continue
 choices={}
 for lay,rr in pin['rects']:
  if lay not in C.ASAP7_TRACKS_NM:continue
  axis='y'if C.ASAP7_LAYERS[lay][0]=='H'else'x';P,T=C.track_residues(C.ASAP7_TRACKS_NM[lay],axis);cc=rr[1]+rr[3]if axis=='y'else rr[0]+rr[2];legal={((2*t-cc)//2)%P for t in T if(2*t-cc)%2==0};choices.setdefault((axis,lay,P),set()).update(legal)
 for(axis,lay,P),a in choices.items():constraints[axis].append((P,a))
phase={}
for axis,cs in constraints.items():
 P=math.lcm(*(p for p,_ in cs));a=set(range(P))
 for p,v in cs:a={z for z in a if z%p in v}
 assert a;phase[axis]=(P,sorted(a))
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--plan',required=True);args=ap.parse_args();plan=json.load(open(args.plan));rows=[]
for b in plan['blocks']:
 if b['kind']!='ctrl':continue
 old=[b['x'],b['y']];new=[]
 for axis,value in zip(['x','y'],old):
  p,res=phase[axis];v=round(value*1000);candidates=[v+((a-v)%p)+n*p for a in res for n in[-1,0]];new.append(min(candidates,key=lambda x:(abs(x-v),x))/1000)
 before=C.check_placement(m,'R0',round(old[0]*1000),round(old[1]*1000));after=C.check_placement(m,'R0',round(new[0]*1000),round(new[1]*1000));assert not sum(v['offtrack']for v in after['layers'].values())
 rows.append({'instance':b['name'],'old_um':old,'candidate_um':new,'delta_nm':[round((n-o)*1000)for n,o in zip(new,old)],'actual_before':before,'candidate_after':after})
assert len(rows)==16
files={p:hashlib.sha256(get(ref,vp+'/'+p)).hexdigest()for p in['dsfd_ctrl_rg3.lef','dsfd_ctrl_rg3_tt.lib','dsfd_ctrl_rg3_ff.lib','dsfd_ctrl_rg3_ss.lib','insertion.json','abstract.json','child_lint.json']}
record=json.loads(get(ref,'results/closure_loop/s81ctrl_rg3s-rg3sx-22595e899/verdict.json'));assert record['status']=='CLOSED'
packet={'record':ref,'source_ref':source,'module':'dsfd_ctrl_rg3','params':{},'defines':spec['defines'],'outline_um':[388.8,324],'view':vp,'source_sha256':sources,'view_sha256':files,'closed_metrics':{k:record['metrics'][k]for k in ['ss_ps','ff_ps','drc','setup_corner','ss_sensitivity_ps']},'master_lattice':phase,'placements':rows,'scope':'ExactconfiguredCLOSED FB successor; no defaultG8 hardwarealias. Allactualwholehardview signalpins checked perinstance; candidatecoordinateadjustments are source-model only pendingplanapplication/fullcorridor andpeerPHY check.','reset_contract':'S81CTRL_NATIVE32 usesG12 copies andsrbank/hrbank resetdistribution release+1 localclk/ckh edge vsdefaultG8; derive diebootdates, no blanket runtimecycle','clock_contract':'clk core root; ckh peerPHYroot; ck_o forwardscoreclk; fullactualview/sourceclockroles preserved'}
(out/'binding.json').write_text(json.dumps(packet,indent=1)+'\n');print('CTRL_CLOSED',packet['closed_metrics'],'phase',phase,'deltas',[(x['instance'],x['delta_nm'])for x in rows])
