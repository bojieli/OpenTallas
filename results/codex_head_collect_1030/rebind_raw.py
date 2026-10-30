#!/usr/bin/env python3
import json,re,sys
from pathlib import Path
plan,rtl,placement=map(Path,sys.argv[1:4]);p=json.loads(plan.read_text());t=p['partition_types']['hd_serdes'];text=rtl.read_text();sites={}
for k,x,y,tag in re.findall(r'^rtr_place (rst_rl_\d+) \{[^\n]*\} ([\d.]+) ([\d.]+) (\S+)$',placement.read_text(),re.M):sites[k]=(float(x),float(y),tag)
raw={}
for inst,pins in re.findall(r'\bot_dp_rrelay\s+(u_rrl_\d+)\s*\(([^;]+)\);',text):
 q=re.search(r'\.q\((\w+)\)',pins).group(1)
 if q in sites:raw[inst]=(q,*sites[q])
report=[]
for row in t['reset_start_raw_exports']:
 x,y=row['xy_um'];matches=[(i,v) for i,v in raw.items() if abs(v[1]-x)<.02 and abs(v[2]-y)<.02]
 if len(matches)!=1:raise ValueError(f"{row['port']}: need unique actual raw at recorded site, got {matches}")
 i,(net,rx,ry,tag)=matches[0];report.append(dict(port=row['port'],old_instance=row['instance'],old_net=row['net'],new_instance=i,new_net=net,xy_um=row['xy_um'],actual_site_um=[rx,ry],actual_depth=int(re.search(r'(\d+)$',tag)[1]),kind='actual ot_dp_rrelay; no gate',added_cycles=0))
 row.update(instance=i,net=net)
 for pin in t.get('clock',{}).get('landing_contract',{}).get('pins',[]):
  if pin['name']==row['port']:
   pin.update(source_instance=i,source_net=net,source_registered=True)
   if pin.get('source_output_pin')=='export_q':
    pin.update(source_net=row['port'],source_copy_from_net=net)
plan.with_name('source_plan_rebound.json').write_text(json.dumps(p,indent=1)+'\n');plan.with_name('raw_alias_rebind.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report))
