#!/usr/bin/env python3
"""Real library timing at a requested early control tap; D setup remains a gate."""
import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'results/arch/hbm_native_1013/sm_local_icg_1014/static_tap';E=Path(__file__).resolve().parents[1]/'results/arch/hbm_native_1013/sm_local_icg_1014/clock_baseline'
s=(E/'gating.v').read_text().replace('module gating(input clk,','module gating(input next_enable, input clk_aux, input clk,').replace('wire ena;','wire ena; wire old_ena; wire local_qn; wire aux_ena; wire aux_qn;\nDFFHQNx1_ASAP7_75t_R mirror_aux(.CLK(clk_aux),.D(next_enable),.QN(aux_qn));\nINVx4_ASAP7_75t_R aux_inv(.A(aux_qn),.Y(aux_ena));\nDFFHQNx1_ASAP7_75t_R mirror(.CLK(clk),.D(next_enable),.QN(local_qn));\nINVx4_ASAP7_75t_R local_inv(.A(local_qn),.Y(ena));').replace('.cut_8870(ena)','.cut_8870(old_ena)');
for i in [0,1,2,3,5,6,7,8]: s=s.replace(f'gate_{i}(.CLK(clk_child_{i}), .ENA(ena)',f'gate_{i}(.CLK(clk_child_{i}), .ENA(aux_ena)')
(O/'gating.v').write_text(s)
phase_plan=json.loads((E/'plan.json').read_text())
for c in ('tt','ff','ss'):
 ownR=phase_plan['own_ENA'][c]['R_ps']
 s=(E/f'probe_{c}.tcl').read_text().replace('read_verilog /probe/gating.v',f'read_liberty /probe/INVBUF_{c}.lib\nread_verilog /probe/gating.v')
 s=s.replace('own/cut_8870','mirror/QN')
 s=s.replace('create_clock -name RAW_0',f'create_clock -name OWN_AUX -period 833.333 [get_ports clk_aux]\nset_clock_latency -source {-ownR+80.0} [get_clocks OWN_AUX]\ncreate_clock -name RAW_0')
 s=s.replace('set cmd [list find_timing_paths -from [get_pins mirror/QN]', 'set launch_pin [expr {$i in {4 9 10 11} ? "mirror/QN" : "mirror_aux/QN"}]\n    set cmd [list find_timing_paths -from [get_pins $launch_pin]')
 s=s.replace('if {$sc ne "OWN_RAW"', 'set expected_clock [expr {$i in {4 9 10 11} ? "OWN_RAW" : "OWN_AUX"}]\n    if {$sc ne $expected_clock')
 s=s.replace('set current_U($i) $u','set current_U($i) $u')
 s=s.replace('set after [check_paths', 'for {set i 0} {$i<12} {incr i} {set_clock_uncertainty -setup $current_U($i) -from [get_clocks OWN_AUX] -to [get_clocks RAW_$i]}\nset after [check_paths')
 s=s.replace('set_propagated_clock [all_clocks]', 'set_propagated_clock [all_clocks]')
 assert f'set_clock_latency -source -{ownR} [get_clocks OWN_RAW]' in s
 s=s.replace(f'set_clock_latency -source -{ownR} [get_clocks OWN_RAW]',f'set_clock_latency -source {-ownR+20.0} [get_clocks OWN_RAW]').replace(f'abs($ownarr+{ownR})',f'abs($ownarr+{ownR-20.0})')
 s=s.replace('static_diagnostic_only_no_native_phase_qualification','REQUESTED_EARLY_TAP_20PS_IDEAL_WIRES_NO_D_SETUP_PHYSICAL_QUALIFICATION');(O/f'probe_{c}.tcl').write_text(s)
(O/'run.sh').write_text('''#!/bin/bash
set -euo pipefail
if [[ ! -f SEQ/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib ]]; then tar -xzf frozen_inputs.tar.gz; fi
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
for c in tt ff ss; do
 C=${c^^}
 docker run --rm "$image" zcat /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_${C}_nldm_220122.lib.gz > "INVBUF_${c}.lib"
 docker run --rm -v "$PWD:/probe" "$image" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "/probe/probe_$c.tcl" > "probe_$c.receipt.log" 2>&1
 cat "probe_$c.receipt.log"
 grep -q "SM_GATING_PASS $c" "probe_$c.receipt.log"
done
''')
(O/'request.json').write_text(json.dumps({'status':'EARLY_TAP_DIAGNOSTIC_ONLY','candidate_leaf_sha256':hashlib.sha256((O.parent/'eg_leaf.json').read_bytes()).hexdigest(),'clock_local_insertion_requested_ps':{'critical':20,'auxiliary':80},'source_clock':'actual OWN_RAW phi-Rown','all12_ICG_sources':'actual frozen child RAW source associations','D_unconstrained_control_for_clocktoq_diagnostic':True,'no_D_setup_or_native_physical_qualification':True},indent=2)+'\n')
