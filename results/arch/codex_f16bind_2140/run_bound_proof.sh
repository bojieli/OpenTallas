#!/bin/bash
set -euo pipefail
python3 results/arch/codex_f16bind_2140/prove_lctx_full_transition.py bound_construct/original.json bound_construct/construction.json bound_construct/transition.sv > bound_construct/proof_build.json
python3 results/arch/codex_f16bind_2140/audit_lctx_full_emitter.py --graph bound_construct/construction.json --source bound_construct/qfd_sys_face_lctx4_bounded_f16.sv --helpers bound_construct/qfd_sys_face_lctx4_f16_helpers.sv > bound_construct/emitter_audit.json
docker run --rm -v "$PWD/bound_construct:/out" -w /out openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -p "read_verilog /out/transition.sv; prep -top lctx_full_transition -flatten; sat -verify -enable_undef -prove bad 0 -set-def-inputs" > /out/fourstate_sat.log 2>&1'
docker run --rm -v "$PWD/bound_construct:/out" -w /out openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -p "read_verilog /out/transition.sv; prep -top lctx_full_transition -flatten; sat -verify -prove control_next_bad 0 -set reset_control_is_zero 1 -set-def-inputs; sat -verify -prove bad 0 -set reset_control_is_zero 1 -set-def-inputs" > /out/reset_valid_sat.log 2>&1'
cat bound_construct/proof_build.json
cat bound_construct/emitter_audit.json
echo PASS F16_BOUNDED_SOURCE_CORRESPONDENCE
