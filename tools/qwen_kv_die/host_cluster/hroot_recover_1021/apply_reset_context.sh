#!/usr/bin/env bash
set -euo pipefail
cd controller_onebank
mkdir -p reset_context
L='';for f in libs/*.lib;do L="$L read_liberty -lib $f;";done
yosys -l reset_context/mapped.log -p "$L read_json parent_bound.json; read_verilog qkd_hr_ingest_soft_n32.sv; hierarchy -check -top qkd_hr_ingest_qm; tcl ../reset_context.tcl; synth -top qkd_hr_ingest_qm -noabc; dfflibmap -liberty libs/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; opt_clean; write_verilog -noattr reset_context/whole_reset_context.v; write_json reset_context/whole_reset_context.json" > reset_context/stdout.log 2>&1
args=(python3 native_census.py --netlist reset_context/whole_reset_context.v --top qkd_hr_ingest_qm --out reset_context/native.json);for f in libs/*.lib macro_libs/*.lib;do args+=(--liberty "$f");done
"${args[@]}" > reset_context/native.log 2>&1
