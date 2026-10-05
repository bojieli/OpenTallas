"""Actual inline OLD/W2 visibility adapter sources for the enclosing owner.

No simulator, callbacks, memory store, clocks or synthetic completion authority.
Instantiate next to the existing observer; apply permits symmetrically to valid
and ready. state_client_mask is the actual state-route classifier (NC6), not an
unconditionally enabled seventh client. command_sector_granted must derive from
the installed mapper's retained exclusive sector grant; keep it through reply.
command_new_data carries only original source PATCH bytes at sector offsets,
command_byte_mask its actual byte enables. The tap merges unmodified bytes from
physical OLD, then checks the accepted NEW against that exact merge. This avoids
requiring the serialized byte handler to know OLD before its read.
Read-only state reads use command_write=0. Writes including full sectors require
an actual OLD capture under the same grant. Existing partial-write handlers
already do OLD->NEW; full writes require an added physical read, priced once.

For an ACQUIRE record the command reply follows actual write visibility/reverse;
the observer retains the event until the later ACQUIRE command. Do not await
that event in the byte RPC: the serialized source would deadlock. Drain must
combine tap.quiescent, observer.drained and actual held upstream parent receipts.
Only matching sector reverses, with actual rank/owner46/address/direction, go
here; never global W2 idle/reverse_fenced or elapsed completion. repair_busy and
local_reset pause accepted debt. Warm reset cannot drive cold por_n.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TOP='ot_gpu_qwen_kv_state_w2_tap'
def source_files(root=ROOT):
    root=Path(root)
    base=root/'rtl/model/qwen_kv_connections_20261003'
    return (base/(TOP+'.sv'), base/'ot_gpu_qwen_kv_state_observer.sv')
def observer_bindings():
    return {name:name for name in ('observe_valid','observe_ready','observe_rank',
        'observe_source_addr','observe_physical_addr','observe_owner',
        'observe_old_data','observe_new_data','observe_old_captured',
        'ACK_valid','ACK_ready','ACK_owner','ACK_physical_addr','ACK_visible','ACK_reverse')}
