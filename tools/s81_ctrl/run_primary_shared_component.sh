#!/bin/bash
# Admitted remote only; independent serial and actualwide two-domain component.
set -euo pipefail
SRC=${SRC:-$(pwd)};OUT=$1;mkdir -p "$OUT/vectors"
python3 "$SRC/tools/s81_ctrl/primary_shared_vectors.py" "$OUT/vectors"
S=("$SRC/rtl/hdc/ot_hdc_fastfp.sv" "$SRC/rtl/hdc/ot_hdc_prefix.sv" "$SRC/rtl/hdc/ot_hdc_fp32_add_lat.sv"
 "$SRC/rtl/lib/ot_reset_sync.sv" "$SRC/rtl/lib/ot_async_fifo.sv"
 "$SRC/rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv"
 "$SRC/rtl/dsrom_sys/s81_ctrl/ot_s81_primary_shared_last.sv"
 "$SRC/rtl/dsrom_sys/s81_ctrl/test/tb_s81_primary_shared_last.sv")
sha256sum "${S[@]}" "$SRC/tools/hdc_golden.py" "$OUT/vectors/expected.hex" > "$OUT/source.sha256"
for mode in serial async;do
 mkdir -p "$OUT/$mode";EXTRA=();[[ $mode == async ]]&&EXTRA=(-DPRIMARY_ASYNC)
 iverilog -g2012 "${EXTRA[@]}" -s tb_s81_primary_shared_last -o "$OUT/$mode/base.vvp" "${S[@]}" > "$OUT/$mode/build.log" 2>&1
 for bad in 0 1 2 3 4 5;do vvp "$OUT/$mode/base.vvp" +vectors="$OUT/vectors" +bad=$bad > "$OUT/$mode/bad$bad.log" 2>&1;done
done
iverilog -g2012 -DP2_MUT_PRE_ROUND -s tb_s81_primary_shared_last -o "$OUT/mut.vvp" "${S[@]}" > "$OUT/mut.build" 2>&1
if vvp "$OUT/mut.vvp" +vectors="$OUT/vectors" > "$OUT/mut.log" 2>&1;then echo MUTANT_UNEXPECTED_PASS;exit 1;fi
