#!/usr/bin/env bash
# S81/PORTFIX-FLT (2026-10-25, S81 DECISION 4): die fault network bench (tb_s81_fault_ring.sv) on Verilator 5.050 (the
# closure daemon's version).  unit fault -> ot_s81_frs ring stops -> dsdv_hostb_seqhost_mux die fault word -> t_host ->
# ot_s81sl_lep host plane -> lanes / PHY -> host THOST frames.
#   base     PASS expected
#   frs1..3  ot_s81_frs MUT 1 (stop not sticky) / 2 (ring OR dropped) / 3 (local fault dropped)      -> FAIL expected
#   fmut1..3 seqhost FMUT 1 (ring heads not driven) / 2 (own bit dropped) / 3 (sid / vid fields swapped) -> FAIL expected
# Usage (cwd = repo root): run_fault_ring_bench.sh OUTDIR        Prints FAULT_RING_GATE PASS / FAIL.
set -u
O=$(realpath -m "${1:?outdir}"); mkdir -p "$O"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version > "$O/verilator_version.txt"
U=rtl/dsrom_sys/s81_dv/unit; H=rtl/dsrom_sys/s81_dv/hostb; L=rtl/dsrom_sys/s81_link; SL=rtl/dsrom_sys/s81_dv/slice
SEQ="rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv rtl/lib/ot_rst_relay.sv rtl/link/ot_link_afifo.sv
 rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv rtl/hdc/ingest/ot_hdc_kv_ingest.sv
 rtl/hdc/ingest/ot_rom_host_ingest.sv physical/rom_host_ingest/rtl/dsfd_host.sv
 rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv
 rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv $U/ot_dsdv_fixed_issue.sv $U/ot_dsdv_walk_issue.sv $U/ot_dsdv_vstop.sv $U/dsdv_sh_sd.sv
 $U/dsdv_seq_host.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
 $U/dsdv_mu_hslot.sv $U/dsdv_mu_hwin.sv $U/dsdv_static_ks6.sv $H/dsdv_hostb_landing.sv $H/dsdv_hostb_source.sv
 $H/dsdv_hostb_seqhost_mux.sv $U/ot_s81_frs.sv"
LEP="rtl/link/ot_link_crc32.sv rtl/common/ot_link_credit.sv
 rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv
 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_skid2.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv
 $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_bm.sv $L/ot_s81_kp4_dsyn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dchn.sv
 $L/ot_s81_kp4_dout.sv $L/ot_s81_kp4_dec.sv $L/ot_pdie_serdes.sv
 physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v
 physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v
 $SL/ot_s81sl_slice_lep.sv $SL/dsdv_mu_land.sv"
D="+define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2"
sha256sum $SEQ $LEP $U/test/tb_s81_fault_ring.sv > "$O/sources.sha256"
bad=0
one() { n=$1; exp=$2; shift 2
  $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style -Wno-UNOPTFLAT +incdir+$L $D "$@" \
    --top-module tb_s81_fault_ring -Mdir "$O/$n" $SEQ $LEP $U/test/tb_s81_fault_ring.sv --build-jobs ${J:-8} \
    -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > "$O/build_$n.log" 2>&1 \
    || { echo "$n: BUILD_FAILED"; grep -m10 %Error "$O/build_$n.log"; touch "$O/$n.bad"; return; }
  "$O/$n/Vtb_s81_fault_ring" > "$O/$n.log" 2>&1
  v=$(grep -m1 -E "^(PASS|FAIL) fault_ring" "$O/$n.log"); echo "$n: $v"
  grep -E "^(ERR|OK) " "$O/$n.log" | head -12 | sed 's/^/  /'
  case $exp in PASS) echo "$v" | grep -q '^PASS fault_ring' || touch "$O/$n.bad" ;;
               FAIL) echo "$v" | grep -q '^FAIL fault_ring' || { echo "  $n NOT detected"; touch "$O/$n.bad"; } ;; esac
}
rm -f "$O"/*.bad
one base PASS &
one frs1 FAIL -GFRS_MUT=1 & one frs2 FAIL -GFRS_MUT=2 & one frs3 FAIL -GFRS_MUT=3 & wait
one fmut1 FAIL -GFMUT=1 & one fmut2 FAIL -GFMUT=2 & one fmut3 FAIL -GFMUT=3 & wait
ls "$O"/*.bad >/dev/null 2>&1 && bad=1
[ $bad = 0 ] && echo "FAULT_RING_GATE PASS" || echo "FAULT_RING_GATE FAIL"; exit $bad
