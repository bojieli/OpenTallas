#!/usr/bin/env python3
"""Opt-in same-edge station controls; configuration acceptance is +2 edges.

No shared arithmetic source is edited. Registered valid copies are made at
the arithmetic's existing output boundary, not from its output one edge later.
"""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BOUNDED='--bounded' in sys.argv
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
 (* keep_hierarchy="yes" *) qfd_dv_station_mode #(.ID(z),.USE2(z%2==0)) u_m(.ck(ck),.rst_n(rst_n),.cfg_v(CFG_LOCAL[z]),.mode(mode_payload[z]),.q(local_mode[z]));
end
wire[15:0] ws_rep;
for(genvar z=0;z<16;z=z+1) begin:g_ws
 (* keep_hierarchy="yes" *) qfd_dv_station_copy #(.ID(200+z)) u_c(.ck(ck),.d(ws2),.q(ws_rep[z]));
end
'''
if BOUNDED:
 local=local.replace('(* keep_hierarchy="yes" *) qfd_dv_station_copy #(.ID(200+z)) u_c(.ck(ck),.d(ws2),.q(ws_rep[z]));', '''wire ws_source;
+ (* keep_hierarchy="yes" *) qfd_dv_station_cfgbit #(.ID(z)) u_c(.ck(ck),.rst_n(rst_n),.cfg_v(CFG_LOCAL[2*z]),.d(cfg_wsrc),.q(ws_source));
+ qfd_dv_ring_delay #(.W(1),.D(3)) u_d(.clk(ck),.rst_n(rst_n),.d(ws_source),.q(ws_rep[z]));'''.replace('\n+','\n'))
 a=s.index('    reg         fv1, fv2, fv3,');b=s.index('    wire [511:0] y;',a)
 s=s[:a]+'''wire fv3,ls3;wire[7:0] j3;
+qfd_dv_ring_delay #(.W(10),.D(3)) u_meta(.clk(ck),.rst_n(rst_n),.d({fv,j,j+8'd1==nwords}),.q({fv3,j3,ls3}));
+'''.replace('\n+','\n')+s[b:]
 s=s.replace('ot_hdc_delay #(.W(9), .D(SCALE_LAT))','qfd_dv_ring_delay #(.W(9), .D(SCALE_LAT))')
s=s[:header]+local+s[header:]
if BOUNDED:
 # Only actual reset consumers get leaves: 16lo+1hi+16L8+1L9+1scale.
 s=s.replace('u_lo (.clk(ck), .rst_n(rst_n)', 'u_lo (.clk(ck), .rst_n(math_reset[l])')
 s=s.replace('u_hi (.clk(ck), .rst_n(rst_n)', "u_hi (.clk(ck), .rst_n(l==0?math_reset[16]:1'b1)")
 for label,nxt,reset_expr in [('g_l8','g_l9','math_reset[17+l]'),('g_l9','g_sc',"l==0?math_reset[33]:1'b1"),('g_sc',None,"l==0?math_reset[34]:1'b1")]:
  a=s.index('begin : '+label);b=s.index('end endgenerate',a)
  s=s[:a]+s[a:b].replace('.rst_n(rst_n)',f'.rst_n({reset_expr})')+s[b:]
s,record=partition(s,'qfd_dv_redstn2',reset='rst_n')
if BOUNDED:
 s=s.replace('endmodule','wire[34:0] math_reset;\nqfd_dv_reset_tree #(.N(35)) u_math_reset(.ck(ck),.rst_n(rst_n),.q(math_reset));\nendmodule',1)
 record['parallel_math_reset_leaves']=35

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
body=body.replace('CFG_LOCAL[z]','cfg_final[z]').replace('CFG_LOCAL[2*z]','cfg_final[2*z]')
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
(* keep_hierarchy="yes" *) module qfd_dv_station_cfgbit #(parameter integer ID=0)(input wire ck,rst_n,cfg_v,d,output reg q);
always @(posedge ck or negedge rst_n) if(!rst_n)q<=0;else if(cfg_v)q<=d;
endmodule
(* keep_hierarchy="yes" *) module qfd_dv_station_mode #(parameter integer ID=0,USE2=1)(input wire ck,rst_n,cfg_v,input wire[1:0] mode,output wire[3:0] q);
reg[2:0] used_q;
always @(posedge ck or negedge rst_n) if(!rst_n) used_q<=3'b001;else if(cfg_v) used_q<={mode==3,mode==1,mode==0};
assign {q[3],q[1],q[0]}=used_q;
generate if(USE2) begin:g_two
reg m2;always @(posedge ck or negedge rst_n) if(!rst_n)m2<=0;else if(cfg_v)m2<=mode==2;assign q[2]=m2;
end else begin:g_no_two assign q[2]=1'b0;end endgenerate
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
if BOUNDED:
 s=s.replace('qfd_dv_station_add_lat #','qfd_dv_station_add_bounded #').replace('ot_hdc_fp32_mul_lat #','qfd_dv_station_mul_bounded #')
 s=s.replace('qfd_dv_station_add_bounded #(.LAT(ADD_LAT), .DRST(0)) u_hi','qfd_dv_station_add_bounded #(.LAT(ADD_LAT), .DRST(0),.REPS(0)) u_hi')
 a=s.index('begin : g_l9');b=s.index('end endgenerate',a)
 s=s[:a]+s[a:b].replace('qfd_dv_station_add_bounded #(.LAT(ADD_LAT), .DRST(0))','qfd_dv_station_add_bounded #(.LAT(ADD_LAT), .DRST(0),.REPS(0))')+s[b:]
 s=s.replace('qfd_dv_station_add_bounded #(.LAT(ADD_LAT), .DRST(0)', 'qfd_dv_station_add_bounded #(.LAT(ADD_LAT), .DRST(0),.CV(l==0)')
 s=s.replace('qfd_dv_station_mul_bounded #(.LAT(SCALE_LAT), .DRST(SCALE_DRST))','qfd_dv_station_mul_bounded #(.LAT(SCALE_LAT), .DRST(SCALE_DRST),.CV(l==0))')
 x=''
 for kind,lat,rep in [('add',7,True),('mul',6,False)]:
  ports='input wire clk,rst_n,valid_in,input wire[31:0] a,b,output wire[31:0] y,output wire[1:0] err,output wire valid_out'+(',output wire[1:0] valid_rep' if rep else '')
  x+=f'module qfd_dv_station_{kind}_bounded #(parameter integer LAT={lat},DRST=0,CV=1'+(',REPS=1' if rep else '')+f')({ports});\n'
  x+=f'generate if(LAT=={lat} && DRST==0) begin:g_exact\n'
  if rep:x+='if(REPS) begin:g_rep if(CV) begin:g_v qfd_dv_station_add_g u_g(.*);end else begin:g_nv qfd_dv_station_add_nov_g u_g(.clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.y(y),.err(err),.valid_rep(valid_rep));assign valid_out=0;end end else begin:g_base if(CV) begin:g_v qfd_dv_station_add_base_g u_g(.clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.y(y),.err(err),.valid_out(valid_out));end else begin:g_nv qfd_dv_station_add_base_nov_g u_g(.clk(clk),.a(a),.b(b),.y(y),.err(err));assign valid_out=0;end assign valid_rep=0;end\n'
  else:x+='if(CV) begin:g_v qfd_dv_station_mul_g u_g(.*);end else begin:g_nv qfd_dv_station_mul_nov_g u_g(.clk(clk),.a(a),.b(b),.y(y),.err(err));assign valid_out=0;end\n'
  x+='end else begin:g_bad\nqfd_station_math_requires_fixed_ADD7_SCALE6_DRST0 u_fail();\nend endgenerate\nendmodule\n'
filename='qfd_dv_redstn2_gsafe.sv' if BOUNDED else 'qfd_dv_redstn2_csafe.sv'
(ROOT/'rtl/qwen_dv'/filename).write_text('// GENERATED by tools/qwen_dv/gen_station_csafe.py\n'+s+'\n'+x+'\n')
record.update(configuration_added_edges=2,configuration_ii=1,steady_data_added_edges=0,cfg_valid_copies=count+mid,native_fanout_qualification='PENDING')
if BOUNDED:record.update(arithmetic_specialization={'ADD_LAT':7,'SCALE_LAT':6,'DRST':0,'invalid_shape':'elaboration trap'},math_source='rtl/qwen_dv/qfd_dv_station_math_g.sv',native_fanout_qualification='PENDING exact equivalence and native recursive census')
(ROOT/'results/arch/safe_qw_slice_1019'/('station_bound_control_model.json' if BOUNDED else 'station_control_model.json')).write_text(json.dumps(record,indent=2)+'\n')
print('STATION_CSAFE',count,'CFG leaves, data+0 CFG+2; native census PENDING')
