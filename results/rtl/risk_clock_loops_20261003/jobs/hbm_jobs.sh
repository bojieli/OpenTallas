#!/bin/bash
# HBM comparator (Qwen3-8B HBM, DeepSeek-V4.1 HBM; GPU-organised) control-loop SS screens, 2026-10-03.
# Pinned source: ~/rcl-20261003/src = commit e156ed54e8ff31def4b8c58d69da3743bb6b498c (rtl/ tools/ physical/ configs/).
# ../jobs/hbm_design/ = results/uarch/Euclid_W4_RFACK_identity_contract_20261003/selfcontained-peer-r10/design/*.sv
#   (the ACK_ID variants named by rtl/model/qwen_hbm_integrated_20261003/sources.f lines 2-10) plus
#   ot_gpu_expert_fetch_noring.sv = rtl/gpu/ot_gpu_expert_fetch.sv with the 256-bit data ring removed (control-only).
# Gate: <=16 of these concurrent; MemAvailable >= NEED GB before each launch (4 small, 12 large; host shared).
cd ~/rcl-20261003/src
T="python3 tools/risk_clock_loops_screen.py"
O=../runs/hbm; mkdir -p $O
L=../jobs/hbm_srcs.txt; LA=../jobs/hbm_srcs_ack.txt
W6=rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv
R14="--source rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv --source rtl/model_ready_hbm_r14/ot_hbm_r14_pc.sv --source physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_bb.v --blackbox ot_sram_1r1w_64x512_m1_r2c2"
KVJ="--source $W6 --source rtl/model/qwen_hbm_integrated_20261003/ot_gpu_qwen_joined_kv.sv --source rtl/model/qwen_native_consumer_drain_20261003/ot_gpu_qwen_native_consumer_drain.sv --source rtl/model/qwen_kv_connections_20261003/ot_gpu_qwen_kv_metadata_join.sv --source rtl/model/qwen_kv_connections_20261003/ot_gpu_qwen_kv_state_observer.sv --source rtl/model/qwen_kv_connections_20261003/ot_gpu_qwen_kv_shared_router.sv --source rtl/model/qwen_kv_lifecycle_20261003/ot_gpu_qwen_kv_lifecycle_controller.sv"
mine() { pgrep -u ubuntu -f "risk_clock_loops_screen.py.*runs/hbm/" | wc -l; }
memok() { [ $(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo) -ge ${NEED:-4} ]; }
run() { lab=$1; shift
  [ -f $O/$lab.json ] && return
  while [ $(mine) -ge 16 ] || ! memok; do sleep 20; done
  nohup $T --work $O/$lab --output $O/$lab.json --label $lab "$@" > $O/$lab.log 2>&1 &
  sleep 30; }
SM="--domain 1.2GHz-SM"
FI='issue=(^|\.)(ph|si|rb|gi|ti|issuing|retired|cr|cg|cxb|wb|items_q|rows_q|xa_r)(\[|$)'
FB='ctl=(^|\.)(q_cnt|q_wp|q_rp|act|a_addr|a_left|full|alloc_p|cons_p|oq_n|rd_v)(\[|$)'
run issue_q_833 --resolve-from $L --top ot_gpu_issue --param IL=8 --param RMAX=4096 --param XDEPTH=1024 --period-ns 0.833 $SM --focus "$FI"
run issue_ds_833 --resolve-from $L --top ot_gpu_issue --param IL=8 --param RMAX=4096 --param XDEPTH=128 --period-ns 0.833 $SM --focus "$FI"
run stack_833 --resolve-from $L --top ot_gpu_stack --param LEV=5 --param IL=8 --param TAGW=12 --param ALAT=7 --period-ns 0.833 $SM '--focus' 'ctl=(^|\.)(pend_v|seen|t_n)(\[|$)'
run fence_833 --resolve-from $L --top ot_gpu_rf_visibility_fence --param ENABLE=1 --period-ns 0.833 $SM --focus 'ctl=(^|\.)(expected|issued|retired|epoch|ACK_addr|active|pending|producer_done|fault_q)(\[|$)'
run fence_w6_833 --source $W6 --source rtl/gpu/w6/ot_gpu_rf_visibility_fence_w6.sv --top ot_gpu_rf_visibility_fence_w6 --param ENABLE=1 --period-ns 0.833 $SM --focus 'ctl=(^|\.)protected_state(\[|$)'
run scratch_833 --resolve-from $LA --top ot_gpu_scratch_service --blackbox ot_sram_1r1w_1024x256_m2_r2c2 --period-ns 0.833 $SM --focus 'ctl=(^|\.)pending(\[|$)'
run rfsvc_ack_833 --resolve-from $LA --top ot_gpu_rf_service --param ACK_ID=1 --blackbox ot_sram_1r1w_128x256_m1_r2c2 --period-ns 0.833 $SM --focus 'ctl=(^|\.)(read_pending|prefer_write|write_pending|page_a|page_b|accepted_identity)(\[|$)'
run fullsm_ack_833 --resolve-from $LA --top ot_gpu_full_sm_service --param ENABLE=1 --param ACK_ID=1 --blackbox ot_gpu_fadd --blackbox ot_gpu_fmul --blackbox ot_sram_1r1w_128x256_m1_r2c2 --blackbox ot_sram_1r1w_1024x256_m2_r2c2 --period-ns 0.833 $SM --focus 'fsm=(^|\.)(state|mul_q|prefer_simd|alu_valid|fault_q|a_q|b_q|dst_q)(\[|$)' --focus 'rf=u_rf\.(read_pending|prefer_write|write_pending|page_a|page_b)(\[|$)'
run barrier_833 --resolve-from $L --top ot_gpu_barrier_node --param K=8 --period-ns 0.833 $SM
NEED=12 run w2nc6_833 --resolve-from $L --top ot_w2_nc6_protected_completion_reset_quarantine --param NC=6 --param MAX_OUT=16 --param AW=34 --param CTAGW=32 --param GENW=4 --param PTAGW=35 --param OPT_EXACT=1 --param OPT_RESET_QUARANTINE=1 --period-ns 0.833 --domain component-service --focus 'ctl=(^|\.)(S|C|J|Q|X|H|RQ|RD|WQ|rr|phase|count_pending|offer_drained|cancel_request|reopen_epoch|scrub_v|fault_busy)(\[|$)'
NEED=12 run w2nc6_1024 --resolve-from $L --top ot_w2_nc6_protected_completion_reset_quarantine --param NC=6 --param MAX_OUT=16 --param AW=34 --param CTAGW=32 --param GENW=4 --param PTAGW=35 --param OPT_EXACT=1 --param OPT_RESET_QUARANTINE=1 --period-ns 1.024 --domain component-service --focus 'ctl=(^|\.)(S|C|J|Q|X|H|RQ|RD|WQ|rr|phase|count_pending|offer_drained|cancel_request|reopen_epoch|scrub_v|fault_busy)(\[|$)'
FKV='fsm=(^|\.)(state|pc|beat|cstage|op|reader_count|sector_cursor|writer_live|commit_sent|drain_sent|receipt_visible|receipt_reverse)(\[|$)'
NEED=12 run kvlife_833 --resolve-from $L --top ot_gpu_qwen_kv_lifecycle_controller --param ENABLE=1 --period-ns 0.833 $SM --focus "$FKV"
NEED=12 run r14pc_1024 $R14 --top ot_hbm_r14_pc --period-ns 1.024 --domain HBM-service-976MHz --focus 'fsm=(^|\.)(state|head|tail|n|scan_issue|scan_capture|window|best_index|best_est|selected_index|shift_index|pad|skips|read_pending|candidate_legal)(\[|$)'
NEED=12 run r14pc_833 $R14 --top ot_hbm_r14_pc --period-ns 0.833 --domain HBM-service-at-1.2GHz --focus 'fsm=(^|\.)(state|head|tail|n|scan_issue|scan_capture|window|best_index|best_est|selected_index|shift_index|pad|skips|read_pending|candidate_legal)(\[|$)'
run mtp_1111 --source $W6 --source rtl/experimental/ds_mtp_accept_20261003/ot_hdc_mtp_accept_guarded.sv --top ot_hdc_mtp_accept_guarded --param NSLOT=8 --param NW=21 --param ENABLE=1 --period-ns 1.111 --domain 0.9GHz-serial --focus 'q=(^|\.)(q|run|fresh|ce)(\[|$)'
NEED=12 run topk_833 --resolve-from $L --top ot_gpu_router_topk --param N=384 --param P=16 --param K=6 --param IW=9 --period-ns 0.833 $SM --focus 'ctl=(^|\.)(beat_base|fresh|fin_v|c|idx|vpipe)(\[|$)'
NEED=12 run bulkcopy_q_833 --resolve-from $L --top ot_gpu_bulk_copy --param LINE_BITS=1024 --param DEPTH=1024 --param MAX_OUT=512 --param SRAM_RING=1 --blackbox ot_sram_1r1w_1024x256_m2_r2c2 --period-ns 0.833 $SM --focus "$FB"
NEED=12 run bulkcopy_ds_833 --resolve-from $L --top ot_gpu_bulk_copy --param LINE_BITS=1088 --param DEPTH=1024 --param MAX_OUT=512 --param SRAM_RING=1 --blackbox ot_sram_1r1w_1024x256_m2_r2c2 --period-ns 0.833 $SM --focus "$FB"
NEED=12 run kvjoined_833 $KVJ --top ot_gpu_qwen_joined_kv --param ENABLE=1 --period-ns 0.833 $SM --focus "$FKV"
# reduced datapath: P=48 kept (control width), LANES=1, DEPTH=16, SW_PIPE=2 (FIFO data + wire pipe are not control)
NEED=12 run nvls_967 --resolve-from $L --top ot_link_nvls_switch --param P=48 --param LANES=1 --param DEPTH=16 --param SW_PIPE=2 --period-ns 0.967 --domain switch-1.034GHz --focus 'ctl=(^|\.)(cnt|rp|wp|rot)(\[|$)'
NEED=12 run nvls_833 --resolve-from $L --top ot_link_nvls_switch --param P=48 --param LANES=1 --param DEPTH=16 --param SW_PIPE=2 --period-ns 0.833 $SM --focus 'ctl=(^|\.)(cnt|rp|wp|rot)(\[|$)'
NEED=12 run efetch_nr_833 --source ../jobs/hbm_design/ot_gpu_expert_fetch_noring.sv --top ot_gpu_expert_fetch --param NSM=8 --param NPC=32 --period-ns 0.833 $SM --focus 'grant=(^|\.)(rr|alloc_p|cons_p|in_sect|a_left|a_addr|act|q_cnt|q_rp|prio)(\[|$)' --focus 'mask=(^|\.)mask(\[|$)'
wait
