#!/usr/bin/env bash
# HBMA-SVC 2026-10-17: ot_hbm_svc_stack_fault bench at the d4f binding (OWN_W=6).  run_stack_fault_bench.sh OUT MUT [OWN_W]
set -u
cd "$(dirname "$0")/../../../.."
out=$(realpath -m "${1:?out}"); mut=${2:-0}; own=${3:-6}; mkdir -p "$out"
n=rtl/hbm_accel/loader/service_native
src=("$n/tb_hbm_svc_stack_fault.sv" "$n/ot_hbm_svc_stack_fault.sv" "$n/ot_hbm_svc_async_fifo.sv" rtl/lib/ot_reset_sync.sv)
sha256sum "${src[@]}" > "$out/source.sha256"
iverilog -g2012 -s tb_hbm_svc_stack_fault -P tb_hbm_svc_stack_fault.MUT=$mut -P tb_hbm_svc_stack_fault.OWN_W=$own \
 -o "$out/sim.vvp" "${src[@]}" > "$out/build.log" 2>&1 || { cat "$out/build.log"; echo "BUILD_FAIL"; exit 2; }
vvp -n "$out/sim.vvp" | tee "$out/sim.log" | grep -E "^(PASS|FAIL)|source|legal" 
grep -q "^PASS tb_hbm_svc_stack_fault" "$out/sim.log"
