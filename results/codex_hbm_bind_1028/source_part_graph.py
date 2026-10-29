"""Dump selected-source mapped leaf/port bits before transport construction.
Usage: source_part_graph.py PLAN ASBUILT MANIFEST OUT PART [PART ...]
"""
from pathlib import Path
import collections,json,sys
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/die_plan'))
import bind as M
plan,asbuilt,manifest,out=map(Path,sys.argv[1:5]);parts=set(sys.argv[5:])
p=json.loads(plan.read_text());ab=json.loads(manifest.read_text())
if ab.get('map_file') and not Path(ab['map_file']).is_absolute():ab['map_file']=str(manifest.parent/ab['map_file'])
p['asbuilt']=ab;b=M.Binder(p,json.loads(asbuilt.read_text()),plan.parent,ab['base']);b.map_cells()
def source(bit):
 d=b.G.source(bit)
 if d[0]=='pin':
  c=b.F.cells[d[1]];part=b.cpart.get(d[1])
  return dict(kind='pin',path=c.path,module=c.module,partition=part,
              plan_instance=b.rel_of(d[1]) if part else None,port=d[2],bit=d[3],stages=d[4])
 if d[0] in ('or','and'):return dict(kind=d[0],inputs=[desc(x) for x in d[1]],stages=d[2])
 return dict(kind=d[0],detail=list(d[1:]))
def desc(d):
 if d[0]=='pin':
  c=b.F.cells[d[1]];part=b.cpart.get(d[1])
  return dict(kind='pin',path=c.path,module=c.module,partition=part,
              plan_instance=b.rel_of(d[1]) if part else None,port=d[2],bit=d[3],stages=d[4])
 if d[0] in ('or','and'):return dict(kind=d[0],inputs=[desc(x) for x in d[1]],stages=d[2])
 return dict(kind=d[0],detail=list(d[1:]))
rows=[]
for ci,part in sorted(b.cpart.items()):
 if part not in parts:continue
 c=b.F.cells[ci]
 ports={}
 for pn,bits in c.ports.items():
  direction=b.G.dirs[ci].get(pn)
  ports[pn]=dict(direction=direction,width=len(bits),bits=bits,
                 sources=[source(bit) for bit in bits] if direction=='input' else [])
 rows.append(dict(path=c.path,module=c.module,kind=b.G.kind[ci],partition=part,
                  plan_instance=b.rel_of(ci),params=c.params,ports=ports))
rec=dict(schema='opentallas.hbm.selected_source_part_graph.v1',source_json=str(asbuilt),manifest=str(manifest),
         requested_parts=sorted(parts),cells=rows,source_errors=b.errors,
         status='SOURCE_BIT_GRAPH_NO_GEOMETRY_OR_CA_ADOPTION',
         note='Graph includes selected instance substitutions and exact transport source traces. Clock/reset descriptors are not data edges.')
out.write_text(json.dumps(rec,separators=(',',':'))+'\n')
print('selected source part graph',len(rows),'cells',collections.Counter(r['kind'] for r in rows),flush=True)
