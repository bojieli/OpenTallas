#!/usr/bin/env python3
"""Opt-in same-edge station controls; configuration acceptance is +2 edges.

No shared arithmetic source is edited. Registered valid copies are made at
the arithmetic's existing output boundary, not from its output one edge later.
"""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import die_port_bind as P
from reset_partition import partition
s=P.preprocess(P.strip_comments((ROOT/'rtl/qwen_dv/qfd_dv_redstn2.sv').read_text()),{'OT_QFD_DV_SAFE_STORAGE':''})
s=s.replace('ot_hdc_fp32_add_lat #','qfd_dv_station_add_lat #')
for name,prefix in [('vlol','vlo'),('vhil','vhi'),('v8l','v8'),('v9l','v9')]:
 s=s.replace(f'wire [15:0] {name};',f'wire [15:0] {name}; wire[31:0] {prefix}_rep;')
 # The declaration of L7 lists two signals in one statement.
 s=s.replace('wire [15:0] vlol, vhil;', 'wire [15:0] vlol, vhil; wire[31:0] vlo_rep,vhi_rep;',1) if 'wire[31:0] vlo_rep,vhi_rep;' not in s else s
 s=s.replace(f'.valid_out({name}[l]))',f'.valid_rep({prefix}_rep[2*l+:2]), .valid_out({name}[l]))')
# Each 16-bit selection uses a separately retained state driver.
a=s.index('    wire [511:0] y7 =');b=s.index(';',a)+1
s=s[:a]+'''wire[511:0] y7;
for(genvar z=0;z<32;z=z+1) begin:g_y7
 assign y7[16*z+:16]=vlo_rep[z]?ylo[16*z+:16]:hb_q[16*z+:16];
end
'''+s[b:]
a=s.index('    always @(posedge ck or negedge rst_n)\n        if (!rst_n) nb_o');b=s.index('    wire        fv',a)
s=s[:a]+'''for(genvar z=0;z<32;z=z+1) begin:g_nb
 qfd_dv_station_out #(.W(16),.ID(z)) u_o(.ck(ck),.rst_n(rst_n),.d((v8_rep[z]&&local_mode[z][3])?y8[16*z+:16]:16'd0),.q(nb_o[16*z+:16]));
end
qfd_dv_station_out #(.W(2),.ID(100)) u_ov(.ck(ck),.rst_n(rst_n),.d({1'b0,v8&&mode==2'd3}),.q(nb_o[513:512]));
'''+s[b:]
s=s.replace("wire [511:0] fd = (mode == 2'd0) ? y7 : (mode == 2'd1) ? y8 : y9;",'''wire[511:0] fd;
for(genvar z=0;z<32;z=z+1) begin:g_fd
 assign fd[16*z+:16]=local_mode[z][0]?y7[16*z+:16]:local_mode[z][1]?y8[16*z+:16]:y9[16*z+:16];
end''')
s=s.replace('.valid_in(v9_in),','.valid_in(nbv && local_mode[2*l][2]),')
s=s.replace(".b({ws3 ? 16'h3F80", ".b({ws_rep[l] ? 16'h3F80")
header=s.index(');')+2
local='''
wire[3:0] local_mode[0:31];
wire[1:0] mode_mid[0:1];wire[1:0] mode_payload[0:31];
for(genvar z=0;z<2;z=z+1) begin:g_mode_mid
 (* keep_hierarchy="yes" *) qfd_dv_station_copy #(.W(2),.ID(z)) u_c(.ck(ck),.d(cfg_mode),.q(mode_mid[z]));
end
for(genvar z=0;z<32;z=z+1) begin:g_mode_payload
 (* keep_hierarchy="yes" *) qfd_dv_station_copy #(.W(2),.ID(100+z)) u_p(.ck(ck),.d(mode_mid[z/16]),.q(mode_payload[z]));
 (* keep_hierarchy="yes" *) qfd_dv_station_mode #(.ID(z)) u_m(.ck(ck),.rst_n(rst_n),.cfg_v(CFG_LOCAL[z]),.mode(mode_payload[z]),.q(local_mode[z]));
end
wire[15:0] ws_rep;
for(genvar z=0;z<16;z=z+1) begin:g_ws
 (* keep_hierarchy="yes" *) qfd_dv_station_copy #(.ID(200+z)) u_c(.ck(ck),.d(ws2),.q(ws_rep[z]));
end
'''
s=s[:header]+local+s[header:]
s,record=partition(s,'qfd_dv_redstn2',reset='rst_n')
# Every textual configuration consumer gets a private valid. The local mode
# loop expands to 32 leaves; scalar/pointer controls use separate leaves.
header=s.index(');')+2
head,body=s[:header],s[header:]
fields=[('cfg_mode',2),('cfg_wsrc',1),('cfg_nwords',8),('cfg_sbase',9),('cfg_kcm1',8)]
for name,w in fields:body=re.sub(r'\b'+name+r'\b','safe_'+name,body)
# mode_mid deliberately captures original pin mode at stage one.
body=body.replace('.d(safe_cfg_mode),.q(mode_mid','.d(cfg_mode),.q(mode_mid')
count=32
def leaf(_):
 global count
 out=f'cfg_final[{count}]';count+=1;return out
body=re.sub(r'\bcfg_v\b(?!\s*\()',leaf,body)
body=body.replace('CFG_LOCAL[z]','cfg_final[z]')
mid=(count+23)//24
decl='\nreg[27:0] cfg_payload0,cfg_payload1;\n'
decl+='\n'.join(f'wire[{w-1}:0] safe_{n};' for n,w in fields)+'\n'
decl+='assign {'+','.join('safe_'+n for n,w in fields)+'}=cfg_payload1;\n'
decl+='always @(posedge ck) begin cfg_payload0<={'+','.join(n for n,w in fields)+'};cfg_payload1<=cfg_payload0;end\n'
decl+=f'wire[{mid-1}:0] cfg_mid;wire[{count-1}:0] cfg_final;\n'
decl+=f'for(genvar z=0;z<{mid};z=z+1) begin:g_cfg_mid\n(* keep_hierarchy="yes" *) qfd_dv_station_copy #(.ID(400+z)) u_c(.ck(ck),.d(cfg_v),.q(cfg_mid[z]));end\n'
decl+=f'for(genvar z=0;z<{count};z=z+1) begin:g_cfg_final\n(* keep_hierarchy="yes" *) qfd_dv_station_copy #(.ID(500+z)) u_c(.ck(ck),.d(cfg_mid[z/24]),.q(cfg_final[z]));end\n'
decl+='wire cfg_schedule_fault=(cfg_v||cfg_mid[0]||cfg_final[0])&&(rs_s[512]||rs_s[1026]||rs_n[512]||rs_n[1026]||nb_i[512]);\n'
body=body.replace('fault | in_bad | fp_bad','fault | in_bad | fp_bad | cfg_schedule_fault')
s=head+decl+body
s+='''
(* keep_hierarchy="yes" *) module qfd_dv_station_copy #(parameter integer W=1,ID=0)(input wire ck,input wire[W-1:0] d,output reg[W-1:0] q);
always @(posedge ck) q<=d;
endmodule
(* keep_hierarchy="yes" *) module qfd_dv_station_out #(parameter integer W=16,ID=0)(input wire ck,rst_n,input wire[W-1:0] d,output reg[W-1:0] q);
always @(posedge ck or negedge rst_n) if(!rst_n) q<=0;else q<=d;
endmodule
(* keep_hierarchy="yes" *) module qfd_dv_station_mode #(parameter integer ID=0)(input wire ck,rst_n,cfg_v,input wire[1:0] mode,output reg[3:0] q);
always @(posedge ck or negedge rst_n) if(!rst_n) q<=4'b0001;else if(cfg_v) q<=4'b0001<<mode;
endmodule
'''
x=(ROOT/'rtl/hdc/ot_hdc_fp32_add_lat.sv').read_text()
x=x[x.index('module ot_hdc_fp32_add_lat '):];x=x[:x.index('endmodule')+len('endmodule')]
x=x.replace('module ot_hdc_fp32_add_lat','module qfd_dv_station_add_lat',1)
x=x.replace('output reg         valid_out','output wire [1:0] valid_rep,\n    output reg         valid_out')
x=x.replace('endmodule','''for(genvar z=0;z<2;z=z+1) begin:g_rep
 (* keep_hierarchy="yes" *) qfd_dv_station_copy #(.ID(700+z)) u_c(.ck(clk),.d(rst_n && u_v),.q(valid_rep[z]));
end
endmodule''')
(ROOT/'rtl/qwen_dv/qfd_dv_redstn2_csafe.sv').write_text('// GENERATED by tools/qwen_dv/gen_station_csafe.py\n'+s+'\n'+x+'\n')
record.update(configuration_added_edges=2,configuration_ii=1,steady_data_added_edges=0,cfg_valid_copies=count+mid,native_fanout_qualification='PENDING')
(ROOT/'results/arch/safe_qw_slice_1019/station_control_model.json').write_text(json.dumps(record,indent=2)+'\n')
print('STATION_CSAFE',count,'CFG leaves, data+0 CFG+2; native census PENDING')
