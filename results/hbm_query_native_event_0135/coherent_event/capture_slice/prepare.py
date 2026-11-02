from pathlib import Path
import re,json
b=Path('/srv/opentallas-scratch/claude/wt/codex-hbm-query-native-event-0135/results/hbm_query_native_event_0135')
a=(b/'coherent_event/hbm_arch_q_b102.sv').read_text();z=(b/'coherent_event/hbm_arch_q_b102__physical_v1.sv').read_text()
blocks=lambda s:re.findall(r'    \(\* keep \*\) reg \[564:0\] ownface_.*?    end\n',s,re.S)
frags=blocks(a);assert len(frags)==16 and frags==blocks(z)
text='`timescale 1ns/1ps\nmodule tb; reg clk=0; always #5 clk=~clk; integer checks=0,diff=0,c,i;\n'
for g in range(2):
 text+=f'reg [567:0] w_gc_{g}_leaf_procdff_71558_Q; reg [2175:0] w_gc_{g}_leaf_procdff_71561_Q; reg [0:0] w_gc_{g}_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y;\n'
 text+=f'reg [567:0] golden_q{g}; reg [2175:0] golden_k{g}; reg golden_v{g};\n'
 old=(b/'full_proposed/hbm_arch_q_b102.sv').read_text()
 ds=[]
 for num in [71519,71524,71522]:ds.append(re.search(r'always @\(posedge clk\) g_gc_'+str(g)+r'_leaf_core_procdff_'+str(num)+r'_q <= ([^;]+);',old)[1])
 text+=f'always @(posedge clk) begin golden_q{g}<={ds[0]}; golden_k{g}<={ds[1]}; golden_v{g}<={ds[2]}; end\n'
text+=''.join(frags)
first=re.search(r'(ownface_\w+)_q0 <= ([^;]+);',text);assert first
text=text[:first.start()]+text[first.start():].replace(first[0],first[1]+'_q0 <= '+first[2]+"\n`ifdef MUT\n ^ 565'd1\n`endif\n;",1)
text+='initial begin\nfor(c=0;c<64;c=c+1) begin @(negedge clk);\n'
for g in range(2):
 text+=f'for(i=0;i<17;i=i+1) w_gc_{g}_leaf_procdff_71558_Q[i*32+:32]=$urandom; w_gc_{g}_leaf_procdff_71558_Q[564:544]=$urandom; w_gc_{g}_leaf_procdff_71558_Q[567:565]=0;\n'
 text+=f'for(i=0;i<68;i=i+1) w_gc_{g}_leaf_procdff_71561_Q[i*32+:32]=$urandom; w_gc_{g}_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y=$urandom;\n'
text+='@(posedge clk); #1;\n'
for f in frags:
 name=re.search(r'(ownface_\w+)_q0',f)[1];g=re.search(r'w_gc_(\d+)_leaf_procdff_71558_Q',f)[1];key=re.search(r'_k0 <= w_gc_\d+_leaf_procdff_71561_Q\[([^]]+)\]',f)[1]
 for region in [0,1]:
  for suffix,want in [('q',f'golden_q{g}[564:0]'),('k',f'golden_k{g}[{key}]'),('v',f'golden_v{g}')]:
   text+=f'checks=checks+1;if({name}_{suffix}{region} !== {want}) diff=diff+1;\n'
text+='$display("CAPTURE checks=%0d diff=%0d",checks,diff); end if(diff) $fatal(1,"private face mutant or mismatch"); $display("CAPTURE_EQ_PASS checks=%0d",checks); $finish; end endmodule\n'
Path('/home/ubuntu/coord/tmp/codex-query-ownface-miter-0410/tb.sv').write_text(text)
