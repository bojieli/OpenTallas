#!/bin/bash
# HBM comparator control-loop SS screens, round 2 (2026-10-03), with ../jobs/risk_clock_loops_screen_hbm.py:
# copy of tools/risk_clock_loops_screen.py (pinned e156ed54e) + --macro (SRAM LEF + SS .lib, macros FIRM-placed)
# + IO-perimeter-aware utilisation + non-macro black boxes cut to top inputs (yosys delete + setundef -expose).
# Round 1 (hbm_jobs.sh, pinned tool unchanged) records kept: issue_q_833, issue_ds_833, stack_833, barrier_833.
# ../jobs/hbm_design/w6fix/: package import hoisted from module body to file scope (yosys 0.68 rejects the in-body
# import); otherwise byte-identical to the rtl/ source.
cd ~/rcl-20261003/src
T="python3 ../jobs/risk_clock_loops_screen_hbm.py"
O=../runs/hbm2; mkdir -p $O
L=../jobs/hbm_srcs.txt; LA=../jobs/hbm_srcs_ack.txt
W6=rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv; FX=../jobs/hbm_design/w6fix
R14="--source rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv --source $FX/ot_hbm_r14_pc.sv --source physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_bb.v --blackbox ot_sram_1r1w_64x512_m1_r2c2 --macro ot_sram_1r1w_64x512_m1_r2c2"
KVJ="--source $W6 --source rtl/model/qwen_hbm_integrated_20261003/ot_gpu_qwen_joined_kv.sv --source $FX/ot_gpu_qwen_native_consumer_drain.sv --source rtl/model/qwen_kv_connections_20261003/ot_gpu_qwen_kv_metadata_join.sv --source rtl/model/qwen_kv_connections_20261003/ot_gpu_qwen_kv_state_observer.sv --source rtl/model/qwen_kv_connections_20261003/ot_gpu_qwen_kv_shared_router.sv --source rtl/model/qwen_kv_lifecycle_20261003/ot_gpu_qwen_kv_lifecycle_controller.sv"
B1K="--blackbox ot_sram_1r1w_1024x256_m2_r2c2 --macro ot_sram_1r1w_1024x256_m2_r2c2"
B128="--blackbox ot_sram_1r1w_128x256_m1_r2c2 --macro ot_sram_1r1w_128x256_m1_r2c2"
mine() { pgrep -u ubuntu -f "risk_clock_loops_screen.*runs/hbm2/" | wc -l; }
memok() { [ $(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo) -ge ${NEED:-4} ]; }
run() { lab=$1; shift
  [ -f $O/$lab.log ] && return   # launched already (rerun: delete the log)
  while [ $(mine) -ge 16 ] || ! memok; do sleep 20; done
  nohup $T --work $O/$lab --output $O/$lab.json --label $lab "$@" > $O/$lab.log 2>&1 < /dev/null &
  sleep 20; }
SM="--domain 1.2GHz-SM"
FI='issue=(^|\.)(ph|si|rb|gi|ti|issuing|retired|cr|cg|cxb|wb|items_q|rows_q|xa_r)(\[|$)'
FB='ctl=(^|\.)(q_cnt|q_wp|q_rp|act|a_addr|a_left|full|alloc_p|cons_p|oq_n|rd_v)(\[|$)'
FKV='fsm=(^|\.)(state|pc|beat|cstage|op|reader_count|sector_cursor|writer_live|commit_sent|drain_sent|receipt_visible|receipt_reverse)(\[|$)'
FR14='fsm=(^|\.)(state|head|tail|n|scan_issue|scan_capture|window|best_index|best_est|selected_index|shift_index|pad|skips|read_pending|candidate_legal)(\[|$)'
FW2='ctl=(^|\.)(S|C|J|Q|X|H|RQ|RD|WQ|rr|phase|count_pending|offer_drained|cancel_request|reopen_epoch|scrub_v|fault_busy)(\[|$)'
W2P="--param NC=6 --param MAX_OUT=16 --param AW=34 --param CTAGW=32 --param GENW=4 --param PTAGW=35 --param OPT_EXACT=1 --param OPT_RESET_QUARANTINE=1"
run fence_833 --resolve-from $L --top ot_gpu_rf_visibility_fence --param ENABLE=1 --period-ns 0.833 $SM --focus 'ctl=(^|\.)(expected|issued|retired|epoch|ACK_addr|active|pending|producer_done|fault_q)(\[|$)'
run scratch_833 --resolve-from $LA --top ot_gpu_scratch_service $B1K --period-ns 0.833 $SM --focus 'ctl=(^|\.)pending(\[|$)'
run fence_w6_833 --source $W6 --source $FX/ot_gpu_rf_visibility_fence_w6.sv --top ot_gpu_rf_visibility_fence_w6 --param ENABLE=1 --period-ns 0.833 $SM --focus 'ctl=(^|\.)protected_state(\[|$)'
run rfsvc_ack_833 --resolve-from $LA --top ot_gpu_rf_service --param ACK_ID=1 $B128 --period-ns 0.833 $SM --focus 'ctl=(^|\.)(read_pending|prefer_write|write_pending|page_a|page_b|accepted_identity|protected_ACK)(\[|$)'
run mtp_1111 --source $W6 --source $FX/ot_hdc_mtp_accept_guarded.sv --top ot_hdc_mtp_accept_guarded --param NSLOT=8 --param NW=21 --param ENABLE=1 --period-ns 1.111 --domain 0.9GHz-serial --focus 'q=(^|\.)(q|run|fresh|ce)(\[|$)'
run issue_q_1024 --resolve-from $L --top ot_gpu_issue --param IL=8 --param RMAX=4096 --param XDEPTH=1024 --period-ns 1.024 $SM --focus "$FI"
run issue_q_1111 --resolve-from $L --top ot_gpu_issue --param IL=8 --param RMAX=4096 --param XDEPTH=1024 --period-ns 1.111 $SM --focus "$FI"
run issue_ds_1111 --resolve-from $L --top ot_gpu_issue --param IL=8 --param RMAX=4096 --param XDEPTH=128 --period-ns 1.111 $SM --focus "$FI"
NEED=10 run fullsm_ack_833 --resolve-from $LA --top ot_gpu_full_sm_service --param ENABLE=1 --param ACK_ID=1 --blackbox ot_gpu_fadd --blackbox ot_gpu_fmul $B128 $B1K --period-ns 0.833 $SM --focus 'fsm=(^|\.)(state|mul_q|prefer_simd|alu_valid|fault_q|a_q|b_q|dst_q)(\[|$)' --focus 'rf=u_rf\.(read_pending|prefer_write|write_pending|page_a|page_b)(\[|$)'
NEED=10 run kvlife_833 --resolve-from $L --top ot_gpu_qwen_kv_lifecycle_controller --param ENABLE=1 --period-ns 0.833 $SM --focus "$FKV"
NEED=10 run r14pc_1024 $R14 --top ot_hbm_r14_pc --period-ns 1.024 --domain HBM-service-976MHz --focus "$FR14"
NEED=10 run r14pc_833 $R14 --top ot_hbm_r14_pc --period-ns 0.833 --domain HBM-service-at-1.2GHz --focus "$FR14"
NEED=10 run w2nc6_833 --resolve-from $L --top ot_w2_nc6_protected_completion_reset_quarantine $W2P --period-ns 0.833 --domain component-service --focus "$FW2"
NEED=10 run w2nc6_1024 --resolve-from $L --top ot_w2_nc6_protected_completion_reset_quarantine $W2P --period-ns 1.024 --domain component-service --focus "$FW2"
NEED=10 run topk_833 --resolve-from $L --top ot_gpu_router_topk --param N=384 --param P=16 --param K=6 --param IW=9 --period-ns 0.833 $SM --focus 'ctl=(^|\.)(beat_base|fresh|fin_v|c|idx|vpipe)(\[|$)'
NEED=12 run bulkcopy_q_833 --resolve-from $L --top ot_gpu_bulk_copy --param LINE_BITS=1024 --param DEPTH=1024 --param MAX_OUT=512 --param SRAM_RING=1 $B1K --period-ns 0.833 $SM --focus "$FB"
NEED=12 run bulkcopy_ds_833 --resolve-from $L --top ot_gpu_bulk_copy --param LINE_BITS=1088 --param DEPTH=1024 --param MAX_OUT=512 --param SRAM_RING=1 $B1K --period-ns 0.833 $SM --focus "$FB"
NEED=12 run kvjoined_833 $KVJ --top ot_gpu_qwen_joined_kv --param ENABLE=1 --period-ns 0.833 $SM --focus "$FKV"
# reduced datapath: P=48 kept (control width), LANES=1, DEPTH=16, SW_PIPE=2 (FIFO data + wire pipe are not control)
NEED=12 run nvls_967 --resolve-from $L --top ot_link_nvls_switch --param P=48 --param LANES=1 --param DEPTH=16 --param SW_PIPE=2 --period-ns 0.967 --domain switch-1.034GHz --focus 'ctl=(^|\.)(cnt|rp|wp|rot)(\[|$)'
NEED=12 run nvls_833 --resolve-from $L --top ot_link_nvls_switch --param P=48 --param LANES=1 --param DEPTH=16 --param SW_PIPE=2 --period-ns 0.833 $SM --focus 'ctl=(^|\.)(cnt|rp|wp|rot)(\[|$)'
NEED=16 run efetch_nr_833 --source ../jobs/hbm_design/ot_gpu_expert_fetch_noring.sv --top ot_gpu_expert_fetch --param NSM=8 --param NPC=32 --period-ns 0.833 $SM --focus 'grant=(^|\.)(rr|alloc_p|cons_p|in_sect|a_left|a_addr|act|q_cnt|q_rp|prio)(\[|$)' --focus 'mask=(^|\.)mask(\[|$)'
wait
