`timescale 1ns/1ps
// Model eb10d5073/a6b27da1a, Claude F5 approval. SRAM payload ECC only.
// Full128 logical reservations include capture/encode/SRAM/read pending.
// Release only at actual async acceptance; UE fails closed until reset.
module ot_qfd_hub_sram_ingress #(parameter integer MUT_EARLY_CREDIT=0)(
 input wire clk,rst_n,i_v,input wire [522:0] i_d,
 output wire i_cr,fault,output wire [31:0] ce_count,
 output wire af_valid,output wire [522:0] af_data,input wire af_ready
);
  function automatic [71:0] enc64(input [63:0] data);
    reg [71:0] c; integer p, k, j;
    begin
      c = '0; j = 0;
      for (p = 1; p <= 71; p = p + 1)
        if ((p & (p - 1)) != 0) begin c[p-1] = data[j]; j = j + 1; end
      for (k = 0; k < 7; k = k + 1)
        for (p = 1; p <= 71; p = p + 1)
          if ((p & (1 << k)) != 0 && p != (1 << k)) c[(1<<k)-1] = c[(1<<k)-1] ^ c[p-1];
      c[71] = ^c[70:0]; enc64 = c;
    end
  endfunction
  function automatic [287:0] enc256(input [255:0] d);
    enc256 = {enc64(d[255:192]), enc64(d[191:128]), enc64(d[127:64]), enc64(d[63:0])};
  endfunction
  // decode stage A: {syndrome[6:0], overall parity}
  function automatic [7:0] syn64(input [71:0] code);
    reg [6:0] sy; integer p, k;
    begin
      sy = '0;
      for (k = 0; k < 7; k = k + 1)
        for (p = 1; p <= 71; p = p + 1)
          if ((p & (1 << k)) != 0) sy[k] = sy[k] ^ code[p-1];
      syn64 = {sy, ^code};
    end
  endfunction
  // decode stage B: {ue, corrected, data[63:0]} from the code and its stage-A syndrome
  function automatic [65:0] cor64(input [71:0] code, input [7:0] so);
    reg [71:0] c; reg [6:0] sy; reg ov, ue, ce; reg [63:0] d; integer p, j;
    begin
      c = code; sy = so[7:1]; ov = so[0]; ue = 1'b0; ce = 1'b0;
      if (sy != 0) begin
        if (ov && sy <= 71) begin c[sy-1] = ~c[sy-1]; ce = 1'b1; end
        else ue = 1'b1;
      end else if (ov) begin c[71] = ~c[71]; ce = 1'b1; end
      d = '0; j = 0;
      for (p = 1; p <= 71; p = p + 1)
        if ((p & (p - 1)) != 0) begin d[j] = c[p-1]; j = j + 1; end
      cor64 = {ue, ce, d};
    end
  endfunction


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
  wire [255:0] wd;
  if(n<2)begin:wfull assign wd=enc_q[n*256+:256];end
  else begin:wlast assign wd={120'b0,enc_q[512+:136]};end
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
