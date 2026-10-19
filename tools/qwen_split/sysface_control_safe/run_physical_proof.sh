#!/bin/bash
# Isolated functional-source correspondence, never native characterization.
set -eu
export PHYSICAL_BOUNDARY=results/rtl/sysface_physical_proof_1019/frozen_boundary/ot_pin_regs_wrapper.v
CHECK=tools/qwen_split/sysface_control_safe
CFG=results/rtl/sysface_physical_proof_1019/frozen_boundary/config.mk
python3 "$CHECK/check_frozen_boundary.py" "$PHYSICAL_BOUNDARY" "$CFG" cold/original.json --out cold/frozen_boundary_proof.json
mkdir -p legacy
gzip -dc results/rtl/sysface_native12_1019/legacy/original.json.gz > legacy/original.json
cp results/rtl/sysface_native12_1019/legacy/manifest.json legacy/manifest.json
python3 "$CHECK/generate.py" --graph legacy/original.json --manifest legacy/manifest.json --out legacy/generated --useful-cones --physical-wrapper > legacy/generate.log 2>&1
python3 "$CHECK/check_graph.py" legacy/original.json legacy/generated/graph.json legacy/generated/receipt.json --out legacy/graph_proof.json
for p in cold legacy; do
 python3 "$CHECK/build_miter.py" --graph "$p/original.json" --manifest "$p/manifest.json" --receipt "$p/generated/receipt.json" --source rtl/qwen_split/qfd_sys_face.sv --out "$p/miter" --physical-boundary "$PHYSICAL_BOUNDARY"
done
SRAM_CAL=1 MUT=0 bash rtl/test/qwen_split/run_sys_face_cold_safe.sh cold/sim_physical > cold/physical_runner.log 2>&1
SRAM_CAL=1 D2D_MU=1 bash rtl/test/qwen_split/run_sys_face_age_safe.sh legacy/sim_physical > legacy/physical_runner.log 2>&1
bash "$CHECK/run_reset.sh" > cold/physical_reset_runner.log 2>&1
for kind in copy_d reset_short gate_input; do
 python3 "$CHECK/make_mutant.py" cold "$kind"
 set +e
 SRAM_CAL=1 MUT=0 SAFE_DIR="cold_mut_$kind" bash rtl/test/qwen_split/run_sys_face_cold_safe.sh "cold_mut_$kind/sim_physical" > "cold_mut_$kind/runner.log" 2>&1
 rc=$?
 set -e
 test "$rc" != 0
 grep -E 'SYSFACE_SAFE_(EQUIV|RESET|COPY)_FAIL' "cold_mut_$kind/sim_physical/run.log"
done
echo PHYSICAL_SOURCE_MATRIX_DONE
