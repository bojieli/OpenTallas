#!/bin/bash
# run_ldm_half.sh <outdir> : transaction-level exactness of the half-rate loader (ot_hfd_loader_half around the
# unchanged ot_hfd_loader_host_m) against the unchanged ot_hbm_accel_loader_host (tb_loader_m_equiv.sv: MREQ / DMA write
# streams and every CSR except CYCLES): SHARED 0 with separate host / memory clocks (seeds 1 2 3), SHARED 1 on one clock
# (seeds 1 2); negatives (must FAIL): handshake gating removed (every valid / ready seen for two fast cycles) and a core
# mutation (load fold ring direction).  Prints LDM_HALF PASS / LDM_HALF FAIL.
set -u
O=$1; NPROG=${NPROG:-40}; mkdir -p $O
L=physical/hbm_accel_die_views/loader/rtl
DEPS="physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv rtl/hdc/ot_hdc_prefix.sv rtl/hbm_accel/loader/ot_hbm_accel_dma64.sv rtl/gpu_sys/ot_gpu_cdc_fifo.sv rtl/link/ot_link_afifo.sv rtl/hbm_accel/loader/ot_hbm_accel_loader_host.sv rtl/hbm_accel/loader/ot_hbm_accel_loader.sv rtl/hbm_accel/loader/ot_hbm_accel_store.sv"
run() { # name seed defines... -- files
  local n=$1 s=$2; shift 2; local defs=(); while [ "$1" != "--" ]; do defs+=("$1"); shift; done; shift
  verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -DSEED=$s -DNPROG=$NPROG -DMARGIN_B=1 "${defs[@]}" --top-module tb_loader_m_equiv \
    -Mdir $O/$n.$s.obj -o sim $DEPS "$@" $L/tb_loader_m_equiv.sv > $O/$n.$s.build 2>&1 || { echo "$n seed $s BUILD_FAILED"; grep -m5 -i error $O/$n.$s.build; return 2; }
  timeout 3600 $O/$n.$s.obj/sim > $O/$n.$s.log 2>&1; local rc=$?
  echo "$n seed $s rc=$rc $(grep LDM_EQUIV $O/$n.$s.log | tail -1)"
  [ $rc -eq 0 ] && grep -q "mismatches=0" $O/$n.$s.log; }
CORE="$L/ot_hfd_loader_m.sv $L/ot_hfd_store_m.sv $L/ot_hfd_loader_host_m.sv"
ok=1
for s in 1 2 3; do run sep $s -DHALF_B=0 -- $CORE $L/ot_hfd_loader_half.sv || ok=0; done
for s in 1 2; do run shared $s -DHALF_B=1 -DSAME_CLK -- $CORE $L/ot_hfd_loader_half.sv || ok=0; done
sed 's/ & {$bits(c_[a-z_]*){ph_[hm]}}//' $L/ot_hfd_loader_half.sv > $O/nogate.sv; cmp -s $O/nogate.sv $L/ot_hfd_loader_half.sv && { echo "nogate NOT APPLIED"; ok=0; }
run neg_nogate 1 -DHALF_B=0 -- $CORE $O/nogate.sv && { echo "neg_nogate NOT DETECTED"; ok=0; } || echo "neg_nogate detected"
sed 's/f_oh <= {f_oh\[VOUT-2:0\], f_oh\[VOUT-1\]}/f_oh <= {f_oh[0], f_oh[VOUT-1:1]}/' $L/ot_hfd_loader_m.sv > $O/foh.sv; cmp -s $O/foh.sv $L/ot_hfd_loader_m.sv && { echo "foh NOT APPLIED"; ok=0; }
run neg_foh 1 -DHALF_B=0 -- $O/foh.sv $L/ot_hfd_store_m.sv $L/ot_hfd_loader_host_m.sv $L/ot_hfd_loader_half.sv && { echo "neg_foh NOT DETECTED"; ok=0; } || echo "neg_foh detected"
[ $ok = 1 ] && echo "LDM_HALF PASS" || echo "LDM_HALF FAIL"
