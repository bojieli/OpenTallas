from pathlib import Path
import json,math
p=Path(__file__).resolve().parent;ports=json.loads((p/'source_candidate.json').read_text())['ports'];inputs=[x for x in ports if x['direction']=='input'and x['name']not in ('clk','rst_n','strap_qid')];outputs=[x for x in ports if x['direction']=='output']
l=['`timescale 1ps/1fs','module tb_ring_face_bridge;','reg clk=0;always #416.5 clk=~clk;','reg rst_n=1;integer cycle=0,checks=0,known_ports=0,nonzero_ports=0;integer seed=32\'h5ac931e7;']
for x in inputs:l.append(f"reg {x['range']} {x['name']}=0;")
l+=['genvar q;generate for(q=0;q<2;q=q+1)begin:g_q','localparam [1:0] QID=q+2;']
for x in outputs:
 for profile in ('a','b'):l.append(f"wire {x['range']} {profile}_{x['name']};")
for profile,mod in (('a','physical_ot_hfd_coll_q2_hard_v8g__ring_ag'),('b','current_native_ring_face')):
 connects=[]
 for x in ports:
  n=x['name'];v='QID'if n=='strap_qid'else(profile+'_'+n if x['direction']=='output'else n);connects.append(f'.{n}({v})')
 l.append(mod+' u_'+profile+'('+','.join(connects)+');')
a=','.join('a_'+x['name']for x in outputs);b=','.join('b_'+x['name']for x in outputs)
l+=['always @(posedge clk) begin #1;',f' if({{{a}}} !== {{{b}}}) begin $display("RING_FACE_DIFF cycle%0d qid%0d",cycle,QID);$fatal(1,"current-native face candidate differs from actual physical shell");end','end','end endgenerate']
l+=['always @(negedge clk)begin','cycle=cycle+1;']
for x in inputs:
 n=x['name'];words=math.ceil(x['width']/32);l.append(f" {n}="+'{'+','.join('$random(seed)'for _ in range(words))+'};')
l+=['if(cycle==66||cycle==310||cycle==755)rst_n=1;','if(cycle==244||cycle==689)rst_n=0;',
     "if(cycle%29==0)begin ra_lp_data[7:0]=8'bxzxz0101;pr_cw_i[31:24]=8'bzxxz1001;end",
     'if(cycle==1600)begin $display("RING_FACE_PASS edges%0d full_output_bits1345 qids2_3 no_valid_mask POR66 repeated_reset XZ",cycle);$finish;end','end',
     'initial begin #1;rst_n=0;end','endmodule']
(p/'tb_ring_face_bridge.sv').write_text('\n'.join(l)+'\n')
