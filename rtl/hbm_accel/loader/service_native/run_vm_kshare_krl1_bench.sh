#!/usr/bin/env bash
# H-PC 2026-10-16: ot_hbm_svc_vm_kshare KRL1 (ready-latency-1 controller responses, PC H9b) unit benches.
#   run_vm_kshare_krl1_bench.sh OUTDIR [case]   cases: pos pos_fast pos_slow reg0 mut_depth2 mut_skid0 (default all)
# pos*: KRL1=1 with a ready-latency-1 controller model -> PASS; reg0: KRL1=0 legacy -> PASS;
# mut_depth2: KRL1=1, C ring depth 2 (MUT 6) -> FAIL; mut_skid0: legacy 2-entry skid (KRL1=0) under a ready-latency-1
# controller -> FAIL (beats overrun the skid).
set -u
out=${1:?outdir}; only=${2:-all}; mkdir -p "$out"; R=$(cd "$(dirname "$0")/../../../.." && pwd)
S=$R/rtl/hbm_accel/loader/service_native
DEP="$S/ot_hbm_svc_pc_ctrl_leaf.sv $S/ot_hbm_svc_async_fifo.sv $S/ot_hbm_svc_ring_h9b.sv $R/rtl/lib/ot_reset_sync.sv"
run(){ name=$1; shift; args=$1; shift
  [ "$only" = all ] || [ "$only" = "$name" ] || return 0
  iverilog -g2012 -s tb_hbm_svc_vm_kshare "$@" -o "$out/$name.vvp" $S/tb_hbm_svc_vm_kshare.sv $S/ot_hbm_svc_vm_kshare.sv $DEP > "$out/$name.build.log" 2>&1 || { echo "BUILD_FAIL $name"; cat "$out/$name.build.log"; return; }
  vvp -n "$out/$name.vvp" $args > "$out/$name.log" 2>&1; echo "$name: $(grep -E 'PASS|FAIL' "$out/$name.log" | tail -n 1)"; }
run pos "+WINDOWS=8" -P tb_hbm_svc_vm_kshare.KRL1=1 &
run pos_fast "+WINDOWS=8 +HBM_HALF=400 +STR_HALF=700" -P tb_hbm_svc_vm_kshare.KRL1=1 &
run pos_slow "+WINDOWS=8 +HBM_HALF=700 +STR_HALF=400" -P tb_hbm_svc_vm_kshare.KRL1=1 &
run reg0 "+WINDOWS=8" &
run mut_depth2 "+WINDOWS=8" -P tb_hbm_svc_vm_kshare.KRL1=1 -P tb_hbm_svc_vm_kshare.MUT=6 &
run mut_skid0 "+WINDOWS=8" -P tb_hbm_svc_vm_kshare.TBL1=1 &
wait
