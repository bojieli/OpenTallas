"""Candidate-only tapered SVC row shift and exact local reset/landing recomposition."""
import copy,json,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/die_plan'))
import schema as S,reset_tree as RT,clock_landing_plan as C
TN='svc_hi_dsdv_svc_rs__t1'
def prepare(old,path):
 new=copy.deepcopy(old);t=new['partition_types'][TN];ot=old['partition_types'][TN];report=dict(type=TN,status='PROTOTYPE_NOT_QUALIFIED',data_cycles_added=0,moved=[])
 for c in t['hard_cores']:
  if 'u_hc.' not in c['inst']:continue
  for y,dy in [(34.56,34.56),(311.04,25.92),(587.52,17.28),(864.,8.64)]:
   if abs(c['origin_um'][1]-y)<1e-5:
    before=list(c['origin_um']);c['origin_um'][1]=round(y+dy,6)
    report['moved'].append(dict(inst=c['inst'],old_um=before,new_um=c['origin_um']))
 assert len(report['moved'])==32
 moves={m['inst']:[b-a for a,b in zip(m['old_um'],m['new_um'])] for m in report['moved']}
 for tap in t['clock'].get('taps',[]):
  for inst,delta in moves.items():
   if tap.get('kind')=='core' and (tap['name']==inst or tap['name'].startswith(inst+'.')):
    tap['xy']=[round(a+b,6) for a,b in zip(tap['xy'],delta)]
 lc=t['clock']['landing_contract'];oldtree=copy.deepcopy(lc['collector_tree'])
 C.BAND_RESERVE='ring_ff';C.BAND_SPREAD=1.;C.BAND_RING='ff'
 used=[v['rect_um'] for v in lc['bands'].values() if v.get('rect_um')]
 band=C._storage_band(t,'attnh_i0',2133,used,resets=C.reset_site_rects(oldtree))
 x,y,xx,yy=band['rect_um'];reserved=[x-2.16,y-2.16,xx+2.16,yy+2.16]
 t['clock'].setdefault('keepouts_um',[]).append(reserved)
 P=S.Plan(new,path)
 before_grid=S.tap_grid(S.Plan(old,path),TN);after_grid=S.tap_grid(P,TN)
 report['grid_clock_pin_moves']=[dict(old=list(a),new=list(b)) for a,b in zip(before_grid,after_grid) if a!=b]
 tree=RT.for_type(P,TN);nodes={r['q']:r['xy'] for r in tree['relays']};nodes['rst_root_n']=tree['root']
 missing=[n for n in [lc.get('collector_root_node')]+[r.get('node') for r in lc.get('collector_children',[])] if n and n not in nodes]
 if missing:raise ValueError(f'collector node identity lost: {missing}')
 bands=lc['bands']
 if any(C._rect_overlap(band['rect_um'],r) for r in C.reset_site_rects(tree)):
  raise ValueError('recomputed reset sites still overlap reserved landing')
 band['instance']='u_cland_attnh_i0';bands['attnh_i0']=band
 report['clock_reset_keepout_um']=reserved
 lc['collector_tree']=tree
 for child in lc.get('collector_children',[]):
  if child.get('node'):child['xy_um']=copy.deepcopy(nodes[child['node']])
 taps={int(k[7:]):v for k,v in nodes.items() if k.startswith('rst_n_t')}
 for src in lc.get('collector_local_sources',[]):
  name=src['name'];src['band']=copy.deepcopy(bands[name]);xy=C._bus_xy(t,name);src['pin_xy_um']=xy
  tap=min(taps,key=lambda i:sum(abs(a-b) for a,b in zip(taps[i],xy)))
  if sum(abs(a-b) for a,b in zip(taps[tap],xy))>405:
   r=src['band']['rect_um'];xy=[(r[0]+r[2])/2,(r[1]+r[3])/2];tap=min(taps,key=lambda i:sum(abs(a-b) for a,b in zip(taps[i],xy)))
  if sum(abs(a-b) for a,b in zip(taps[tap],xy))>405:raise ValueError(f'{name}: collector source reach')
  src['tap']=tap;src['xy_um']=xy
 report.update(old_reset_depth=oldtree['depth'],new_reset_depth=tree['depth'],old_reset_nodes=len(oldtree['relays']),new_reset_nodes=len(tree['relays']),band=band,
   boundary_buses_unchanged=t['buses']==ot['buses'],clock_tap_means_unchanged=all({k:v for k,v in a.items() if k!='xy'}=={k:v for k,v in b.items() if k!='xy'} for a,b in zip(t['clock']['taps'],ot['clock']['taps'])),
   pending=['parent CTS clock endpoints regenerated from moved actual LEFs','sidecar boot-graph deadline recomposition if reset depth/topology changed','actual render and halo/reach checks','parent GEN/PLACE/GRT'])
 # A changed reset topology is always visible, never declared cycle-neutral.
 report['reset_depth_delta']=tree['depth']-oldtree['depth']
 report['max_reset_hop_um']=tree['max_hop_um']
 report['pending'].append('explicit disposition of moved R4 grid clock ports; source-preserved freeze is not legal for clk_t9/clk_t10 under this row shift')
 return new,report
if __name__=='__main__':
 p=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
 try:
  new,r=prepare(json.loads(p.read_text()),p);(out/'candidate.json').write_text(json.dumps(new,separators=(',',':'))+'\n')
  (out/'report.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r,indent=1))
 except Exception as e:
  (out/'failure.json').write_text(json.dumps(dict(error=str(e),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest()),indent=1)+'\n');raise
