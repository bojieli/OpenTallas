"""Generate a bounded preparation record. No source generation, RTL or build."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_plan():
    binding_path = ROOT / 'results/rtl/w17_window_fault_recovery_20261001/source_binding.json'
    binding = json.loads(binding_path.read_text())
    pins = {p['path']: p['sha256'] for p in binding['source_pins']}
    uarch = ROOT / 'tools/uarch_model.py'
    text = uarch.read_text()
    assert 'DFF_UM2 = 0.2916' in text and 'mux_bits * 0.2 + 512' in text
    counts = {'backend_read_counts':32*4, 'backend_unissued_write_counts':32*2,
              'backend_visibility_watermark':64+1,
              'source_controller':16, 'accepted_block_intent':3}
    storage = sum(counts.values())
    muxbits = 192+64
    area = storage * .2916 + muxbits * .2 + 512
    modifications = {
      'window_prefetch_recovery.sv': {
        'from':binding['epoch9_candidate'],
        'changes':['OPT_RECOVERY=0 default; preserve healthy request/read arithmetic and scale-last order.',
          'Freeze producer/prefetch/prime admission on recovery; suppress row/stage publication while faulted. Retain fault cause until commit.',
          'Continue exact pending identity retirement while faulted with discard instead of stage write; poison data may retire a correctly identified transport delivery, invalid epoch/sector/beat or duplicate never releases another identity.',
          'Retain pre-fault accepted block intent: selected policy DRAIN both WC and WS rather than implementing cancellation. Allow only this existing continuation; no new blk admission. Same-edge grants are accepted first.',
          'Use existing issued/received masks and pending register; no per-entry serial or lease added to request tag. Fence violation locks restart until external whole-domain intervention.',
          'Clear/rebuild invalid publication and advance epoch only after fresh closed-provider ACK; owner-local clear never drives rn.']},
      'kv_reqmux_recovery.sv': {'from':{'path':'rtl/chip/ot_chip_v41x_kv_reqmux.sv','sha256':pins['rtl/chip/ot_chip_v41x_kv_reqmux.sv']},
        'changes':['Default-off fence control, propagate WINDOW freeze/continuation handshake and token. CKV remains active/read-only. No combinational response buffer introduced.']},
      'kv_rope_reqmux_recovery.sv': {'from':{'path':'rtl/chip/ot_chip_v41x_kv_rope_reqmux.sv','sha256':pins['rtl/chip/ot_chip_v41x_kv_rope_reqmux.sv']},
        'changes':['Default-off fixed WINDOW owner fence forwarding; preserve owner-tag routing and RoPE traffic. Scope only actual nested mux.']},
      'hbm_karb_recovery.sv': {'from':{'path':'rtl/chip/ot_chip_v41x_hbm_karb.sv','sha256':pins['rtl/chip/ot_chip_v41x_hbm_karb.sv']},
        'changes':['Default-off owner fence adapter; preserve direct PIPE_OUT=0/PIPE_RSP=0 lowest-PC selection and all unrelated grants.',
                   'Check selected owner request/response offers and write ACK routing; no read ledger inferred from kw_out. Pipeline/local variants rejected in preflight.']},
      'idx_hbm_recovery.sv': {'from':{'path':'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv','sha256':pins['rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv']},
        'changes':['Default-off SELECT_WINDOW_RECOVERY on selected stack K backend only; preserve backing/timing/queue/calendar/payload semantics.',
          'Per-PC selected-owner read count accepts single beat requests and retires only on rsp_v&&rsp_rdy; unissued WR count accepts at handshake and retires at issue. Simultaneous increments/decrements computed atomically, bounded under/overflow fails closed.',
          'At owner WR issue update internal max visibility deadline=h_tcol+CWL_PS+BURST_PS and valid flag. Visible ACK when existing model now reaches deadline, all accepted owner writes issued, write ACK routes clear. Plan only: no timer or visibility code implemented.',
          'Source serialization permits one outstanding unissued write total, read population <=8; any LEN!=1/owner aperture violation rejects candidate admission.',
          'Prove counters equal ring owner-filter oracle including registered response; h_sched aliases Q and rsp_v aliases R. Owner drain leaves unrelated Q/R untouched.'],
        'qualification_limit':'Projected visibility of this pinned simulation timing model, NOT PHY completion. Physical provider remains separately required.'},
    }
    return {
      'status':'PREPARATION_ONLY; COMPILE_GO_FALSE; ACTUAL_ADMISSION_FALSE',
      'source_commit':binding['manifest_source_commit'],
      'manifest':{'path':binding['manifest_path'],'sha256':binding['manifest_sha256'],'sources':145},
      'source_binding_sha256':hashlib.sha256(binding_path.read_bytes()).hexdigest(),
      'unified_uarch_binding':{'tool':'tools/uarch_model.py','sha256':hashlib.sha256(uarch.read_bytes()).hexdigest(),
        'schema':'dedicated_ledger element/replicas/ports/storage/area/latency compatible additive record; no unified model edits or evaluate integration claimed.',
        'estimate_basis':'DFF_UM2=0.2916 and source-local control estimate storage*DFF + mux_bit_equivalents*0.2 +512; estimate only.'},
      'element':{'name':'selected_WINDOW_recovery_fence','replicas_fixed':1,
        'parameters':{'OPT_RECOVERY':0,'WIN_STACK':0,'NPC':32,'QD':64,'RQD':32,'RW':16,'MAXSKIP':16,'REFPB':3,'CLK_PS':1000,'LENW':4,'BEATW':4,'AW':30,'owner_TAGW':16,'backend_TAGW':17,'epoch_bits':9,'REFILL_CREDITS':8,'PIPE_OUT':0,'PIPE_RSP':0,'KARB_LOCAL':0,'MEM_MODE':0,'MEM_WORDS':264320,'user':0},
        'macs_per_element':0,'compute_intensity_MAC_per_byte':0,
        'ports_per_element':{'request_bits':342,'response_bits':279,'response_ready_bits':1,'write_issue_ack_bits':1,
          'additional_control_forward_bits':3,'additional_control_reverse_bits':3},
        'ports_total':{'request_bits':342,'response_bits':279,'additional_control_forward_bits':3,'additional_control_reverse_bits':3},
        'port_breakdown':{'request':'valid1+address30+len4+tag17+we1+data256+strb32+ready1=342',
          'response':'valid1+tag17+beat4+data256+ready1=279; ready included, not extra payload',
          'new_control':'freeze1+fence_token1+owner_commit1 forward; owner_empty1+visible_empty1+token_ack1 reverse; all level-held, same clk, request remains asserted through ACK.'},
        'bytes_per_cycle':{'existing_request_payload_max':32,'existing_response_payload_max':32,'new_payload':0},
        'entries':{'read_owned_max':8,'read_sectors_per_row':17,'write_unissued_total_max':1,'accepted_block_intents_max':1,
          'write_intent_sectors_per_block':2,'writes_per_row':32,'owner_wire_tag_bits':14,'physical_queue_slots_unchanged':32*(64+32)},
        'storage_bits_by_resource':counts,'storage_bits':storage,'mux_bit_equivalents':muxbits,
        'area_est_um2':round(area,6),'area_budget_um2':round(2*area,6),
        'area_basis':'Unhardened estimate, twice estimate cap. Includes selected-owner counters, internal simulation-time watermark, 16 controller bits (FSM3,freeze1,discard1,commit1,token1,ack7,violation1,ACKpending1), intent3. Existing issued/received masks, payload/code registers, queue tags and row valid arrays reused.',
        'visibility_storage':'Single owner watermark64+valid1 updated monotonically max; internal idx model state, zero extra bits on payload wire. Time overflow aborts. A hardware physical provider may have different state/area and is not priced as implemented.',
        'replication':'One fixed selected owner/stack; no new per-PC engine replicas beyond32 small counters. Four independent selected-owner adapters would be4x costs, but not proposed here.'},
      'routing':{'boundaries':['WINDOW->inner_mux','inner_mux->outer_mux','outer_mux->KARB','KARB->selected_idx'],
        'extra_bits_each_boundary':6,'total_point_to_point_conductor_segments':24,
        'forward_fanout':'Each control follows one selected-owner path; backend owner mask decoded locally across32PCs. Counter updates use existing local handshake/tag paths.',
        'receipt_aggregation':'Seven logical ACK conditions mapped to source controller7bits, same fence token; combine local predicates, not seven64bit identities or payload demuxes.',
        'routing_tracks_proxy_per_boundary':6,'capacity_reference_tracks':1153,'proxy_fraction':round(6/1153,6),
        'qualification':'Logical conductor count only; unified FLOORPLAN spine reference is not this local corridor capacity. Physical floorplan placement/fanout/actual routing capacity unresolved; mandatory hub routing check before adoption.'},
      'latency':{'healthy_added_pipeline_cycles':0,'healthy_timing_status':'Zero extra stages intended, no SS/FF closure asserted. Admission/fault fanout must be checked in context before adoption.',
        'fault_formula':'Nread*(A+S+R)+Nwrite_intent*(A+S+V)+4 fence/control cycles; Nread<=8; pre-fault block continuation<=2 writes plus previously issued visibility tail included by V. Bounds must cover shared interference, response holding and physical/projected visibility.',
        'control_edges':'After last owner retire/visibility at B, verify registered offers clear B+1; capture joined owner-empty/token ACK B+2; commit B+3; permit new owner traffic B+4. Test exact edge convention, no simultaneous old/new owner handshake.',
        'single_user_token_composition':'Healthy extra modeled cycles0 and new payload0. Fault recovery conditional bound only, not converted to layer/token/rate. No speed gain/adoption eligibility claim.',
        'healthy_visibility':'Nash causal scale-last/read safety verdict remains separate. No healthy publication timer implementation or choice.'},
      'fence_selection':{'identity':'One toggling fence token on control only. Reuse permitted only after every actor acknowledges same closed transaction; level-held request, one request in flight, no asynchronous ACK transport in this source.',
        'no_future_delivery':'Candidate idx offers only owned Q/R entries, never an untracked delayed callback; count/ring/registered-offer equivalence and no-scheduled-entry after owner drain establish closed delivery. Mux/KARB direct path has no extra state. Same clock event ordering must include current handshakes.',
        'violation':'Detected unexplained old/duplicate completion or delivery fails closed and forbids local restart; quiet intervals or token toggling do not cleanse it. A delayed same-wire identity alias after512 wrap can be undetectable at the source: the closed provider must exclude it. Oracle observes injected full identity and reports qualification FAIL if this exclusion is violated; no claim candidate can detect arbitrary ghost identity from wire bits.',
        'scope':'Owner-local recovery only; external/global rn must not be asserted by this controller. Reset during owned entries tested as forbidden admission; actual shared reset destroys queues and is not a recovery success.'},
      'planned_added_paths':{'copies_root':'rtl/test/w17_window_recovery_candidate/',
        'copies':modifications,'wrapper':'rtl/test/w17_window_recovery_candidate/connected_recovery.sv',
        'bench':'rtl/test/w17_window_recovery_candidate/tb.sv','runner':'tools/w17_window_recovery_candidate_gate.py',
        'tests':'tests/test_w17_window_recovery_candidate_gate.py','evidence':'results/rtl/w17_window_recovery_candidate_<date>_attempt<N>/',
        'original_byte_integrity':'All sources and previously committed gate/census files unchanged; namespace rename in added copies only, no live source manifest/overlay selection.'},
      'bench_plan':{'top':'One selected WINDOW -> real nested mux -> actual direct KARB -> selected idx K backend. Explicit finite geometry; legal synthetic backing, no checkpoint payload.',
        'competitors':'CKV/RoPE read offers and B/weight traffic remain active before/during/after WINDOW drain; assert they keep ownership and are not reset. Admission/service bounded only for successful liveness scenarios.',
        'stimuli':['fault on 1st/last/middle accepted read','fault simultaneous read grant and return','hold backend registered response until controlled ready release','queued return past fault, poison exact identity retired/discarded','wrong epoch/sector/beat and valid duplicate must not release legitimate credit','WC fault before/at/after grant and column issue ACK; retain/drain WS accepted-block continuation','WS fault before/at/after grant and ACK; prevent row publication','owner queue empty while physical visibility tail remains','another owner Q/R nonempty when WINDOW fence succeeds','attempt recovery with missing/stale token ACK and same-tag512 wrap delayed ghost','request local restart or global reset while owned entries exist; forbid it','successful drain->fence->local restart with new epoch and fresh refill','unbounded ready/service holds: bounded test timeout retains fault and identity'],
        'oracle':'Test-only64bit operation/serial identities record reserve/accept/cancel/issue/return/ACK/visible/retire at each actual boundary. Independently enumerate occupied q/r rings by selected owner and compare counters every cycle; h_sched and registered offers checked as aliases. Oracle identity never routed in candidate.',
        'quiescence_success':'Frozen ingress, no latent block continuation, no WINDOW accepted read/write obligation, no matching Q/R/scheduled/registered offer or pending WR ACK, projected writes visible, fresh joined token ACK and closed delivery provenance. Unrelated owner population allowed and must remain conserved.',
        'mutants':['omit fault discard retirement => liveness FAIL','early fence ignores held return => safety FAIL','WR issue ACK used as visibility => safety FAIL','drop WS intent on fault => ownership FAIL','stale/duplicate accepted after wrap => safety FAIL'],
        'provenance':'Pin all source/candidate generator/copy/bench hashes, source diff and elaborated params before compile. Event traces and failed attempts immutable; compare projected deadline against column timing oracle, not mem[] commit.'},
      'budget':{'compile_GO':False,'cpus_max':2,'memory_GiB_max':4,'disk_generated_MiB_max':256,'compile_wall_seconds_max':180,'simulation_wall_seconds_max':60,'sim_cycles_per_case_max':250000,'seed_count_max':3,'directed_cases_max':24,'whole_field_die_builds':0,
        'enforcement':'Future runner wall timeout, shared taskset2CPU, compile jobs<=2 and aggregate cgroup memory.max4GiB (require enforceable group limit or do not run), total generated-output256MiB guard plus per-file cap and per-case cycle bounds; fail receipt on cap hit, no automatic tuning or rerun. Preflight CPU/memory/disk headroom before execution.',
        'before_compile_GO':['parent review this selected policy, finite bounds and visibility scope','Nash visibility verdict before any healthy timer code; recovery watermark also remains plan-only until explicit compile/implementation authorization','review generated source diff and hash receipt','review fixture oracle/mutant schedule and caps'],
        'remaining_physical_gate':'Projected idx fence is not physical completion, SS/FF timing, end-to-end PHY reset/drain or whole-token qualification.'},
    }


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise SystemExit('refuse to overwrite existing preparation evidence')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(build_plan(),indent=2)+'\n')


if __name__ == '__main__':
    main()
