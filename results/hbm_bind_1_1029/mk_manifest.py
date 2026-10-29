# Build HBM-BIND-1 candidate B1 manifest = Codex native_cones_r2 manifest + SU ownership r3 (map parts + compose with FF fractures)
import json,sys,hashlib
from pathlib import Path
C=Path('/srv/opentallas-scratch2/claude/codex-hbm-bind-0300'); R=Path(sys.argv[1]); R.mkdir(exist_ok=True)
a=json.loads((C/'native_cones_r2/asbuilt.json').read_text())
m=json.loads(Path(a['map_file']).read_text())
o=json.loads((C/'su_ownership_r3/ownership.json').read_text())
n0=len(m['parts']); m['parts'].update(o['source_map']['parts'])
extra=json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv)>2 else {}
m['parts'].update(extra.get('parts',{}))
(R/'map_b.json').write_text(json.dumps(m))
comp=json.loads((C/'su_ownership_r3/compose_proposal.json').read_text())
(R/'compose_b.json').write_text(json.dumps(comp))
a['map_file']=str(R/'map_b.json'); a['compose']=str(R/'compose_b.json')
a['note']='HBM-BIND-1 B: '+a['note']
(R/'asbuilt_b.json').write_text(json.dumps(a,indent=1))
print('map parts',n0,'->',len(m['parts']),'compose cores',len(comp['cores']),'splits',len(comp.get('primitive_splits',[])))
