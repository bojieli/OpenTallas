#!/bin/bash
# Run only in an isolated fleet source copy through ot-run. This is not a gate.
set -eu
for p in cold legacy; do
 python3 tools/qwen_split/sysface_control_safe/build_profile.py --profile "$p" --out "$p"
 yosys -Q -s "$p/synth.ys" > "$p/synth.log" 2>&1
 python3 tools/qwen_split/sysface_control_safe/generate.py --graph "$p/original.json" --manifest "$p/manifest.json" --out "$p/generated"
 python3 tools/qwen_split/sysface_control_safe/check_graph.py "$p/original.json" "$p/generated/graph.json" "$p/generated/receipt.json" --out "$p/proof.json"
 python3 tools/qwen_split/sysface_control_safe/build_miter.py --graph "$p/original.json" --manifest "$p/manifest.json" --receipt "$p/generated/receipt.json" --source rtl/qwen_split/qfd_sys_face.sv --out "$p/miter"
done
SRAM_CAL=1 MUT=0 bash rtl/test/qwen_split/run_sys_face_cold_safe.sh cold/sim_final
SRAM_CAL=1 D2D_MU=1 bash rtl/test/qwen_split/run_sys_face_age_safe.sh legacy/sim
bash tools/qwen_split/sysface_control_safe/run_reset.sh
bash tools/qwen_split/sysface_control_safe/map_generic.sh cold
python3 tools/qwen_split/sysface_control_safe/check_emitted.py cold/generated/graph.json cold/roundtrip.json --source cold/generated/parent.sv --out cold/emitted_proof.json
python3 tools/qwen_split/sysface_control_safe/test_guards.py
python3 tools/qwen_split/sysface_control_safe/test_emitted_guards.py
for kind in copy_d reset_short buffer_input; do
 python3 tools/qwen_split/sysface_control_safe/make_mutant.py cold "$kind"
 set +e
 SRAM_CAL=1 MUT=0 SAFE_DIR="cold_mut_$kind" bash rtl/test/qwen_split/run_sys_face_cold_safe.sh "cold_mut_$kind/sim" > "cold_mut_$kind/runner.log" 2>&1
 rc=$?
 set -e
 test "$rc" != 0
 grep -E 'SYSFACE_SAFE_(EQUIV|RESET|COPY)_FAIL' "cold_mut_$kind/sim/run.log"
done
