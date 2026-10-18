#!/usr/bin/env bash
# run_xdie_hbm_link.sh <src root> <out dir>   (TOKEN-XDIE-HBM 2026-10-18; Verilator 5.050, run on the fleet via ot-run)
# Two-die HBM d4g GEN2 cross-die transport co-sim (tb_xdie_hbm_link.sv header): COLL rail endpoint ot_hgi_coll_link_e
# (extracted byte-identical from the GEN2 COLL parent source ot_hfd_coll_q_hard_v5.sv) + RLY lane relays + hfd_ep_static
# + ot_pdie_serdes (KP4) per die; off-chip flight modelled.
#   pass 0  calibration (+PROBE, dynamic): measures DRX and the landing / ready bounds -> static LA, LXB, GAPB
#   pass DS  switched crossing SWD=333 (277.6 ns switch+cable) at the census payload sweep, static bound LXB, must PASS
#   pass QW  in-package (Qwen TP8, no switch) SWD=4 (3.3 ns package trace), same sweep, must PASS
#   mutants  m1 (EPMUT_B 2), m2 (+MUT=2), m3, m4, m5 (EPMUT_B 4): each must FAIL; logs kept as fail witnesses
set -u
SRC=$(realpath "$1"); OUT=$(realpath -m "$2"); mkdir -p "$OUT/src"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
X=$SRC/rtl/hbm_accel/generic/collective/xdie; P=$SRC/rtl/hbm_accel/generic/collective/p2p
E=$SRC/rtl/hbm_accel/tu/ep_static_20261015; L=$SRC/rtl/dsrom_sys/s81_link; Q=$SRC/rtl/qwen_sys/split_20261014
# the GEN2 COLL rail endpoint modules, byte-identical text from the parent source
awk '/^module ot_hgi_coll_capture_ctl_e\(/{on=1} on{print} on&&/^endmodule/{on=0;print ""}
     /^module ot_hgi_coll_link_e\(/{on2=1} on2&&!on{print} on2&&/^endmodule/{on2=0}' "$P/ot_hfd_coll_q_hard_v5.sv" \
  | sed '1i `timescale 1ns/1ps' > "$OUT/src/ot_hgi_coll_link_e_extract.sv"
grep -c '^module' "$OUT/src/ot_hgi_coll_link_e_extract.sv" | grep -qx 2 || { echo "XDIE extract failed"; exit 2; }
F="$X/tb_xdie_hbm_link.sv $OUT/src/ot_hgi_coll_link_e_extract.sv $P/ot_hgi_coll_static_capture_ctl.sv
   $P/ot_hgi_coll_static_pinreg_ctl.sv $P/ot_hgi_coll_static_pinreg_store.sv $P/ot_hgi_coll_static_seq_ctl.sv
   $Q/ot_qkvd_d2d_llr.sv $Q/ot_qwen_crc_parallel.sv
   $SRC/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
   $E/hfd_ep_static.sv $E/ot_hep_rx_store.sv $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_dec.sv $L/ot_pdie_serdes.sv
   $SRC/physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v
   $SRC/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v"
sha256sum $F $P/ot_hfd_coll_q_hard_v5.sv $P/ot_hfd_coll_q_hard_v8g.sv > "$OUT/sources.sha256"
build() {  # name EPMUT_B
  "$V" --binary --timing -O2 -j ${JOBS:-8} -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
    -Wno-TIMESCALEMOD -Wno-INITIALDLY +incdir+$L --top-module tb_xdie_hbm_link -GEPMUT_B=$2 --Mdir "$OUT/obj_$1" -o tb $F \
    > "$OUT/build_$1.log" 2>&1 || { tail -40 "$OUT/build_$1.log"; echo "XDIE build $1 FAIL"; exit 2; }
}
run() {  # log args...
  local lg=$1 b=$2; shift 2
  timeout 7200 "$OUT/obj_$b/tb" +verilator+seed+7 "$@" > "$OUT/$lg.log" 2>&1
  grep -E 'XDIE_(PROBE|INST|STATIC|HBM|SCHED|ERR)' "$OUT/$lg.log" | head -40
}
build base 0
# pass 0 (calibration, PROBE: dynamic arm-on-landing / release-on-ready, only to MEASURE the landing bounds; 4 + 256 + 64 frames)
probe() {  # tag swd -> sets DRXO LA LXB GAPB
  run p0_probe_$1 base +PROBE +NI=3 +P0=4 +P1=256 +P2=64 +GAPB=240 +SWD=$2
  DRXO=$(grep -m1 -o 'drain->COLL pin [0-9]*' "$OUT/p0_probe_$1.log" | awk '{print $3}')
  RL=$(grep -m1 -o 'worst_ready_after_tx_last=[0-9.]*' "$OUT/p0_probe_$1.log" | cut -d= -f2)
  LMIN=$(grep -m1 -o 'min=[0-9.]*' "$OUT/p0_probe_$1.log" | cut -d= -f2); LMAX=$(grep -m1 -o 'max=[0-9.]*' "$OUT/p0_probe_$1.log" | cut -d= -f2)
  grep -q '^XDIE_HBM .* PASS$' "$OUT/p0_probe_$1.log" && [ -n "$DRXO" ] && [ -n "$RL" ] && [ -n "$LMAX" ] || { echo "XDIE probe $1 failed"; exit 3; }
  # compiler constants from the measured bounds: arm LA = landing max + 2 cycles; release LXB = ready max + 8 cycles;
  # inter-block TX gap GAPB = (LA - landing min) in cycles + 6 (arm pin path 2.5 + 2 guard + 1 landing)
  read LA LXB GAPB < <(python3 -c "import math;cn=1/1.2;la=$LMAX+2*cn;print(int(round(la*1000)),int(round(($RL+8*cn)*1000)),math.ceil((la-$LMIN)/cn)+6)")
  echo "XDIE_CONST $1 DRX=$DRXO landing=[$LMIN,$LMAX] ns ready_max=$RL ns -> LA_PS=$LA LXB_PS=$LXB GAPB=$GAPB" | tee -a "$OUT/constants.txt"
}
SWEEP="+NI=10 +P0=1 +P1=2 +P2=3 +P3=8 +P4=32 +P5=39 +P6=64 +P7=115 +P8=192 +P9=256"
probe ds 333
run ds_pass base $SWEEP +DRX=$DRXO +LA_PS=$LA +LXB_PS=$LXB +GAPB=$GAPB +SWD=333
DS_C="+DRX=$DRXO +LA_PS=$LA +LXB_PS=$LXB +GAPB=$GAPB +SWD=333"
probe qw 4
run qw_pass base $SWEEP +DRX=$DRXO +LA_PS=$LA +LXB_PS=$LXB +GAPB=$GAPB +SWD=4
# mutants (each must FAIL)
run m2 base +NI=2 +P0=64 +P1=8 $DS_C +MUT=2
run m3 base +NI=2 +P0=64 +P1=8 $DS_C +MUT=3
run m4 base +NI=2 +P0=1100 +P1=8 $DS_C +MUT=4
build ep2 2; run m1 ep2 +NI=2 +P0=64 +P1=8 $DS_C +MUT=1
build ep4 4; run m5 ep4 +NI=2 +P0=64 +P1=8 $DS_C +MUT=5
rm -rf "$OUT"/obj_*
rc=0
for g in ds_pass qw_pass; do grep -q '^XDIE_HBM .* PASS$' "$OUT/$g.log" || { echo "XDIE $g did not PASS"; rc=1; }; done
for m in m1 m2 m3 m4 m5; do
  if grep -q '^XDIE_HBM .* FAIL$' "$OUT/$m.log"; then echo "XDIE_MUTANT $m REJECTED"; else echo "XDIE_MUTANT $m SURVIVED"; rc=1; fi
done
echo "XDIE_HBM_GATE rc=$rc"
exit $rc
