#!/usr/bin/env python3
from pathlib import Path
import subprocess,json,hashlib
original_path='rtl/qwen_sys/kv_bootage_20261019/qkd_kv_die_cfg_a.sv'
original=subprocess.check_output(['git','show','04b625135:'+original_path],text=True)
prior_path='rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_s32_misc.sv'
prior=subprocess.check_output(['git','show','codex/kv-ctl3-native36-1020:'+prior_path],text=True)
start=prior.index('    end else begin : g_s32',prior.index('module qkd_kv_die_cfg_s32'))+len('    end else begin : g_s32\n');end=prior.index('    end endgenerate',start);bounded=prior[start:end]
bounded=bounded.replace('qkd_kv_die_cfg_s32_fld','qkd_kv_cfg_age_field')
s=original.replace('module qkd_kv_die_cfg_a #','module qkd_kv_die_cfg_a_s32_age #',1)
old='parameter integer AGES = 1, parameter integer MUT = 0)';assert s.count(old)==1;s=s.replace(old,'parameter integer AGES = 1, parameter integer MUT = 0, parameter integer S32 = 0)',1)
s=s.replace('    reg [1:0] ps;','    (* keep *) reg [1:0] ps;',1)
a=s.index('    always @(posedge ck or negedge pr_n) begin',s.index('    integer i;'));z=s.index('    assign fused_program_capability',a);plain=s[a:z]
age=['        // PRIVATE age fields: same pin-capture data and write edge; kept <=16-bit fields.',
'        (* keep *) reg age_por0; always @(posedge ck or negedge por_n) if(!por_n) age_por0<=0;else age_por0<=1;',
'        (* keep, ot_rst_split *) reg [9:0] age_rcp;',
'        always @(posedge ck or negedge age_por0) if(!age_por0)age_rcp<=0;else age_rcp<={10{age_por0}};',
'        (* keep *) reg [9:0] seal_pub;',
'        always @(posedge ck or negedge age_rcp[9]) if(!age_rcp[9])seal_pub<=0;else if(wr&&is_seal)seal_pub<=10\'h3ff;',
'        (* keep *) wire [2:0] age_hi; (* keep *) wire [7:0] age_lo;',
'        for(genvar h=0;h<3;h=h+1)begin:g_ahi assign age_hi[h]=wr&&is_age&&g_ix[7:5]==0&&g_ix[4:3]==h;end',
'        for(genvar l=0;l<8;l=l+1)begin:g_alo assign age_lo[l]=g_ix[2:0]==l;end']
fields=[('attn_lo',16,0,'ag_attn[15:0]','d_q[15:0]'),('attn_hi',16,0,'ag_attn[31:16]','d_q[31:16]'),('pair0',8,1,'ag_pv[7:0]','d_q[7:0]'),('pair1',8,2,'ag_pv[15:8]','d_q[7:0]')]+[(f'vp{i}',16,i+3,f'ag_vp[{16*i}+:16]','d_q[15:0]') for i in range(16)]
off=0
for name,width,word,dst,data in fields:
 age+=[f'        wire en_{name};wire[{width-1}:0]q_{name};',f'        qkd_kv_cfg_age_en e_{name}(.h(age_hi[{word//8}]),.l(age_lo[{word%8}]),.y(en_{name}));',f'        qkd_kv_cfg_age_field #(.W({width})) f_{name}(.ck(ck),.rn(age_rcp[{off//32}]),.en(en_{name}),.d({data}),.q(q_{name}));',f'        always @* {dst}=q_{name};'];off+=width
assert off==304
s=s[:a]+'    generate if(S32==0)begin:g_original\n'+plain+'    end else begin:g_s32\n'+bounded+'\n'.join(age)+'\n    end endgenerate\n'+s[z:]
a=s.index('    wire ag_on =');s=s[:a]+'''    generate if(S32==0)begin:g_output_original
    wire ag_on=(MUT==7)||sealed;
    assign age_attn=ag_on?ag_attn:32'd0;assign age_pv=ag_on?ag_pv:16'd0;assign age_vport=ag_on?ag_vp:256'd0;
    end else begin:g_output_private
    wire[303:0] raw_age={ag_vp,ag_pv,ag_attn};wire[303:0] published;
    for(genvar k=0;k<304;k=k+1)begin:g_bit assign published[k]=((MUT==7)||g_s32.seal_pub[k/32])?raw_age[k]:1'b0;end
    assign {age_vport,age_pv,age_attn}=published;
    end endgenerate
endmodule
(* keep_hierarchy *) module qkd_kv_cfg_age_field #(parameter integer W=15)(input wire ck,rn,en,input wire[W-1:0]d,output reg[W-1:0]q);
 always @(posedge ck or negedge rn)if(!rn)q<={W{1'b0}};else if(en)q<=d;
endmodule
(* keep_hierarchy *) module qkd_kv_cfg_age_en(input wire h,l,output wire y);assign y=h&l;endmodule
'''
out=Path('rtl/qwen_sys/kv_bootage_20261019/qkd_kv_die_cfg_a_s32_age.sv');out.write_text('// PRIVATE PROTOTYPE; S32=0 source baseline, S32=1 distributed fields. No parent/view qualification.\n'+s)
Path('results/arch/kv_cfg_age_proto_0720/source_identity.json').write_text(json.dumps(dict(scope='PRIVATE UNQUALIFIED PROTOTYPE',original_path=original_path,original_sha256=hashlib.sha256(original.encode()).hexdigest(),bounded_source_ref='codex/kv-ctl3-native36-1020',bounded_source_path=prior_path,bounded_source_sha256=hashlib.sha256(prior.encode()).hexdigest(),prototype_sha256=hashlib.sha256(out.read_bytes()).hexdigest()),indent=2)+'\n')
