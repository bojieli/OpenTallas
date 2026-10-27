"""Reconstruct a reviewed E2/E6 placement successor from its pinned parent kit.
Only the coherent S-face capture-bank sites/orientations change; RTL, pins,
constraints, clocks and cycle counts are inherited unchanged.
"""
import hashlib,json,sys
from pathlib import Path
k=Path(sys.argv[1]);e=int(sys.argv[2]);commit=sys.argv[3];assert e in (2,6)
hook=Path(__file__).with_name('head_face_reach_orient.tcl').read_bytes();(k/'head_face_reach_orient.tcl').write_bytes(hook)
parent=json.load(open(k/'freeze.json'));old=parent['kit_hash'];oldsrc=parent['source_commit'];front=1 if e==2 else 3
source=f'\nset SOURCE_FRONT u_g_front_{front}_u_front\nsource /work/head_face_reach_orient.tcl\n'
p=k/'face_flops_release.tcl'
if 'source /work/head_face_reach_orient.tcl' not in p.read_text():p.write_text(p.read_text()+source)
key=(old+'\0'+source).encode()+hook
parent.update(kit_hash=hashlib.sha256(key).hexdigest()[:16],source_commit=commit)
parent['placement_successor']=dict(parent_source=oldsrc,parent_kit_hash=old,hook_sha256=hashlib.sha256(hook).hexdigest(),moved_captures=16,target_row_orientation=True,cycles_added=0,geom_ref=f'KV-CORES-CODEX E{e} final')
(k/'freeze.json').write_text(json.dumps(parent,indent=1)+'\n')
print(parent['kit_hash'])
