#!/bin/bash
# redesign-qwen 2026-10-09: ot_qkvd_kv_wq_dist (distributed KV-die landing write queue) on kv-die's end-to-end write-path
# bench (rtl/test/qwen_kv_die/tb_qkvd_kv_wq.sv: queue -> 32 STREAM4 CDCs -> HBM-side controller model -> 32 pcport KVW 2).
#   kvwq_dist_bench.sh pos OUT : base (24 rows) and long (144 rows, controller latency 40) exact -> KVWQ_DIST_PASS
#   kvwq_dist_bench.sh neg OUT : mutants 1 (PC group swap) and 2 (wrong quarter) must be inexact, 3 (quarter 0 never pushed)
#                                must not retire every row -> KVWQ_DIST_NEG_DETECTED (rc 1)
set -u
m=$1; mkdir -p "$2"; O=$(readlink -f "$2")
W=$(cd "$(dirname "$0")/../.." && pwd)/rtl
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$VL" ] || VL=verilator
SRC="$W/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pkg.sv $W/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pcport.sv $W/hdc/kv/ot_qwen_stream4_cdc_pc.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq_dist.sv $W/test/qwen_kv_die/tb_qkvd_kv_wq.sv"
run() { local n=$1; shift
  $VL --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_qkvd_kv_wq -GDIST=1 "$@" $SRC \
      --Mdir $O/obj_$n -o Vtb > $O/build_$n.log 2>&1 || { echo "BUILD_FAIL $n"; return 2; }
  $O/obj_$n/Vtb 2>/dev/null | grep '"mut"' | tee $O/$n.json
}
if [[ $m == pos ]]; then
  ok=1
  for v in "base -GMUT=0" "long -GNROW=144 -GCTRL_LAT=40"; do set -- $v; n=$1; shift
    r=$(run $n "$@"); echo "$r"
    echo "$r" | grep -q '"exact": *true' || ok=0
    echo "$r" | grep -q '"faults": 0' || ok=0
  done
  [[ $ok == 1 ]] && { echo KVWQ_DIST_PASS; exit 0; }; echo KVWQ_DIST_FAIL; exit 1
fi
det=0
for v in "mut1 -GMUT=1" "mut2 -GMUT=2" "mut3 -GMUT=3"; do set -- $v; n=$1; shift
  r=$(run $n "$@"); echo "$n: $r"
  if [[ $n == mut3 ]]; then
    python3 -c "import json,sys; d=json.loads(sys.argv[1]) if sys.argv[1] else {}; sys.exit(0 if (not d) or d.get('retired',0) < d.get('rows',1) or not d.get('exact') else 1)" "$r" && det=$((det+1))
  else
    echo "$r" | grep -q '"exact": *false' && det=$((det+1))
  fi
done
[[ $det == 3 ]] && { echo KVWQ_DIST_NEG_DETECTED; exit 1; }
echo "KVWQ_DIST_NEG_MISSED ($det of 3)"; exit 0
