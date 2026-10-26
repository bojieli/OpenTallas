#!/usr/bin/env bash
# S81/H23 (10-24): build + run the on-die SEL_IDS producer chain bench (tb_dsdv_selchain: dsdv_bk_selids -> rung ->
# dsdv_seq_host SELR 1 -> unit lanes -> dsdv_svc_selq x 2) and its negative controls.
# usage: run_selchain.sh <outdir> [variant ...]; variants: base (must PASS), selmut1 (encoder s_first frozen: must
# FAIL), sqmut1 (entry payload halves swapped: must FAIL).  Prints SELCHAIN_GATE PASS / FAIL.  Verilator 5.050 (daemon pin).
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd); O=$1; shift; VARS=${*:-"base selmut1 sqmut1"}
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
U=$R/rtl/dsrom_sys/s81_dv/unit
F="$R/rtl/lib/ot_async_fifo.sv $R/rtl/lib/ot_reset_sync.sv $R/rtl/lib/ot_rst_relay.sv $R/rtl/link/ot_link_afifo.sv
   $R/rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv $R/rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv $R/rtl/hdc/ingest/ot_hdc_kv_ingest.sv
   $R/rtl/hdc/ingest/ot_rom_host_ingest.sv $R/physical/rom_host_ingest/rtl/dsfd_host.sv
   $R/rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv
   $R/rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_c.sv
   $R/rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv $U/ot_dsdv_fixed_issue.sv $U/ot_dsdv_walk_issue.sv $U/ot_dsdv_vstop.sv $U/dsdv_sh_sd.sv $U/dsdv_seq_host.sv
   $R/physical/asap7_memory_macros/ot_sram_1r1w2c_16x546_m1/ot_sram_1r1w2c_16x546_m1.v
   $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
   $R/rtl/dsrom_sys/s81_dv/idx/dsdv_idx_l20s.sv $R/rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs.sv
   $U/test/tb_dsdv_selchain.sv"
mkdir -p "$O"; bad=0
for v in $VARS; do
  case $v in base) D="";; selmut1) D="-DSEL_MUT=1";; sqmut1) D="-DSQ_MUT=1";; *) echo "variant? $v"; exit 2;; esac
  B=$O/$v; mkdir -p "$B/obj"
  if [ ! -x "$B/obj/Vtb_dsdv_selchain" ]; then
    $VL --binary --timing -j "${J:-8}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD \
      +define+DSFD_HOST_C_STATIC $D -I$R/rtl/dsrom_sys/s81_dv/svc_rs --top-module tb_dsdv_selchain -Mdir "$B/obj" $F \
      > "$O/build_$v.log" 2>&1 || { echo "BUILD_FAIL $v"; grep -m5 -i error "$O/build_$v.log"; tail -5 "$O/build_$v.log"; bad=1; continue; }
  fi
  for s in ${SEEDS:-1 2 3}; do
    "$B/obj/Vtb_dsdv_selchain" +seed=$s +njob=${NJOB:-4} > "$O/run_${v}_s$s.log" 2>&1
    l=$(grep -h '^SELC ' "$O/run_${v}_s$s.log" | tail -1); echo "$v s$s: $l"; grep -h '^SELC_JOB0' "$O/run_${v}_s$s.log"
    if [ "$v" = base ]; then case "$l" in *verdict=PASS*) ;; *) bad=1; grep -m5 "SELC_" "$O/run_${v}_s$s.log";; esac
    else case "$l" in *verdict=FAIL*) ;; *) echo "MUTANT_NOT_CAUGHT $v s$s"; bad=1;; esac; fi
  done
done
[ $bad = 0 ] && echo "SELCHAIN_GATE PASS" || echo "SELCHAIN_GATE FAIL"; exit $bad
