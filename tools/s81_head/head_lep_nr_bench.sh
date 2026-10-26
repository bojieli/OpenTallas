#!/usr/bin/env bash
# Invoke inside an ot-run admitted/staged source repository.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=${1:?new output directory required}
if [ -e "$OUT" ]; then echo "refusing existing output $OUT" >&2; exit 2; fi
mkdir -p "$OUT"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
GEN=$ROOT/rtl/dsrom_sys/s81_head/generated/ot_s81hd_lep_nr.sv
for kind in mem rx mu; do
  D=$OUT/$kind; mkdir -p "$D"
  cp "$GEN" "$D/"
  if [ "$kind" = mem ]; then
    TOP=tb_head_nr_mem
    cp "$ROOT/rtl/lib/ot_sram_oldread_wreg.sv" "$D/"
    cp "$ROOT/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r0c0/ot_sram_1r1w_512x128_m4_r0c0.v" "$D/nr_macro.v"
    cp "$ROOT/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v" "$D/legacy_macro.v"
  elif [ "$kind" = rx ]; then
    TOP=tb_head_rx_nr
    cp "$ROOT/rtl/lib/ot_sram_showahead_1r1w.sv" "$D/"
    cp "$ROOT/physical/asap7_memory_macros_v2/ot_sram_1r1w_32x128_m1_r0c0/ot_sram_1r1w_32x128_m1_r0c0.v" "$D/nr_macro.v"
    cp "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v" "$D/legacy_macro.v"
  else
    TOP=tb_head_mu_nr
    cp "$ROOT/rtl/dsrom_sys/s81_dv/slice/dsdv_mu_land.sv" "$ROOT/rtl/lib/ot_rst_relay.sv" "$D/"
    cp "$ROOT/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r0c0/ot_sram_1r1w_128x256_m1_r0c0.v" "$D/nr_macro.v"
    cp "$ROOT/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" "$D/legacy_macro.v"
    python3 - "$GEN" "$D/mut.sv" <<'PY'
from pathlib import Path
import re,sys
s=Path(sys.argv[1]).read_text();s=re.search(r'^module dsdv_mu_land_head_nr\b.*?^endmodule',s,re.M|re.S).group()
s=s.replace('module dsdv_mu_land_head_nr','module dsdv_mu_land_head_nr_mut',1).replace(".r_addr_in(7'(ra))",".r_addr_in(7'(ra)^7'd1)")
Path(sys.argv[2]).write_text(s+'\n')
PY
  fi
  cp "$ROOT/rtl/dsrom_sys/s81_head/test/$TOP.sv" "$D/"
  verilator --binary --timing -j "${BUILD_THREADS:-2}" -Wno-fatal --top-module "$TOP" --Mdir "$D/obj" "$D"/*.sv "$D"/*.v > "$D/build.log" 2>&1
  "$D/obj/V$TOP" > "$D/run.log" 2>&1
  cat "$D/run.log"
done
