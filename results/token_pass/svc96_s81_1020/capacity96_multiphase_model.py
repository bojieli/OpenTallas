"""Opt-in successor allocator MODEL, first phase + prospective second-phase ROM.

Calls the unchanged real multi-op allocator with a four-row phase-zero map.
Adds the actual isolated second-phase ROM allocation to the matching physical
pairs. It does not emit a deployable combined programme or admit CAP/gather.
"""
import json
import os
from pathlib import Path
import sys

D = Path(__file__).resolve().parent
assert os.environ.get('OT_S81_SERVICE96_MULTIPHASE_MODEL') == '1', 'opt-in model only'
sys.path.insert(0,str(D))
import capacity96 as C
import lower_xs as LX
import xs_capacity as XC

model = json.loads((D/'multiphase_model.json').read_text())
items = model['lowered']
first = {x['frame']:x for x in items if x['phase']==0}
second = {x['frame']:x for x in items if x['phase']==1}
original_alloc = XC.frame_alloc
original_signature = XC.frame_signature

def signature(die, frame, fixd, spec):
    base = original_signature(die, frame, fixd, spec)
    extra = second.get(frame) if spec.get('dense_layer') is not None else None
    return base + json.dumps(None if extra is None else
                            [extra['physical_pairs'], extra['rom_fill']],sort_keys=True)

XC.frame_signature = signature

def placement(die, sl, fx=None):
    return LX.slice_index(die,sl), [dict(frame=f,master=die.inst[f]['master'],lk=die.strap(f,'lk'),
                                        rows=first[f]['rank_rows']) for f in die.frames_of(sl)]

LX.placement = placement

def alloc(die, frame, fixd, spec):
    rec = original_alloc(die,frame,fixd,spec)
    if spec.get('dense_layer') is not None and frame in second:
        extra = second[frame]
        # The field's q slots are the physical pairs in rec.pairs. The isolated
        # frame_programme reports its own physical pair order explicitly.
        bypair = dict(zip(extra['physical_pairs'], extra['rom_fill']))
        import frame_bench as FB
        import xs_place as XP
        # Original rec serialises q_fill in the stable qa field-slot order.
        # Reproduce that order using phase zero's actual pair list, then the
        # remaining native pairs, exactly as compile_frame does.
        qa = list(first[frame]['physical_pairs'])
        q,_ = FB.frame_pairs(LX.base_master(die.inst[frame]['master']))
        qa += [p for p in q if p not in qa]
        assert len(qa)==len(rec['q_fill'])==12
        for k, pair in enumerate(qa):
            rec['q_fill'][k] += bypair.get(pair,0)
            rec['q_fill_ub'][k] += bypair.get(pair,0)
        rec['nphases'] += 1
        # Complete image packing/stream dedup is deliberately not fabricated.
        rec['multiphase_model_obligation'] = 'append/pack actual phase, cfg rank tags, CAP and GO calendar owed'
    return rec

XC.frame_alloc = alloc
if __name__ == '__main__':
    sys.exit(XC.main())
