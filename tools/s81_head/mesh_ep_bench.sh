#!/usr/bin/env bash
# HEAD-RTL 2026-10-26: ot_s81hd_mesh_ep_core bench (Verilator 5.050, the daemon's pinned version).  usage (repo root cwd):
#   mesh_ep_bench.sh OUTDIR        -> production (PASS expected) + mutants 1..4 (FAIL expected); exit 0 iff all as expected
set -u
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=${1:?outdir}; T=rtl/dsrom_sys/s81_head; mkdir -p "$O"; rc=0
SRC="rtl/link/ot_link_crc32.sv rtl/lib/ot_rst_relay_tree3.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv
 rtl/lib/ot_sram_oldread_b64.sv rtl/lib/ot_sram_showahead_b64.sv rtl/common/ot_link_credit_rx_b64.sv
 rtl/common/ot_link_credit_tx_rc.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe4.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv
 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv $T/ot_s81hd_util.sv $T/ot_s81hd_lsc_parts.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1/ot_sram_1r1w2c_256x64_m1.v
 $T/ot_s81hd_beat_link.sv $T/ot_s81hd_best64.sv $T/ot_s81hd_mesh_ep_core.sv $T/test/tb_s81hd_mesh_ep.sv"
"$VL" --version | tee "$O/verilator_version.txt"
for m in 0 1 2 3 4; do
  E=$([ $m = 0 ] && echo PASS || echo FAIL)
  "$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style \
    +define+OT_COLL_NATIVE32 +define+OT_COLL_NATIVE32_OFF --top-module tb_s81hd_mesh_ep -GMUT=$m \
    -Mdir "$O/obj_m$m" $SRC --build-jobs ${J:-2} > "$O/build_m$m.log" 2>&1 \
    || { echo "m$m BUILD FAIL"; grep -m10 %Error "$O/build_m$m.log"; rc=1; continue; }
  "$O/obj_m$m/Vtb_s81hd_mesh_ep" > "$O/run_m$m.log" 2>&1
  r=$(grep -oE '^MESH_EP (PASS|FAIL)' "$O/run_m$m.log" | awk '{print $2}')
  v=$([ "$r" = "$E" ] && echo OK || echo BAD); [ $v = OK ] || rc=1
  echo "mut$m expect=$E got=${r:-NONE} $v | $(grep -E '^MESH_(STATS|EP)' "$O/run_m$m.log" | tr '\n' ' ')"
done
echo "MESH_EP_BENCH rc=$rc"; exit $rc
