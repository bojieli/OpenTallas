"""Causal failures for the full production80-beat row/owner/lifetime map."""
import copy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from layer_prog import final_ffn as F


def reject(label, operation):
    try:
        operation()
    except ValueError as e:
        print('EXPECTED_REJECT', label, str(e))
        return
    raise AssertionError('accepted ' + label)


moves = [r for rank in range(4) for r in F.transfers(rank)]
assert F.verify_moves(moves)
for field, change in [('leaf', lambda x: (x + 1) % 5), ('row', lambda x: x + 2),
                      ('source_row', lambda x: x + 16), ('expert', lambda x: (x + 1) % 7)]:
    mutant = copy.deepcopy(moves)
    mutant[0][field] = change(mutant[0][field])
    reject('changed_' + field, lambda: F.verify_moves(mutant))
reject('missing', lambda: F.verify_moves(moves[:-1]))
reject('duplicate', lambda: F.verify_moves(moves + moves[:1]))
reject('live_gain', lambda: F.check_lease([dict(first=0,last=100,row0=320,row1=336,consumer='GAIN')], 50, 200))
reject('live_capture', lambda: F.check_lease([dict(first=0,last=100,row0=128,row1=144,consumer='prior owner')],50,200))
for sid in range(16):
    for leaf in range(5):
        subset = [r for r in moves if r['sid'] == sid and r['leaf'] == leaf]
        assert len(subset) == 56
        binding = dict(rank=(5*sid+leaf)//20,arrivals=[dict(expert=r['expert'],row=r['row'],cycle=i) for i,r in enumerate(subset)],
                       leases=[],combine_issue=56,post_issue=159,post_end=230)
        program = F.local_program(sid,leaf,binding)
        assert program['beat'] == 5*sid+leaf
        assert (program['templates'][1][1] >> (26+14)) & 1023 == 448
        assert F.commands(sid,leaf)['pre'] == 1008
        bad = dict(binding,post_issue=158)
        reject(f'early_POST_{sid}_{leaf}',lambda: F.local_program(sid,leaf,bad))
print('FINAL_FFN_MAP_PASS pairs=4480 beats=80 arrivals_per_beat=56 negatives=88')
gather = F.broadcasts()
assert len(gather) == 480 and sum(r['words']*4 for r in gather) == 61440
assert all(r['source_rank'] != r['destination_rank'] for r in gather)
assert len({(r['destination_rank'],r['beat'],r['row']) for r in gather}) == 480
print('FINAL_FFN_ALLGATHER_MAP_PASS rd_beats=480 bytes=61440 destination_ranks=4')
from layer_prog import lower_vpx
class Die:
    def slices(self):
        return {'u_s_0N':{'sid':0}}
arrivals=[dict(expert=r['expert'],row=r['row'],cycle=i) for i,r in enumerate(moves) if r['beat']==0]
latest=max(r['cycle'] for r in arrivals)
ctx=dict(slice='u_s_0N',leaf=0,final_ffn=dict(rank=0,arrivals=arrivals,leases=[],
         combine_issue=latest+1,post_issue=latest+104,post_end=latest+180))
for op in ('ffn.combine_allreduce','ffn.hc_post'):
    lowered=lower_vpx.lower(Die(),dict(op=op),ctx)
    assert lowered['status']=='PARTIAL' and lowered['rows']==[] and len(lowered['templates'])==1
    assert lowered['pending_leaf_program']['cycle_basis']=='VP c_v input pin'
print('FINAL_FFN_LOWERING_PASS guarded_templates=2 unreserved_calendar_rows=0')
