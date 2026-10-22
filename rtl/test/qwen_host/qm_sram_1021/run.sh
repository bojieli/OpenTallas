#!/usr/bin/env bash
# SQK-INGEST 10-21: ingest_qm SRAM-FIFO fork miter (tb_qm_sram_equiv) on 8 clock / stall configurations.
# Usage: run.sh OUTDIR [DEFINE]   (DEFINE e.g. QKD_HR_QM_SRAM_MUT = bench mutant, must FAIL)
# Verilator 5.050 (the closure daemon's version) when present.
set -euo pipefail
cd "$(dirname "$0")/../../../.."
out=${1:?out}; def=${2:-}; mkdir -p "$out"; out=$(cd "$out" && pwd)
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"; [[ -x "$v" ]] || v=$(command -v verilator)
"$v" --version | tee "$out/version.txt"
python3 tools/qwen_host/native_fixture.py "$out" 2 edge > "$out/fixture.log"
read -r nd np ns < <(python3 -c "import json,sys;j=json.load(open(sys.argv[1]));print(j['descriptors'],j['beats'],j['sectors'])" "$out/fixture.json")
D=(); [[ -n "$def" ]] && D=(+define+"$def")
"$v" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-TIMESCALEMOD "${D[@]}" \
  --top-module tb_qm_sram_equiv --Mdir "$out/obj" \
  rtl/lib/ot_reset_sync.sv rtl/physical/ot_host_die_cdc_sram.sv rtl/link/ot_link_afifo.sv rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv \
  rtl/qwen_sys/host_20261013/qkd_host_native_engine.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
  physical/asap7_memory_macros/ot_sram_1r1w2c_32x546_m1_p192_mir/ot_sram_1r1w2c_32x546_m1_p192_mir.v \
  rtl/qwen_sys/host_cluster_cdc_20261018/qkd_hr_native_qm_cdc.sv \
  rtl/test/qwen_host/qm_sram_1021/qkd_hr_native_qm_cdc_ref.sv \
  rtl/test/qwen_host/qm_sram_1021/tb_qm_sram_equiv.sv > "$out/build.log" 2>&1
CFG=("1000 1666 833 0 0 0 0 0 11" "970 1666 833 0 0 0 0 0 7930" "1000 1610 833 0 0 0 10 10 15849" "1043 1700 810 0 0 0 0 30 23768"
     "1900 1667 833 0 0 0 0 0 31687" "999 1666 833 0 0 0 30 40 39606" "1000 1666 833 137 411 59 0 70 4242" "600 2500 833 0 0 0 50 20 777")
pass=0; n=0
for c in "${CFG[@]}"; do
  read -r HP IP CP HPH IPH CPH HGAP MSTALL SEED <<< "$c"
  (cd "$out" && ./obj/Vtb_qm_sram_equiv +ND=$nd +NP=$np +NSECTOR=$ns +HP=$HP +IP=$IP +CP=$CP +HPH=$HPH +IPH=$IPH +CPH=$CPH \
     +HGAP=$HGAP +MSTALL=$MSTALL +SEED=$SEED +SHARE=$(( n % 2 ? 96 : 0 ))) > "$out/cfg$n.log" 2>&1 || true
  r=$(grep -h "QM_SRAM_EQUIV" "$out/cfg$n.log" | tail -1); echo "cfg$n HP=$HP IP=$IP CP=$CP HGAP=$HGAP MSTALL=$MSTALL: $r"
  grep -q "QM_SRAM_EQUIV PASS" "$out/cfg$n.log" && pass=$((pass+1)); n=$((n+1))
done
if [[ $pass == $n ]]; then echo "QM_SRAM_EQUIV_SUITE PASS $pass/$n"; else echo "QM_SRAM_EQUIV_SUITE FAIL $pass/$n"; exit 1; fi
