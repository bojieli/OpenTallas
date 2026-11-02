import json
from pathlib import Path
r=Path('/srv/opentallas-scratch/claude/wt/codex-hbm-hfdep-native-0250/results/hbm_hfdep_native_0250');m=json.loads((r/'model.json').read_text());ports=m['ports'];o=Path(__file__).parent
s='`timescale 1ns/1ps\nmodule tb; reg clk=0; always #5 clk=~clk; integer c,j,checks=0,diff=0,nonzero_fault=0;\n'
for n,p in ports.items():
 if n=='clk':continue
 w=p['width'];dims=''if w==1 else'['+str(w-1)+':0] '
 if p['direction']=='input':s+='reg '+dims+n+';\n'
 else:
  s+='wire '+dims+'g_'+n+';\n';w=9 if n=='fault_cause'else w;dims=''if w==1 else'['+str(w-1)+':0] ';s+='wire '+dims+'n_'+n+';\n'
for mod,prefix in [('hfd_ep_static','g'),('hfd_ep_static_fc9','n')]:
 conns=[]
 for n,p in ports.items():conns.append('.'+n+'('+(prefix+'_'+n if p['direction']=='output'else n)+')')
 s+=mod+' #(.IDLE_K(204),.MUT(0)) '+prefix+'('+','.join(conns)+');\n'
s+='initial begin\n'
for n,p in ports.items():
 if p['direction']=='input'and n!='clk':s+=n+"='0;\n"
s+='rst_n=1; #1; rst_n=0;\nfor(c=0;c<2600;c=c+1) begin @(negedge clk);\nrst_n=!((c<4)||(c>=1200&&c<1204)||(c>=2450&&c<2454));\n'
for n,p in ports.items():
 if p['direction']!='input'or n in ['clk','rst_n']:continue
 w=p['width']
 if w>32:
  full=w//32;rem=w%32;s+=f'for(j=0;j<{full};j=j+1){n}[j*32+:32]=$urandom;\n'
  if rem:s+=f'{n}[{w-1}:{full*32}]=$urandom;\n'
 else:s+=n+'=$urandom;\n'
s+='if(c%7==0)rx_block_words=0; if(c%11==0)rx_block_words=65;\n@(posedge clk);#1;\n'
for n,p in ports.items():
 if p['direction']=='output':
  old="{g_fault_cause[10:5],g_fault_cause[2:0]}"if n=='fault_cause'else'g_'+n
  s+=f'checks=checks+1;if(n_{n} !== {old})begin diff=diff+1;if(diff<5)$display("DIFF {n} cycle%0d",c);end\n'
s+='if(g_fault===1)nonzero_fault=nonzero_fault+1;\nend\n$display("HF_FC9 checks=%0d diff=%0d fault_active=%0d",checks,diff,nonzero_fault);if(diff)$fatal(1,"FC9 projected source mismatch");if(nonzero_fault==0)$fatal(1,"vacuousfault");$display("HF_FC9_EQ_PASS");$finish;end endmodule\n'
(o/'tb.sv').write_text(s)
