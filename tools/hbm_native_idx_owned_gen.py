#!/usr/bin/env python3
"""Distinct fixed native scoring graph; all physical clock/pin claims are unqualified."""
from pathlib import Path
import re,hashlib
BASE=Path('rtl/hdc/v41x/ot_hdc_v41x_idx_engine_hslice.sv')
CH=Path('rtl/hdc/v41x/ot_hdc_v41x_idx_chunk_el.sv')
LAT=Path('rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv')
assert hashlib.sha256(BASE.read_bytes()).hexdigest()=='2b8f96a2275df9fbe6c8747d9c1c179777d56ba6f06a60390f3da659e19b7b62'
# Distinct ready successor exposes actual local final reset state; old closed source stays byte-identical.
hs=Path('rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv').read_text()
hs=hs.replace('module ot_hdc_v41x_idx_hslice #(', 'module ot_hbm_idx_hslice_ready_native #(')
hs=hs.replace('    input  wire              rst_n,','    input  wire              rst_n, output reg online,')
hs=hs.replace('    // ---- pin flops',"    always @(posedge clk or negedge rst_n)\n      if (!rst_n) online<=1'b0; else online<=rs && rn_p;\n    // ---- pin flops")
# rn_p is the actual consumer reset sample. Declaration remains in original body.
s=CH.read_text();a=s.index(') (')+4;b=s.index(');',a);ports=s[a:b];body=s[b+2:s.rindex('endmodule')]
ports=ports.replace('input  wire                  clk,','input wire clk, input wire [31:0] clk_hslice,')
body=body.replace('ot_hdc_v41x_idx_hslice','ot_hbm_idx_hslice_ready_native')
body=body.replace('.rst_n(rr[g]), .hid(hid[h])', '.rst_n(rr[g]), .online(hrdy[8*g+h]), .hid(hid[h])')
body=body.replace('    localparam integer HC = 8;', '''    wire [31:0] hrdy; reg [31:0] rdy1,rdy2;
    always @(posedge clk or negedge rst_n)
      if(!rst_n)begin rdy1<=0;rdy2<=0;online<=0;end
      else begin rdy1<=hrdy;rdy2<=rdy1;online<=(&rdy2);end
    localparam integer HC = 8;''')
ports+=', output reg online'
body=body.replace('u_s (.clk(clk)', 'u_s (.clk(clk_hslice[8*g+h])')
chunk='(* keep_hierarchy="yes" *) module ot_hbm_idx_chunk_owned_native (\n'+ports+'\n);\n localparam integer NB=4,NKT=4,FPL=7,FML=5,QL=5;\n'+body+'endmodule\n'
s=BASE.read_text();a=s.index(') (')+4;b=s.index(');',a);ports=s[a:b];body=s[b+2:s.rindex('endmodule')]
# All engine queue/counters/keep state has one named clock owner, separately from arithmetic leaves.
p=body.index('    // chunks');q=body.index('    // output FIFO')
chunks=body[p:q]
keep='''    wire [NK-1:0] keep_d;
    ot_hdc_delay #(.W(NK), .D(LAT_C)) u_keep (.clk(clk), .rst_n(rst_n), .d(k_keep), .q(keep_d));
'''
ctrlbody=body[:p]+keep+body[q:]
ctrlbody=ctrlbody.replace('wire take = k_valid && k_ready;', 'assign take = k_valid && k_ready;').replace('    wire [NK-1:0] keep_d;','')
ctrlports=ports.replace('    input  wire [7:0]           ql_head,','').replace('    input  wire [NB*128-1:0]    ql_codes,','').replace('    input  wire [NB*8-1:0]      ql_sc,','').replace('    input  wire [15:0]          ql_w,','').replace('    input  wire [NK*NB*136-1:0] k_key,','')
ctrlports+=''', input wire [3:0] chunks_online, output reg online, input wire tv, input wire [3:0] tkv,tf, input wire [63:0] ts,
 output wire take, output wire [3:0] keep_d'''
ctrlbody=ctrlbody.replace('    wire out_free =', '''    reg [3:0] rdy1,rdy2;
    always @(posedge clk or negedge rst_n)if(!rst_n)begin rdy1<=0;rdy2<=0;online<=0;end
      else begin rdy1<=chunks_online;rdy2<=rdy1;online<=(&rdy2);end
    wire out_free =''')
ctrlbody=ctrlbody.replace('assign k_ready = rst_n &&', 'assign k_ready = rst_n && online &&')
ctrl='(* keep_hierarchy="yes" *) module ot_hbm_idx_engine_state_native (\n'+ctrlports+'\n);\n localparam integer NK=4,IH=32,NB=4,FD=128,FPL=7,FML=5,QL=5;\n'+ctrlbody+'endmodule\n'
parentports=ports.replace('    input  wire                 clk,','    input wire clk, input wire clk_tail, input wire [3:0] clk_chunk, input wire [127:0] clk_hslice,')
parentports=parentports.replace('output reg', 'output wire')+', output wire online'
# Original chunks and wiring; no retained state in parent.
chunks=chunks.replace('.c_v(cv[c])', '.online(chunks_online[c]), .c_v(cv[c])')
chunks=chunks.replace('wire [NK-1:0] keep_d;', 'wire [NK-1:0] keep_d;')
start=chunks.index('    // the mask travels');end=chunks.index('    reg [NK*NCH*32-1:0] tsum;')
chunks=chunks[:start]+chunks[end:]
start=chunks.index('    reg [NK*NCH*32-1:0] tsum;');end=chunks.index('    wire              tv;')
w='''    wire [NK*NCH*32-1:0] tsum;
    wire [NK*NCH-1:0] tfl;
    for(genvar gi=0;gi<NK;gi=gi+1)begin:g_transpose
      for(genvar ci=0;ci<NCH;ci=ci+1)begin:g_chunk
        assign tsum[(gi*NCH+ci)*32+:32]=csum[ci][32*gi+:32];
        assign tfl[gi*NCH+ci]=cfl[ci][gi];
      end
    end
'''
chunks=chunks[:start]+w+chunks[end:]
chunks=chunks.replace('ot_hdc_v41x_idx_chunk_el #(.NB(NB), .NKT(NK), .FPL(FPL), .FML(FML), .QL(QL))','ot_hbm_idx_chunk_owned_native')
chunks=chunks.replace('.clk(clk), .rst_n(rst_n), .hb', '.clk(clk_chunk[c]), .clk_hslice(clk_hslice[32*c+:32]), .rst_n(rst_n), .hb')
chunks=chunks.replace('ot_hdc_v41x_idx_tail_l #(.NCH(NCH), .NKT(NK), .FPL(FPL))','ot_hbm_idx_tail_native')
chunks=chunks.replace('u_t (.clk(clk)', 'u_t (.clk(clk_tail)')
ctrl_names=re.findall(r'\b(?:input|output)\s+(?:wire|reg)\s+(?:\[[^\]]+\]\s*)?(\w+)',ctrlports)
if 'tf' not in ctrl_names:ctrl_names.append('tf')
inst='    ot_hbm_idx_engine_state_native u_state(\n        '+',\n        '.join('.%s(%s)'%(n,n) for n in ctrl_names)+'\n    );\n'
parent='module ot_hbm_idx_engine_owned_native #(parameter integer MUT=0)(\n'+parentports+'\n);\n localparam integer NK=4,IH=32,NB=4,NCH=4,FPL=7,FML=5,QL=5;\n wire take;wire[3:0]keep_d,chunks_online;\n'+chunks+inst+'endmodule\n'
assert not re.search(r'\b(reg|always|always_ff|always_comb)\b',parent)
# Tail has one named root. Preserve its source arithmetic and all latency state.
s=LAT.read_text();a=s.index('module ot_hdc_v41x_idx_tail_l #(');b=s.index(') (',a)+4;e=s.index('endmodule',b);tailports=s[b:s.index(');',b)];tailbody=s[s.index(');',b)+2:e]
tail='(* keep_hierarchy="yes" *) module ot_hbm_idx_tail_native (\n'+tailports+'\n);\n localparam integer NCH=4,NKT=4,FPL=7;\n'+tailbody+'endmodule\n'
# Metadata belongs to one separate leaf per4-key engine, with +23 edges retained.
a=s.index('module ot_hdc_v41x_idx_score_slice_l #(');b=s.index(') (',a)+4;e=s.index('endmodule',b);sp=s[b:s.index(');',b)];sb=s[s.index(');',b)+2:e]
sp=sp.replace('input wire clk, rst_n,', 'input wire clk, rst_n, input wire clk_engine,clk_tail, input wire[3:0]clk_chunk,input wire[127:0]clk_hslice,')
sb='    wire engine_online; reg rdy1,rdy2;\n    always @(posedge clk or negedge rst_n)if(!rst_n)begin rdy1<=0;rdy2<=0;end else begin rdy1<=engine_online;rdy2<=rdy1;end\n'+sb
sb=sb.replace('assign ql_ready=(count==0)', 'assign ql_ready=rdy2 && (count==0)')
sb=sb.replace('.clk(clk),.rst_n(rst_n),.ql_v', '.clk(clk),.online(engine_online),.rst_n(rst_n),.ql_v')
sb=sb.replace('localparam integer LATE=', 'localparam integer LATE=23+')
sb=sb.replace('ot_hdc_v41x_idx_engine_l #(.NK(NK),.IH(IH),.NB(NB),.FD(MDE),.FPL(FPL),.FML(FML),.QL(QL))','ot_hbm_idx_engine_owned_native #(.MUT(MUT))')
sb=sb.replace('.clk(clk),.online(engine_online),.rst_n(rst_n),.ql_v', '.clk(clk_engine),.clk_tail(clk_tail),.clk_chunk(clk_chunk),.clk_hslice(clk_hslice),.online(engine_online),.rst_n(rst_n),.ql_v')
slice='(* keep_hierarchy="yes" *) module ot_hbm_idx_slice_owned_native #(parameter integer MUT=0)(\n'+sp+'\n);\n localparam integer NK=4,NB=4,IH=32,IW=20,MD=64,FPL=7,FML=5,QL=5,ARRAY_PHASE_GATE=1;\n'+sb+'endmodule\n'
# Full512-leaf scorer; NS16 instantiates full2048-leaf native die arithmetic.
a=s.index('module ot_hdc_v41x_idx_array_l #(');b=s.index(') (',a)+4;e=s.index('endmodule',b);ap=s[b:s.index(');',b)];ab=s[s.index(');',b)+2:e]
ap=ap.replace('input  wire                     clk,', 'input wire clk, input wire[NS-1:0]clk_engine,clk_meta,clk_tail,input wire[NS*4-1:0]clk_chunk,input wire[NS*128-1:0]clk_hslice,')
ab=ab.replace('ot_hdc_v41x_idx_score_slice_l #(.NK(NK), .NB(NB), .IH(IH), .IW(IW), .MD(MD), .FPL(FPL), .FML(FML), .QL(QL), .ARRAY_PHASE_GATE(SAFE_QUERY_GATE))','ot_hbm_idx_slice_owned_native #(.MUT(MUT))')
ab=ab.replace('.clk(clk), .rst_n(rst_n),', '.clk(clk_meta[s]), .clk_engine(clk_engine[s]),.clk_tail(clk_tail[s]),.clk_chunk(clk_chunk[4*s+:4]),.clk_hslice(clk_hslice[128*s+:128]), .rst_n(rst_n),')
array='module ot_hbm_idx_array_owned_native #(parameter integer NS=4,MUT=0)(\n'+ap+'\n);\n localparam integer NK=4,NB=4,IH=32,IW=20,MD=64,FPL=7,FML=5,QL=5,SAFE_QUERY_GATE=1;\n'+ab+'endmodule\n'
Path('rtl/hdc/v41x/ot_hbm_idx_owned_native.sv').write_text('`timescale 1ns/1ps\n// Native clock-owned functional prototype. Slots/clock delivery/parentclosure unqualified.\n'+hs+chunk+tail+ctrl+parent+slice+array)
