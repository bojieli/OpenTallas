#!/usr/bin/env bash
# DIE-HBM-61 RE-FORM C4 round 2: cfg_h9b leaf lockstep (new vs origin/main) + killing mutants, in parallel.
# Usage: run_h9b_leaf_eq.sh REPO WORK  (TIMING_833=0 only: the 833 profile needs the paired-PC phase context;
# the controller WP_REG change is lockstepped on TIMING_833 0/1 in run_h9_eq.sh)
set -uo pipefail
R=$(cd "${1:?repo}" && pwd); W=${2:?work}; mkdir -p "$W"; cd "$W"
D=rtl/hbm_accel/loader/service_native; L=$D/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv; C=rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv
git -C "$R" show origin/main:$L | sed 's/\bot_hbm_svc_pc_ctrl_leaf_cfg_h9b\b/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b_old/; s/\bot_hbm_r14_stream_pc_strap_h9\b/ot_hbm_r14_stream_pc_strap_h9_old/' > old_leaf.sv
git -C "$R" show origin/main:$C | sed 's/\bot_hbm_r14_stream_pc_strap_h9\b/ot_hbm_r14_stream_pc_strap_h9_old/' > old_ctl.sv
COMMON="$R/rtl/lib/ot_rst_relay.sv $R/$D/ot_hbm_svc_pin_skid2_h9.sv $R/$D/ot_hbm_svc_ring_h9b.sv $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v old_leaf.sv old_ctl.sv $R/$C"
TB=$R/tests/hbm_b2/reform_c4/tb_h9b_leaf_eq.sv
run() { # name leaf expect T
  iverilog -g2012 -s tb -Ptb.T=$4 -o $1_$4.vvp $COMMON "$2" "$TB" > $1_$4.comp.log 2>&1 || { echo "$1 T=$4 COMPILE-FAIL $(head -n 3 $1_$4.comp.log)"; return; }
  r=$(timeout 2400 vvp -n $1_$4.vvp | grep H9B_LEAF_EQ); echo "$1 expect=$3 :: $r"
}
mk() { sed "$2" "$R/$L" > $1.sv; cmp -s $1.sv "$R/$L" && echo "MUTANT $1 did not apply"; }
mk mut_hfall 's/:queue\[rp1\];/:head_q;/'
mk mut_pfall 's/:queue\[ep1\];/:push_q;/'
mk mut_cnt   's/rp_hit1=rp_off1<5'"'"'d4 \&\& count+6'"'"'(rp_off1)<6'"'"'d32;/rp_hit1=rp_off1<5'"'"'d4;/'
mk mut_rr    's/q_rr<=read_reserved_n<32;/q_rr<=read_reserved<32;/'
mk mut_run   's/q_run<=state_n==RUN;/q_run<=state==RUN;/'
mk mut_ephit 's/ep_hit0=ep_off0<5'"'"'d4 \&\& count+6'"'"'(ep_off0)<6'"'"'d32,/ep_hit0=ep_off1<5'"'"'d4 \&\& count+6'"'"'(ep_off1)<6'"'"'d32,/'
( run pos "$R/$L" pass 0 ) &
for m in mut_hfall mut_pfall mut_cnt mut_ephit mut_rr mut_run; do ( run $m $m.sv fail 0 ) & done
wait
