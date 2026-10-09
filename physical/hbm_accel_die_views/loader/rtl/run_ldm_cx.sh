# Driver for full ND2 golden equivalence with phase-offset independent 600MHz core.
# Two face-clock configurations plus payload and arithmetic mutants. No wall-time limit.
set -u
O=$1; NPROG=${NPROG:-40}; mkdir -p $O
L=physical/hbm_accel_die_views/loader/rtl
DEPS="physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv rtl/hdc/ot_hdc_prefix.sv rtl/hbm_accel/loader/ot_hbm_accel_dma64.sv rtl/gpu_sys/ot_gpu_cdc_fifo.sv rtl/link/ot_link_afifo.sv rtl/lib/ot_reset_sync.sv rtl/hbm_accel/loader/ot_hbm_accel_loader_host.sv rtl/hbm_accel/loader/ot_hbm_accel_loader.sv rtl/hbm_accel/loader/ot_hbm_accel_store.sv"
run() { # name seed defines... -- files
  local n=$1 s=$2; shift 2; local defs=(); while [ "$1" != "--" ]; do defs+=("$1"); shift; done; shift
  verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -DSEED=$s -DNPROG=$NPROG -DMARGIN_B=1 -DLDM_TMO=${LDM_TMO:-1200000} "${defs[@]}" --top-module tb_loader_m_equiv \
    -Mdir $O/$n.$s.obj -o sim $DEPS "$@" $L/tb_loader_cx_equiv.sv > $O/$n.$s.build 2>&1 || { echo "$n seed $s BUILD_FAILED"; grep -m5 -i error $O/$n.$s.build; return 2; }
  $O/$n.$s.obj/sim > $O/$n.$s.log 2>&1; local rc=$?
  echo "$n seed $s rc=$rc $(grep LDM_EQUIV $O/$n.$s.log | tail -1)"
  [ $rc -eq 0 ] && grep -q "mismatches=0" $O/$n.$s.log; }
CORE="$L/ot_hfd_loader_m.sv $L/ot_hfd_store_m.sv $L/ot_hfd_loader_host_m.sv"
ok=1
for s in 1; do run sep $s -DDIV_B=0 -- $CORE $L/ot_hfd_loader_cx.sv || ok=0; done
for s in 2; do run shared $s -DDIV_B=1 -DSAME_CLK -- $CORE $L/ot_hfd_loader_cx.sv || ok=0; done
sed 's/s_wvalid, {s_wstrb, s_wdata}, s_wready/s_wvalid, {s_wstrb, s_wdata ^ 32'"'"'d1}, s_wready/' $L/ot_hfd_loader_cx.sv > $O/xdata.sv; cmp -s $O/xdata.sv $L/ot_hfd_loader_cx.sv && { echo "xdata NOT APPLIED"; ok=0; }
run neg_xdata 1 -DDIV_B=0 -- $CORE $O/xdata.sv && { echo "neg_xdata NOT DETECTED"; ok=0; } || echo "neg_xdata detected"
sed 's/f_oh <= {f_oh\[VOUT-2:0\], f_oh\[VOUT-1\]}/f_oh <= {f_oh[0], f_oh[VOUT-1:1]}/' $L/ot_hfd_loader_m.sv > $O/foh.sv; cmp -s $O/foh.sv $L/ot_hfd_loader_m.sv && { echo "foh NOT APPLIED"; ok=0; }
run neg_foh 1 -DDIV_B=0 -- $O/foh.sv $L/ot_hfd_store_m.sv $L/ot_hfd_loader_host_m.sv $L/ot_hfd_loader_cx.sv && { echo "neg_foh NOT DETECTED"; ok=0; } || echo "neg_foh detected"
[ $ok = 1 ] && echo "LDM_CX PASS" || echo "LDM_CX FAIL"
