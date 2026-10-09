#!/usr/bin/env bash
set -eu
SRC=${1:?pinned source}
RUN=${2:?durable remote output}
mkdir -p "$RUN"
cd "$SRC"
files=(rtl/test/qwen_system/qwen_w1_macro_fixture/ot_rom_4096x266_m8.v rtl/qwen_sys/dspark_native_20261009/ot_qwen_dspark_w1_bank.sv rtl/qwen_sys/dspark_native_20261009/ot_qwen_dspark_w1_dequant.sv rtl/qwen_sys/dspark_native_20261009/ot_qwen_dspark_w1_lookup.sv rtl/test/qwen_system/tb_qwen_dspark_w1_lookup.sv)
for bank in 0 37; do
  iverilog -g2012 -DOT_QWEN_W1_SIM_NO_INSTANCE -s tb_qwen_dspark_w1_lookup -Ptb_qwen_dspark_w1_lookup.BANK="$bank" -o "$RUN/lookup_$bank" "${files[@]}" >"$RUN/compile_$bank.log" 2>&1
  vvp "$RUN/lookup_$bank" >"$RUN/run_$bank.log" 2>&1
  echo RC=0 >"$RUN/status_$bank"
done
iverilog -g2012 -DOT_QWEN_W1_SIM_NO_INSTANCE -s tb_qwen_dspark_w1_lookup -Ptb_qwen_dspark_w1_lookup.MUT=1 -o "$RUN/mutant" "${files[@]}" >"$RUN/mut_compile.log" 2>&1
if vvp "$RUN/mutant" >"$RUN/mut_run.log" 2>&1; then
 echo 'unexpected mutant PASS' >&2
 exit 1
fi
grep -q 'ROM/dequant join payload mutant' "$RUN/mut_run.log"
echo 'W1_LOOKUP_GATE_PASS positive4096+384rows_mutantblocked=1' >"$RUN/status"
