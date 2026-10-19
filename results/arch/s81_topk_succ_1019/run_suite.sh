#!/bin/bash
# S81-TOPK successor suite (Verilator 5.050): INDEXED13 + FIFO_SRAM + p192 macros + one-hot kept bank selects + RST64.
# Run from the source root.  usage: run_suite.sh <outdir>
set -uo pipefail
O=${1:?out}; mkdir -p "$O"
S=results/arch/s81_topk_final_1019/bench
DEF="-DOT_S81PH_SEL_INDEXED13 -DOT_S81PH_FIFO_SRAM -DOT_SRAM_P192 -DOT_S81PH_SEL_SUCC -DOT_S81PH_SEL_RST64"
for d in legacy indexed13 indexed13_ties indexed13_ninf indexed13_zeros indexed13_identity indexed13_corrupt indexed13_early; do
  rm -rf "$O/$d"; mkdir -p "$O/$d"; cp $S/$d/stim.txt $S/$d/exp.txt $S/$d/meta.json "$O/$d/"
done
rm -rf "$O/mut_oh"; mkdir -p "$O/mut_oh"; cp $S/indexed13/stim.txt $S/indexed13/exp.txt $S/indexed13/meta.json "$O/mut_oh/"
VL_EXTRA="$DEF" bash tools/s81_dv/layer_prog/bk/run_bk_layer.sh "$O/build" $(for d in legacy indexed13 indexed13_ties indexed13_ninf indexed13_zeros indexed13_identity indexed13_corrupt indexed13_early; do echo "$O/$d"; done)
VL_EXTRA="$DEF -DOT_S81PH_SEL_SUCC_MUT_OH" bash tools/s81_dv/layer_prog/bk/run_bk_layer.sh "$O/build_mut_oh" "$O/mut_oh"
# probe: does any stimulus read bank 1 (lines >= 128)? group-0 stuck-at-bank-0 build on every positive stim
for d in legacy indexed13 indexed13_ties indexed13_ninf indexed13_zeros; do rm -rf "$O/probe0_$d"; mkdir -p "$O/probe0_$d"; cp $S/$d/stim.txt $S/$d/exp.txt $S/$d/meta.json "$O/probe0_$d/"; done
VL_EXTRA="$DEF -DOT_S81PH_SEL_SUCC_MUT_OH0" bash tools/s81_dv/layer_prog/bk/run_bk_layer.sh "$O/build_probe0" $(for d in legacy indexed13 indexed13_ties indexed13_ninf indexed13_zeros; do echo "$O/probe0_$d"; done)
# component FIFO proof on the p192 macro (tb_fifo: MUT 0 pass, 1/2 forwarding mutants fail)
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for m in 0 1 2; do
  mkdir -p "$O/component_$m"
  $VL --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -DMUT=$m -DOT_SRAM_P192 --top-module tb_fifo results/arch/s81_topk_fifo_safe_1019/tb_fifo.sv \
    rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_queue_store.sv rtl/lib/ot_sram_showahead_1r1w.sv \
    physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1_p192_rc/ot_sram_1r1w_32x128_m1_p192_rc.v -Mdir "$O/component_$m/obj" > "$O/component_$m/build.log" 2>&1
  "$O/component_$m/obj/Vtb_fifo" > "$O/component_$m/run.log" 2>&1; echo "COMPONENT MUT=$m rc=$? $(grep -m1 -o 'FIFO [A-Z]*' $O/component_$m/run.log)"
done
python3 - "$O" <<'PY'
import json,sys
from pathlib import Path
o=Path(sys.argv[1]); r={}
for d in sorted(o.iterdir()):
    v=d/'verdict.txt'
    if v.exists(): r[d.name]=v.read_text().split()[1] if len(v.read_text().split())>1 else '?'
pos=['legacy','indexed13','indexed13_ties','indexed13_ninf','indexed13_zeros']; neg=['indexed13_identity','indexed13_corrupt','indexed13_early','mut_oh']
c=[(o/f'component_{m}/run.log').read_text() for m in range(3)]
ok=all(r.get(p)=='PASS' for p in pos) and all(r.get(n)=='FAIL' for n in neg) and 'FIFO PASS' in c[0] and 'FIFO FAIL' in c[1] and 'FIFO FAIL' in c[2]
print('SUCC_SUITE', 'PASS' if ok else 'FAIL', json.dumps(r))
sys.exit(0 if ok else 1)
PY
