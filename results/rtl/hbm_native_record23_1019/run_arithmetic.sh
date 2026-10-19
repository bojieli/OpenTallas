#!/bin/bash
set -euo pipefail
python3 run_unit.py > unit_model.log 2>&1
D=current53cb/rtl/hbm_accel/generic/adapters/static_su
args=()
while IFS= read -r d; do args+=(-y "$d"); done < <(find current53cb/rtl current53cb/physical -type d)
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version > verilator.version
"$V" --binary --timing -Wno-fatal --top-module tb --Mdir obj_arithmetic_clock -j 6 -O1 -CFLAGS -O0 +libext+.sv+.v "${args[@]}" native_record23_tb.sv pll_functional_model.sv ckgen.sv release.sv current53cb/rtl/hbm_accel/generic/vm/static/faces_q0/hfd_vms_bank_native_q0_faces.sv current53cb/rtl/hbm_accel/generic/vm/static/faces_q0/ot_vms_bank_q0_faces_core.sv current53cb/rtl/hbm_accel/generic/vm/static/faces_q0/ot_vms_bank_q0_faces_body.sv hfd_hgi_vm_calendar_f20.sv ot_hbm_host_cfg_leaf_sw.sv "$D/programme/ot_hbm_su_programme_pgcol.sv" "$D/programme/ot_hbm_su_programme.sv" "$D/programme/multirate_bridge.sv" "$D/ot_hbm_su_static_vm_ports.sv" "$D/data_store/ot_hbm_su_static_data_store.sv" current53cb/rtl/hbm_accel/die_glue/hbfd_rly_masters.sv current53cb/rtl/hbm_accel/die_glue/ot_hbm_rly.sv current53cb/rtl/hbm_accel/die_glue/hbfd_pad.sv current53cb/rtl/hdc/ot_hdc_fastfp.sv current53cb/rtl/hdc/ot_hdc_fp32_mul_lat.sv current53cb/rtl/hdc/ot_hdc_fp32_add_lat.sv current53cb/rtl/hdc/ot_hdc_fastfp_lat.sv current53cb/rtl/hdc/ot_hdc_sfu.sv current53cb/rtl/hdc/ot_hdc_prefix.sv current53cb/rtl/hdc/ot_hdc_fpu.sv current53cb/rtl/hdc/v41x/ot_hdc_v41x_sfu.sv > arithmetic_build.log 2>&1
for negative in NO_CLOCK NO_LOCK; do
 if obj_arithmetic_clock/Vtb +"$negative" +CFG=record23_profile/native18/cols/config.mem +GOLD=record23_profile/native18/quarter.mem +N=52 +W=66 > "$negative.log" 2>&1; then echo "UNEXPECTED $negative PASS"; exit 1; fi
 grep -q CLOCK_CAUSAL_GUARD "$negative.log"
done
W=$(wc -l < record23_profile/native18/cols/config.mem)
obj_arithmetic_clock/Vtb +CFG=record23_profile/native18/cols/config.mem +GOLD=record23_profile/native18/quarter.mem +N=52 +W="$W" > arithmetic.log 2>&1
W=$(wc -l < record23_profile/old_fill_mutant/cols/config.mem)
if obj_arithmetic_clock/Vtb +CFG=record23_profile/old_fill_mutant/cols/config.mem +GOLD=record23_profile/old_fill_mutant/quarter.mem +N=52 +W="$W" > old_fill_mutant.log 2>&1; then echo 'UNEXPECTED OLD FILL PASS'; exit 1; fi
grep -q 'ARITHMETIC FAIL' old_fill_mutant.log
sha256sum native_record23_tb.sv pll_functional_model.sv calendar.mem vmb.sv current_sources.tar su_SW0_gen2c_l12_source_profile.json > source.sha256
