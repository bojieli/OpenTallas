#!/usr/bin/env bash
# RTLGAP-SO (10-21): build + run tb_so_golden (16 real ot_s81_su_sms, -DSU_SMU_T as in the svc slice) on the images of
# so_bench.py.  Usage (repo root): tools/s81_dv/layer_prog/svc/run_so_bench.sh OUTDIR IMGDIR   (IMGDIR/{base,cs_swap,hm_shift})
set -euo pipefail
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$(realpath -m "$1"); IMG=$2
S=rtl; D=rtl/dsrom_sys; SM=$D/s81_dv/su_sm
SRC=($SM/ot_s81_su_sms.sv $SM/ot_s81_su_smq.sv $SM/ot_s81_su_smh.sv $SM/dsfd_su_t_smh.sv $SM/dsfd_su_t_smhq.sv
     $SM/dsfd_su_t_smhr.sv $D/s81_suhc/hier/dsfd_su_t_sm.sv $D/s81_suhc/hier/ot_s81_su_sm.sv
     $S/hdc/ot_hdc_delay.sv $S/hdc/ot_hdc_fastfp_lat_f12.sv $S/hdc/ot_hdc_fastfp.sv $S/hdc/ot_hdc_fp32_add_lat.sv
     $S/hdc/ot_hdc_fp32_f12.sv $S/hdc/ot_hdc_fp32_mul_lat.sv $S/hdc/ot_hdc_prefix.sv $S/hdc/ot_hdc_sfu.sv
     $S/hdc/v41x/ot_dsrom_fp32_add_l6.sv $S/hdc/v41x/ot_dsrom_su_add6.sv $S/hdc/v41x/ot_dsrom_su_f12.sv
     $S/hdc/v41x/ot_dsrom_su_fdiv_f12.sv $S/hdc/v41x/ot_dsrom_su_softmax_add6.sv $S/hdc/v41x/ot_dsrom_su_softmax_add.sv
     $S/hdc/v41x/ot_dsrom_su_softmax_f12r.sv $S/hdc/v41x/ot_dsrom_su_softmax_m9.sv $S/hdc/v41x/ot_hdc_v41x_sfu.sv)
TB=tools/s81_dv/layer_prog/svc/tb_so_golden.sv
mkdir -p "$O"
"$VL" --version > "$O/verilator.version"
if [ ! -x "$O/obj/Vtb_so_golden" ]; then
  "$VL" --binary -O2 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_so_golden -Mdir "$O/obj" -j ${JOBS:-8} \
    --unroll-count 4 -fno-dfg -CFLAGS -O1 -DSU_SMU_T "$TB" "${SRC[@]}" > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; exit 1; }
fi
sha256sum "${SRC[@]}" $TB tools/s81_dv/layer_prog/svc/so_bench.py tools/s81_dv/layer_prog/lower_svc.py \
  tools/s81_dv/layer_prog/svc/run_so_bench.sh > "$O/sources.sha256"
for m in base cs_swap hm_shift; do
  [ -d "$IMG/$m" ] || continue
  "$O/obj/Vtb_so_golden" +dir="$IMG/$m" > "$O/run_$m.log" 2>&1 || true
  echo "$m: $(grep -h '^SOGOLD ' "$O/run_$m.log" | tail -1 | grep -o 'verdict=[A-Z]*')"
done
