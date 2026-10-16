#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
out=${1:?output directory required}
mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
sources=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_prefetch_burst_bank.sv" "$mem" rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv rtl/hdc/kv/ot_hdc_hbm_model.sv rtl/chip/ot_chip_v41x_hbm3e_phy.sv)
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_svc_prefetch_burst_cdc --Mdir "$out/positive_obj" -o positive "${sources[@]}" "$d/ot_hbm_svc_prefetch_burst_owner.sv" "$d/ot_hbm_svc_prefetch_burst_cdc.sv" "$d/tb_hbm_svc_prefetch_burst_cdc.sv" > "$out/build.log" 2>&1
performance_failures=0
for phase in 137 773; do
  # Preserve complete functional and negative evidence even if latency gate fails.
  # A gate failure remains explicit and makes this runner fail after all proofs.
  "$out/positive_obj/positive" +PHASE=$phase +ALLOW_PERF_FAIL > "$out/phase_$phase.log"
  grep -q 'PASS PREFETCH_BURST_CDC actualPHY' "$out/phase_$phase.log"
  if grep -q 'PREFETCH_BURST_CDC_PERFORMANCE FAIL' "$out/phase_$phase.log"; then performance_failures=$((performance_failures+1)); fi
done
"$out/positive_obj/positive" +DUPBEAT > "$out/duplicate_beat.log"
grep -q 'PASS PREFETCH_BURST_CDC duplicate response beat rejected' "$out/duplicate_beat.log"
# Mutant generation is deliberately exact and fails if the source changed.
python3 - "$d/ot_hbm_svc_prefetch_burst_owner.sv" "$out/mutant.sv" <<'PY'
import pathlib, sys
source=pathlib.Path(sys.argv[1]).read_text()
# Corrupt both initial and subsequent chunks consistently: drop XOR inverse.
for original, replacement in (
    ('chunk_pc=PC^effective_group[4:0]^effective_group[9:5];', 'chunk_pc=PC;'),
    ('initial_chunk_pc=PC^initial_group[4:0]^initial_group[9:5];', 'initial_chunk_pc=PC;'),
):
    if source.count(original) != 1:
        raise SystemExit(f'expected one reviewed inverse-PC expression: {original}')
    source=source.replace(original,replacement)
pathlib.Path(sys.argv[2]).write_text(source)
PY
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_svc_prefetch_burst_cdc --Mdir "$out/mutant_obj" -o mutant "${sources[@]}" "$out/mutant.sv" "$d/ot_hbm_svc_prefetch_burst_cdc.sv" "$d/tb_hbm_svc_prefetch_burst_cdc.sv" > "$out/mutant_build.log" 2>&1
if "$out/mutant_obj/mutant" +ALLOW_PERF_FAIL > "$out/mutant.log"; then echo 'wrong low5 PC mutant unexpectedly passed'; exit 1; fi
grep -q 'actual XOR PC mismatch' "$out/mutant.log"
cat "$out/phase_137.log" "$out/phase_773.log" "$out/duplicate_beat.log"
echo 'PREFETCH_BURST_CDC MUTANT rejected actual-PC routing corruption'
if ((performance_failures)); then
  echo "PREFETCH_BURST_CDC PERFORMANCE FAIL phase_runs=$performance_failures raw_baseline_1.10_gate"
  exit 2
fi
echo 'PREFETCH_BURST_CDC PERFORMANCE PASS both_raw_phase_runs'
