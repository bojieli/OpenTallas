#!/usr/bin/env python3
"""Generate a native ASAP7 data-hop repeater vehicle (TT setup/FF hold,833ps).
Ideal common clock isolates signal-wire repair; never whole-die closure.
"""
import argparse,json,math
from pathlib import Path
import matplotlib.pyplot as plt

def main():
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);z=a.parse_args();z.out.mkdir(parents=True,exist_ok=True);fig,axs=plt.subplots(2,2,figsize=(14,7))
 for ax,(name,gap,buf) in zip(axs.flat,[('bare',10000,'BUFx4_ASAP7_75t_R'),('g150_x4',150,'BUFx4_ASAP7_75t_R'),('g200_x12',200,'BUFx12_ASAP7_75t_R'),('g250_x24',250,'BUFx24_ASAP7_75t_R')]):
  d=z.out/name;d.mkdir(exist_ok=True);v=['module hop(input clk,input [39:0] din,output [39:0] dout);'];place=[]
  for j in range(40):
   length=[200,400,600,750,950][j//8];y=8+j*3;count=max(0,math.ceil(length/gap)-1);v += [f'wire [{count}:0] n{j};',f'DFFHQNx1_ASAP7_75t_R source_{j}(.CLK(clk),.D(din[{j}]),.QN(n{j}[0]));',f'DFFHQNx1_ASAP7_75t_R capture_{j}(.CLK(clk),.D(n{j}[{count}]),.QN(dout[{j}]));'];place.extend([(f'source_{j}',8,y),(f'capture_{j}',8+length,y)])
   for k in range(count):
    x=8+length*(k+1)/(count+1);v.append(f'{buf} rep_{j}_{k}(.A(n{j}[{k}]),.Y(n{j}[{k+1}]));');place.append((f'rep_{j}_{k}',x,y));ax.scatter(x,y,s=4,c='red')
   ax.plot([8,8+length],[y,y],lw=.3,c='blue')
  v.append('endmodule');(d/'probe.v').write_text('\n'.join(v)+'\n');tc=['set PL /OpenROAD-flow-scripts/flow/platforms/asap7','define_corners TT FF','foreach c {TT FF} {foreach f [glob $PL/lib/NLDM/*RVT_${c}*.lib*] {read_liberty -corner $c $f}}','read_lef $PL/lef/asap7_tech_1x_201209.lef','read_lef $PL/lef/asap7sc7p5t_28_R_1x_220121a.lef','read_verilog /work/probe.v','link_design hop','initialize_floorplan -die_area {0 0 1000 140} -core_area {4.32 4.32 995.68 135.68} -site asap7sc7p5t','create_clock -name clk -period 833 [get_ports clk]','set_clock_latency -source 250 [get_clocks clk]','set_clock_uncertainty 60 -setup [all_clocks]','set_clock_uncertainty 25 -hold [all_clocks]','source $PL/setRC.tcl','set_wire_rc -signal -layer M8']
  tc.extend(f'place_inst -name {n} -location {{{x:.3f} {y:.3f}}} -status PLACED' for n,x,y in place);tc+=['estimate_parasitics -placement','puts TT_SETUP_BEGIN','report_checks -path_delay max -scenes TT -group_path_count 1 -format full_clock_expanded','puts FF_HOLD_BEGIN','report_checks -path_delay min -scenes FF -group_path_count 1 -format full_clock_expanded','puts DRV_BEGIN','report_check_types -max_slew -max_capacitance -violators','puts OT_DONE'];(d/'probe.tcl').write_text('\n'.join(tc)+'\n');(d/'meta.json').write_text(json.dumps(dict(gap_um=gap,buffer=buf,paths=40,scope=__doc__))+'\n');ax.set(xlim=(0,1000),ylim=(0,140),title=name)
 fig.tight_layout();fig.savefig(z.out/'plan.png',dpi=120)
if __name__=='__main__':main()
