#!/usr/bin/env python3
"""Extract actual hardened-root port connectivity from the proc/opt census JSON.
Unmatched leaf pins are retained explicitly; no physical reach claim is made.
"""
import argparse,json,collections,hashlib
from pathlib import Path
LEAVES={'ot_s81_engram_'+x for x in ('mul4','chunk8','add8','norm','sum','mix_control','signed_sqrt','sigmoid')}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('hierarchical',type=Path);p.add_argument('output',type=Path);a=p.parse_args();mods=json.loads(a.hierarchical.read_text())['modules'];nodes=[];pins=[]
 def walk(name,path,mp):
  m=mods[name];hdl=m.get('attributes',{}).get('hdlname',name)
  def bit(b):return mp.get(b,path+':'+str(b)) if isinstance(b,int) else b
  if hdl in LEAVES:
   ports={k:{'direction':v['direction'],'bits':len(v['bits'])} for k,v in m['ports'].items()};clock='clk'
   nodes.append({'instance':path,'master':hdl,'clock':bit(m['ports'][clock]['bits'][0]),'ports':ports,'source_parameters':m.get('parameter_default_values',{})})
   for pn,pv in m['ports'].items():
    if pn in ('clk','arst_n'):continue
    for i,b in enumerate(pv['bits']):pins.append((bit(b),path,pn,i,pv['direction']))
   return
  for cn,c in m.get('cells',{}).items():
   if c['type'] not in mods:continue
   sm=mods[c['type']];cm={}
   for pn,pv in sm['ports'].items():
    for local,remote in zip(pv['bits'],c['connections'].get(pn,[])):cm[local]=bit(remote)
   walk(c['type'],path+'/'+cn,cm)
 top=mods['ot_s81_engram_mixq'];mp={}
 for pn,pv in top['ports'].items():
  for i,b in enumerate(pv['bits']):mp[b]=f'parent.{pn}[{i}]'
 walk('ot_s81_engram_mixq','cluster',mp)
 bynet=collections.defaultdict(list)
 for pin in pins:
  if pin[0] not in ('0','1','x','z'):bynet[pin[0]].append(pin)
 bundles=collections.defaultdict(list);unmatched=[]
 for net,pp in bynet.items():
  outputs=[x for x in pp if x[4]=='output'];inputs=[x for x in pp if x[4]=='input']
  for src in outputs:
   for dst in inputs:bundles[(src[1],src[2],dst[1],dst[2])].append([src[3],dst[3]])
  if not outputs or not inputs:
   for x in pp:unmatched.append({'instance':x[1],'port':x[2],'bit':x[3],'direction':x[4],'net':net})
 res={'hierarchical_json_sha256':hashlib.sha256(a.hierarchical.read_bytes()).hexdigest(),'scope':'Actual root port net identity after hierarchical proc/opt. Edges are not placement or timing evidence. Unmatched pins connect shell logic, parent ports or unused outputs; they must be resolved before reach closure.','root_count':len(nodes)+1,'shell':{'instance':'cluster','master':'ot_s81_engram_mixq','clock':'parent.ck[0]','note':'One additional clock-owned shell root; ports are NOT a hardened abstract.'},'roots':nodes,'bundles':[dict(source_instance=k[0],source_port=k[1],sink_instance=k[2],sink_port=k[3],bits=len(v),bit_pairs=v) for k,v in sorted(bundles.items())],'unmatched_pins':unmatched}
 a.output.write_text(json.dumps(res,indent=1)+'\n');print('ROOT_GRAPH',len(nodes)+1,'roots',len(bundles),'bundles',len(unmatched),'unmatched pins')
if __name__=='__main__':main()
