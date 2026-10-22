"""True TOPK input operands; expected IDs are comparison-only."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from hgi_sim.machine import topk_ids
src,layout_path,out=map(Path,sys.argv[1:4]);out.mkdir(parents=True,exist_ok=True)
layouts=json.loads(layout_path.read_text());scores=[];expected=[];bases=[];rows=[]
for layer in ('L00','L02','L14'):
 p=src/layer;metadata=json.loads((p/'records.json').read_text());rec=next(r for r in metadata['records']['0'] if r['tag']=='route.top6')
 arrays=np.load(p/'operands.npz');a=np.asarray(arrays[rec['inputs']['A']['array']],np.uint32).reshape(-1)
 o=np.asarray(arrays[rec['outputs']['O']['array']],np.uint32).reshape(-1)
 assert len(a)==384 and len(o)==6 and np.array_equal(topk_ids(a.view(np.float32),6,True),o)
 assert hashlib.sha256(a.tobytes()).hexdigest()==rec['inputs']['A']['sha256']
 scores.extend(f'{int(v):08x}'for v in a);expected.extend(f'{int(v):08x}'for v in o)
 base=layouts['L'+str(int(layer[1:]))]['index_base'];assert base%64==0 and base<65536
 bases.append(f'{base:05x}')
 rows.append(dict(layer=layer,component_input_base=0,component_output_base=base,
  input_sha256=rec['inputs']['A']['sha256'],expected_O_sha256=rec['outputs']['O']['sha256'],
  metadata_sha256=hashlib.sha256((p/'records.json').read_bytes()).hexdigest(),
  scope='True pre-operation input; controlled finite component placement; expected IDs comparison only'))
(out/'scores.mem').write_text('\n'.join(scores)+'\n');(out/'expected.mem').write_text('\n'.join(expected)+'\n');(out/'bases.mem').write_text('\n'.join(bases)+'\n')
(out/'provenance.json').write_text(json.dumps(dict(cases=rows,scope='Local CQ/shared-hub/native output proof; no upstream readiness or global dates'),indent=2)+'\n')
print('PREPARED 3 real384-score inputs; expected top6 IDs used only for comparison')
