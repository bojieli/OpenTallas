from pathlib import Path
import re,subprocess,json
p=Path(__file__).parent;w=Path('/srv/opentallas-scratch3/claude/wt/codex-lec-transfer-1106');root=p.parent
new=(w/'rtl/dsrom_sys/s81_link/ot_s81_kp4_dsyn.sv').read_text()
old=(root/'am_proof/ot_s81_kp4_dsyn_old.sv').read_text()
helper=re.search(r'module ot_s81_kp4_am_face3\b.*?endmodule',new,re.S).group()
pad=(root/'am_proof/face_literal.sv').read_text()
func=re.search(r'function automatic \[3:0\] pop12.*?endfunction',old,re.S).group()
oldcheck=re.search(r'always @\(posedge clk\) begin am_ok <= p_v && \(pop12\(amx\) <= 2\); pv <= p_v; end',old).group()
newcheck=new[new.index("    wire [3:0] am_distance"):new.index('`else',new.index('    wire [3:0] am_distance'))]
leaf=''
for top in ['old_am','new_am']:
 leaf+='''module TOP(input clk,raw_v,input [543:0] pma_rx,output [543:0] face_data,output reg am_ok,pv);
wire [543:0] raw_word;
ot_s81_pma_rxm prx(.pma_rck(clk),.pma_rx(pma_rx),.q(raw_word));
ot_pl_pad #(.W(544),.N(1)) u_face_p_d(.ck(clk),.d(raw_word),.q(face_data));
wire p_v;ot_pl_pad #(.W(1),.N(1)) u_face_p_v(.ck(clk),.d(raw_v),.q(p_v));
wire [543:0] p_d=face_data;
'''.replace('TOP',top)
 if top=='old_am':leaf+="wire [11:0] amx=p_d[543:532]^12'hA5C;\n"+func+'\n'+oldcheck+'\n'
 else:leaf+='wire [8:0] am_face3;ot_s81_kp4_am_face3 u_face_am3(.clk(clk),.p_d(raw_word),.parts(am_face3));\n'+newcheck
 leaf+='endmodule\n'
(p/'leaf.sv').write_text(leaf+helper+'\n'+pad+'\n')
libs=json.loads((root/'postcts_gate_tt.libraries.json').read_text())['libraries'];std=[r['path'] for r in libs if '_RVT_TT_' in r['path']];assert len(std)==5
seq=next(x for x in std if '_SEQ_' in x)
libargs=' '.join('-liberty '+x for x in std)
for top in ['old_am','new_am']:
 ys='read_verilog -lib /work/am_map_fa/ot_s81_pma_rxm_bb.v\nread_verilog -sv /work/am_map_fa/leaf.sv\nhierarchy -top '+top+'\nsynth -top '+top+' -flatten -noabc\n'+ '\n'.join('read_liberty -lib '+x for x in std)+'\nextract_fa\ntechmap -map /work/am_map_fa/adder_map.v\ntechmap\nopt -fast\ndfflibmap -liberty '+seq+'\n'
 ys+='abc -script /OpenROAD-flow-scripts/flow/scripts/abc_speed.script '+libargs+' -dont_use *x1p*_ASAP7* -dont_use *xp*_ASAP7* -dont_use SDF* -dont_use ICG* -D 833\n'
 ys+='\n'.join('read_liberty -lib '+x for x in std)+'\nclean -purge\nstat\nwrite_verilog -noattr -noexpr /work/am_map_fa/'+top+'.mapped.v\nwrite_json /work/am_map_fa/'+top+'.json\n'
 (p/(top+'.ys')).write_text(ys)
