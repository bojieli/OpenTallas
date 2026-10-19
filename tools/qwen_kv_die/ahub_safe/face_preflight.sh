#!/bin/bash
# Fleet only. Reproduce the optional native face source and independent proof.
set -euo pipefail
O=$(realpath -m "$1"); S=$PWD
mkdir -p "$O"
gzip -dc results/arch/kv_ahub_structural_source_1019/safe2.mapped.json.gz > "$O/original.json"
python3 tools/qwen_kv_die/ahub_safe/distribute_faces.py "$O/original.json" "$O" --profile GEN7_AP_-40_-40_-38_-39_FR_-7 > "$O/generator.log"
cmp "$O/qkd_ahub_static_dw_safe_native.v" rtl/hdc/nearhbm/qkd_ahub_static_dw_safe_face_native.v
docker run --rm --cpus=4 --memory=96g -v "$O:/out" -v "$S:/src:ro" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -l /out/reparse.log -p "read_json /out/original.json; read_verilog /out/qkd_ahub_static_dw_safe_native.v; hierarchy -check -top qkd_ahub_static_dw_safe_native; synth -top qkd_ahub_static_dw_safe_native -flatten; check -assert; write_json /out/reparsed.json"'
python3 tools/qwen_kv_die/ahub_safe/verify_faces.py "$O/original.json" "$O/reparsed.json" "$O/distribution.json" > "$O/verification.json"
python3 tools/qwen_kv_die/ahub_safe/face_geometry.py "$O/reparsed.json" "$O/verification.json" results/arch/kv_ahub_face_copy_1019/face_model_input.json > "$O/face_geometry.json"
