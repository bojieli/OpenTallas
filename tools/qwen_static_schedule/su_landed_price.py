"""Opt-in measured W SU_LT capture price; never silently adopt a native view.

Receipt6576b05ca compares c4adbc1c3 to9b41881fe (already scalar+1).
This contract is separate from scalar result, CFG setup and reset timing.
It does not reschedule the public F16 frame or qualify physical clock phases.
"""
import hashlib,json
from pathlib import Path
from .calendar import ScheduleError
VARIANT='SU_LT1_HD_W1301_MU_NU4_FACE1'
RECEIPT_SHA256='682468dab3246125f775279b5f23efe7d47652f87d8c6b8c346fd673d0abd581'

def load(*,variant=None,receipt=None):
    if variant is None:
        return dict(enabled=False,capture_edges=0,scalar_capture_edges=None,
                    cfg_setup_edges=None,reset_guard_edges=None,production_bound=False)
    if variant!=VARIANT or receipt is None:
        raise ScheduleError('SU landed opt-in requires the exact measured W variant and source receipt')
    path=Path(receipt);raw=path.read_bytes();r=json.loads(raw)
    if hashlib.sha256(raw).hexdigest()!=RECEIPT_SHA256:
        raise ScheduleError('SU landed source receipt hash mismatch')
    if (r.get('schema')!='opentallas.qwen.su8_landed_timing.v1' or r.get('status')!='SOURCE_EXACT_W_FUNCTIONAL_TIMING_PASS_NOT_NATIVE_GATE' or
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
                baseline_source=r['baseline_core'],candidate_source=r['landed_candidate'],receipt_commit='6576b05ca',
                scalar_capture_edges='baseline already includes+1; price separately',cfg_setup_edges='separate boot8→10+2',reset_guard_edges='separate; unbound',
                production_bound=False,native_phase_qualified=False,apply_to_public_F16=False,
                other_unselected_contracts=dict(scalar_result_capture_edges=1,CFG_setup_edges=2,post_reset_boot_guard_edges=16,
                    source='4ec4aa5f2; CFG receipt scalar_cfg64_census_report.json; guard dv_bench2.py RESET_WARM',
                    apply_to_SU_capture_window=False,production_reset_to_epoch_bound=False))

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
