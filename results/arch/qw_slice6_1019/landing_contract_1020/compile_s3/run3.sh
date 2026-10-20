#!/usr/bin/env bash
set -euo pipefail
mkdir -p src out3
tar -xzf base3.tgz -C src
tar -xzf candidate.tgz -C src
cd src
V="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$V" --version > ../out3/version.txt
mapfile -t sources < ../all_sources.txt
sha256sum "${sources[@]}" rtl/qwen_dv/s5/btab_candidate/*.sv > ../out3/source_sha256.txt
rc=0
for top in qfd_dv_s5_flat_btab_s3_candidate qfd_dv_s5_lp_btab_s3_candidate qfd_dv_s5b_lp_btab_s3_candidate; do
 if "$V" --lint-only --timing -I. -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --top-module "$top" -DOT_S5_HARD -DOT_STATION_REGIONAL "${sources[@]}" "rtl/qwen_dv/s5/btab_candidate/$top.sv" > "../out3/$top.log" 2>&1;then echo "$top COMPILE_PASS";else echo "$top COMPILE_FAIL";rc=1;fi
done
exit "$rc"
