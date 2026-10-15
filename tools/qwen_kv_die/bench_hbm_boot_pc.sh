#!/usr/bin/env bash
# Controller strip masters (el1013-qwen-kvstrips): exact benches through the die buses.
#   bench.sh pc OUT_DIR [MUT]        qkd_ctrl_pc: PCs 0 13 31 (mutant: PC 13 only, MUT 1..4)
#   bench.sh kc OUT_DIR [MUT]        qkd_ctrl_kc (+ a 3-station tap chain)
# Prints "PASS qkd_ctrl_<x> ..." (rc 0) or "FAIL qkd_ctrl_<x> ..." (rc 1).  Field offsets come from kv_die.STRIP_FIELDS.
set -u
WHAT=$1; OUT=$2; MUT=${3:-0}
R=$(cd "$(dirname "$0")/../.." && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=$(command -v verilator)
mkdir -p "$OUT"
python3 - "$R" > "$OUT/qkd_strip_map.vh" <<'PY' || { echo "FAIL qkd_ctrl_$WHAT map"; exit 1; }
import sys,ast
from pathlib import Path
tree=ast.parse(Path(sys.argv[1]+'/tools/qwen_kv_die/kv_die.py').read_text())
fields=next(eval(compile(ast.Expression(n.value),'strip fields','eval'),{'__builtins__':{},'dict':dict}) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='STRIP_FIELDS' for t in n.targets))
W = dict(ci=319, co=294, es=288, er=261, po=328, pi=289, ki=33, ko=33, kc=33)
for mst, buses in fields.items():
    if mst not in ('qkd_ctrl_pc', 'qkd_ctrl_kc'):   # STRIP_FIELDS also holds the landing / aggregator strip masters (their own benches)
        continue
    for bus, fields in buses.items():
        o = 0
        for f, w in fields:
            if mst == 'qkd_ctrl_pc':
                print('localparam integer O_%s_%s = %d;' % (bus, f, o))
            o += w
        assert o == W[bus], (mst, bus, o)
PY
K=$R/rtl/qwen_sys/kv_die_20261009; E=$R/rtl/qwen_sys/emb_hbm_20261008
SRC="$R/rtl/qwen_sys/split_20261014/qkd_hbm_boot_static.sv $R/rtl/qwen_sys/split_20261014/qkd_hbm_boot_pc.sv $K/qkd_ctrl_strip.sv $K/ot_qkvd_kcmd_tap.sv $E/ot_qwen_ctrl_pc_emb.sv $E/ot_hbm_r14_stream_pc_srow.sv $E/synth/ot_qfd_emb_pcport.sv $E/ot_qfd_emb_cdc.sv $R/rtl/lib/ot_async_fifo.sv $R/rtl/lib/ot_reset_sync.sv $R/rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv"
build() { # tag top tb params...
  local tag=$1 top=$2 tb=$3; shift 3
  $V --binary --timing -O2 -j ${JOBS:-4} -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD \
     -I"$OUT" --top-module $top "$@" --Mdir "$OUT/obj_$tag" $SRC "$tb" > "$OUT/build_$tag.log" 2>&1 \
     || { tail -20 "$OUT/build_$tag.log"; echo "FAIL qkd_ctrl_$WHAT build $tag"; exit 1; }
  "$OUT/obj_$tag/V$top" > "$OUT/run_$tag.log" 2>&1
  grep -E '^(MISMATCH|PASS|FAIL)' "$OUT/run_$tag.log" | tail -6
}
build "boot$MUT" tb_qkd_hbm_boot_pc_controller "$R/rtl/test/qwen_kv_die/tb_qkd_hbm_boot_pc_controller.sv" -GMUT=$MUT > "$OUT/all.log"
cat "$OUT/all.log"
grep -q '^PASS real qkd_ctrl_pc boot' "$OUT/run_boot$MUT.log" && exit 0
exit 1
