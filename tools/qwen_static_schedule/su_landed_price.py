"""Opt-in measured W SU_LT capture price; never silently adopt a native view.

Receipt5753e895b compares c4adbc1c3 to9b41881fe (already scalar+1).
This contract is separate from scalar result, CFG setup and reset timing.
It does not reschedule the public F16 frame or qualify physical clock phases.
"""
import hashlib,json
from pathlib import Path
from .calendar import ScheduleError
VARIANT='SU_LT1_HD_W1301_MU_NU4_FACE1'
RECEIPT_SHA256='02a53ace89060f967298882e48ea9fa04a0af7960a52a5906f2ecf1e2a4b2085'

def load(*,variant=None,receipt=None):
    if variant is None:
        return dict(enabled=False,capture_edges=0,scalar_capture_edges=None,
                    cfg_setup_edges=None,reset_guard_edges=None,production_bound=False)
    if variant!=VARIANT or receipt is None:
        raise ScheduleError('SU landed opt-in requires the exact measured W variant and source receipt')
    path=Path(receipt);raw=path.read_bytes();r=json.loads(raw)
    if hashlib.sha256(raw).hexdigest()!=RECEIPT_SHA256:
        raise ScheduleError('SU landed source receipt hash mismatch')
    if (r.get('status')!='SOURCE_EXACT_W_FUNCTIONAL_TIMING_PASS_NOT_NATIVE_GATE' or
        r.get('baseline_core')!='9b41881fe' or r.get('landed_candidate')!='c4adbc1c3' or
        not r.get('input_events_normalized_exact')):
        raise ScheduleError('foreign/unqualified SU landed timing receipt')
    ports=r.get('ports',{})
    for name,count,delta in [('S0DD',118,6),('S1SD',7,6),('S1E',46,0),('S0ST',1,0),('S1ST',1,0),('S0AG',1,0)]:
        p=ports.get(name,{})
        if p.get('words')!=count or p.get('delta_edges')!=delta or not p.get('all_values_and_order_exact'):
            raise ScheduleError(f'SU landed receipt missing actual {name} capture witness')
    budget=r.get('edge_budget',{})
    if budget!=dict(issue_control=1,read_roundtrip=4,result_return=1,total=6):
        raise ScheduleError('SU landed timing decomposition differs from measured source')
    return dict(enabled=True,variant=variant,capture_edges=budget['total'],source_receipt_sha256=hashlib.sha256(raw).hexdigest(),
                baseline_source=r['baseline_core'],candidate_source=r['landed_candidate'],receipt_commit='5753e895b',
                scalar_capture_edges='baseline already includes+1; price separately',cfg_setup_edges='separate boot8→10+2',reset_guard_edges='separate; unbound',
                production_bound=False,native_phase_qualified=False,apply_to_public_F16=False)

def capture_window(*,issue,baseline_last,span,contract):
    """Reserve a measured result stream; baseline issue reference/span retained.

    Callers must supply the actual selected SU op's baseline result window.
    This function never shifts issue, status, gather or unrelated architectures.
    """
    if type(span) is not int or span<1 or baseline_last<span-1:
        raise ScheduleError('invalid baseline SU capture interval')
    delta=contract['capture_edges']
    return dict(issue=issue,first=issue+baseline_last-span+1+delta,last=issue+baseline_last+delta,
                span=span,su_landed_added_edges=delta)
