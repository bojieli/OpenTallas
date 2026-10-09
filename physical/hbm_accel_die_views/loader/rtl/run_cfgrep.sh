#!/bin/bash
# run_cfgrep.sh <outdir> : CFGREP exactness (drive-2125, REVIEW_20261008 DQ1).  (1) lockstep of the new hfd_loader (cfg-valid
# copies, RG 8) vs the unchanged wrapper + SKID half loader (cfgrep_ref/: a0e0d1e08, modules renamed *_ref0), seeds 1 2 3;
# (2) mutant (copies registered from cfg[k] instead of cfg[k-1]: one cycle late) must FAIL; (3) the transaction bench
# run_ldm_half.sh on the regenerated half loader (RG 0).  Prints CFGREP PASS / CFGREP FAIL.
set -u
O=$1; NCYC=${NCYC:-6000}; mkdir -p $O
L=physical/hbm_accel_die_views/loader/rtl
DEPS="physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv rtl/hdc/ot_hdc_prefix.sv $L/ot_hfd_loader_host_m.sv $L/ot_hfd_loader_m.sv $L/ot_hfd_store_m.sv rtl/hbm_accel/loader/ot_hbm_accel_dma64.sv rtl/gpu_sys/ot_gpu_cdc_fifo.sv rtl/link/ot_link_afifo.sv rtl/common/ot_fwd_link_stage.sv"
run() { local n=$1 s=$2 w=$3
  verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -DSEED=$s -DNCYC=$NCYC --top-module tb_cfgrep_lockstep \
    -Mdir $O/$n.$s.obj -o sim $DEPS $L/ot_hfd_loader_half.sv $w $L/cfgrep_ref/ot_hfd_loader_half_ref0.sv $L/cfgrep_ref/hfd_loader_ref0.sv $L/tb_cfgrep_lockstep.sv > $O/$n.$s.build 2>&1 \
    || { echo "$n seed $s BUILD_FAILED"; grep -m5 -i error $O/$n.$s.build; return 2; }
  timeout 3600 $O/$n.$s.obj/sim > $O/$n.$s.log 2>&1; local rc=$?
  echo "$n seed $s rc=$rc $(grep CFGREP_LOCKSTEP $O/$n.$s.log | tail -1)"; [ $rc -eq 0 ]; }
ok=1
for s in 1 2 3; do run pos $s $L/hfd_loader.sv || ok=0; done
sed 's/\.d(cfg\[139 + k \/ CFG_RG\])/.d(cfg[140 + k \/ CFG_RG])/; s/\.d(cfg\[64\])/.d(cfg[65])/' $L/hfd_loader.sv > $O/mut_late.sv
cmp -s $O/mut_late.sv $L/hfd_loader.sv && { echo "mut_late NOT APPLIED"; ok=0; }
run mut_late 1 $O/mut_late.sv && { echo "mut_late NOT DETECTED"; ok=0; } || echo "mut_late detected"
bash $L/run_ldm_half.sh $O/ldm | tee $O/ldm.txt | tail -3; grep -q 'LDM_HALF PASS' $O/ldm.txt || ok=0
[ $ok = 1 ] && echo "CFGREP PASS" || echo "CFGREP FAIL"
