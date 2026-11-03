#!/bin/bash
# DIE-HBM-61/RTL-TAILX 11-03: RE-FORM lockstep + killing mutants (run from the repo root on epyc2).
set -u; cd "$(dirname "$0")/../.."; O=results/hbm_reform_tailx_1103; D=${OUT:-/tmp/dh61_tailx_eq}; mkdir -p $D
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}
F="rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_delay.sv"
R=rtl/hbm_accel/cores_split/sk_en_q4/ot_hbm_hc_tail_rest_core_ce.sv
GOLD_REV=${GOLD_REV:-08542fa9d7d}
git show $GOLD_REV:$R | sed 's/\bot_hbm_hc_tail_rest_core_ce\b/gold_rest_core_ce/; s/\bot_hbm_hc_tail_static_rest_ce\b/gold_static_rest_ce/g' > $D/gold.sv
python3 tools/hbm_b2/sk_ce_kit.py --emit-rest | cmp -s - $R || { echo "GENERATOR != committed RTL"; exit 3; }
mk(){ sed "$2" $R > $D/$1.sv; cmp -s $R $D/$1.sv && { echo "mutant $1 not applied"; exit 2; }; }
mk mut_index_late 's/i_q<=address(age_next,active_next)/i_q<=address(age,active)/'
mk mut_phase_edge 's/else p_q<={act_nx\&\&age_nx>=P7/else p_q<={act_nx\&\&age_nx>P7/'
mk mut_phase_prio "s/wire act_nx=sink_capture?1'b0:launch?1'b1:active;/wire act_nx=launch?1'b1:sink_capture?1'b0:active;/"
mk mut_opq_short 's/D(3+OPQ)) mt/D(3)) mt/'
mk mut_opq_exp_v 's/assign {mv_u,av_u,ev_u,dv_u,neg_u}={mv_q,av_q,ev_q,dv_q,neg_q};/assign {mv_u,av_u,ev_u,dv_u,neg_u}={mv_q,av_q,p4,dv_q,neg_q};/'
mk mut_neg 's/neg_q<=(i<8)/neg_q<=(i<4)/'
mk mut_max_early 's/MAX=55+REFORM,/MAX=55,/'
mk mut_p3_early 's/P3=56+2\*REFORM,/P3=56+REFORM,/'
mk mut_mx_stage 's/age==MAX+1)for/age==MAX)for/'
mk mut_pair_order 's/mlo\[r\]<=greater(t\[9+4\*r\],t\[8+4\*r\])?t\[9+4\*r\]:t\[8+4\*r\];/mlo[r]<=greater(t[9+4*r],t[8+4*r])?t[8+4*r]:t[9+4*r];/'
mk eqv_bal_tie 's/mlo\[r\]<=greater(t\[9+4\*r\],t\[8+4\*r\])?t\[9+4\*r\]:t\[8+4\*r\];/mlo[r]<=greater(t[8+4*r],t[9+4*r])?t[8+4*r]:t[9+4*r];/'
run(){ # name src REFORM seed expect
  $V --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -DDUTR=$3 -DSEED=$4 --top-module tb --Mdir $D/obj_$1 -o sim $O/tb_reform.sv $D/gold.sv $F $2 > $D/$1.build.log 2>&1 || { echo "$1 build FAIL"; tail -n 5 $D/$1.build.log; return; }
  $D/obj_$1/sim > $D/$1.log 2>&1; echo "$1 R=$3 seed=$4 expect=$5 rc=$?: $(grep TAILX_REFORM $D/$1.log | tr '\n' ' ')"; rm -rf $D/obj_$1; }
run pos_r1 $R 1 20261103 pass & run pos_r1_s2 $R 1 7741 pass & run pos_r0 $R 0 20261103 pass &
for m in mut_index_late mut_phase_edge mut_phase_prio mut_opq_short mut_opq_exp_v mut_neg mut_max_early mut_p3_early mut_mx_stage mut_pair_order eqv_bal_tie; do run $m $D/$m.sv 1 20261103 fail & done; wait
rc=0; for n in pos_r1 pos_r1_s2 pos_r0; do grep -q "TAILX_REFORM PASS" $D/$n.log || rc=1; done
for n in mut_index_late mut_phase_edge mut_phase_prio mut_opq_short mut_opq_exp_v mut_neg mut_max_early mut_p3_early mut_mx_stage mut_pair_order; do grep -q "TAILX_REFORM PASS" $D/$n.log && rc=1; grep -q "TAILX_REFORM" $D/$n.log || rc=1; done
sha256sum $R $O/tb_reform.sv tools/hbm_b2/sk_ce_kit.py; echo "OVERALL rc=$rc (eqv_bal_tie is the declared-equivalent tie mutant: expected PASS)"; exit $rc
