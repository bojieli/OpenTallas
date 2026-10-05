"""Offline metadata trace receipt. Never samples jobs, images, or DUT getters."""
import argparse,json
from pathlib import Path
from w17_connected_observation_model import Capture,parse_frame,feed,fulltoken_verdict

def check(lines):
    it=iter(lines);header=next(it,'').split()
    if header not in [['W17_CAUSAL_TRACE_V1','layer0','WINDOW'],['W17_CAUSAL_TRACE_V1','layer20','CKV']]:raise ValueError('unbound trace mode/stage')
    _,stage,mode=header;state=Capture();counts={}
    for line in it:
        state,events=feed(state,parse_frame(line),mode)
        for event in events:counts[event.kind]=counts.get(event.kind,0)+1
    return dict(status='TRACE_LOCAL_CONSISTENCY_ONLY',stage=stage,mode=mode,frames=state.frames,sticky_faults=state.sticky_faults,done_seen=state.done_seen,event_counts=counts,outstanding_requests=[len(s.requests) for s in state.states],pending_stage_reads=[len(s.stages) for s in state.states],physical_owner_quiescence='UNAVAILABLE',fulltoken=fulltoken_verdict([stage],{stage:state},{},False),causal_deadlines='BOUND_MISSING')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--trace',type=Path,required=True);ap.add_argument('--receipt',type=Path,required=True);a=ap.parse_args()
    if a.receipt.exists():raise FileExistsError('old receipt must remain unchanged')
    with a.trace.open() as f:result=check(f)
    with a.receipt.open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
