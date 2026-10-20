from pathlib import Path
import json,re
r=Path(__file__).resolve().parent;parent=r.parent
s=(parent/'top.sv').read_text();assert s.count('module qkd_kvs_hroot_safe32 (')==1;(r/'gold_inner.sv').write_text(s.replace('module qkd_kvs_hroot_safe32 (','module qkd_kvs_hroot_safe32__ot_pr_core (',1))
header=s[s.index('(')+1:s.index(');')];ports=re.findall(r'\b(input|output) wire\s*(\[[^]]+\])?\s*(\w+)',header);decl=[];conns={side:[] for side in ['gold','gate']};outputs=[]
for direction,width,n in ports:
 w=(width+' ') if width else ''
 if direction=='input':decl.append('input '+w+n+';')
 else:
  outputs.append(n)
  for side in ['gold','gate']:decl.append('wire '+w+side+'_'+n+';')
 for side in ['gold','gate']:conns[side].append('.'+n+'('+n+')' if direction=='input' else '.'+n+'('+side+'_'+n+')')
checks=['(!head_required || gold_o_pc == gate_o_pc)']+['(!relay_required || gold_'+n+' == gate_'+n+')' for n in outputs if n!='o_pc']
m='module leaf_equiv('+','.join(n for d,w,n in ports if d=='input')+',ok);\n'+'\n'.join(decl)+'\noutput ok;\n'+''.join(side+'_top '+side+'('+','.join(conns[side])+');\n' for side in ['gold','gate'])+'''\n// Observer-only knowledge flags; no DUT/gold/gate FF init assumptions.
reg [2:0] input_known=0;
reg [3:0] reset_known=0;
reg [3:0] reset_samples;
reg head_ever_known=0;
always @(posedge ck)begin
 input_known<={input_known[1:0],1'b1};
 reset_known<={reset_known[2:0],1'b1};
 reset_samples<={reset_samples[2:0],rst_n};
 if(reset_known[3] && !reset_samples[3])head_ever_known<=1'b1;
end
wire relay_required=input_known[2];
wire head_required=head_ever_known || (reset_known[3] && !reset_samples[3]);
assign ok='''+' && '.join(checks)+';\nendmodule\n';(r/'miter.sv').write_text(m)
