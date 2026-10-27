yosys read_verilog -sv /srv/opentallas-scratch2/claude/codex-kv-cores-1351/own_gate/new.sv /srv/opentallas-scratch2/claude/wt/codex-kv-cores-1351/rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_es_merge.sv /srv/opentallas-scratch2/claude/wt/codex-kv-cores-1351/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_map.sv
yosys hierarchy -top own_dut
source /srv/opentallas-scratch2/claude/wt/codex-kv-cores-1351/physical/common_flow/ot_keep_regs.tcl
yosys synth -top own_dut
yosys write_json /srv/opentallas-scratch2/claude/codex-kv-cores-1351/own_gate/retained.json
