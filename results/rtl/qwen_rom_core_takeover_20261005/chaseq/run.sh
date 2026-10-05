#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/codex/qwen-rom-core-chaseq1-20261005
cd "$R/src"
mkdir -p "$R/component"
python3 tools/qwen_rom_core_takeover_component.py --bounded --chaseq --out "$R/component/component.sv"
for v in 0 1; do
 for p in 8187 262135; do
  iverilog -g2012 -Irtl/hdc -s tb -Ptb.VPOS=$v -Ptb.POSITION=$p -Ptb.BOUNDED=1 -Ptb.CHASEQ=1 -o "$R/component/v${v}p${p}.vvp" "$R/component/component.sv" rtl/test/tb_qwen_rom_dec_la_takeover.sv rtl/hdc/ot_hdc_dyn_ttiles.sv rtl/hdc/ot_hdc_prefix.sv > "$R/component/compile_v${v}p${p}.log" 2>&1
  vvp "$R/component/v${v}p${p}.vvp" > "$R/component/run_v${v}p${p}.log" 2>&1
 done
done
python3 tools/qwen_rom_core_takeover_context.py --bounded --chaseq --retained "$R/retained_context" --out "$R/context_prepare"
/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys -q -s "$R/context_prepare/prepare.ys" > "$R/context_prepare/yosys.log" 2>&1
mkdir -p "$R/context_src/rtl"
python3 tools/qwen_rom_core_reuse_controller_ports.py --input "$R/context_prepare/control_context.v" --retained /srv/opentallas-scratch/codex/qwen-rom-controller-cut-context5-20261005/context_src/rtl/control_context.v --out "$R/context_src/rtl/control_context.v" --report "$R/interface.json"
cp -r /srv/opentallas-scratch/codex/qwen-rom-controller-cut-context5-20261005/context_src/configs "$R/context_src/"
cd "$R/context_src"
git init -q
git -c user.name=Codex -c user.email=codex@opentallas.local add rtl/control_context.v configs
git -c user.name=Codex -c user.email=codex@opentallas.local -c gc.auto=0 commit -qm 'Pinned bounded remainder and chase-count registered ROM controller, retained interface'
cd "$R/src"
export OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
python3 tools/run_abi3_physical.py --source-root "$R/context_src" --view asap7 --top ot_qwen_rom_core \
 --source rtl/control_context.v --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages synth,pnr \
 --core-utilization 30 --place-density 0.5 --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
 --slew-margin-percent 30 --purpose signoff_target --nickname-tag codex_rom_dec_la_chaseq1 \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --keep-workdir "$R/work" --output "$R/physical.json"
python3 tools/w18/corner_sta.py --orfs-dir "$R/work/orfs" --output "$R/corner_sta.json"
