#!/bin/bash
# QLB-C4 10-18: SC_TX 2 image regression on the fleet (Verilator 5.050).  run_bench.sh SRC OUT KIND ARGS
#   d2d   CFG MUT      rtl/test/qwen_split/run_d2d_program.sh (CFG default: PR=1 DRV=0 KV_PIN_SEQ=0 | seqpin: PR=1 DRV=1 KV_PIN_SEQ=1)
#   lrom  MUT          tools/qwen_static_kv/layer_rom_bench.sh (production calendar; committed images must equal the compiler)
#   lcfg               tools/qwen_static_kv/run_link_cfg_boot.sh (KV link cfg target 11 from LINK_ARGS)
set -u
SRC=$1; OUT=$2; K=$3; shift 3
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
cd "$SRC" || exit 9
mkdir -p "$OUT"
verilator --version > "$OUT/verilator.version" 2>&1
case $K in
  d2d) CFG=$1; M=$2; O=$OUT/${CFG}_m$M
       if [ "$CFG" = seqpin ]; then E="PR=1 DRV=1 KV_PIN_SEQ=1"; else E="PR=1 DRV=0 KV_PIN_SEQ=0"; fi
       env $E BACKEND=verilator JOBS=4 bash rtl/test/qwen_split/run_d2d_program.sh "$O" "$M" > "$OUT/${CFG}_m$M.log" 2>&1; rc=$?
       cp "$O/run.log" "$OUT/${CFG}_m${M}_run.log" 2>/dev/null; cp "$O/source.sha256" "$OUT/${CFG}_m${M}_source.sha256" 2>/dev/null
       echo "rc=$rc" >> "$OUT/${CFG}_m$M.log";;
  lrom) M=$1; bash tools/qwen_static_kv/layer_rom_bench.sh "$OUT/lrom_m$M" "$M" 2 > "$OUT/lrom_m$M.log" 2>&1; rc=$?
       cp "$OUT/lrom_m$M/run_m$M.log" "$OUT/lrom_m${M}_run.log" 2>/dev/null; echo "rc=$rc" >> "$OUT/lrom_m$M.log";;
  lcfg) bash tools/qwen_static_kv/run_link_cfg_boot.sh "$OUT/lcfg" > "$OUT/lcfg.log" 2>&1; rc=$?; echo "rc=$rc" >> "$OUT/lcfg.log";;
esac
exit $rc
