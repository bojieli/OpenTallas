#!/bin/bash
# DIE-HBM-61/RTL-TAILX 11-03: RE-FORM lockstep + killing mutants (run from the repo root on epyc2).
set -u; cd "$(dirname "$0")/../.."; O=results/hbm_reform_tailx_1103; D=${OUT:-/tmp/dh61_tailx_eq}; mkdir -p $D
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}
C=rtl/hbm_accel/integrated_20261006/sfu_c12_selected
F="$C/00_ot_hdc_fastfp_lat_c12.sv $C/01_ot_hdc_fp32_f12.sv $C/02_ot_hdc_prefix.sv $C/03_ot_dsrom_su_add6.sv $C/04_ot_dsrom_su_f12.sv $C/05_ot_hdc_fsqrt_c12.sv $C/06_ot_hdc_v41x_sfu_c12.sv $C/08_ot_hdc_delay.sv $C/09_ot_hdc_sfu.sv $C/14_ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_delay.sv"
R=rtl/hbm_accel/cores_split/sk_en_q4/ot_hbm_hc_tail_rest_core_ce.sv
GOLD_REV=${GOLD_REV:-08542fa9d7d}
git show $GOLD_REV:$R | sed 's/\bot_hbm_hc_tail_rest_core_ce\b/gold_rest_core_ce/; s/\bot_hbm_hc_tail_static_rest_ce\b/gold_static_rest_ce/g' > $D/gold.sv
python3 tools/hbm_b2/sk_ce_kit.py --emit-rest | cmp -s - $R || { echo "GENERATOR != committed RTL"; exit 3; }
mk(){ sed "$2" $R > $D/$1.sv; cmp -s $R $D/$1.sv && { echo "mutant $1 not applied"; exit 2; }; }
mk mut_index_late 's/i_q<=address(age_next,active_next)/i_q<=address(age,active)/'
mk mut_phase_edge 's/else p_q<={act_nx\&\&age_nx>=P7/else p_q<={act_nx\&\&age_nx>P7/'
# eqv_phase_prio: launch-vs-capture priority in the phase predecode. Equivalent since LDQ: launch makes age_nx=1 < P1=2,
# so every phase flag is 0 whatever act_nx is (it was killed before LDQ, when P1 was 1).
mk eqv_phase_prio "s/wire act_nx=sink_capture?1'b0:launch?1'b1:active;/wire act_nx=launch?1'b1:sink_capture?1'b0:active;/"
mk mut_opq_short 's/D(LMU+OPQ)) mt/D(LMU)) mt/'
mk mut_vline 's/assign mo=mvl\[LMU\];/assign mo=mvl[LMU-1];/'
mk mut_opq_exp_v 's/assign {mv_u,av_u,ev_u,dv_u,neg_u}={mv_q,av_q,ev_q,dv_q,neg_q};/assign {mv_u,av_u,ev_u,dv_u,neg_u}={mv_q,av_q,p4,dv_q,neg_q};/'
mk mut_neg 's/neg_q<=(i<8)/neg_q<=(i<4)/'
mk mut_max_early 's/MAX=P2+24+LAU+OPQ,/MAX=P2+24+LAU,/; s/? 279 : 197/? 278 : 197/'
mk mut_p3_early 's/P3=MAX+1+MXS,/P3=MAX+1,/; s/? 279 : 197/? 278 : 197/'
mk mut_mx_stage 's/age==MAX+1)for/age==MAX)for/'
mk mut_pair_order 's/mlo\[r\]<=greater(t\[9+4\*r\],t\[8+4\*r\])?t\[9+4\*r\]:t\[8+4\*r\];/mlo[r]<=greater(t[9+4*r],t[8+4*r])?t[8+4*r]:t[9+4*r];/'
mk mut_skl 's/SDIV \* ((TE + 1 - 198 + SDIV - 1) \/ SDIV),/SDIV * ((TE + 1 - 198 + SDIV - 1) \/ SDIV) - SDIV,/'
mk mut_ld_data "s/assign ld_mix=mix_q;/assign ld_mix=mixes;/"
mk mut_ld_scl "s/if(ld_r\[0\])for(integer j=0;j<3;j=j+1)s\[j\]<=ld_scl/if(launch)for(integer j=0;j<3;j=j+1)s[j]<=ld_scl/"
mk mut_p1_early "s/P1=1+LDQ,/P1=1,/; s/? 279 : 197/? 278 : 197/"
mk mut_oh_late "s/else oh_q<=onehot(i_nx);/else oh_q<=onehot(i);/"
mk mut_etq "s/LEU=7\*LMU+8\*LAU+4+ETQ,/LEU=7*LMU+8*LAU+4,/"
mk mut_bsel "s/b_sel=b_sel|(b\[n\]/b_sel=b_sel|(t[n]/"
# c12 opt-in cut mutants: a mutated copy of one c12 file replaces it in F (FF)
mkf(){ mkdir -p $D/$1; sed "$3" $C/$2 > $D/$1/$2; cmp -s $C/$2 $D/$1/$2 && { echo "mutant $1 not applied"; exit 2; }; }
mkf mut_add7_cut 03_ot_dsrom_su_add6.sv "s/#(.CUTS(7'b1101111))/#(.CUTS(7'b1101011))/"
mkf mut_nrep_late 06_ot_hdc_v41x_sfu_c12.sv "s/nint_r\[q\] <= tsg ? 8'(-{1'b0, tmn}) : tmn;/nint_r[q] <= nint[7:0];/"
mkf mut_tq_bypass 06_ot_hdc_v41x_sfu_c12.sv "s/assign tsg = sg_q;/assign tsg = t[31];/; s/assign tmn = z_q ? 8'd0 : (ip_q + {7'd0, rb_q});/assign tmn = tmag;/"
mkf mut_tq_round 06_ot_hdc_v41x_sfu_c12.sv "s/rb_q <= thalf \&\& (tstk || tip\[0\]);/rb_q <= 1'b0;/"
mkf mut_nrep_slice 06_ot_hdc_v41x_sfu_c12.sv "s/ln2_nk(nint_r\[q\]) >> (q\*TW);/ln2_nk(nint_r[q]) >> ((q^1)*TW);/"
mk eqv_bal_tie 's/mlo\[r\]<=greater(t\[9+4\*r\],t\[8+4\*r\])?t\[9+4\*r\]:t\[8+4\*r\];/mlo[r]<=greater(t[8+4*r],t[9+4*r])?t[8+4*r]:t[9+4*r];/'
run(){ # name src - seed expect
  $V --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style  -DSEED=$4 --top-module tb --Mdir $D/obj_$1 -o sim $O/tb_reform.sv $D/gold.sv ${FF:-$F} $2 > $D/$1.build.log 2>&1 || { echo "$1 build FAIL"; tail -n 5 $D/$1.build.log; return; }
  $D/obj_$1/sim > $D/$1.log 2>&1; echo "$1 seed=$4 expect=$5 rc=$?: $(grep TAILX_REFORM $D/$1.log | tr '\n' ' ')"; rm -rf $D/obj_$1; }
run pos_s1 $R - 20261103 pass & run pos_s2 $R - 7741 pass &
for m in mut_index_late mut_phase_edge mut_opq_short mut_vline mut_opq_exp_v mut_neg mut_max_early mut_p3_early mut_mx_stage mut_pair_order mut_skl mut_ld_data mut_ld_scl mut_p1_early mut_oh_late mut_bsel mut_etq eqv_bal_tie eqv_phase_prio; do run $m $D/$m.sv - 20261103 fail & done
for m in mut_add7_cut mut_nrep_late mut_nrep_slice mut_tq_bypass mut_tq_round; do f=$(ls $D/$m); FF=$(echo " $F " | sed "s# $C/$f # $D/$m/$f #") run $m $R - 20261103 fail & done; wait
rc=0; for n in pos_s1 pos_s2; do grep -q "TAILX_REFORM PASS" $D/$n.log || rc=1; done
for n in mut_index_late mut_phase_edge mut_opq_short mut_vline mut_opq_exp_v mut_neg mut_max_early mut_p3_early mut_mx_stage mut_pair_order mut_skl mut_ld_data mut_ld_scl mut_p1_early mut_oh_late mut_bsel mut_etq mut_add7_cut mut_nrep_late mut_nrep_slice mut_tq_bypass mut_tq_round; do grep -q "TAILX_REFORM PASS" $D/$n.log && rc=1; grep -q "TAILX_REFORM" $D/$n.log || rc=1; done
sha256sum $R $O/tb_reform.sv tools/hbm_b2/sk_ce_kit.py; echo "OVERALL rc=$rc (eqv_bal_tie, eqv_phase_prio are declared-equivalent mutants: expected PASS)"; exit $rc
