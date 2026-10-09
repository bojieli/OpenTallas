#!/bin/bash
# TT-VIEWS launchers (2026-10-07, owner: launch all remaining TT routes as dependency chains, no agent polling).
# Every step is its own detached process (setsid nohup) logging to logs/<step>.log; 'ttv.py produce' waits for its
# route and writes store/<view>/PRODUCED.json; 'ttv.py queue' waits for its views and drops the spec into the loop inbox.
cd $(dirname $0); T=$PWD; A=$T/specs/awaiting; S=$T/specs
P="python3 $T/ttv.py"
L1=/srv/opentallas-scratch/claude/hbm-die/lanes_tc
run() { n=$1; shift; setsid nohup bash -c "$*" > $T/logs/$n.log 2>&1 < /dev/null & echo "$n pid $!" >> $T/logs/PIDS; }
: > $T/logs/PIDS
# ---- HBM attention: leaf (EPYC2 routes_l/lb_u45_m6) -> quad TC re-route -> tile r23 / r23h; banks from the loop TC routes
run p_leaf "$P produce --name ot_attn_hgrp_m6h1 --host ot-epyc2 --orfs /srv/opentallas-scratch2/scratch/claude/hbm-attn/routes_l/lb_u45_m6/work/orfs"
for o in sn ew; do
  run p_bank_$o "$P produce --name ot_attn_bank_${o}544 --loop-job hbm_attn_bank_${o}544_tc_e1f264030 --orfs '{RUN}/routes/*/work/orfs' --view-src '{RUN}/record/view'"
done
run q_quad "$P queue --spec $S/hbm_attn_quad_qb1_tc_6ce4b64fd.json --view physical/hbm_attn_tile_r/leaf_b/ot_attn_hgrp_m6h1=ot_attn_hgrp_m6h1"
run p_quad "$P produce --name ot_attn_tile_m6h1q --loop-job hbm_attn_quad_qb1_tc_6ce4b64fd --orfs '{RUN}/routes/*/work/orfs' --ready '{RUN}/routes/*/view' --wait-file '{RUN}/routes/*/view/abstract.json'"
for j in hbm_attn_tile_r23_9604a57e4-tt hbm_attn_tile_r23h_mmcg_0d1f9513e-tt; do
  run q_$j "$P queue --spec $A/$j.json --view physical/hbm_attn_tile_r/quad_b/ot_attn_tile_m6h1q=ot_attn_tile_m6h1q --view physical/hbm_attn_tile_r/quad_b_cts/ot_attn_tile_m6h1q=ot_attn_tile_m6h1q --view physical/hbm_attn_tile_r/bank/ot_attn_bank_sn544=ot_attn_bank_sn544 --view physical/hbm_attn_tile_r/bank/ot_attn_bank_ew544=ot_attn_bank_ew544"
done
# ---- HBM hub lanes: hbm-die TC re-hardens on EPYC1 (lanes_tc) -> TT on the same interface SDC -> HC / SU quarters
run p_hcpost "$P produce --name ot_dsrom_su_hcpost_lane --host ot-epyc1tb --orfs $L1/routes/hcpost_tc/work/orfs --view-src $L1/routes/hcpost_tc/view --wait-file $L1/routes/hcpost_tc/view/abstract.json --interface-sdc $L1/src_hc/physical/hbm_die_abstracts_20261006/compute/ot_su12_full/interface.sdc"
run p_light "$P produce --name ot_su12_light --host ot-epyc1tb --orfs $L1/routes/light_tc/work/orfs --view-src $L1/routes/light_tc/view --wait-file $L1/routes/light_tc/view/abstract.json --interface-sdc $L1/src_light/physical/hbm_die_abstracts_20261006/compute/ot_su12_full/interface.sdc"
for j in hbm_hc_quarter_01353018a-tt hbm_hc_quarter_r23_5b48044bf-tt hbm_hc_quarter_r24_1ad3621a6-tt hbm_hc_quarter_r24p_mmcg_4d90ba1cc-tt; do
  run q_$j "$P queue --spec $A/$j.json --view physical/hbm_accel_die_views/hc/lane/ot_dsrom_su_hcpost_lane=ot_dsrom_su_hcpost_lane"
done
for j in hbm_su_quarter_01353018a_dpl-tt hbm_su_quarter_r23_5b48044bf-tt hbm_su_quarter_r24_1ad3621a6-tt hbm_su_quarter_r24p_92137c9b6-tt hbm_su_quarter_r24p_nrd_mmcg_4d90ba1cc-tt; do
  run q_$j "$P queue --spec $A/$j.json --view physical/hbm_accel_die_views/su/lane/ot_su12_light=ot_su12_light"
done
# ---- SFU lane: pin-keepout lane loop job hbm_sfu_lane_ring3ko_tc_fd22c77cb -> TT -> SFU quarters
run p_sfu "$P produce --name ot_su12_sfu --loop-job hbm_sfu_lane_ring3ko_tc_fd22c77cb --orfs '{RUN}/routes/*/work/orfs' --view-src '{RUN}/routes/*/view' --wait-file '{RUN}/routes/*/view/abstract.json' --interface-sdc '{RUN}/src/physical/hbm_die_abstracts_20261006/compute/ot_su12_full/interface.sdc'"
for j in hbm_sfu_quarter_r23_5b48044bf-tt hbm_sfu_quarter_r24_1ad3621a6-tt; do
  run q_$j "$P queue --spec $A/$j.json --view physical/hbm_accel_die_views/sfu/lane/ot_su12_sfu=ot_su12_sfu"
done
# ---- DS fused head: SRAM lane loop job dsfh-sramlane-tc-6ce4b64fd (queued directly) -> 8 hquad / quad routes
run p_sramlane "$P produce --name ot_hdc_v41_fh_sram_lane_hardened --loop-job dsfh-sramlane-tc-6ce4b64fd --orfs '{RUN}/routes/*/work/orfs' --ready '{RUN}/routes/*/view' --wait-file '{RUN}/routes/*/view/export.json'"
for j in dshead-hquad-half2-447ba47fa-mmq-tt dshead-hquad-half-4123ff389-tt dshead-hquad-r4-cd3cbef4b-tt dshead-hquad-r5-60f5a0a90-tt dshead-hquad-ss-c073b6f60-tt dshead-quad-safe-b529ca8c9-tt dshead-quad-ss-a318fdf47-tt; do
  run q_$j "$P queue --spec $A/$j.json --view physical/dsrom_fh_quad/ot_hdc_v41_fh_sram_lane_hardened=ot_hdc_v41_fh_sram_lane_hardened"
done
# ---- S81 die views (store only, for s81-die): head delay leaf (queued directly) + the m6 window columns (tt-batch TC jobs)
run p_headdelay "$P produce --name ot_s81_head_delay8x32 --loop-job s81-head-delay8x32-tc-6ce4b64fd --orfs '{RUN}/routes/*/work/orfs' --ready '{RUN}/routes/*/view' --wait-file '{RUN}/routes/*/view/abstract.json'"
for w in 128 256; do
  run p_wcol$w "$P produce --name ot_dsrom_window_column_$w --loop-job wcol$w-m6-01a487c86-mmq-tt --orfs '{RUN}/routes/*/work/orfs' --view-src '{RUN}/routes/*/view' --wait-file '{RUN}/routes/*/view/abstract.json'"
done
