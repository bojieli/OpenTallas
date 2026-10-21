"""Exact structural frame-signature inclusion test; no evidence inheritance on miss.

This tests whether an exact allocator record for the original inventory contains
every frame class required by split112. Source and environment identity must be
checked separately before any result can be transported. Misses remain open.
"""
import hashlib
import json
from multiprocessing import Pool
from pathlib import Path
import sys

D=Path(__file__).resolve().parent
sys.path.insert(0,str(D))
import capacity112 as C
import xs_capacity as XC
import xs_topo as TP

DIE='/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'
FIX='/srv/opentallas-scratch/claude/s81-calpipe/fixtures'

def worker(task):
    variant,frame,spec=task
    die=C.ORIGINAL(DIE) if variant=='original122' else C.actual112(DIE)
    TP.set_from_die(die)
    _,_,fix=XC.spec_ops(spec)
    sig=XC.frame_signature(die,frame,str(Path(FIX)/fix),spec)
    return variant,frame,hashlib.sha256(sig.encode()).hexdigest()

def main():
    spec=json.loads(Path(sys.argv[1]).read_text())
    if isinstance(spec,list):
        assert len(spec)==1
        spec=spec[0]
    old=C.ORIGINAL(DIE)
    of=[f for sl in sorted(old.slices()) for f in old.frames_of(sl)]
    new=C.actual112(DIE)
    nf=[f for sl in sorted(new.slices()) for f in new.frames_of(sl)]
    with Pool(32) as pool:
        rows=pool.map(worker,[(v,f,spec) for v,fs in [('original122',of),('split112',nf)] for f in fs])
    oldmap={sig:f for v,f,sig in rows if v=='original122'}
    mappings=[dict(frame=f,signature=sig,old_representative=oldmap.get(sig))
              for v,f,sig in rows if v=='split112']
    out=dict(scope='STRUCTURAL_SIGNATURE_INCLUSION_ONLY',spec=spec,
             original_frames=len(of),candidate_frames=len(nf),
             original_classes=len(oldmap),candidate_classes=len({r['signature'] for r in mappings}),
             matched=sum(r['old_representative'] is not None for r in mappings),
             missing=[r for r in mappings if r['old_representative'] is None],mappings=mappings,
             result='INCLUDED' if all(r['old_representative'] is not None for r in mappings) else 'MISSING')
    (D/f"transport_{spec['id']}.json").write_text(json.dumps(out,indent=1)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('mappings','missing')}),flush=True)

if __name__=='__main__':
    main()
