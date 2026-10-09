// Opt-in PP successor. bank_q is each real pair's two-edge capture;
// 18 unused bits are not ECC. Fault-free ROM contract. No head integration claim.
module ot_dsrom_markov_embed_port_pp #(
 parameter bit ENABLE=0, parameter integer ID_W=32
)(input wire clk, rst_n,
 input wire req_valid, output wire req_ready, input wire [16:0] req_token,
 input wire [ID_W-1:0] req_id,
 output reg fault_valid, output reg [ID_W-1:0] fault_id,
 output reg [252:0] bank_re, output reg [16*13-1:0] bank_addr,
 input wire [253*256-1:0] bank_q,
 output wire out_valid,input wire out_ready,output wire [255:0] out_data,
 output wire [ID_W-1:0] out_id,output wire [3:0] out_beat,output wire out_last);
 reg busy; reg [16:0] token; reg [ID_W-1:0] identity;
 reg [4:0] next_beat; reg [3:0] reserved,count;
 reg [2:0] wp,rp;
 reg [255:0] fifo_data[0:7];reg [3:0] fifo_beat[0:7];
 reg [5:0] v;
 reg [7:0] bank_pipe[0:5];reg [3:0] beat_pipe[0:5];
 // bank_q is already captured by each hardened two-edge pair.
 reg [255:0] group_q[0:15];reg [255:0] final_q;
 wire issue=ENABLE && busy && next_beat<16 && reserved<8;
 wire take=out_valid&&out_ready;
 wire [20:0] address={token,next_beat[3:0]};
 wire [7:0] selected_bank=address[20:13];
 assign req_ready=ENABLE&&!busy;
 assign out_valid=count!=0;assign out_data=fifo_data[rp];
 assign out_beat=fifo_beat[rp];assign out_last=out_beat==15;
 assign out_id=identity;
 integer i,g,b;
 always @(posedge clk) begin
  if(!rst_n) begin
   busy<=0;token<=0;identity<=0;next_beat<=0;reserved<=0;count<=0;wp<=0;rp<=0;v<=0;
   bank_re<=0;bank_addr<=0;fault_valid<=0;fault_id<=0;
  end else begin
   fault_valid<=0; bank_re<=0;
   if(req_valid&&req_ready) begin
    if(req_token>=129280) begin fault_valid<=1;fault_id<=req_id;end
    else begin busy<=1;token<=req_token;identity<=req_id;next_beat<=0;end
   end
   if(issue) begin
    bank_re[selected_bank]<=1;
    for(g=0;g<16;g=g+1) bank_addr[g*13+:13]<=address[12:0];
    next_beat<=next_beat+1;
   end
   // Request E0, macro read E1, local two-edge capture E3, group E4,
   // final E5, finite response FIFO E6. All six stages reserve credits.
   v<={v[4:0],issue};bank_pipe[0]<=selected_bank;beat_pipe[0]<=next_beat[3:0];
   for(i=1;i<6;i=i+1) begin bank_pipe[i]<=bank_pipe[i-1];beat_pipe[i]<=beat_pipe[i-1];end
   // Payload stages run continuously; only qualified beats enter the FIFO.
   for(g=0;g<16;g=g+1) begin
    group_q[g]<=0;
    for(b=0;b<16;b=b+1) if(g*16+b<253 && bank_pipe[3][3:0]==b)
      group_q[g]<=bank_q[(g*16+b)*256+:256];
   end
   final_q<=group_q[bank_pipe[4][7:4]];
   if(v[5]) begin fifo_data[wp]<=final_q;fifo_beat[wp]<=beat_pipe[5];wp<=wp+1;end
   if(take) begin rp<=rp+1;if(out_last) busy<=0;end
   case({issue,take}) 2'b10:reserved<=reserved+1;2'b01:reserved<=reserved-1;default:;endcase
   case({v[5],take}) 2'b10:count<=count+1;2'b01:count<=count-1;default:;endcase
  end
 end
endmodule


// One physically hardenable pair. Alternate words go to alternate real macros;
// a macro output is held until the next read two edges later. The capture reads
// the prior output before the same-edge next read changes q after744ps.
module ot_dsrom_markov_embed_pp_pair #(
 parameter bit ENABLE=0,parameter integer BANK=0
)(input wire clk,rst_n,input wire re,input wire[12:0] addr,
 output reg[255:0] captured_data,output reg captured_valid,output reg fault);
 wire[273:0] q0,q1;reg select_read,select_capture;reg[1:0] read_pipe;
 reg previous_re,previous_parity;
 wire collision=previous_re&&addr[0]==previous_parity;
 wire accepted=ENABLE&&re&&!fault&&!collision;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  select_read<=0;select_capture<=0;read_pipe<=0;captured_valid<=0;previous_re<=0;previous_parity<=0;fault<=0;
 end else begin
  if(accepted)select_read<=addr[0];select_capture<=select_read;
  previous_re<=accepted;if(accepted)previous_parity<=addr[0];
  if(ENABLE&&re&&!fault&&collision)fault<=1;
  read_pipe<={read_pipe[0],accepted};captured_valid<=read_pipe[1]&&!fault;
 end
 // Continuous capture removes accepted-valid fanout to256 payload enables.
 always @(posedge clk)captured_data<=select_capture?q1[255:0]:q0[255:0];
`ifdef SYNTHESIS
 ot_rom_4096x274_m8 m0(.clk(clk),.ce_in(accepted&&!addr[0]),.addr_in(addr[12:1]),.rd_out(q0));
 ot_rom_4096x274_m8 m1(.clk(clk),.ce_in(accepted&&addr[0]),.addr_in(addr[12:1]),.rd_out(q1));
`else
 ot_rom_4096x274_m8 #(.INSTANCE($sformatf("macro%03d",2*BANK))) m0(.clk(clk),.ce_in(accepted&&!addr[0]),.addr_in(addr[12:1]),.rd_out(q0));
 ot_rom_4096x274_m8 #(.INSTANCE($sformatf("macro%03d",2*BANK+1))) m1(.clk(clk),.ce_in(accepted&&addr[0]),.addr_in(addr[12:1]),.rd_out(q1));
`endif
endmodule

module ot_dsrom_markov_embed_rom_pp #(
 parameter bit ENABLE=0,parameter integer ID_W=32
)(input wire clk,rst_n,input wire req_valid,output wire req_ready,
 input wire[16:0] req_token,input wire[ID_W-1:0] req_id,
 output wire fault_valid,output wire[ID_W-1:0] fault_id,
 output wire out_valid,input wire out_ready,output wire[255:0] out_data,
 output wire[ID_W-1:0] out_id,output wire[3:0] out_beat,output wire out_last);
 wire[252:0] bank_re,pair_fault;wire[207:0] bank_addr;wire[64767:0] bank_q;
 wire request_ready,request_fault,response_valid;wire[ID_W-1:0] request_fault_id;
 assign req_ready=request_ready&&!(|pair_fault);
 assign fault_valid=request_fault|(|pair_fault);assign fault_id=request_fault?request_fault_id:out_id;
 assign out_valid=response_valid&&!(|pair_fault);
 ot_dsrom_markov_embed_port_pp #(.ENABLE(ENABLE),.ID_W(ID_W)) port(
  .clk(clk),.rst_n(rst_n),.req_valid(req_valid&&!(|pair_fault)),.req_ready(request_ready),.req_token(req_token),.req_id(req_id),
  .fault_valid(request_fault),.fault_id(request_fault_id),.bank_re(bank_re),.bank_addr(bank_addr),.bank_q(bank_q),
  .out_valid(response_valid),.out_ready(out_ready&&!(|pair_fault)),.out_data(out_data),.out_id(out_id),.out_beat(out_beat),.out_last(out_last));
 for(genvar b=0;b<253;b=b+1)begin:banks
  ot_dsrom_markov_embed_pp_pair #(.ENABLE(ENABLE),.BANK(b)) pair(
   .clk(clk),.rst_n(rst_n),.re(bank_re[b]),.addr(bank_addr[(b/16)*13+:13]),
   .captured_data(bank_q[b*256+:256]),.captured_valid(),.fault(pair_fault[b]));
 end
endmodule
