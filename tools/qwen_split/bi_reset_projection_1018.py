"""Emit a reset-only component projection; root clocks share netlist-bench phase.

The result does not prove physical reset phase. Compile against qfd_link_slots.sv,
qfd_fwd_lane.sv and ot_qwen_rst_rep.sv; no digital block is replaced internally.
Regenerate on every GEN. Inputs: emitted die.v and output projection.sv.
"""
import re
import sys
from pathlib import Path
s=Path(sys.argv[1]).read_text(); lines=[]; nets=set(); monitors=[]
for l in s.splitlines():
 m=re.match(r'  (qfd_rst\w+|qfd_rlyr\w*) (\w+) \(',l)
 if not m:continue
 master,name=m.groups();p=dict(re.findall(r'\.(\w+)\((\w+)\)',l));nets.update(p.values())
 if master.startswith('qfd_rlyr'):
  if master.startswith('qfd_rlyrl'):l=f'ot_qfd_rlane_land {name} (.ck({p["ck"]}),.a({p["a"]}),.b({p["b"]}));'
  else:l=f'ot_qfd_rlane_st {name} (.cap({p.get("ck",p.get("ckf"))}),.a({p["a"]}),.b({p["b"]}),.ck_o({p.get("ck_o", "unused_"+name)}));';nets.add(p.get('ck_o','unused_'+name))
 lines.append(l)
 for port in ['rso_d','rso_f','rso_seq','rso_ctlm','rso_io','rso_s','b']:
  if port in p:monitors.append(f'always @(posedge {p[port]}) if(cyc>1000) $display("RELEASE {name}.{port} %0d",cyc);')
clocks={n for n in nets if n.startswith('n_clk')};nets.add('n_rst_fwd')
out='module tb; reg ck=0;always #5 ck=~ck; integer cyc=0;always @(posedge ck) cyc<=cyc+1; reg reset=1; initial begin #0.1;reset=0;#10240;reset=1;#24000;$finish;end\n'
out+='\n'.join('wire '+n+';' for n in sorted(nets))+'\n'
out+='\n'.join('assign '+n+'=ck;' for n in clocks)+'\nassign n_rst_fwd=reset;\n'
out+='\n'.join(lines+monitors)+'\nendmodule\n'
out+='module qfd_rst_rep(input wire clk,d,output wire q0,q1); ot_qwen_rst_rep u(.clk(clk),.d(d),.q0(q0),.q1(q1));endmodule\n'
out+='module qfd_rst_rep_p8(input wire clk,d,output wire q0,q1); ot_qwen_rst_rep #(.PAD(8)) u(.clk(clk),.d(d),.q0(q0),.q1(q1));endmodule\n'
Path(sys.argv[2]).write_text(out)
