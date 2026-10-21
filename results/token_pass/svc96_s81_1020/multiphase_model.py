"""Opt-in two-phase a_proj lowering MODEL; never an adopted die programme.

Uses the real frame_programme allocator on all 112 four-row chunks. Phase zero
contains rows 0..383 on all 96 frames. Phase one contains rows 384..447 on the
last 16 frames (same wkv tensor); other frames have no phase-one work. Each
slice's participating rows are contiguous within each phase, so a prospective
CAP descriptor can name exactly its produced rows, with no sparse-row mask.
"""
import hashlib
import json
import os
from pathlib import Path
from multiprocessing import Pool
import sys

D = Path(__file__).resolve().parent
for k, v in dict(OT_XS_QPAIRS='12', OT_XS_PAIR_ROTATE='0', OT_XS_GU_MERGE='1',
                 OT_XS_TOPO='1', OT_XS_PROP='1', OT_XS_APROJ_TOPO='1',
                 OT_XS_APROJ_RANK_TAGS='1', OT_XS_COMPACT_TAILS='0',
                 OT_XS_KSLOT='1', PYTHONDONTWRITEBYTECODE='1').items():
    os.environ[k] = v
sys.path.insert(0, str(D))
import capacity96 as C
import lower_xs as LX

DIE = '/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'
FIX = '/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0'

def lower(item):
    fx = LX.load_fixture(FIX)
    mats, indices = LX.frame_mats(fx, item['rank_rows'])
    assert len(mats) == 1 and mats[0].rows == 4
    field, phase, plan, qa, q, bf = LX.frame_programme(
        item['master'], item['lk'], mats, fx['x'], iters=4000,
        rank_rows=item['rank_rows'])
    rank_plan = LX.rank_plan(plan | {'rows_vals': {}}, item['rank_rows'])
    assert len(rank_plan['ret']) == plan['ret_words']
    return item | dict(golden_indices=indices, tensor=mats[0].name,
                       faults=plan['faults'], ret_words=plan['ret_words'],
                       ret_last=max(w[0] for w in plan['ret']),
                       stream_words=phase['nbeat'], rom_fill=list(map(int, field.fill)),
                       physical_pairs=qa, rank_ret=rank_plan['ret'])

def main():
    assert os.environ.get('OT_S81_SERVICE96_MULTIPHASE_MODEL') == '1', 'opt-in model only'
    die = C.actual96(DIE)
    slices = sorted(die.slices(), key=lambda s: LX.slice_index(die, s))
    frames = [(s, f) for s in slices for f in die.frames_of(s)]
    assert len(frames) == 96
    tasks = []
    for phase in (0, 1):
        active = frames if phase == 0 else frames[-16:]
        first = 0 if phase == 0 else 384
        for i, (sl, f) in enumerate(active):
            tasks.append(dict(phase=phase, frame=f, slice=sl,
                              master=die.inst[f]['master'], lk=die.strap(f, 'lk'),
                              rank_rows=list(range(first + 4*i, first + 4*i + 4))))
    rows = [r for t in tasks for r in t['rank_rows']]
    assert sorted(rows) == list(range(448)) and len(set(rows)) == 448
    descriptors = []
    for phase in (0, 1):
        for sl in slices:
            rs = [r for t in tasks if t['phase'] == phase and t['slice'] == sl for r in t['rank_rows']]
            if not rs:
                continue
            assert rs == list(range(rs[0], rs[0]+len(rs)))
            descriptors.append(dict(phase=phase, slice=sl, rank_base=rs[0], count=len(rs),
                                    flags='GO epoch, explicit phase-tag lifetime required',
                                    admitted=False))
    with Pool(16) as pool:
        lowered = pool.map(lower, tasks)
    perframe = {}
    for t in lowered:
        perframe.setdefault(t['frame'], []).append(t)
    maxfill = max(max(sum((t['rom_fill'][k] for t in ts), 0) for k in range(len(ts[0]['rom_fill'])))
                  for ts in perframe.values())
    summary = dict(scope='OPT_IN_MULTIPHASE_LOWERING_MODEL_NOT_A_DIE_RESULT',
                   inventory_sha256=C.inventory_hash, frames=96, phases=2,
                   active_frames=[96,16], chunks=len(tasks), rank_rows=448,
                   faults=sum(t['faults'] for t in lowered),
                   max_a_proj_only_rom_fill=maxfill,
                   max_phase_return_last=max(t['ret_last'] for t in lowered),
                   measured_phase_budget=361, added_token_ar_cycles=40*361,
                   added_token_verify_position_cycles=6*40*361,
                   full_stage_rom_capacity='OWED: append second phase to actual dense+expert fields',
                   static_calendar='OWED: price phase GO/stream/release and CAP/consumer age',
                   cap_descriptors=descriptors, lowered=lowered)
    (D/'multiphase_model.json').write_text(json.dumps(summary, indent=1)+'\n')
    print('MULTIPHASE_MODEL',json.dumps({k:v for k,v in summary.items() if k not in ('lowered','cap_descriptors')}),flush=True)

if __name__ == '__main__':
    main()
