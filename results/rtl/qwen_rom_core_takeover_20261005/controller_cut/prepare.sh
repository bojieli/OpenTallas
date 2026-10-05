#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/codex/qwen-rom-controller-cut-context5-20261005
Y=/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys
LIB=/home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
SOURCE=/srv/opentallas-scratch/codex/qwen-rom-core-context2-20261005/context_src
mkdir -p "$R/context_src/rtl"
"$Y" -Q -T -p "read_liberty -lib $LIB; read_verilog $SOURCE/rtl/control_context.v; proc; write_json $R/original.json" > "$R/read.log" 2>&1
python3 "$R/src/tools/qwen_rom_core_controller_cut.py" --input "$R/original.json" --output "$R/controller.json" --report "$R/cut_report.json"
"$Y" -Q -T -p "read_json $R/controller.json; write_verilog -noattr $R/context_src/rtl/control_context.v" > "$R/write.log" 2>&1
cp -r "$SOURCE/configs" "$R/context_src/"
cd "$R/context_src"
git init -q
git -c user.name=Codex -c user.email=codex@opentallas.local add rtl/control_context.v configs
git -c user.name=Codex -c user.email=codex@opentallas.local -c gc.auto=0 commit -qm 'Pinned controller graph with passive legacy ports removed'
