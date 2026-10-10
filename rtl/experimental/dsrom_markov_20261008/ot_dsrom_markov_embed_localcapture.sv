// Z7 opt-in successor. Direct macro-pin captures; post-capture selection.
// Same two-edge qualified capture and six-stage finite lookup as PP history.
// Fault-free ROM, no ECC/parity and no transaction identity beyond token index.
module ot_dsrom_markov_embed_localcapture_pair #(
 parameter bit ENABLE=0,parameter integer BANK=0
)(input wire clk,rst_n,input wire re,input wire[12:0] addr,
 output wire[255:0] captured_data,output reg captured_valid,output reg fault);
 wire[273:0] q0,q1;
 (* keep = 1, dont_touch = "true" *) reg[255:0] cap0,cap1;
 reg select_read,select_capture,select_output;reg[1:0] read_pipe;
 reg previous_re,previous_parity;
 wire collision=previous_re&&addr[0]==previous_parity;
 wire accepted=ENABLE&&re&&!fault&&!collision;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  select_read<=0;select_capture<=0;select_output<=0;read_pipe<=0;
  captured_valid<=0;previous_re<=0;previous_parity<=0;fault<=0;
 end else begin
  if(accepted)select_read<=addr[0];
  select_capture<=select_read;select_output<=select_capture;
  previous_re<=accepted;if(accepted)previous_parity<=addr[0];
  if(ENABLE&&re&&!fault&&collision)fault<=1;
  read_pipe<={read_pipe[0],accepted};captured_valid<=read_pipe[1]&&!fault;
 end
 // No logic between either real macro q pin and its local capture D pin.
 // Both banks capture continuously. Only the bank with two elapsed read
 // edges is selected for a qualified result; an early inactive capture is
 // never consumed. The added phase FF preserves the old valid/data edge.
 always @(posedge clk)begin cap0<=q0[255:0];cap1<=q1[255:0];end
 assign captured_data=select_output?cap1:cap0;
`ifdef SYNTHESIS
 ot_rom_4096x274_m8 m0(.clk(clk),.ce_in(accepted&&!addr[0]),.addr_in(addr[12:1]),.rd_out(q0));
 ot_rom_4096x274_m8 m1(.clk(clk),.ce_in(accepted&&addr[0]),.addr_in(addr[12:1]),.rd_out(q1));
`else
 ot_rom_4096x274_m8 #(.INSTANCE($sformatf("macro%03d",2*BANK))) m0(.clk(clk),.ce_in(accepted&&!addr[0]),.addr_in(addr[12:1]),.rd_out(q0));
 ot_rom_4096x274_m8 #(.INSTANCE($sformatf("macro%03d",2*BANK+1))) m1(.clk(clk),.ce_in(accepted&&addr[0]),.addr_in(addr[12:1]),.rd_out(q1));
`endif
endmodule

module ot_dsrom_markov_embed_localcapture_port #(
 parameter bit ENABLE=0
)(input wire clk,rst_n,input wire req_valid,output wire req_ready,
 input wire[16:0] req_token,output reg fault_valid,output reg[16:0] fault_token,
 output reg[252:0] bank_re,output reg[16*13-1:0] bank_addr,
 input wire[253*256-1:0] bank_q,
 output wire out_valid,input wire out_ready,output wire[255:0] out_data,
 output wire[16:0] out_token,output wire[3:0] out_beat,output wire out_last);
 reg busy;reg[16:0] token;reg[4:0] next_beat;reg[3:0] reserved,count;
 reg[2:0] wp,rp;reg[255:0] fifo_data[0:7];reg[3:0] fifo_beat[0:7];
 reg[5:0] v;reg[7:0] bank_pipe[0:5];reg[3:0] beat_pipe[0:5];
 reg[255:0] group_q[0:15];reg[255:0] final_q;
 wire issue=ENABLE&&busy&&next_beat<16&&reserved<8;
 wire take=out_valid&&out_ready;
 wire[20:0] address={token,next_beat[3:0]};wire[7:0] selected_bank=address[20:13];
 assign req_ready=ENABLE&&!busy;
 assign out_valid=count!=0;assign out_data=fifo_data[rp];assign out_token=token;
 assign out_beat=fifo_beat[rp];assign out_last=out_beat==15;
 integer i,g,b;
 always @(posedge clk)begin
  if(!rst_n)begin
   busy<=0;token<=0;next_beat<=0;reserved<=0;count<=0;wp<=0;rp<=0;v<=0;
   bank_re<=0;bank_addr<=0;fault_valid<=0;fault_token<=0;
  end else begin
   fault_valid<=0;bank_re<=0;
   if(req_valid&&req_ready)begin
    if(req_token>=129280)begin fault_valid<=1;fault_token<=req_token;end
    else begin busy<=1;token<=req_token;next_beat<=0;end
   end
   if(issue)begin
    bank_re[selected_bank]<=1;
    for(g=0;g<16;g=g+1)bank_addr[g*13+:13]<=address[12:0];
    next_beat<=next_beat+1;
   end
   v<={v[4:0],issue};bank_pipe[0]<=selected_bank;beat_pipe[0]<=next_beat[3:0];
   for(i=1;i<6;i=i+1)begin bank_pipe[i]<=bank_pipe[i-1];beat_pipe[i]<=beat_pipe[i-1];end
   for(g=0;g<16;g=g+1)begin
    group_q[g]<=0;
    for(b=0;b<16;b=b+1)if(g*16+b<253&&bank_pipe[3][3:0]==b)
     group_q[g]<=bank_q[(g*16+b)*256+:256];
   end
   final_q<=group_q[bank_pipe[4][7:4]];
   if(v[5])begin fifo_data[wp]<=final_q;fifo_beat[wp]<=beat_pipe[5];wp<=wp+1;end
   if(take)begin rp<=rp+1;if(out_last)busy<=0;end
   case({issue,take})2'b10:reserved<=reserved+1;2'b01:reserved<=reserved-1;default:;endcase
   case({v[5],take})2'b10:count<=count+1;2'b01:count<=count-1;default:;endcase
  end
 end
endmodule

module ot_dsrom_markov_embed_localcapture_rom #(
 parameter bit ENABLE=0
)(input wire clk,rst_n,input wire req_valid,output wire req_ready,
 input wire[16:0] req_token,output wire fault_valid,output wire[16:0] fault_token,
 output wire out_valid,input wire out_ready,output wire[255:0] out_data,
 output wire[16:0] out_token,output wire[3:0] out_beat,output wire out_last);
 wire[252:0] bank_re,bank_fault;wire[207:0] bank_addr;
 wire[64767:0] bank_q;wire port_ready,port_valid,port_fault;wire[16:0] rejected_token;
 wire any_bank_fault=|bank_fault;
 assign req_ready=port_ready&&!any_bank_fault;assign out_valid=port_valid&&!any_bank_fault;
 assign fault_valid=port_fault||any_bank_fault;
 assign fault_token=port_fault?rejected_token:out_token;
 ot_dsrom_markov_embed_localcapture_port #(.ENABLE(ENABLE))port(
  .clk(clk),.rst_n(rst_n),.req_valid(req_valid&&!any_bank_fault),.req_ready(port_ready),
  .req_token(req_token),.fault_valid(port_fault),.fault_token(rejected_token),
  .bank_re(bank_re),.bank_addr(bank_addr),.bank_q(bank_q),.out_valid(port_valid),
  .out_ready(out_ready&&!any_bank_fault),.out_data(out_data),.out_token(out_token),
  .out_beat(out_beat),.out_last(out_last));
 genvar k;generate for(k=0;k<253;k=k+1)begin:g_bank
  wire unused_valid;
  ot_dsrom_markov_embed_localcapture_pair #(.ENABLE(ENABLE),.BANK(k))pair(
   .clk(clk),.rst_n(rst_n),.re(bank_re[k]),.addr(bank_addr[(k/16)*13+:13]),
   .captured_data(bank_q[k*256+:256]),.captured_valid(unused_valid),.fault(bank_fault[k]));
 end endgenerate
endmodule
