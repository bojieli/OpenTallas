#!/bin/bash
set -euo pipefail
O=../out_reset_asr;mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
S=(rtl/dsrom_sys/s81_dv/svc_rs/ot_s81svc_reset9_n32.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs_glue.sv)
"$V" --binary --timing -j 4 -Wno-fatal -Irtl/dsrom_sys/s81_dv/svc_rs --top-module tb_asr --Mdir "$O/obj" "${S[@]}" tools/s81_dv/svc_rs/reset_profile/tb_asr.sv > "$O/build.log" 2>&1
"$O/obj/Vtb_asr" > "$O/run.log" 2>&1;cat "$O/run.log"
bash tools/s81_dv/svc_rs/reset_profile/run_tr_reset.sh
