#!/usr/bin/env python3
"""Publish qualified common-clock pin cuts; all existing data geometry is immutable."""
import argparse,hashlib,json,shutil
from pathlib import Path
ALIASES={'ot_hfd_coll_q3_body_core':'body','ot_hfd_coll_q3_edge_core':'edge','ot_hfd_coll_q3_vm_core':'vm','ot_hfd_coll_q2_hard_v8g__reduce':'reduce','ot_hfd_coll_q2_hard_v8g__ring_ag':'ring_ag'}
def bits(r):
 return {p['name'] if p['width']==1 else f"{p['name']}[{i}]" for p in r['clocks'] for i in range(p['width'])}
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for k in ['src','out','qualified']:ap.add_argument('--'+k,type=Path,required=True)
 a=ap.parse_args()
 if a.out.exists():raise SystemExit('output must be new')
 manifest=json.loads((a.qualified/'manifest.json').read_text());q=json.loads((a.qualified/'qualification.json').read_text())
 if q['status']!='PASS_CLOCK_ADAPTER' or q['native']['clock_bits']!=147:raise ValueError('unqualified clock adapter')
 p=json.loads((a.src/'die_plan.json').read_text());updates={};report={'release_ready':False,'clock_tree_republish_required':True,'data_cycle_delta':0,'boot_cycle_delta':0,'outline_delta_um':[0,0],'qualification':str(a.qualified),'cuts':[]}
 for tn,t in p['partition_types'].items():
  for h in t.get('hard_cores',[]):
   kind=ALIASES.get(h['module'])
   if not kind:continue
   r=manifest['cores'][kind];expected=bits(r)
   # These legacy physical cuts are aliases of the same explicitly qualified
   # native vectors. Their data aliases stay unchanged for the source bridge.
   if kind=='reduce':expected={f'clk_reduce[{i}]'for i in range(33)}
   elif kind=='ring_ag':expected={f'clk_ring[{i}]'for i in range(17)}
   old=json.loads((a.src/h['pins_file']).read_text());pins=old.get('pins',[])if isinstance(old,dict)else old
   if len({v['name']for v in pins})!=len(pins):raise ValueError('duplicate physical pin name')
   clocks=[v for v in pins if v['name']in expected];data=[v for v in pins if v['name']not in expected]
   if {v['name']for v in clocks}!=expected or len(data)!=r['nonclock_bits']:raise ValueError(f'{tn}.{h["inst"]}: interface differs from qualified bit inventory')
   if any(v['name']=='clk'for v in data):raise ValueError('data clk collision')
   primary={'body':'clk_control','edge':'arg_clk','vm':'writer_clk_rgx_ctrl','reduce':'clk_reduce[0]','ring_ag':'clk_ring[0]'}[kind]
   clk=dict(next(v for v in clocks if v['name']==primary));clk['name']='clk'
   new=data+[clk];out=dict(old,pins=new)if isinstance(old,dict)else new
   if [v for v in new if v['name']!='clk']!=data:raise ValueError('changed nonclock pins')
   name=str(Path(h['pins_file']).with_name(Path(h['pins_file']).stem+'__oneclk.json'))
   if name in updates and updates[name]!=out:raise ValueError('inconsistent common template')
   updates[name]=out;oldpath=h['pins_file'];h['pins_file']=name
   report['cuts'].append({'type':tn,'inst':h['inst'],'module':h['module'],'generated_master':r['wrapper'],'old_pins_file':oldpath,'pins_file':name,'old_clock_bits':len(clocks),'new_clock_bits':1,'selected_primary':primary,'clk_site':clk,'nonclock_bits':len(data),'nonclock_sha256_before':digest(data),'nonclock_sha256_after':digest([v for v in new if v['name']!='clk'])})
 if set(v['generated_master']for v in report['cuts'])!={r['wrapper']for r in manifest['cores'].values()}:raise ValueError('not all five qualified cuts selected')
 shutil.copytree(a.src,a.out)
 for name,x in updates.items():(a.out/name).write_text(json.dumps(x,indent=1)+'\n')
 (a.out/'die_plan.json').write_text(json.dumps(p,indent=1)+'\n');(a.out/'oneclk_pins_report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({'cuts':len(report['cuts']),'templates':len(updates),'data_cycles':0,'clock_pending':True}))
if __name__=='__main__':main()
