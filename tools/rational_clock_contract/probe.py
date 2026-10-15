"""Small actual-Liberty OpenROAD edge-enumeration probe, not a route gate."""
from pathlib import Path
from fractions import Fraction as F
import json, subprocess, sys
from model import clocks_tcl
OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path('/home/ubuntu/artifacts/rational-clock-contract-1015')
OUT.mkdir(parents=True,exist_ok=True)
IMAGE='openroad/orfs:latest'
OR='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
net='''module top(input pll_ref,d,shared_rx,output q,z,z0,z1,z2);
wire core_ck,fdi_ck,rx0_ck,rx1_ck,rx2_ck,c,padding,rx0_unused;
BUFx4_ASAP7_75t_R core_gen(.A(pll_ref),.Y(core_ck));
BUFx4_ASAP7_75t_R fdi_gen(.A(pll_ref),.Y(fdi_ck));
BUFx4_ASAP7_75t_R rx0_gen(.A(pll_ref),.Y(rx0_ck));
BUFx4_ASAP7_75t_R rx1_gen(.A(pll_ref),.Y(rx1_ck));
BUFx4_ASAP7_75t_R rx2_gen(.A(pll_ref),.Y(rx2_ck));
DFFHQNx1_ASAP7_75t_R core_launch(.CLK(core_ck),.D(d),.QN(c));
DFFHQNx1_ASAP7_75t_R fdi_capture(.CLK(fdi_ck),.D(c),.QN(q));
DFFHQNx1_ASAP7_75t_R core_capture(.CLK(core_ck),.D(q),.QN(z));
DFFHQNx1_ASAP7_75t_R rx0_capture(.CLK(rx0_ck),.D(q),.QN(z0));
DFFHQNx1_ASAP7_75t_R rx0_input(.CLK(rx0_ck),.D(shared_rx),.QN(rx0_unused));
DFFHQNx1_ASAP7_75t_R rx1_capture(.CLK(rx1_ck),.D(shared_rx),.QN(z1));
DFFHQNx1_ASAP7_75t_R rx2_capture(.CLK(rx2_ck),.D(shared_rx),.QN(z2));
DFFHQNx1_ASAP7_75t_R padding_fault(.CLK(fdi_ck),.D(shared_rx),.QN(padding));
endmodule
'''
# Artificial cells intentionally don't claim gearbox logic/area/timing.
flow='''set_thread_count 1
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
set tlibs [glob $P/lib/NLDM/*RVT_TT*]
set flibs [glob $P/lib/NLDM/*RVT_FF*]
foreach l [concat $tlibs $flibs] {read_liberty $l}
read_verilog /w/top.v
link_design top
read_sdc -mode ss /w/clocks.sdc
read_sdc -mode ff /w/clocks.sdc
define_scene TC -mode ss -liberty $tlibs
define_scene BC -mode ff -liberty $flibs
set_mode ss
foreach sc {TC BC} {
 set_scene $sc
 report_clock_properties [all_clocks]
 foreach clock {core fdi_ck rx0_ck rx1_ck rx2_ck} {
  set expected [expr {$clock eq "core" ? 2500.0/3.0 : 1000.0}]
  if {abs([sta::time_sta_ui [[lindex [get_clocks $clock] 0] period]]-$expected)>0.01} {error "Wrong clock frequency $clock"}
 }
 puts "SCENE $sc"
 report_clock_properties [all_clocks]
 foreach pair {{core_launch fdi_capture} {fdi_capture core_capture} {fdi_capture rx0_capture}} {
  lassign $pair a b
  foreach kind {max min} {
   set paths [find_timing_paths -from [get_pins $a/CLK] -to [get_pins $b/D] -scenes $sc -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
   if {[llength $paths] != 1} {error "Missing ordinary $kind path $a to $b in $sc"}
   puts "ORDINARY_PATH $sc $a $b $kind"
   report_checks -from [get_pins $a/CLK] -to [get_pins $b/D] -scenes $sc -path_delay $kind -format full_clock_expanded -digits 6
  }
 }
 foreach endpoint {padding_fault rx0_input rx1_capture rx2_capture} {
  foreach kind {max min} {
   set paths [find_timing_paths -scenes $sc -from [get_ports shared_rx] -to [get_pins $endpoint/D] -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
   if {[llength $paths] != 1} {error "Missing actual shared input $kind path $endpoint in $sc"}
   puts "SHARED_INPUT_PATH $sc $endpoint $kind"
   report_checks -scenes $sc -from [get_ports shared_rx] -to [get_pins $endpoint/D] -path_delay $kind -format full_clock_expanded -digits 6
  }
 }
}
puts "RATIONAL_EDGE_PROBE PASS_ENGINE_ONLY"
'''
receipts=[]
for tick in range(-5,6):
 w=OUT/('phase_'+str(tick));w.mkdir(exist_ok=True)
 (w/'top.v').write_text(net)
 sdc=clocks_tcl(F(500*tick,3))
 for root in ['core','fdi','rx0','rx1','rx2']:
  sdc=sdc.replace('[get_ports '+root+'_ck]', '[get_pins '+root+'_gen/Y]')
 sdc+='set_input_delay 10 -clock core [get_ports d]\n'
 # One real physical input can terminate in several samephase domains.
 for clock in ['fdi_ck','rx0_ck','rx1_ck','rx2_ck']:
  sdc+=f'set_input_delay 10 -clock {clock} -add_delay [get_ports shared_rx]\n'
 (w/'clocks.sdc').write_text(sdc);(w/'run.tcl').write_text(flow)
 p=subprocess.run(['docker','run','--rm','-v',f'{w}:/w',IMAGE,OR,'-no_init','-exit','/w/run.tcl'],capture_output=True,text=True)
 (w/'openroad.log').write_text(p.stdout+p.stderr)
 passed=p.returncode==0 and 'RATIONAL_EDGE_PROBE PASS_ENGINE_ONLY' in p.stdout
 receipts.append(dict(phase_tick=tick,phase_ps=str(F(500*tick,3)),returncode=p.returncode,engine_probe_pass=passed,
                      physical_qualification=False))
 if not passed:
  print((p.stdout+p.stderr)[-4000:]);break
(OUT/'receipt.json').write_text(json.dumps(dict(image=IMAGE,cases=receipts,scope='actual TT/FF Liberty ordinary max/min edge visibility; no physical/PLL/enable exception qualification'),indent=2)+'\n')
print(json.dumps(receipts))
if len(receipts)!=11 or not all(r['engine_probe_pass'] for r in receipts):sys.exit(1)
