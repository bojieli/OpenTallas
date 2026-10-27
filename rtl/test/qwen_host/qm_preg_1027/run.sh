#!/usr/bin/env bash
# QK-CORES-6: tb_qm_preg_equiv (ENG_PREG 1 vs 0 transaction miter) on clock / gap / stall configs. run.sh OUTDIR [DEFINE]
set -euo pipefail
cd "$(dirname "$0")/../../../.."
out=${1:?out}; def=${2:-}; mkdir -p "$out"; out=$(cd "$out" && pwd)
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"; [[ -x "$v" ]] || v=$(command -v verilator)
"$v" --version | tee "$out/version.txt"
python3 tools/qwen_host/native_fixture.py "$out" 2 edge > "$out/fixture.log"
read -r nd np ns < <(python3 -c "import json,sys;j=json.load(open(sys.argv[1]));print(j['descriptors'],j['beats'],j['sectors'])" "$out/fixture.json")
pass=0; n=0
for sc in 0 1; do
  D=(); [[ $sc == 1 ]] && D+=(+define+QM_PREG_SAMECLK); [[ -n "$def" ]] && D+=(+define+"$def")
  "$v" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-TIMESCALEMOD "${D[@]}" \
    --top-module tb_qm_preg_equiv --Mdir "$out/obj$sc" \
    rtl/lib/ot_reset_sync.sv rtl/link/ot_link_afifo.sv rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv \
    rtl/qwen_sys/host_20261013/qkd_host_native_engine.sv rtl/qwen_sys/host_20261013/qkd_host_native_engine_preg.sv \
    physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
    rtl/qwen_sys/host_20261013/qkd_host_native_qm_debt.sv \
    rtl/test/qwen_host/qm_preg_1027/tb_qm_preg_equiv.sv > "$out/build$sc.log" 2>&1 || { tail -30 "$out/build$sc.log"; exit 2; }
  if [[ $sc == 1 ]]; then CFG=("833 833 833 0 0 11" "833 833 833 30 40 7930" "833 833 833 10 70 4242")
  else CFG=("1000 1666 833 0 0 11" "970 1666 833 0 0 7930" "1000 1610 833 10 10 15849" "1043 1700 810 0 30 23768" "999 1666 833 30 40 39606" "600 2500 833 50 20 777"); fi
  for c in "${CFG[@]}"; do
    read -r HP IP CP HGAP MSTALL SEED <<< "$c"
    (cd "$out" && timeout 3000 ./obj$sc/Vtb_qm_preg_equiv +ND=$nd +NP=$np +NSECTOR=$ns +HP=$HP +IP=$IP +CP=$CP \
       +HGAP=$HGAP +MSTALL=$MSTALL +SEED=$SEED +SHARE=$(( n % 2 ? 96 : 0 ))) > "$out/cfg$n.log" 2>&1 || true
    r=$(grep -h "QM_PREG_EQUIV" "$out/cfg$n.log" | tail -1); echo "cfg$n SAMECLK=$sc HP=$HP IP=$IP CP=$CP HGAP=$HGAP MSTALL=$MSTALL: $r"
    grep -q "QM_PREG_EQUIV PASS" "$out/cfg$n.log" && pass=$((pass+1)); n=$((n+1))
  done
done
if [[ $pass == $n ]]; then echo "QM_PREG_EQUIV_SUITE PASS $pass/$n"; else echo "QM_PREG_EQUIV_SUITE FAIL $pass/$n"; exit 1; fi
