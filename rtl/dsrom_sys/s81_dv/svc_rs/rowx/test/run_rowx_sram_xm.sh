#!/usr/bin/env bash
set -euo pipefail
R=$(git rev-parse --show-toplevel); O=${1:?output directory}; mkdir -p "$O"
D=$R/rtl/dsrom_sys/s81_dv/svc_rs/rowx; P=$R/physical/asap7_memory_macros
VL=${VL:-$HOME/.local/opentallas-tools/bin/verilator}
python3 - "$D/test/tb_dsdv_rowx_xm.sv" "$O/tb.sv" <<'PY'
import sys
s=open(sys.argv[1]).read();old='.MUT(`TB_MUT), .D(16)';assert s.count(old)==1
open(sys.argv[2],'w').write(s.replace(old,old+', .USE_SRAM(1)'))
PY
"$VL" --binary --timing -j "${J:-4}" -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
 -DTB_MUT=0 --top-module tb_dsdv_rowx_xm -Mdir "$O/obj" \
 "$D/dsdv_rowx_lc.sv" "$D/dsdv_rowx_lc_sram.sv" "$D/dsdv_rowx_rp.sv" "$D/dsdv_rowx_rp_sram.sv" "$D/dsdv_rowx_xm.sv" \
 "$R/rtl/lib/sram_p192_1019/ot_sram_1r1w_32x512_m1__p192.sv" \
 "$R/rtl/lib/sram_p192_1019/ot_sram_1r1w_64x512_m1_r2c2__p192.sv" \
 "$P/ot_sram_1r1w_32x512_m1_p192_mir/ot_sram_1r1w_32x512_m1_p192_mir.v" \
 "$P/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir.v" \
 "$O/tb.sv" > "$O/build.log" 2>&1
# Existing production-shape16-owner oracle: packed links at764/1000 beats/cycle,
# every link has37cycles and4cycles jitter. No new full-die simulation.
"$O/obj/Vtb_dsdv_rowx_xm" +seed=9 +pk=1 +rate=764 +rall=1 +lon=37 +lx=37 +j=4 | tee "$O/run.log"
grep -q '^ROWXM .*verdict=PASS' "$O/run.log"
