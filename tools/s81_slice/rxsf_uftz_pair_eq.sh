#!/bin/bash
# rxsf_uftz_pair_eq.sh <outdir> [base|mut] (cwd = repo root): S81-CORES-R1 lockstep bench of the rxsf -> rxsb hard-core pair
# (dsfd_su_t_rxsf m_u2 UFTZ 1) vs the shipped units.  base must PASS; mut (+define+OT_RXSF_MUT_FTZ) must FAIL.
set -u; O=$1; M=${2:-base}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
SRCS="rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_rxh.sv rtl/dsrom_sys/s81_suhc/ot_s81_su_rw.sv rtl/dsrom_sys/s81_suhc/ot_s81_su_rx.sv rtl/hdc/v41x/ot_hdc_v41x_spshort.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_dsrom_su_norm.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv"
DEF=""; [ "$M" = mut ] && DEF="+define+OT_RXSF_MUT_FTZ"
$V --binary -O2 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTITOP $DEF --top-module tb_rxsf_uftz_pair_eq -Mdir $O/obj_$M $SRCS \
  rtl/dsrom_sys/s81_suhc/test/tb_rxsf_uftz_pair_eq.sv --build-jobs ${J:-8} > $O/build_$M.log 2>&1 || { echo "BUILD_FAILED"; tail -n 12 $O/build_$M.log; exit 3; }
$O/obj_$M/Vtb_rxsf_uftz_pair_eq > $O/run_$M.log 2>&1; grep -E "MISMATCH|^RXSFPAIR|^PASS|^FAIL" $O/run_$M.log | head -12
if [ "$M" = base ]; then grep -q '^PASS' $O/run_$M.log && exit 0; exit 1; fi
grep -q '^FAIL' $O/run_$M.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED $M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED $M (bench blind)"; exit 1
