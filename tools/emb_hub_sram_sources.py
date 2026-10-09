#!/usr/bin/env python3
"""Emit additive SRAM payload ingress; originals remain byte-identical."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'rtl/qwen_sys/emb_hbm_20261008'

INGRESS=r'''`timescale 1ns/1ps
// Model eb10d5073/a6b27da1a, Claude F5 approval. SRAM payload ECC only.
// Full128 logical reservations include capture/encode/SRAM/read pending.
// Release only at actual async acceptance; UE fails closed until reset.
module ot_qfd_hub_sram_ingress #(parameter integer MUT_EARLY_CREDIT=0)(
 input wire clk,rst_n,i_v,input wire [522:0] i_d,
 output wire i_cr,fault,output wire [31:0] ce_count,
 output wire af_valid,output wire [522:0] af_data,input wire af_ready
);
@@ECC@@
 reg iv_q,ev_q;reg [522:0] id_q;
 reg [6:0] wa_q,ea_q,wp;
 reg [647:0] enc_q;
 reg [7:0] committed,issued;
 reg [8:0] occupied;
 reg [1:0] pending;
 reg head,tail,rv_q,slot_q;
 reg [1:0] decoded_valid;
 reg [647:0] code0,code1;
 reg [71:0] syn0,syn1;
 reg sticky,credit_q;
 reg [31:0] corrected_count;
 wire [647:0] raw;
 wire [575:0] padded={53'b0,id_q};
 wire [647:0] enc;
 wire [71:0] raw_syn;
 wire [647:0] selected_code=head?code1:code0;
 wire [71:0] selected_syn=head?syn1:syn0;
 wire [575:0] corrected;
 wire [8:0] ce,ue;
 genvar n;
 generate for(n=0;n<9;n=n+1)begin:g_ecc
  assign enc[n*72+:72]=enc64(padded[n*64+:64]);
  assign raw_syn[n*8+:8]=syn64(raw[n*72+:72]);
  wire [65:0] result=cor64(selected_code[n*72+:72],selected_syn[n*8+:8]);
  assign corrected[n*64+:64]=result[63:0];
  assign ce[n]=result[64];assign ue[n]=result[65];
 end endgenerate
 wire head_valid=decoded_valid[head];
 wire uncorrectable=head_valid && (|ue);
 assign af_valid=head_valid && !sticky && !uncorrectable;
 assign af_data=corrected[522:0];
 wire retire=af_valid && af_ready;
 wire accept=i_v && !sticky && (occupied<128 || retire);
 wire read_issue=!sticky && committed!=issued && (pending<2 || retire);
 assign i_cr=credit_q;
 assign fault=sticky;
 assign ce_count=corrected_count;
 generate for(n=0;n<3;n=n+1)begin:g_bank
  wire [255:0] wd=n<2 ? enc_q[n*256+:256] : {120'b0,enc_q[512+:136]};
  wire [255:0] rd;
  ot_sram_1r1w_128x256_m1_r2c2 u_mem(
   .clk(clk),.r_ce_in(read_issue),.r_addr_in(issued[6:0]),.rd_out(rd),
   .w_ce_in(ev_q&&!sticky),.w_addr_in(ea_q),.wd_in(wd),.w_mask_in(256'hffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  if(n<2)begin:full assign raw[n*256+:256]=rd;end
  else begin:last assign raw[512+:136]=rd[135:0];end
 end endgenerate
 // Payload state is not reset. Valid/pointers alone flush stale data.
 always @(posedge clk)begin
  id_q<=i_d;wa_q<=wp;
  enc_q<=enc;ea_q<=wa_q;
  if(rv_q)begin
   if(slot_q)begin code1<=raw;syn1<=raw_syn;end
   else begin code0<=raw;syn0<=raw_syn;end
  end
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin
   iv_q<=0;ev_q<=0;wp<=0;committed<=0;issued<=0;occupied<=0;
   pending<=0;head<=0;tail<=0;rv_q<=0;slot_q<=0;
   decoded_valid<=0;sticky<=0;credit_q<=0;corrected_count<=0;
  end else begin
   iv_q<=accept;ev_q<=iv_q && !sticky;
   if(accept)wp<=wp+1'b1;
   if(ev_q&&!sticky)committed<=committed+1'b1;
   occupied<=occupied+accept-retire;
   pending<=pending+read_issue-retire;
   rv_q<=read_issue;slot_q<=tail;
   if(read_issue)begin issued<=issued+1'b1;tail<=~tail;end
   if(retire)begin head<=~head;decoded_valid[head]<=0;end
   if(rv_q)decoded_valid[slot_q]<=1;
   credit_q<=MUT_EARLY_CREDIT!=0 ? read_issue : retire;
   if(retire && |ce)corrected_count<=corrected_count+1'b1;
   sticky<=sticky || uncorrectable || (i_v&&!accept) || occupied>128 || pending>2;
  end
endmodule
'''

def main():
 pkg=(DIR/'ot_qfd_emb_pkg.sv').read_text()
 start=pkg.index('  function automatic [71:0] enc64')
 end=pkg.index('  // ---- boot checksum',start)
 ecc=pkg[start:end]
 (DIR/'ot_qfd_hub_sram_ingress.sv').write_text(INGRESS.replace('@@ECC@@',ecc))
 # Original unchanged CDC body, replacing the synchronous ingress only.
 cdc=(ROOT/'rtl/physical/ot_qwen_die_cdc_ch.sv').read_text()
 cdc=cdc.replace('module ot_qwen_die_cdc_ch #(', 'module ot_qwen_die_cdc_ch_sram #(\n    parameter integer SRAM = 0,')
 begin=cdc.index('    reg         iv_q;')
 end=cdc.index('    // ---- crossing',begin)
 original=cdc[begin:end]
 original=original.replace('ib[ir[IA-1:0]]','ingress_data')
 # Keep baseline local memory data expression in its default branch.
 original += '\n    assign ingress_data = ib[ir[IA-1:0]];\n'
 replacement='''    wire af_ready, pop;wire [W-1:0] ingress_data;
    generate if(SRAM!=0)begin:g_sram_ingress
      initial if(W!=523 || IBUF!=128 || PIPE!=0 || AFW!=0)
        $error("SRAM ingress qualified only W523/IBUF128/PIPE0/AFW0");
      ot_qfd_hub_sram_ingress u_ingress(.clk(wclk),.rst_n(wr_n),.i_v(i_v),.i_d(i_d),
        .i_cr(i_cr),.fault(w_fault),.ce_count(),.af_valid(pop),.af_data(ingress_data),.af_ready(af_ready));
    end else begin:g_original_ingress
'''
 # Avoid duplicate declarations now outside conditional.
 original=original.replace('    wire        af_ready;\n','')
 original=original.replace('    wire        pop = !ib_empty && af_ready;','    assign pop = !ib_empty && af_ready;')
 cdc=cdc[:begin]+replacement+original+'    end endgenerate\n'+cdc[end:]
 cdc=cdc.replace('.wr_data(ib[ir[IA-1:0]])','.wr_data(ingress_data)')
 (DIR/'ot_qwen_die_cdc_ch_sram.sv').write_text(cdc)
 hub=(DIR/'synth/ot_qwen_die_hub_emb.sv').read_text()
 hub=hub.replace('ot_qwen_die_hub_emb','ot_qwen_die_hub_emb_sram')
 hub=hub.replace('parameter integer MUT = 0','parameter integer INGRESS_SRAM = 0, parameter integer MUT = 0')
 hub=hub.replace('ot_qwen_die_cdc_ch #(.W(523)', 'ot_qwen_die_cdc_ch_sram #(.SRAM(INGRESS_SRAM), .W(523)')
 hub=hub.replace('.RQD(RQD), .MUT(MUT)) u (','.RQD(RQD), .INGRESS_SRAM(INGRESS_SRAM), .MUT(MUT)) u (')
 (DIR/'ot_qwen_die_hub_emb_sram.sv').write_text('// Generated additive successor by tools/emb_hub_sram_sources.py; originals untouched.\n'+hub)

if __name__=='__main__':main()
