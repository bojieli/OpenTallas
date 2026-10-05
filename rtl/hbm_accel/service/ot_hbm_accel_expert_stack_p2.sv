`timescale 1ps/1fs
// Additive real caller/codec/receiver context for the P2 fetch. The legacy
// tagged256 stack is unchanged. Static layout is loaded once per cold reset;
// the enclosing owner must drain and reset before updating it. Ordered PHY
// returns carry the ordinal of the actual column command, not a made-up tag.
// This component owns payload capture, not the enclosing RF/task lease.
module ot_hbm_accel_expert_stack_p2 #(
 parameter ENABLE=0, REF_MODE=1, PHASE=0
)(
 input wire stream_clk,service_clk,por_n,
 input wire cfg_v,output wire cfg_r,input wire[127:0] cfg_lines,
 input wire[6271:0] cfg_lut,
 input wire e_valid,output wire e_ready,input wire[8:0] e_id,
 input wire notice,
 output wire[31:0] row_v,col_v,output wire[95:0] row_op,
 output wire[159:0] row_bank,col_bank,col_col,output wire[607:0] row_row,
 output wire[511:0] col_ordinal,
 input wire[31:0] rsp_v,input wire[8191:0] rsp_data,input wire[511:0] rsp_ordinal,
 output wire[7:0] s_valid,input wire[7:0] s_ready,output wire[8191:0] s_data,
 output wire fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:off
  assign cfg_r=0;assign e_ready=0;assign row_v=0;assign col_v=0;
  assign row_op=0;assign row_bank=0;assign col_bank=0;assign col_col=0;
  assign row_row=0;assign col_ordinal=0;assign s_valid=0;assign s_data=0;assign fault=0;
 end else begin:on
  (* keep=1 *) reg configured,configured_n,cbad,cbad_n;
  (* keep=1 *) reg[71:0] layout[0:99];
  wire[6399:0] layout_raw={cfg_lut,cfg_lines};
  wire[6399:0] layout_held;wire[99:0] layout_ue;
  for(genvar w=0;w<100;w++)begin:config_decode
   wire[65:0] d=decode64(layout[w]);
   assign layout_held[w*64+:64]=d[63:0];assign layout_ue[w]=d[65];
  end
  // Hold the real child in reset until the held layout has reached its local
  // captures. Release is independently synchronised in each real clock domain.
  (* async_reg="true",keep=1 *) reg cr1,cr1_n,cr2,cr2_n,hr1,hr1_n,hr2,hr2_n;
  always @(posedge stream_clk or negedge por_n)
   if(!por_n)begin cr1<=0;cr1_n<=1;cr2<=0;cr2_n<=1;end
   else begin cr1<=configured;cr1_n<=configured_n;cr2<=cr1;cr2_n<=cr1_n;end
  always @(posedge service_clk or negedge por_n)
   if(!por_n)begin hr1<=0;hr1_n<=1;hr2<=0;hr2_n<=1;end
   else begin hr1<=configured;hr1_n<=configured_n;hr2<=hr1;hr2_n<=hr1_n;end
  wire creset_n=por_n&&cr2&&(cr2==~cr2_n);
  wire hreset_n=por_n&&hr2&&(hr2==~hr2_n);
  wire cfg_bad=(configured!=~configured_n)||(cr1!=~cr1_n)||(cr2!=~cr2_n)||(configured&&(|layout_ue));
  wire[7:0] endpoint_bad;
  wire leaf_fault;wire core_bad=cbad||(cbad!=~cbad_n)||cfg_bad||(|endpoint_bad)||leaf_fault||hbad2||(hbad2!=~hbad2_n);
  assign fault=core_bad;
  assign cfg_r=!configured&&!core_bad;
  always @(posedge stream_clk or negedge por_n)
   if(!por_n)begin configured<=0;configured_n<=1;cbad<=0;cbad_n<=1;
    for(integer w=0;w<100;w++)layout[w]<=0;end
   else begin
    if(cfg_v&&cfg_r)begin configured<=1;configured_n<=0;
     for(integer w=0;w<100;w++)layout[w]<=encode64(layout_raw[w*64+:64]);end
    if(core_bad)begin cbad<=1;cbad_n<=0;end
   end
  // Actual router caller register: one elastic coded expert descriptor.
  (* keep=1 *) reg ev,ev_n;(* keep=1 *) reg[71:0] expert_word;
  wire er;wire ev_bad=ev!=~ev_n;
  assign e_ready=creset_n&&!core_bad&&!ev_bad&&(!ev||er);
  always @(posedge stream_clk or negedge por_n)
   if(!por_n)begin ev<=0;ev_n<=1;expert_word<=0;end
   else if(!core_bad&&!ev_bad&&(!ev||er))begin
    ev<=e_valid&&e_ready;ev_n<=~(e_valid&&e_ready);
    if(e_valid&&e_ready)expert_word<=encode64({55'd0,e_id});
   end
  // The static schedule notice has a real CK/2 source capture, with a held rail.
  (* keep=1 *) reg notice_q,notice_n;
  always @(posedge service_clk or negedge por_n)
   if(!por_n)begin notice_q<=0;notice_n<=1;end
   else begin notice_q<=notice;notice_n<=~notice;end
  wire[31:0] pc_bad;wire hbad=(hr1!=~hr1_n)||(hr2!=~hr2_n)||(|pc_bad)||(notice_q!=~notice_n)||cbad2||(cbad2!=~cbad2_n);
  (* async_reg="true",keep=1 *) reg hbad1,hbad1_n,hbad2,hbad2_n,cbad1,cbad1_n,cbad2,cbad2_n;
  always @(posedge stream_clk or negedge por_n)
   if(!por_n)begin hbad1<=0;hbad1_n<=1;hbad2<=0;hbad2_n<=1;end
   else begin hbad1<=hbad;hbad1_n<=~hbad;hbad2<=hbad1;hbad2_n<=hbad1_n;end
  always @(posedge service_clk or negedge por_n)
   if(!por_n)begin cbad1<=0;cbad1_n<=1;cbad2<=0;cbad2_n<=1;end
   else begin cbad1<=cbad||ev_bad;cbad1_n<=~(cbad||ev_bad);cbad2<=cbad1;cbad2_n<=cbad1_n;end
  // Real ordered-return consumer. Each ordinal is issued with a column command.
  // At most32 commands may remain outstanding per PC. Encode the received raw
  // data AND its checked transaction identity into a registered360b code slot.
  wire[31:0] cv,rv;wire[11519:0] returned_codes;
  for(genvar p=0;p<32;p++)begin:phy
   (* keep=1 *) reg[15:0] issued,issued_n,returned,returned_n;
   (* keep=1 *) reg poison,poison_n,v,v_n;(* keep=1 *) reg[359:0] code;
   wire[15:0] debt=issued-returned;
   wire state_bad=(issued!=~issued_n)||(returned!=~returned_n)||(poison!=~poison_n)||(v!=~v_n);
   wire response_bad=rsp_v[p]&&(debt==0||debt>32||rsp_ordinal[p*16+:16]!=returned);
   wire issue_bad=cv[p]&&(debt>=32&&!rsp_v[p]);
   assign pc_bad[p]=poison||state_bad||response_bad||issue_bad;
   assign col_ordinal[p*16+:16]=issued;
   assign rv[p]=v&&!pc_bad[p]&&!hbad;
   assign returned_codes[p*360+:360]=code;
   always @(posedge service_clk or negedge por_n)
    if(!por_n)begin issued<=0;issued_n<='1;returned<=0;returned_n<='1;poison<=0;poison_n<=1;v<=0;v_n<=1;code<=0;end
    else begin
     v<=rsp_v[p]&&!pc_bad[p]&&!hbad;v_n<=~(rsp_v[p]&&!pc_bad[p]&&!hbad);
     if(cv[p]&&!hbad)begin issued<=issued+1'b1;issued_n<=~(issued+1'b1);end
     if(rsp_v[p]&&!pc_bad[p]&&!hbad)begin
      returned<=returned+1'b1;returned_n<=~(returned+1'b1);
      for(integer k=0;k<4;k++)code[k*72+:72]<=encode64(rsp_data[p*256+k*64+:64]);
      code[288+:72]<=encode64({43'd0,5'(p),rsp_ordinal[p*16+:16]});
     end
     if(pc_bad[p]||hbad)begin poison<=1;poison_n<=0;end
    end
  end
  wire[7:0] fv,fr;wire[8191:0] fd;
  ot_hbm_accel_expert_fetch_p2 #(.ENABLE(1),.REF_MODE(REF_MODE),.PHASE(PHASE)) fetch(
   .clk(stream_clk),.hclk(service_clk),.rst_n(creset_n),.hrst_n(hreset_n),
   .cfg_lines(layout_held[127:0]),.cfg_lut(layout_held[6399:128]),
   .e_valid(ev&&!core_bad&&!ev_bad),.e_code(expert_word),.e_ready(er),.notice(notice_q&&!hbad),
   .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
   .col_v(cv),.col_bank(col_bank),.col_col(col_col),.rd_v(rv),.rd_code(returned_codes),
   .s_valid(fv),.s_ready(fr),.s_data(fd),.fault(leaf_fault));
  assign col_v=cv&{32{!hbad}};
  // Source-owned SM landing/capture. Two finite elastic slots, both on the real
  // 833.333ps stream clock. W6 single-bit correction terminates in1024b payload
  // registers; per64b parity and valid rails protect those held endpoint flops.
  for(genvar m=0;m<8;m++)begin:sm
   (* keep=1 *) reg v0,v0_n,v1,v1_n,poison,poison_n;
   (* keep=1 *) reg[1151:0] coded;
   (* keep=1 *) reg[1023:0] captured;(* keep=1 *) reg[15:0] parity;
   wire[1023:0] corrected;wire[15:0] ue,par_bad;
   for(genvar k=0;k<16;k++)begin:word
    wire[65:0] d=decode64(coded[k*72+:72]);
    assign corrected[k*64+:64]=d[63:0];assign ue[k]=d[65];
    assign par_bad[k]=parity[k]!=(^captured[k*64+:64]);
   end
   wire bad=(v0!=~v0_n)||(v1!=~v1_n)||(poison!=~poison_n)||(v0&&(|ue))||(v1&&(|par_bad));
   wire take1=!v1||s_ready[m];wire take0=!v0||take1;
   assign endpoint_bad[m]=bad||poison;
   assign fr[m]=take0&&!core_bad;
   assign s_valid[m]=v1&&!core_bad;assign s_data[m*1024+:1024]=captured;
   always @(posedge stream_clk or negedge por_n)
    if(!por_n)begin v0<=0;v0_n<=1;v1<=0;v1_n<=1;poison<=0;poison_n<=1;coded<=0;captured<=0;parity<=0;end
    else begin
     if(bad)begin poison<=1;poison_n<=0;end
     if(!core_bad)begin
      if(take1)begin v1<=v0;v1_n<=~v0;
       if(v0)begin captured<=corrected;for(integer k=0;k<16;k++)parity[k]<=^corrected[k*64+:64];end
      end
      if(take0)begin v0<=fv[m];v0_n<=~fv[m];
       if(fv[m])for(integer k=0;k<16;k++)coded[k*72+:72]<=encode64(fd[m*1024+k*64+:64]);
      end
     end
    end
  end
 end endgenerate
endmodule
