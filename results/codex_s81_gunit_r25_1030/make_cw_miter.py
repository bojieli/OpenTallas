from pathlib import Path
import re
R=Path(__file__).resolve().parent
mods=[]
for tag,file in [('old','gunit_original.sv'),('candidate','gunit_candidate.sv')]:
 t=(R/file).read_text();cap=next(x for x in t.splitlines() if ' u_bin_unit_i0 (' in x)
 stage=[x for x in t.splitlines() if ' u_ist_unit_i0_0 (' in x]
 fields=[re.search(r'\.'+n+r'\((unit_i0[^)]*)\)',t).group(1) for n in ['cw_v','cw_d','cw_a']]
 body='\n'.join([cap]+stage)
 decl='wire [264:0] unit_i0_q,unit_i0_is0_q; wire unit_i0_eq,unit_i0_is0_eq;'
 out='assign cw={' + ','.join(fields) + '}; assign epoch='+('unit_i0_is0_eq' if stage else 'unit_i0_eq')+';'
 for variant in ([tag] if not stage else [tag,'badreset','badpayload']):
  b=body
  if variant=='badreset':b=b.replace('.rst_n(rst_n), .d(unit_i0_q)',".rst_n(1'b1), .d(unit_i0_q)")
  if variant=='badpayload':b=b.replace('.d(unit_i0_q)',".d(unit_i0_q ^ 265'b1)")
  mods.append(f'module cw_{variant}(input clk,rst_n,input[265:0]unit_i0,output[264:0]cw,output epoch);\n{decl}\n{b}\n{out}\nendmodule')
(R/'cw_native_cuts.sv').write_text('\n'.join(mods)+'\n')
