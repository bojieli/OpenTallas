import hashlib,json,subprocess,itertools
from pathlib import Path
root=Path('/home/ubuntu/OpenTallas-review-dewey-owner-r3');out=Path('/tmp/review-dewey-owner-r3')
files=['rtl/gpu/ot_gpu_rf_service.sv','rtl/gpu/ot_gpu_rf_visibility_fence.sv','rtl/gpu/ot_gpu_full_sm_service.sv','rtl/gpu/ot_gpu_hbm_rf_shared_context.sv','tools/h4_hbm_atomic_source_g0.py']
sources={p:(root/p).read_text()for p in files};rf=sources[files[0]];fence=sources[files[1]];parent=sources[files[2]]
for x in ['output reg ack_valid, input wire ack_ready','!read_pending && !rsp_valid && !ack_valid','if(write_go) begin ack_valid<=1','ack_valid<=0','.w_ce_in(write_go && wr_addr[8:7]==p)']:
 assert x in rf,x
assert rf.count('.w_ce_in(write_go && wr_addr[8:7]==p)')==2
for x in ['vector_ACK_visible=rst_n && pending && host_ack_valid','vector_ACK_epoch=epoch','host_ack_ready=rst_n && pending && ack_retire_enable','pending<=0','epoch<=0']:
 assert x in fence,x
assert '.clk(clk),.rst_n(rst_n)'in parent and 'host_ack_valid=idle && wack'in parent
comb=[]
for reset,pending,ack in itertools.product([False,True],repeat=3):
 comb.append(dict(rst_n=reset,local_pending=pending,bare_ACK_valid=ack,vector_visible=reset and pending and ack,wire_epoch_present=False))
r=dict(schema='R3_RF_BARE_ACK_SOURCE_AUDIT_R1',source_sha256={p:hashlib.sha256(s.encode()).hexdigest()for p,s in sources.items()},source_equations_truth_table=comb,RF_ACK_identity='NONE: only valid/ready ports; one outstanding slot held until ACK consumed',visibility_epoch='LOCAL retained operation epoch, not RFACK-carried or independently authenticated epoch',functional_both_copy_basis='same write_go/page/row/data/mask drive two SRAM instances; behavioral posedge writes provide functional basis only',conditional_source_guard='An old RF ACK held valid makes RF idle false and host_wr_ready false, preventing new write acceptance. Common rst_n clears RF ack_valid and fence pending/epoch. This conditional direct synchronous source reasoning does not prove reset/CDC join installed in production.',stale_external_ACK_counterexample='If local pending is true and a stale bare host_ack_valid arrives from an unqualified external transport, vector_ACK_visible is true and outputepoch equals current localepoch; fence has no wire identity to reject it.',DrainGate='Requires individual ready ports and no held ACK/response/SIMD/scratch sinks before owner admission; these tests feed synthetic per-port pins. No reset method/epoch certificate or actual production pin trace bound.',R3_software_tokens='SHA context tags select retained owner/child/sourcecommand; they are not ACK wire fields. Duplicate/stale token tests exercise ledger only.',actual_reset_duplicate_stale_RF_trace_bound=False,CDC_reset_epochs_bound=False,samecycle_old_ACK_exclusion_production_bound=False,contextual_SS_macro_clock_to_Q_write_visibility='UNKNOWN_REQUIRED',physical_tick_credit=False,source_changed=False,hardware_qualified=False)
(out/'rf_ACK_source_audit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
