#!/bin/bash
# usage: run_fsr.sh TAG [extra verilator defines]  ; from repo root
set -u; cd "$(dirname "$0")/../../.."; O=results/die_hbm_1105/sk_fsr; D=${OUT:-/tmp/h66fsr}/$1; T=$1; shift; mkdir -p $D
V=${VERILATOR:-verilator}
C=rtl/hbm_accel/integrated_20261006/sfu_c12_selected; K=rtl/hbm_accel/cores_split/sk_en_q4
F=""; for f in $(python3 -I - <<PY
import json
r=json.load(open("physical/die_plan/hbm_arch_cores/recipes_b2.json"))
print(" ".join(r["ot_hbm_hc_root_static__tailx_rest__v6bc7f2"]["files"]))
PY
); do case $f in *rest_core*) ;; *) F="$F $f";; esac; done
for f in 00_ot_hdc_fastfp_lat_c12 01_ot_hdc_fp32_f12 02_ot_hdc_prefix 03_ot_dsrom_su_add6 04_ot_dsrom_su_f12 05_ot_hdc_fsqrt_c12 06_ot_hdc_v41x_sfu_c12 08_ot_hdc_delay 09_ot_hdc_sfu 14_ot_hdc_fastfp; do case " $F " in *" $C/$f.sv "*) ;; *) F="$F $C/$f.sv";; esac; done
S="$K/ot_hbm_hc_tail_rest_core_ce.sv $K/ot_hdc_sinkhorn_se.sv $K/ot_hdc_sinkhorn_se_phys.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv rtl/hdc/v41/ot_hdc_sinkhorn_fs.sv rtl/hdc/v41/ot_hdc_skf_predecode.sv $K/ot_hbm_hc_tail_unit_static_ce_phys.sv rtl/hbm_accel/cores_split/sk_fsr_1105/ot_hbm_hc_tail_rest_core_fsr.sv rtl/hbm_accel/cores_split/sk_fsr_1105/ot_hbm_hc_tail_sk_fsr.sv"
$V --binary --timing -Wno-fatal -Wno-WIDTH -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-MULTIDRIVEN -Wno-CASEINCOMPLETE -O2 --threads 2 -CFLAGS -O1 --top-module tb -Mdir $D "$@" $F $S $O/tb_fsr.sv > $D/build.log 2>&1 || { tail -20 $D/build.log | cut -c1-200; echo BUILD FAIL $T; exit 2; }
timeout ${SIMT:-900} $D/Vtb > $D/run.log 2>&1; tail -4 $D/run.log | cut -c1-260; echo "$T rc=$?"
