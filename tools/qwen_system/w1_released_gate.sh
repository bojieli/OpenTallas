#!/usr/bin/env bash
set -eu
SRC=${1:?pinned source}
RUN=${2:?durable remote output}
CKPT=${3:?released checkpoint}
mkdir -p "$RUN"
sha256sum "$CKPT" > "$RUN/checkpoint.sha256"
python3 "$SRC/tools/qwen_system/qwen_w1_released_export.py" --checkpoint "$CKPT" --out "$RUN/images" > "$RUN/export.log" 2>&1
files=("$SRC/rtl/test/qwen_system/qwen_w1_macro_fixture/ot_rom_4096x266_m8.v" "$SRC/rtl/qwen_sys/dspark_native_20261009/ot_qwen_dspark_w1_bank.sv" "$SRC/rtl/qwen_sys/dspark_native_20261009/ot_qwen_dspark_w1_dequant.sv" "$SRC/rtl/qwen_sys/dspark_native_20261009/ot_qwen_dspark_w1_lookup.sv" "$SRC/rtl/test/qwen_system/tb_qwen_dspark_w1_released.sv")
for bank in 0 37; do
  iverilog -g2012 -DOT_QWEN_W1_SIM_NO_INSTANCE -s tb_qwen_dspark_w1_released -Ptb_qwen_dspark_w1_released.BANK="$bank" -o "$RUN/released_$bank" "${files[@]}" >"$RUN/compile_$bank.log" 2>&1
  (cd "$RUN/images/bank$bank"; vvp "$RUN/released_$bank") >"$RUN/run_$bank.log" 2>&1
  echo RC=0 >"$RUN/status_$bank"
done
iverilog -g2012 -DOT_QWEN_W1_SIM_NO_INSTANCE -s tb_qwen_dspark_w1_released -Ptb_qwen_dspark_w1_released.MUT=1 -o "$RUN/mutant" "${files[@]}" >"$RUN/mut_compile.log" 2>&1
if (cd "$RUN/images/bank0";vvp "$RUN/mutant") >"$RUN/mut_run.log" 2>&1; then
 echo 'unexpected mutant PASS' >&2
 exit 1
fi
grep -q 'ROM/dequant join payload mutant' "$RUN/mut_run.log"
echo 'W1_RELEASED_GATE_PASS realcheckpoint_W8_candidate4096+384rows_mutantblocked=1 BF16qualityproof=0' >"$RUN/status"
