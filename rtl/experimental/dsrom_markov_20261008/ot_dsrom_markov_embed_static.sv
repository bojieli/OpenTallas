`timescale 1ns/1ps
`default_nettype none
// Real full129280x256 BF16 table. One source request captures token/identity;
// sixteen requests occupy consecutive fixed cycles. Registered responses are
// six cycles after each bank-request pin launch. No queue, ready or credits.
module ot_dsrom_markov_embed_static_port #(parameter integer ID_W=60)(
 input wire clk,rst_n,request_slot,input wire[16:0]token,input wire[ID_W-1:0]identity,
 input wire[15:0]clk_group,
 output reg[252:0]bank_re,output reg[207:0]bank_addr,
 input wire[64767:0]bank_q,input wire[252:0]bank_valid,bank_fault,
 output reg word_v,output reg[255:0]word_data,output reg[3:0]word_beat,
 output reg[16:0]word_token,output reg[ID_W-1:0]word_identity,output reg fault
);
 reg issuing;reg[3:0]next_beat;reg[16:0]held_token;reg[ID_W-1:0]held_id;
 wire issue=request_slot||issuing;
 wire[16:0]issue_token=request_slot?token:held_token;
 wire[3:0]issue_beat=request_slot?4'd0:next_beat;
 wire[ID_W-1:0]issue_id=request_slot?identity:held_id;
 wire[20:0]address={issue_token,issue_beat};wire[7:0]selected_bank=address[20:13];
 reg[5:0]v;reg[7:0]bank_pipe[0:5];reg[3:0]beat_pipe[0:5];
 reg[16:0]token_pipe[0:5];reg[ID_W-1:0]id_pipe[0:5];
 reg[255:0]group_q[0:15];reg[255:0]final_q;
 integer i,g;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   issuing<=0;next_beat<=0;held_token<=0;held_id<=0;bank_re<=0;bank_addr<=0;
   word_v<=0;word_data<=0;word_beat<=0;word_token<=0;word_identity<=0;fault<=0;v<=0;
   for(i=0;i<6;i=i+1)begin bank_pipe[i]<=0;beat_pipe[i]<=0;token_pipe[i]<=0;id_pipe[i]<=0;end
  end else begin
   bank_re<=0;word_v<=v[5];word_data<=final_q;
   word_beat<=beat_pipe[5];word_token<=token_pipe[5];word_identity<=id_pipe[5];
   if(|bank_fault)fault<=1;
   if(request_slot)begin
    if(issuing||(|v)||token>=129280)fault<=1;
    held_token<=token;held_id<=identity;issuing<=1;next_beat<=1;
   end else if(issuing)begin
    if(next_beat==15)issuing<=0;else next_beat<=next_beat+1'b1;
   end
   if(issue)begin
    // Illegal token requests retain their fixed response slots and fault;
    // they cannot index beyond the actual253 physical pair outputs.
    if(selected_bank<253)bank_re[selected_bank]<=1;
    else fault<=1;
    for(g=0;g<16;g=g+1)bank_addr[g*13+:13]<=address[12:0];
   end
   v<={v[4:0],issue};bank_pipe[0]<=selected_bank;beat_pipe[0]<=issue_beat;
   token_pipe[0]<=issue_token;id_pipe[0]<=issue_id;
   for(i=1;i<6;i=i+1)begin bank_pipe[i]<=bank_pipe[i-1];beat_pipe[i]<=beat_pipe[i-1];token_pipe[i]<=token_pipe[i-1];id_pipe[i]<=id_pipe[i-1];end
   // Pair capture is sampled by the group mux one edge later. Missing pair
   // output is an integrity failure; the output-valid schedule is unchanged.
   if(v[3]&&(bank_pipe[3]>=253||!bank_valid[bank_pipe[3]]))fault<=1;
  end
 end
 genvar gg;
 generate for(gg=0;gg<16;gg=gg+1)begin:g_mux
  integer b;
  always @(posedge clk_group[gg])begin
   group_q[gg]<=0;
   for(b=0;b<16;b=b+1)if(gg*16+b<253&&bank_pipe[3][3:0]==b)group_q[gg]<=bank_q[(gg*16+b)*256+:256];
  end
 end endgenerate
 always @(posedge clk)final_q<=group_q[bank_pipe[4][7:4]];
endmodule

module ot_dsrom_markov_embed_static_pair #(parameter integer BANK=0)(
 input wire clk,rst_n,re,input wire[12:0]addr,
 output reg[255:0]captured_data,output reg captured_valid,output reg fault
);
 wire[273:0]q0,q1;reg select_read,select_capture;reg[1:0]read_pipe;
 reg previous_re,previous_parity;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin select_read<=0;select_capture<=0;read_pipe<=0;captured_valid<=0;previous_re<=0;previous_parity<=0;fault<=0;end
  else begin
   if(re)select_read<=addr[0];select_capture<=select_read;
   if(re&&previous_re&&addr[0]==previous_parity)fault<=1;
   previous_re<=re;if(re)previous_parity<=addr[0];
   read_pipe<={read_pipe[0],re};captured_valid<=read_pipe[1];
  end
 end
 always @(posedge clk)captured_data<=select_capture?q1[255:0]:q0[255:0];
`ifdef SYNTHESIS
 ot_rom_4096x274_m8 m0(.clk(clk),.ce_in(re&&!addr[0]),.addr_in(addr[12:1]),.rd_out(q0));
 ot_rom_4096x274_m8 m1(.clk(clk),.ce_in(re&&addr[0]),.addr_in(addr[12:1]),.rd_out(q1));
`else
 ot_rom_4096x274_m8 #(.INSTANCE($sformatf("macro%03d",2*BANK)))m0(.clk(clk),.ce_in(re&&!addr[0]),.addr_in(addr[12:1]),.rd_out(q0));
 ot_rom_4096x274_m8 #(.INSTANCE($sformatf("macro%03d",2*BANK+1)))m1(.clk(clk),.ce_in(re&&addr[0]),.addr_in(addr[12:1]),.rd_out(q1));
`endif
endmodule

// Every bank is a real paired mask-ROM master. 253pairs =506macros, with
// explicit physical pair/group clocks. Same-clock benches are functional only.
module ot_dsrom_markov_embed_static #(parameter integer ID_W=60)(
 input wire clk,rst_n,input wire[252:0]clk_pair,input wire[15:0]clk_group,
 input wire request_slot,input wire[16:0]token,input wire[ID_W-1:0]identity,
 output wire word_v,output wire[255:0]word_data,output wire[3:0]word_beat,
 output wire[16:0]word_token,output wire[ID_W-1:0]word_identity,output wire fault
);
 wire[252:0]re,pair_valid,pair_fault;wire[207:0]addr;wire[64767:0]q;
 ot_dsrom_markov_embed_static_port #(.ID_W(ID_W))u_port(
 .clk(clk),.rst_n(rst_n),.request_slot(request_slot),.token(token),.identity(identity),.clk_group(clk_group),
 .bank_re(re),.bank_addr(addr),.bank_q(q),.bank_valid(pair_valid),.bank_fault(pair_fault),
 .word_v(word_v),.word_data(word_data),.word_beat(word_beat),.word_token(word_token),.word_identity(word_identity),.fault(fault));
 generate for(genvar b=0;b<253;b=b+1)begin:banks
  ot_dsrom_markov_embed_static_pair #(.BANK(b))u_pair(.clk(clk_pair[b]),.rst_n(rst_n),.re(re[b]),.addr(addr[(b/16)*13+:13]),
   .captured_data(q[b*256+:256]),.captured_valid(pair_valid[b]),.fault(pair_fault[b]));
 end endgenerate
endmodule
`default_nettype wire
