#!/usr/bin/env bash
# HEAD-CORE-R17 2026-10-27: copy-B burst-FIFO depth at the production static schedule (tb_s81hd_mesh_ep_burst.sv).
#   mesh_ep_burst_bench.sh OUTDIR [BQ=2]     (repo root cwd; Verilator 5.050, the daemon's pinned version)
# 1 sweep the lane-b blackout window W (+W=) with BQ 32: the largest W without a link fault = worst protocol stall S
#   (8 ACK-timeout replays); W one step longer must end in the link fault (retry limit reached = the protocol bound).
# 2 at that worst W with lane a blacked out too (+BOTH: both bursts on the same edges, copy A first on the port):
#   production BQ PASS (exact, no fault), mutant MUT 7 (BQ - 1) FAIL (record lost + ep_fault[10]).
# exit 0 iff all as expected.
set -u
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=${1:?outdir}; BQP=${2:-2}; T=rtl/dsrom_sys/s81_head; mkdir -p "$O"; rc=0
SRC="rtl/link/ot_link_crc32.sv rtl/lib/ot_rst_relay_tree3.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv
 rtl/lib/ot_sram_oldread_b64.sv rtl/lib/ot_sram_showahead_b64.sv rtl/common/ot_link_credit_rx_b64.sv
 rtl/common/ot_link_credit_tx_rc.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe4.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv
 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv $T/ot_s81hd_util.sv $T/ot_s81hd_lsc_parts.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1/ot_sram_1r1w2c_256x64_m1.v
 $T/ot_s81hd_beat_link.sv $T/ot_s81hd_best64.sv $T/ot_s81hd_mesh_ep_core.sv $T/test/tb_s81hd_mesh_ep_burst.sv"
"$VL" --version | tee "$O/verilator_version.txt"
build() {  # name BQ MUT
  "$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style \
    +define+OT_COLL_NATIVE32 +define+OT_COLL_NATIVE32_OFF --top-module tb_s81hd_mesh_ep_burst -GBQ=$2 -GMUT=$3 \
    -Mdir "$O/obj_$1" $SRC --build-jobs ${J:-4} > "$O/build_$1.log" 2>&1 || { echo "$1 BUILD FAIL"; grep -m10 %Error "$O/build_$1.log"; exit 2; }
}
build wide 32 0 & build prod "$BQP" 0 & build mut "$BQP" 7 & wait
for b in wide prod mut; do test -x "$O/obj_$b/Vtb_s81hd_mesh_ep_burst" || { echo "$b BUILD FAIL"; exit 2; }; done
run() { L="$O/run_$1_W$2${3#+}.log"; "$O/obj_$1/Vtb_s81hd_mesh_ep_burst" +W=$2 $3 > "$L" 2>&1; grep -h '^MESH_' "$L" | tr '\n' ' '; echo; }
# 1 sweep (coarse 250, then fine 10 around the fault edge)
WS=""; for w in $(seq 9000 250 14500); do WS="$WS $w"; done
for w in $WS; do run wide $w "" > "$O/sweep_W$w.txt" & done; wait
lastok=0; for w in $WS; do grep -q 'MESH_EP PASS' "$O/sweep_W$w.txt" && lastok=$w; done
for w in $(seq $lastok 10 $((lastok + 250))); do run wide $w "" > "$O/fine_W$w.txt" & done; wait
wmax=$lastok; for w in $(seq $lastok 10 $((lastok + 250))); do grep -q 'MESH_EP PASS' "$O/fine_W$w.txt" && wmax=$w; done
{ for w in $WS; do echo "W=$w $(cat "$O/sweep_W$w.txt")"; done; for w in $(seq $lastok 10 $((lastok + 250))); do echo "fine W=$w $(cat "$O/fine_W$w.txt")"; done; } > "$O/sweep.txt"
echo "WORST_W $wmax: $(grep -h MESH_BURST_STALL "$O/run_wide_W$wmax.log")"
echo "WORST_W $wmax wide: $(grep -h 'MESH_FIFO\|MESH_EP' "$O/run_wide_W$wmax.log" | tr '\n' ' ')"
f=$(run wide $((wmax + 10)) +EXPECT_LINKFAULT); echo "W=$((wmax + 10)) protocol limit: $f"; echo "$f" | grep -q 'MESH_EP LINKFAULT' || rc=1
p=$(run prod $wmax ""); echo "prod BQ=$BQP W=$wmax expect=PASS: $p"; echo "$p" | grep -q 'MESH_EP PASS' || rc=1
m1=$(run mut $wmax ""); echo "mut7 BQ-1=$((BQP - 1)) W=$wmax lane b only (info: copy A idle, the port drains B at once): $m1"
p2=$(run prod $wmax +BOTH); echo "prod BQ=$BQP W=$wmax +BOTH expect=PASS: $p2"; echo "$p2" | grep -q 'MESH_EP PASS' || rc=1
m=$(run mut $wmax +BOTH); echo "mut7 BQ-1=$((BQP - 1)) W=$wmax +BOTH expect=FAIL: $m"; echo "$m" | grep -q 'MESH_EP FAIL' || rc=1
p0=$(run prod 0 ""); echo "prod BQ=$BQP W=0 (no impairment) expect=PASS: $p0"; echo "$p0" | grep -q 'MESH_EP PASS' || rc=1
echo "MESH_EP_BURST_BENCH rc=$rc"; exit $rc
