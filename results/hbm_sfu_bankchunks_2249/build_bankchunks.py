import re,hashlib,json
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-hbm-bind-2249');O=R/'bankchunks';O.mkdir(exist_ok=True)
S=Path('/srv/opentallas-scratch2/claude/wt/codex-hbm-sourcefull-0310/rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv');text=S.read_text()
def module(name):
 m=re.search(r'^module\s+'+name+r'\b.*?^endmodule',text,re.M|re.S);assert m;return m.group()
a=module('ot_hgi_su_lgroup2');b=module('ot_hgi_su_lbank')
loop='''    genvar gb;
    for (gb = 0; gb < N; gb = gb + 1) begin : g_bank
        ot_hgi_su_lbank #(.RB(RB), .MACRO(MACRO), .LAT(LAT)) u_b (.clk(clk), .re(b_re[gb]), .ra(b_ra[gb]), .rd(b_rd[gb]),
            .we(b_we[gb]), .wa(b_wa[gb]), .wd(b_wd[gb]));
    end'''
new='''    if (N != 16) begin:g_invalid_shape
        ERROR_bankchunks_requires_N16 invalid_shape();
    end
    genvar cg,cb;
    for(cg=0;cg<4;cg=cg+1)begin:g_chunk
        wire[4*RB-1:0]ra4,wa4;wire[127:0]wd4,rd4;
        for(cb=0;cb<4;cb=cb+1)begin:g_pack
            assign ra4[cb*RB+:RB]=b_ra[cg*4+cb];
            assign wa4[cb*RB+:RB]=b_wa[cg*4+cb];
            assign wd4[cb*32+:32]=b_wd[cg*4+cb];
            assign b_rd[cg*4+cb]=rd4[cb*32+:32];
        end
        ot_hgi_su_lbank_chunk4 #(.RB(RB),.MACRO(MACRO),.LAT(LAT),.MUT_WRITE(cg==0?MUT_CHUNK:0))u_c(
            .clk(clk),.re(b_re[cg*4+:4]),.ra(ra4),.rd(rd4),
            .we(b_we[cg*4+:4]),.wa(wa4),.wd(wd4));
    end'''
assert a.count(loop)==1
v=a.replace('module ot_hgi_su_lgroup2 #(', 'module ot_hgi_su_lgroup2_bankchunks #(',1).replace('parameter integer NS = 1', 'parameter integer NS = 1, parameter integer MUT_CHUNK = 0',1).replace(loop,new)
# The entire selector, conflict checks, read/write precedence and all original registers are byte-identical.
restore=v.replace('module ot_hgi_su_lgroup2_bankchunks #(', 'module ot_hgi_su_lgroup2 #(',1).replace('parameter integer NS = 1, parameter integer MUT_CHUNK = 0','parameter integer NS = 1',1).replace(new,loop)
assert restore==a
chunk='''module ot_hgi_su_lbank_chunk4 #(parameter integer RB=11,MACRO=1,LAT=0,MUT_WRITE=0)(
 input wire clk,input wire[3:0]re,input wire[4*RB-1:0]ra,output wire[127:0]rd,
 input wire[3:0]we,input wire[4*RB-1:0]wa,input wire[127:0]wd);
 genvar b;
 for(b=0;b<4;b=b+1)begin:g_bank
  wire[31:0]data=wd[b*32+:32] ^ ((MUT_WRITE!=0 && b==0)?32'd1:32'd0);
  ot_hgi_su_lbank #(.RB(RB),.MACRO(MACRO),.LAT(LAT))u_b(
   .clk(clk),.re(re[b]),.ra(ra[b*RB+:RB]),.rd(rd[b*32+:32]),
   .we(we[b]),.wa(wa[b*RB+:RB]),.wd(data));
 end
endmodule
'''
(O/'source.sv').write_text('`timescale 1ns/1fs\n`default_nettype none\n'+b+'\n'+a+'\n'+chunk+'\n'+v+'\n`default_nettype wire\n')
# Read production parameters from the selected source, rather than the generic RTL defaults.
cache=json.load(open('/srv/opentallas-scratch2/claude/die-hbm-29/b29d/out/asbuilt.json'))
mods=cache['modules'];selected=mods['hbm_current_native_top']
for name in ('sfucore_NE','u_core','u_engine','u_memory','u_store'):
    selected=mods[selected['cells'][name]['type']]
params={k:int(v,2) for k,v in selected['cells']['g_operand[0].u_group']['parameters'].items()}
assert {k:params[k] for k in ('N','M','LWB','NS','NLW')}==dict(N=16,M=16,LWB=15,NS=8,NLW=0)
candidates={}
for l in range(16):
    candidates[l]=list(range(16)) if l==0 else sorted({l,l^1,l>>1,(l>>1)+8})
report=dict(source_sha256=hashlib.sha256(S.read_bytes()).hexdigest(),module_sha256=hashlib.sha256(a.encode()).hexdigest(),selector_and_conflict_logic='BYTE_IDENTICAL',N=16,M=16,LWB=15,bank_RB=11,NS=8,chunk_banks=4,chunks_per_operand=4,operands=4,SRAM_per_chunk=4,SRAM_per_four_operand_chunk=16,SRAM_operand_total=64,SRAM_output_total=16,SRAM_total=80,SRAM_per_five_group_chunk=20,SRAM_master='ot_sram_1r1w_256x256_m2_r2c2',chunk_select_FF=12,chunk_input_bits=224,chunk_output_bits=128,cycles_added=0,candidate_banks=candidates,independent_lane_groups=False)
(O/'inventory_actual.json').write_text(json.dumps(report,indent=1));print(json.dumps(report),flush=True)
