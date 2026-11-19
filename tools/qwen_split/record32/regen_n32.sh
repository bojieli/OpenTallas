#!/bin/bash
# regen_n32.sh [OUT_DIR] [--install]      (FABLE-FIX-S81-GLUE 2026-11-19)
# The recorded generator command of rtl/qwen_split/qfd_sys_face_record_port_n32.sv (QC glue u_record):
#   readable source  rtl/qwen_split/qfd_sys_face_record_port_bal.sv   (depth-balanced, register-identical rewrite of
#                    qfd_sys_face_record_port + qkd_program_commit + qkd_context_records; 0 added cycles)
#   1 yosys synth -flatten -noabc -nofsm (MU_HEAD 1)           -> generic 2-input gates, the source's registers
#   2 depth_opt.py                                             -> arrival-aware AND/OR/XOR re-association (NAND / NOR levels)
#   3 bound_record_graph.py --load-cap 8 --retain-all-comb --transparent-inverters --shared-helpers
#       --port-shape n32_port_shape.json                       -> fanout-bounded netlist with the SAME 36 source copies and
#                                                                 54 reset leaves the parents already bind
#   4 prove_rewrite.py + yosys sat (twice)                     -> the readable rewrite, then the EMITTED graph, against the
#                                                                 original source: every register next state and every
#                                                                 output, arbitrary state and inputs
#   5 run_bench.sh (with --install)                            -> Verilator lockstep of the emitted file against the original
#                                                                 source + the 3 mutants
# Without --install the netlist is only written to OUT_DIR (default bench/record32_regen).  Seconds on one core.
set -eu
cd "$(dirname "$0")/../../.."
OUT=bench/record32_regen; INSTALL=0
for a in "$@"; do case "$a" in --install) INSTALL=1;; *) OUT=$a;; esac; done
Y=${YOSYS:-/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys}
T=tools/qwen_split/record32
mkdir -p "$OUT"
"$Y" -V | tee "$OUT/tool.txt"
OLD="rtl/qwen_split/qfd_sys_face_record_port.sv rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv"
NEW=rtl/qwen_split/qfd_sys_face_record_port_bal.sv
"$Y" -Q -q -l "$OUT/old_synth.log" -p "read_verilog -sv $OLD; chparam -set MU_HEAD 1 qfd_sys_face_record_port; synth -top qfd_sys_face_record_port -flatten -noabc -nofsm; write_json $OUT/old.json"
"$Y" -Q -q -l "$OUT/new_synth.log" -p "read_verilog -sv $NEW; chparam -set MU_HEAD 1 qfd_sys_face_record_port_bal; synth -top qfd_sys_face_record_port_bal -flatten -noabc -nofsm; write_json $OUT/new.json"
python3 -I $T/depth_opt.py "$OUT/new.json" qfd_sys_face_record_port_bal "$OUT/new_opt.json" --report | tee "$OUT/depth_opt.log"
python3 -I $T/bound_record_graph.py "$OUT/new_opt.json" --top qfd_sys_face_record_port_bal --name qfd_sys_face_record_port_n32 \
  --out "$OUT/body.sv" --helpers "$OUT/helpers.sv" --record "$OUT/record32_receipt.json" \
  --load-cap 8 --retain-all-comb --transparent-inverters --shared-helpers --port-shape $T/n32_port_shape.json > "$OUT/generate.log"
{ head -1 "$OUT/body.sv"
  echo "// Source rtl/qwen_split/qfd_sys_face_record_port_bal.sv; regenerate and prove: bash tools/qwen_split/record32/regen_n32.sh --install"
  tail -n +2 "$OUT/body.sv"; cat "$OUT/helpers.sv"; } > "$OUT/qfd_sys_face_record_port_n32.sv"
prove() {   # NAME [--receipt FILE]
  local n=$1; shift
  python3 -I $T/prove_rewrite.py "$OUT/old.json" qfd_sys_face_record_port "$OUT/new.json" qfd_sys_face_record_port_bal "$OUT/$n.sv" "$@" | tee "$OUT/$n.build.log"
  "$Y" -Q -q -l "$OUT/$n.sat.log" -p "read_verilog $OUT/$n.sv; prep -top record32_rewrite; sat -verify -prove bad 0" >/dev/null 2>&1 || { tail -5 "$OUT/$n.sat.log"; echo "RECORD32_REGEN_FAIL $n"; exit 1; }
  grep -q 'SAT proof finished - no model found: SUCCESS!' "$OUT/$n.sat.log" || { echo "RECORD32_REGEN_FAIL $n"; exit 1; }
  echo "RECORD32_PROOF_PASS $n"
}
prove rewrite_source
prove rewrite_emitted --receipt "$OUT/record32_receipt.json"
python3 -I - "$OUT" <<'PY'
import json, sys, collections
o = sys.argv[1]
r = json.load(open(o + '/record32_receipt.json'))
print('RECORD32_SHAPE cells', r['final_cells'], 'copies', len(r['input_copies']), 'leaves', len(r['reset_leaves']),
      'max leaf', max(len(l['cells']) for l in r['reset_leaves']), 'by type', json.dumps(r['final_by_type'], sort_keys=True))
PY
if [ "$INSTALL" = 1 ]; then
  cp "$OUT/qfd_sys_face_record_port_n32.sv" rtl/qwen_split/qfd_sys_face_record_port_n32.sv
  bash $T/run_bench.sh
fi
echo RECORD32_REGEN_PASS
