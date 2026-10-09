#!/bin/bash
set -euo pipefail
out=$1
mkdir -p "$out"
test ! -e "$out/positive.log"
sources=(rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv
physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
rtl/experimental/dsrom_mtp_shared_20261009/ot_dsrom_mtp_shared_producer.sv
rtl/test/dsrom_mtp_shared_20261009/tb_shared_producer.sv)
iverilog -g2012 -s tb_shared_producer -o "$out/base.vvp" "${sources[@]}" > "$out/elaborate.log" 2>&1
vvp "$out/base.vvp" > "$out/positive.log" 2>&1
for bad in 1 2 3 4 5 6 7 8; do vvp "$out/base.vvp" +bad="$bad" > "$out/negative_$bad.log" 2>&1; done
for injection in CE UE; do
iverilog -g2012 -s tb_shared_producer -DSHARED_$injection -o "$out/$injection.vvp" "${sources[@]}" > "$out/$injection.elaborate.log" 2>&1
vvp "$out/$injection.vvp" > "$out/$injection.log" 2>&1
done
