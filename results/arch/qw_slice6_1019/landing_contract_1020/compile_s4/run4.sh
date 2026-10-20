#!/usr/bin/env bash
set -euo pipefail
mkdir -p src out4
tar -xzf base4.tgz -C src
tar -xzf candidate4.tgz -C src
cd src
V="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$V" --version > ../out4/version.txt
mapfile -t sources < ../all_sources4.txt
sha256sum "${sources[@]}" rtl/qwen_dv/s5/btab_candidate/*.sv > ../out4/source_sha256.txt
rc=0
for top in qfd_dv_s5_flat_btab_s4_candidate qfd_dv_s5_lp_btab_s4_candidate qfd_dv_s5b_lp_btab_s4_candidate; do
 if "$V" --lint-only --timing -I. -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --top-module "$top" -DOT_S5_HARD -DOT_STATION_REGIONAL "${sources[@]}" "rtl/qwen_dv/s5/btab_candidate/$top.sv" > "../out4/$top.log" 2>&1;then echo "$top COMPILE_PASS";else echo "$top COMPILE_FAIL";rc=1;fi
done
exit "$rc"
