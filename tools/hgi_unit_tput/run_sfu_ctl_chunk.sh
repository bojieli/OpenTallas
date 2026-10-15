#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j 4 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD --top-module tb_hgi_sfu_ctl_chunk -GMUT_BOUNDARY="${MUT_BOUNDARY:-0}" -GPIN_CAPTURE="${PIN_CAPTURE:-0}" -GWIDTH="${WIDTH:-75}" -GSTATUS_REG="${STATUS_REG:-0}" -GMUT_STALE_STATUS="${MUT_STALE_STATUS:-0}" -GC6="${C6:-0}" -GMUT_TAIL_LATE="${MUT_TAIL_LATE:-0}" --Mdir "$OUT/obj" rtl/lib/ot_rst_relay.sv rtl/hbm_accel/generic/peers/ot_hgi_sfu_ctl_chunk.sv rtl/test/hbm_accel/generic/tb_hgi_sfu_ctl_chunk.sv rtl/hdc/v41x/ot_hdc_v41x_sfu_c12.sv > "$OUT/build.log" 2>&1
rc=0; "$OUT/obj/Vtb_hgi_sfu_ctl_chunk" > "$OUT/run.log" 2>&1 || rc=$?
cat "$OUT/run.log"   # always: a negative bench's fail_regex reads the stage log (set -e used to exit before this)
exit $rc
