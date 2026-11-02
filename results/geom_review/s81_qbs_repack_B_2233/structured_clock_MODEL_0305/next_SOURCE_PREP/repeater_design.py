from pathlib import Path
import json,sys
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan');import die_clock_128 as N
names=['BUFx2_ASAP7_75t_R','BUFx4_ASAP7_75t_R','BUFx8_ASAP7_75t_R','BUFx12_ASAP7_75t_R','BUFx16f_ASAP7_75t_R','BUFx24_ASAP7_75t_R'];libs={c:N.lib_cells(c,'/srv/opentallas-scratch/claude/flat-clock-model/lib',names=names)for c in('TT','FF')};ans=[]
for m in names:
 for length in range(32,201,8):
  samples=[];ok=True
  for c in('TT','FF'):
   for layer,r,cap in[('M6',.0118796,.1305),('M7',.0125096,.0925)]:
    lib=libs[c][m];load=length*cap+lib['cap'];d,s=N.stage(lib,40,length*r,length*cap,lib['cap']);inside=lib['delay'][1][0]<=load<=lib['delay'][1][-1]and lib['delay'][0][0]<=40<=lib['delay'][0][-1];ok &=inside and s<=80;samples.append(dict(corner=c,layer=layer,load_ff=load,delay_ps=d,slew_ps=s,characterized=inside,normalized_delay_per_um=d/length/(250 if c=='TT' else 202.5)))
  if ok:ans.append(dict(master=m,length_um=length,worst_normalized_delay_per_um=max(q['normalized_delay_per_um']for q in samples),samples=samples))
best=min(ans,key=lambda q:q['worst_normalized_delay_per_um']);out=dict(scope='A-priori source-only self-driving repeater design from actual TT/FFNLDM and nativeM6/M7RC, noCTS/GRT/STA/measurements; length<=200um is a conservative MODEL bound, not a new policy',input_slew_ps=40,output_slew_model_limit_ps=80,valid_candidates=len(ans),best=best,alternatives=sorted(ans,key=lambda q:q['worst_normalized_delay_per_um'])[:10]);Path(__file__).with_suffix('.json').write_text(json.dumps(out,indent=2)+'\n');print(best)
