"""Extract actual selected RTL hub leaf pin links, with explicit top-to-plan names.
No pin/reach finding is relaxed. Unmatched physical names stay UNMAPPED; old content stubs are not a placement.
usage actual_hub_graph.py ASBUILT_JSON MANIFEST OUT_JSON
"""
import json,sys,collections
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/die_plan'))
import bind_elab as E
from bind import Rules
src,manifest,out=map(Path,sys.argv[1:4]);ab=json.loads(manifest.read_text())
if ab.get('map_file') and not Path(ab['map_file']).is_absolute():ab['map_file']=str(manifest.parent/ab['map_file'])
R=Rules(ab);yj=json.loads(src.read_text());F=E.flatten(yj,ab['top'],ab.get('substitute_parent',[]))
rows={};drv=collections.defaultdict(list);loads=collections.defaultdict(list)
for ci,c in enumerate(F.cells):
 p=R.part_of(c.path)
 if p not in ('NW_hub','NE_hub'):continue
 lo=R.local_of(c.path)
 # Preserve leaf-levelpath even if top prefix maps several children toonephysicalparent.
 rows[ci]=dict(path=c.path,module=c.module,partition=p,plan_instance=lo,params=c.params)
 for pn,bits in c.ports.items():
  direction=c.dirs.get(pn)
  if direction not in ('input','output'):continue
  dst=drv if direction=='output' else loads
  for bi,b in enumerate(bits):
   if isinstance(b,int):dst[b].append((ci,pn,bi))
groups=collections.defaultdict(list)
for net,ld in loads.items():
 for di,dp,db in ld:
  for si,sp,sb in drv.get(net,[]):
   if si==di:continue
   groups[(si,sp,di,dp)].append((sb,db))
edges=[]
for (si,sp,di,dp),bits in sorted(groups.items()):
 s,d=rows[si],rows[di]
 edges.append(dict(src_path=s['path'],src_partition=s['partition'],src_plan_instance=s['plan_instance'],src_module=s['module'],src_port=sp,dst_path=d['path'],dst_partition=d['partition'],dst_plan_instance=d['plan_instance'],dst_module=d['module'],dst_port=dp,width=len(bits),bit_pairs=bits))
rec=dict(schema='opentallas.hbm.actual_hub_graph.v1',source_json=str(src),manifest=str(manifest),note='ActualselectedleafRTLdirectpinlinks only; glue traversal/timing and absentnewSproducer are not invented',cells=list(rows.values()),edges=edges)
out.write_text(json.dumps(rec,separators=(',',':'))+'\n');print('actual hubcells',len(rows),'directpingroups',len(edges),flush=True)
