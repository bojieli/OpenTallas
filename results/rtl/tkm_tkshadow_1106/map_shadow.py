from pathlib import Path
import gzip,glob,subprocess
p=Path('/OpenROAD-flow-scripts/flow/platforms/asap7');fs=[]
for pat in ['AO','INVBUF','OA','SIMPLE','SEQ']:
 a=list(p.glob(f'lib/NLDM/asap7sc7p5t_{pat}_RVT_TT*.lib*'));assert len(a)==1;fs+=a
Path('tt.lib').write_text('\n'.join(gzip.open(f,'rt').read() if str(f).endswith('.gz') else f.read_text() for f in fs))
abc='abc -script /OpenROAD-flow-scripts/flow/scripts/abc_speed.script '+ ' '.join('-liberty '+str(f) for f in fs)+' -dont_use *x1p*_ASAP7* -dont_use *xp*_ASAP7* -dont_use SDF* -dont_use ICG* -D 833'
y='read_json shadow_cone.json; synth -top tkm_shadow_d -noabc; '+abc+'; clean; '+ '; '.join('read_liberty -lib '+str(f) for f in fs)+'; stat -top tkm_shadow_d; write_verilog -noattr shadow_mapped.v; write_json shadow_mapped.json'
with open('shadow_map.log','w') as f:subprocess.run(['yosys','-Q','-p',y],stdout=f,stderr=subprocess.STDOUT,check=True)
t='read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef\nread_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef\n'+'\n'.join(f'read_liberty {f}' for f in fs)+'\nread_verilog shadow_mapped.v\nlink_design tkm_shadow_d\ncreate_clock -name clk -period 833\nset_input_delay 0 -clock clk [all_inputs]\nset_output_delay 0 -clock clk [all_outputs]\nset_load 1 [all_outputs]\nreport_checks -path_delay max -format full_clock_expanded -fields {slew cap fanout input net}\nexit\n'
Path('shadow_sta.tcl').write_text(t)
with open('shadow_sta.log','w') as f:subprocess.run(['openroad','-exit','shadow_sta.tcl'],stdout=f,stderr=subprocess.STDOUT,check=True)
