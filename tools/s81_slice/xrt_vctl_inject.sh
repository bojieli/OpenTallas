#!/bin/bash
# Real rstop/XRT/rstop control injection timing, plus RTL and timing-metadata negative controls.
set -euo pipefail
out=$1
mkdir -p "$out"
V=$HOME/.local/opentallas-tools/bin/verilator
for hb in 0 1; do
 "$V" --binary --timing -Wno-fatal -Wno-WIDTH -Wno-PINMISSING -GHB=$hb --top-module tb_xrt_vctl_inject \
  -Mdir "$out/obj$hb" --build-jobs 4 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0' \
  rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv \
  rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv rtl/dsrom_sys/s81_dv/slice/test/tb_xrt_vctl_inject.sv >"$out/build$hb.log" 2>&1
 "$out/obj$hb/Vtb_xrt_vctl_inject" >"$out/run$hb.log" 2>&1
 grep '^XRT_INJECT\|^PASS\|^FAIL' "$out/run$hb.log"
 grep -q '^PASS' "$out/run$hb.log"
 "$out/obj$hb/Vtb_xrt_vctl_inject" +age=6 >"$out/age_mut$hb.log" 2>&1
 grep -q '^FAIL' "$out/age_mut$hb.log"
done
# Alter actual forwarding hops in XRT; the bit-exact line comparison must detect this.
"$V" --binary --timing -Wno-fatal -Wno-WIDTH -Wno-PINMISSING -GHB=1 +define+OT_S81SL_XR_MUT_HOPS \
 --top-module tb_xrt_vctl_inject -Mdir "$out/obj_mut" --build-jobs 4 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0' \
 rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv \
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv rtl/dsrom_sys/s81_dv/slice/test/tb_xrt_vctl_inject.sv >"$out/build_mut.log" 2>&1
"$out/obj_mut/Vtb_xrt_vctl_inject" >"$out/run_mut.log" 2>&1
grep -q '^FAIL' "$out/run_mut.log"
echo 'XRT_INJECT_NEGATIVES_CAUGHT age0 age1 hops'
sha256sum rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv >"$out/sources.sha256"
