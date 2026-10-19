#!/bin/bash
# Isolated fleet source/model proof only. No native timing or physical gate.
set -eu
for p in cold legacy; do
 mkdir -p "$p"
 gzip -dc "results/rtl/sysface_native12_1019/$p/original.json.gz" > "$p/original.json"
 cp "results/rtl/sysface_native12_1019/$p/manifest.json" "$p/manifest.json"
 python3 -u tools/qwen_split/sysface_control_safe/generate.py --graph "$p/original.json" --manifest "$p/manifest.json" --out "$p/generated" --useful-cones --physical-wrapper > "$p/generate.log" 2>&1
 python3 tools/qwen_split/sysface_control_safe/check_graph.py "$p/original.json" "$p/generated/graph.json" "$p/generated/receipt.json" --out "$p/proof.json"
 python3 tools/qwen_split/sysface_control_safe/audit_graph_transparent.py "$p/generated/graph.json" --out "$p/abstract_transparent.json"
 cat > "$p/roundtrip.ys" <<YS
read_verilog -sv $p/generated/parent.sv physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1_bb.v
hierarchy -check -top qfd_sys_face_control_safe
synth -top qfd_sys_face_control_safe -flatten -noabc
write_json $p/roundtrip.json
stat
YS
 yosys -Q -s "$p/roundtrip.ys" > "$p/roundtrip.log" 2>&1
 python3 tools/qwen_split/sysface_control_safe/check_emitted.py --top qfd_sys_face_control_safe__safe_core "$p/generated/graph.json" "$p/roundtrip.json" --source "$p/generated/parent.sv" --out "$p/emitted_proof.json"
 python3 tools/qwen_split/sysface_control_safe/check_physical_wrapper.py "$p/original.json" "$p/roundtrip.json" "$p/generated/receipt.json" --out "$p/wrapper_proof.json"
done
