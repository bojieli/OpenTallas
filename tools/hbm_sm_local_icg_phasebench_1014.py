#!/usr/bin/env python3
"""Exercise actual RAW phase associations and mirrored enable pulse identity.
No delay model or Liberty timing qualification is implied by this functional gate.
"""
import re,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];O=ROOT/'results/arch/hbm_native_1013/sm_local_icg_1014'
E=Path(__file__).resolve().parents[1]/'results/arch/hbm_native_1013/sm_local_icg_1014/clock_baseline'
records={}
for c,Rown in [('tt',149.2),('ff',114.9),('ss',207.0)]:
 log=(E/f'probe_{c}.receipt.log').read_text()
 phases=[]
 for i in range(12):
  m=re.search(r'SM_GATE_CAL '+c+' '+str(i)+r' .*?childR=([\d.]+) gate_rise=([\d.]+)',log);assert m
  phases.append((Rown-float(m[1])-float(m[2]))%833.333)
 tb=(O/'eg_tb.sv').read_text().replace('module tb;','module tb;\ntimeunit 1ps; timeprecision 1fs;\ninteger pulses=0; integer enable_checks=0;')
 tb=re.sub(r'gold_eg u_gold\([^;]+;', '',tb)
 decl=[]
 for i,phase in enumerate(phases):
  tb=tb.replace(f'.clk_child_{i}(clk)',f'.clk_child_{i}(phase_raw_{i})')
  decl += [f'reg phase_raw_{i}=0; wire reference_gclk_{i};',f'initial begin #({416.6665+phase:.6f}); forever begin phase_raw_{i}=1; #416.6665; phase_raw_{i}=0; #416.6665; end end',f'ICGx1_ASAP7_75t_R reference_{i}(.CLK(phase_raw_{i}),.ENA(u_split.u_own.cut_8870),.SE(1\'b0),.GCLK(reference_gclk_{i}));',f'always @(phase_raw_{i},reference_gclk_{i},u_split.u_own.local_gclk_{i}) begin #0.001; if(checked>32 && reference_gclk_{i} !== u_split.u_own.local_gclk_{i}) $fatal(1,"phase '+c+f' child{i} mirrored original8870 pulse differs"); end',f'always @(posedge u_split.u_own.local_gclk_{i}) if(checked>32) pulses=pulses+1;']
 tb=tb.replace('initial begin\nclk=0;', '\n'.join(decl)+'\ninitial begin\nclk=0;')
 tb=tb.replace('#2; clk=1; #2;','#416.6665; clk=1; #200;')
 tb=re.sub(r'if\(g_\w+ !== s_\w+\) mismatches=mismatches\+1;', '',tb)
 tb=tb.replace('checked=checked+1; end; clk=0; #2;', 'if(u_split.u_own.local_enable !== u_split.u_own.cut_8870) $fatal(1,"enable mirror state differs from original8870"); enable_checks=enable_checks+1; checked=checked+1; end; #216.6665; clk=0;')
 tb=tb.replace('$display("OWN_LOGIC_CYCLE_BENCH checked=%0d mismatches=%0d",checked,mismatches);', '$display("LOCAL_ICG_PHASE_'+c+' checked=%0d enable_checks=%0d pulses=%0d",checked,enable_checks,pulses); if(pulses<100) $fatal(1,"no enabled pulses exercised");')
 (O/f'phase_{c}_tb.sv').write_text(tb)
 records[c]={'ownR_ps':Rown,'child_RAW_relative_own_ps':phases,'source_phase_log_sha256':hashlib.sha256(log.encode()).hexdigest()}
(O/'phase_binding.json').write_text(json.dumps({'status':'FUNCTIONAL_PHASE_MODEL_ONLY_NOT_LIBERTY_OR_PHYSICAL','corners':records},indent=2)+'\n')
(O/'phase_run.sh').write_text('''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
tag=${1:-split}; corner=${2:-ss}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
yosys -Q -p "read_json eg_${tag}.json; hierarchy -top split_eg; write_verilog -noattr eg_${tag}_phase_dut.sv" > phase_${corner}_${tag}_emit.log
"$V" --binary --timing -j 4 -Wno-fatal --top-module tb --Mdir work_phase_${corner}_${tag} eg_${tag}_phase_dut.sv eg_surrogates.sv phase_${corner}_tb.sv retention_cell_models.sv > phase_${corner}_${tag}_build.log 2>&1
set +e
./work_phase_${corner}_${tag}/Vtb > phase_${corner}_${tag}_runtime.log 2>&1
rc=$?
set -e
cat phase_${corner}_${tag}_runtime.log
exit "$rc"
''')
