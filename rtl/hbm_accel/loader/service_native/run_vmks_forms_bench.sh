#!/usr/bin/env bash
# HBM-CONS-2/KSH proof of the kshare forms: run_vmks_forms_bench.sh OUTDIR [case...]
set -u
out=${1:?outdir};shift;mkdir -p "$out";R=$(cd "$(dirname "$0")/../../../.." && pwd)
S=$R/rtl/hbm_accel/loader/service_native
vl=${VERILATOR:-verilator}
DEP="$S/tb_hbm_svc_vmks_forms.sv $S/ot_hbm_svc_vmks_forms.sv $S/ot_hbm_svc_vm_kshare_splitstrap.sv $S/ot_hbm_svc_pc_ctrl_leaf.sv $S/ot_hbm_svc_async_fifo.sv $S/ot_hbm_svc_ring_h9b_ff.sv $R/rtl/lib/ot_reset_sync.sv"
# name expected G-params plusargs
run(){ n=$1;e=$2;g=$3;pa=$4
 while [ "$(jobs -r|wc -l)" -ge "${JOBS:-8}" ];do wait -n;done
 ( $vl --binary --timing -j 2 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hbm_svc_vmks_forms --Mdir "$out/obj-$n" -o sim $g $DEP > "$out/$n.build.log" 2>&1 || { echo "$n BUILD FAIL";exit 0; }
   timeout 3000 "$out/obj-$n/sim" $pa > "$out/$n.log" 2>&1
   l=$(grep -E '^(PASS|FAIL)' "$out/$n.log"|tail -1)
   case "$e:$l" in PASS:PASS*|FAIL:FAIL*) v=OK;; *) v=UNEXPECTED;; esac
   echo "$v $n expect=$e : $l"; rm -rf "$out/obj-$n" ) &
}
L="-GCHECK=0"; T="-GCHECK=1"
run lock0 PASS "$L" "+WINDOWS=24 +SEED=1"
run lock1 PASS "$L" "+WINDOWS=24 +SEED=2"
run lock_wb PASS "$L" "+WINDOWS=1500 +SEED=6 +WBONLY=1 +GN=200"
run lock_ptronly PASS "$L -GFILLS=0 -GWCNT=0" "+WINDOWS=16 +SEED=3"
run lock_fillonly PASS "$L -GPTR=0 -GWCNT=0" "+WINDOWS=16 +SEED=4"
run lock_wcntonly PASS "$L -GPTR=0 -GFILLS=0" "+WINDOWS=16 +SEED=5"
for m in 1 2 3 4 5 6 7 8 10;do run lock_m$m FAIL "$L -GMUT=$m" "+WINDOWS=24 +SEED=1";done
run lock_m11 FAIL "$L -GMUT=11" "+WINDOWS=1500 +SEED=6 +WBONLY=1 +GN=200"
wait
run tr_eq PASS "$T" "+WINDOWS=24 +SEED=1"
run tr_eq2 PASS "$T" "+WINDOWS=24 +SEED=2"
run tr_fast PASS "$T" "+WINDOWS=24 +SEED=3 +HBM_HALF=350 +STR_HALF=600"
run tr_slow PASS "$T" "+WINDOWS=24 +SEED=4 +HBM_HALF=600 +STR_HALF=350"
for m in 1 2 3 4 5 6 7 8 10 13;do run tr_m$m FAIL "$T -GMUT=$m" "+WINDOWS=24 +SEED=1";done
run tr_m11 FAIL "$T -GMUT=11" "+WINDOWS=1500 +SEED=6 +WBONLY=1 +GN=200"
run tr_wb PASS "$T" "+WINDOWS=1500 +SEED=7 +WBONLY=1 +GN=200"
# fill stage only stalls when the stream side is much slower than hbm (async FIFO full), not at the equal clocks of the lock-step cases
run lock_burst PASS "$L" "+WINDOWS=500 +SEED=9 +WBONLY=2 +GN=200"
run tr_burst PASS "$T" "+WINDOWS=500 +SEED=9 +WBONLY=2 +GN=200"
run tr_m12 FAIL "$T -GMUT=12" "+WINDOWS=500 +SEED=9 +WBONLY=2 +GN=200"
run tr_m14 FAIL "$T -GMUT=14" "+WINDOWS=500 +SEED=9 +WBONLY=2 +GN=200"
run tr_m15 FAIL "$T -GMUT=15" "+WINDOWS=24 +SEED=1"
run tr_bad PASS "$T" "+WINDOWS=24 +SEED=1 +BADTAG=1"
run lock_bad PASS "$L" "+WINDOWS=24 +SEED=1 +BADTAG=1"
run tr_m16 FAIL "$T -GMUT=16" "+WINDOWS=24 +SEED=1 +BADTAG=1"
run tr_slowstr PASS "$T" "+WINDOWS=24 +SEED=8 +HBM_HALF=300 +STR_HALF=1500"
run tr_m9 FAIL "$T -GMUT=9" "+WINDOWS=24 +SEED=8 +HBM_HALF=300 +STR_HALF=1500"
wait
