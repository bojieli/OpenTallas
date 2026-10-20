#!/bin/bash
set -euo pipefail
O=$1;mkdir -p "$O"
python3 tools/qwen_dv/bound_math_netlist.py ../input/generic.json --load-cap 16 --transparent-inverters --retain-mux --shared-helpers --retain-bit 14070 --top qfd_dv_s5_ctl --name qfd_dv_s5_ctl_repair2 --out "$O/qfd_dv_s5_ctl_repair2.sv" --helpers "$O/helpers.sv" --record "$O/model.json" > "$O/construct.log" 2>&1
# A real functional mutant: incorrect collective command bit, not a checker mutation.
yosys -Q -p "read_verilog -sv ../input/ctl_resetstage.sv rtl/qwen_dv/mu/qfd_dv_amax_mu.sv; chparam -set MUT 11 qfd_dv_s5_ctl; hierarchy -check -top qfd_dv_s5_ctl; synth -top qfd_dv_s5_ctl -flatten -noabc -nofsm -noshare; dffunmap; clean; write_json $O/mut11.json" > "$O/mut11_generic.log" 2>&1
python3 tools/qwen_dv/bound_math_netlist.py "$O/mut11.json" --load-cap 16 --transparent-inverters --retain-mux --shared-helpers --retain-bit 14070 --top qfd_dv_s5_ctl --name qfd_dv_s5_ctl_repair2_mut11 --out "$O/mut11.sv" --helpers "$O/mut11_helpers.sv" --record "$O/mut11_model.json" > "$O/mut11_construct.log" 2>&1
