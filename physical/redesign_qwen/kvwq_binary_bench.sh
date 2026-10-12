#!/bin/bash
# Binary ctl feed, one full32-PC stack: realCDC -> controller model -> KVW2 -> HBM.
# Positive includes opt-in-off reference and 24/144 rows; four mutants include
# binary-index corruption (MUT5). No build failure counts as mutant detection.
set -uo pipefail
m=$1; mkdir -p "$2"; O=$(readlink -f "$2")
W=$(cd "$(dirname "$0")/../.." && pwd)/rtl
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$VL" ] || VL=verilator
SRC="$W/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pkg.sv $W/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pcport.sv $W/hdc/kv/ot_qwen_stream4_cdc_pc.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq_dist.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq_tiles.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq_tiles_top.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq_ctl_binary.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq_leaves_binary.sv $W/hdc/ot_hdc_delay.sv $W/test/qwen_kv_die/tb_qkvd_kv_wq_binary.sv"
run() { local n=$1; shift
  $VL --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_qkvd_kv_wq_binary -GDIST=3 -GFLANE_BINARY=${FLANE_BINARY:-1} -GHEAD_PIPE=${HEAD_PIPE:-0} -GRLY=${RLY:-1} "$@" $SRC \
      --Mdir $O/obj_$n -o Vtb > $O/build_$n.log 2>&1 || { echo "BUILD_FAIL $n"; return 2; }
  $O/obj_$n/Vtb 2>/dev/null | grep '"mut"' | tee $O/$n.json
}
if [[ $m == pos ]]; then
  ok=1
  for v in "baseline -GMUT=0 -GFLANE_BINARY=0" "base -GMUT=0" "long -GNROW=144 -GCTRL_LAT=40"; do set -- $v; n=$1; shift
    r=$(run $n "$@"); rc=$?; echo "$r"
    [[ $rc == 0 ]] || exit 2
    echo "$r" | grep -q '"exact": *true' || ok=0
    echo "$r" | grep -q '"faults": 0' || ok=0
  done
  python3 - "$O/baseline.json" "$O/base.json" <<'PY2'
import json,sys
base=json.load(open(sys.argv[1])); binary=json.load(open(sys.argv[2]))
assert base==binary, (base,binary)
PY2
  [[ $? == 0 ]] || ok=0
  [[ $ok == 1 ]] && { echo KVWQ_BINARY_PASS; exit 0; }; echo KVWQ_BINARY_FAIL; exit 1
fi
det=0
for v in "mut1 -GMUT=1" "mut2 -GMUT=2" "mut3 -GMUT=3" "mut5 -GMUT=5"; do set -- $v; n=$1; shift
  r=$(run $n "$@"); rc=$?; echo "$n: $r"
  [[ $rc == 0 && -s "$O/$n.json" ]] || exit 2
  if [[ $n == mut3 ]]; then
    python3 -c "import json,sys; d=json.loads(sys.argv[1]); sys.exit(0 if d.get('retired',0) < d.get('rows',1) or not d.get('exact') else 1)" "$r" && det=$((det+1))
  else
    echo "$r" | grep -q '"exact": *false' && det=$((det+1))
  fi
done
[[ $det == 4 ]] && { echo KVWQ_BINARY_NEG_DETECTED; exit 1; }
echo "KVWQ_BINARY_NEG_MISSED ($det of 4)"; exit 0
