#!/bin/bash
set -eu
p=${1:-cold}
# A source reread, elaboration and synthesis proof, not physical or timing admission.
cat > "$p/native_buf_bb.v" <<'V'
(* blackbox *) module BUFx2_ASAP7_75t_R(input A,output Y);endmodule
V
cat > "$p/roundtrip.ys" <<YS
read_verilog -sv $p/generated/parent.sv $p/native_buf_bb.v physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1_bb.v
hierarchy -check -top qfd_sys_face_control_safe
synth -top qfd_sys_face_control_safe -flatten -noabc
write_json $p/roundtrip.json
stat
YS
yosys -Q -s "$p/roundtrip.ys" > "$p/roundtrip.log" 2>&1
python3 tools/qwen_split/sysface_control_safe/audit_mapped.py "$p/roundtrip.json" --out "$p/roundtrip_audit.json"
