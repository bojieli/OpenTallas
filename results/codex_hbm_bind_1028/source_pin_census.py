"""Source-only diagnostic before full bus/type emission finishes. Not a strict bind verdict.
usage source_pin_census.py PLAN ASBUILT MANIFEST OUT
"""
import json,sys,collections
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/die_plan'))
import bind as B
plan,yjs,manifest,out=map(Path,sys.argv[1:5]);p=json.loads(plan.read_text());ab=json.loads(manifest.read_text());
if ab.get('map_file') and not Path(ab['map_file']).is_absolute():ab['map_file']=str(manifest.parent/ab['map_file'])
p['asbuilt']=ab;b=B.Binder(p,json.loads(yjs.read_text()),plan.parent,ab.get('base',str(root)));b.map_cells();b.analyse()
rec=dict(schema='opentallas.hbm.source_pin_census.v1',counts=b.counts,tied_by_port=dict(b.tied_by_port),tied_bits=sum(b.tied_by_port.values()),errors=b.errors,n_errors=len(b.errors),note='Source-onlydiagnostic: no busconstruction/typecheck/emission;notstrictPASS',bindings=[dict(path=c.path,module=c.module,partition=b.cpart[ci],local=b.rel_of(ci),ports={k:len(v) for k,v in c.ports.items()}) for ci,c in enumerate(b.F.cells) if ci in b.cpart and not c.module.startswith('$')])
out.write_text(json.dumps(rec,indent=2)+'\n');print('sourcecensus',rec['counts'],'tied',rec['tied_bits'],'errors',len(rec['errors']),flush=True)
