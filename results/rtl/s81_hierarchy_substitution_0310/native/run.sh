#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ds-hier-native-0320
cd "$R"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
F=(v41x/ot_s81c_attn_hcore.sv v41x/ot_hdc_v41x_attn_tile_s.sv v41x/ot_hdc_v41x_kreg.sv v41x/ot_hdc_v41x_attn_tile.sv v41x/ot_hdc_v41x_attn_tile_lat.sv ot_hdc_fp32_f12.sv ot_hdc_fp32_add_lat.sv ot_hdc_prefix.sv ot_hdc_fastfp.sv v41x/ot_dsrom_su_add6.sv)
sha256sum "${F[@]}" ot_s81c_attn_hcore_5.sv libot_s81c_attn_hcore_5.a > source_hashes.txt
/usr/bin/time -v "$V" --binary --timing -O1 -j 2 --x-assign fast --x-initial fast -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD +define+OT_S81C_HCORE_CTLA +define+OT_S81C_HCORE_RST_TIMED --output-split 20000 --output-split-cfuncs 2000 -CFLAGS '-O1 -fno-var-tracking' --top-module tb -Mdir "$R/obj" "${F[@]}" ot_s81c_attn_hcore_5.sv tb.sv -LDFLAGS "$R/libot_s81c_attn_hcore_5.a" > build.log 2> build.err
"$R/obj/Vtb" > baseline.log 2>&1
"$R/obj/Vtb" +mutant > mutant.log 2>&1
