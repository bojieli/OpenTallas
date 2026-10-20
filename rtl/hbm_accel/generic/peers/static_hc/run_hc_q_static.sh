#!/bin/bash
# Bench of the static HC quadrant LG client ot_hbm_hc_q_static (die hc_<q>) with its real die neighbours.
# Positive MUT=0 must PASS; MUT=1..4 must FAIL (wave word, store sector, capture edge, tap reservation).
set -u
cd "$(dirname "$0")/../../../../.."
O=${OUT:-/tmp/hc_q_static_bench}; mkdir -p $O; rc=0
SRC="rtl/test/tb_hbm_hc_q_static.sv rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_q_static.sv
 rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_residual_vm_static.sv rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_result_vm_static.sv
 rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_gathered_mix_reader_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_split_term.sv
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank_term.sv rtl/hbm_accel/generic/peers/ot_hgi_sfu_lg_pair_leaf.sv
 rtl/hdc/ot_hdc_delay.sv rtl/test/full_sm_service/sram_models.sv rtl/lib/ot_rst_relay.sv
 rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_xw_rx_static.sv rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_qcal_static.sv"
for m in ${MUTS:-0 1 2 3 4}; do  # MUTS=<n> runs one case (closure-loop mutant benches)
  # QHUB-S1 10-19: HCQ_SAFE=1 benches ot_hbm_hc_q_static SAFE 1 (kit hbm_hcq_hub_s1); MUT 7 is its SAFE-only mutant
  iverilog -g2012 -P tb_hbm_hc_q_static.MUT=$m -P tb_hbm_hc_q_static.SAFE=${HCQ_SAFE:-0} -o $O/tb$m.vvp $SRC || exit 2
  r=$(vvp -n $O/tb$m.vvp | grep TB_HBM_HC_Q_STATIC); echo "$r"
  if [ $m = 0 ]; then [[ "$r" == *PASS* ]] || rc=1; else [[ "$r" == *FAIL* ]] || rc=1; fi
done
[ $rc = 0 ] && echo "HC_Q_STATIC BENCH PASS (cases: ${MUTS:-0 1 2 3 4} SAFE=${HCQ_SAFE:-0})" || echo "HC_Q_STATIC BENCH FAIL"
exit $rc
