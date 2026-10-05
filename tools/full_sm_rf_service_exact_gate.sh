#!/usr/bin/env bash
# Compile/execute ONLY after parent review, in a clean pinned worktree.
# No remote jobs, synthesis or P&R. Arithmetic blackboxes are excluded.
set -euo pipefail
if [[ "${PARENT_REVIEWED_FULL_SM_GATE:-0}" != 1 ]]; then
  echo 'Parent review required: set PARENT_REVIEWED_FULL_SM_GATE=1 after review.' >&2
  exit 2
fi
if [[ -n "$(git status --porcelain --untracked-files=normal)" ]]; then
  echo 'Gate requires clean source-pinned worktree.' >&2
  exit 2
fi
run_dir="${FULL_SM_GATE_OUT:?Set FULL_SM_GATE_OUT to a fresh absolute output directory}"
if [[ "$run_dir" != /* || -e "$run_dir" ]]; then
  echo 'Output must be a fresh absolute directory; never overwrite verdicts.' >&2
  exit 2
fi
mkdir -p "$run_dir"
git rev-parse HEAD > "$run_dir/source_commit.txt"
paths=(rtl/gpu/ot_gpu_full_sm_service.sv rtl/gpu/ot_gpu_rf_service.sv rtl/gpu/ot_gpu_scratch_service.sv
 rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/test/full_sm_service/sram_models.sv rtl/test/full_sm_service/tb_full_service_exact.sv)
sha256sum "${paths[@]}" > "$run_dir/source_sha256.txt"
finish_gate() {
  status=$?
  if [[ $status -eq 0 ]]; then echo PASS > "$run_dir/verdict.txt";else echo "FAIL exit=$status" > "$run_dir/verdict.txt";fi
}
trap finish_gate EXIT
 timeout 180s iverilog -g2012 -s tb_full_service_exact -o "$run_dir/full.vvp" "${paths[@]}" > "$run_dir/compile.log" 2>&1
 timeout 60s vvp "$run_dir/full.vvp" > "$run_dir/exact.log" 2>&1
# Also bind the all-address functional storage gate to this same reviewed pin.
 timeout 30s iverilog -g2012 -s tb_storage -o "$run_dir/storage.vvp" rtl/gpu/ot_gpu_rf_service.sv rtl/gpu/ot_gpu_scratch_service.sv rtl/test/full_sm_service/sram_models.sv rtl/test/full_sm_service/tb_storage.sv > "$run_dir/storage_compile.log" 2>&1
 timeout 30s vvp "$run_dir/storage.vvp" > "$run_dir/storage.log" 2>&1
