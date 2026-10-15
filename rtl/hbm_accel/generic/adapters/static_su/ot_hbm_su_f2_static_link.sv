`timescale 1ns/1ps
`default_nettype none
// Four independent fixed-cycle SU quarter links to the 32 native VM banks.
// Bank q*8+b belongs to quadrant q and bank b. No arbitration, queues or return
// flow control: the compiler owns RG0/WG0 and schedules every read/write slot.
// RD_LAT counts sampled edges: n+6 registered bank response is sampled here
// at n+7 (RD_LAT=7). The extra edge is the registered link return boundary.
// Native bank ECC data is carried without reinterpretation. Address errors and
// missed/unsolicited response slots latch a fault; faults never stall the clock.
// Operand broadcast: a compiler load fills ONE sector per quarter, replayed into
// selected write lanes. Load/replay on the same edge sees the previously loaded
// sector, preserving synchronous SRAM semantics. Source data may be fetched once
// and reused without eight further reads; payload data are not reset.
module ot_hbm_su_f2_static_quarter #(parameter integer QID=0,RD_LAT=7,MUT_ROUTE=0,MUT_REUSE=0)(
 input wire clk,rst_n,
 input wire [8*17-1:0] su_rq,input wire[8*281-1:0]su_wq,
 output reg[8*17-1:0]vm_rq,output reg[8*281-1:0]vm_wq,
 input wire[8*257-1:0]vm_rr,output reg[8*257-1:0]su_rr,
 input wire operand_load,input wire[255:0]operand_data,
 input wire[7:0]operand_replay,output reg fault
);
 reg[255:0]operand;reg operand_valid;
 reg[7:0]expected[0:RD_LAT-1];integer b,s;
 reg[16:0]r;reg[280:0]w;
 initial if(RD_LAT<1)$fatal(1,"RD_LAT must be positive");
 function automatic address_ok(input[15:0]sec,input integer bank);
 address_ok=sec[2:0]==3'(bank)&&(sec[15]?sec[14:13]==2'b00:sec[14:13]==2'(QID));
 endfunction
 always @(posedge clk)begin
  if(!rst_n)begin
   vm_rq<=0;vm_wq<=0;su_rr<=0;operand_valid<=0;fault<=0;
   for(s=0;s<RD_LAT;s=s+1)expected[s]<=0;
  end else begin
   for(s=1;s<RD_LAT;s=s+1)expected[s]<=expected[s-1];
   if(operand_load)begin operand<=operand_data;operand_valid<=1;end
   for(b=0;b<8;b=b+1)begin
    r=su_rq[b*17+:17];w=su_wq[b*281+:281];
    if(r[16]&&!address_ok(r[15:0],b))fault<=1;
    if(w[280]&&!address_ok(w[279:264],b))fault<=1;
    if(w[280]&&operand_replay[b])begin
     if(!operand_valid)fault<=1;
     w[263:8]=operand^(MUT_REUSE!=0?256'd1:256'd0);
    end
    vm_rq[(MUT_ROUTE!=0?(b+1)%8:b)*17+:17]<=r;
    vm_wq[b*281+:281]<=w;
    expected[0][b]<=vm_rq[b*17+16];
    if(vm_rr[b*257+256]!==expected[RD_LAT-1][b])fault<=1;
    su_rr[b*257+:257]<=vm_rr[b*257+:257];
   end
  end
 end
endmodule
module ot_hbm_su_f2_static_link #(parameter integer RD_LAT=7,MUT_ROUTE=0,MUT_REUSE=0)(
 input wire[3:0]quarter_clk,input wire rst_n,
 input wire[32*17-1:0]su_rq,input wire[32*281-1:0]su_wq,
 output wire[32*17-1:0]vm_rq,output wire[32*281-1:0]vm_wq,
 input wire[32*257-1:0]vm_rr,output wire[32*257-1:0]su_rr,
 input wire[3:0]operand_load,input wire[4*256-1:0]operand_data,
 input wire[31:0]operand_replay,output wire[3:0]fault
);
 // Each independently hardened quarter has one compensated clock input and
 // 4,754 register bits (RD_LAT=7); the parent contains only fixed wires.
 for(genvar q=0;q<4;q=q+1)begin:g_quarter
  ot_hbm_su_f2_static_quarter #(.QID(q),.RD_LAT(RD_LAT),.MUT_ROUTE(MUT_ROUTE),.MUT_REUSE(MUT_REUSE))u_q(
   .clk(quarter_clk[q]),.rst_n(rst_n),
   .su_rq(su_rq[q*8*17+:8*17]),.su_wq(su_wq[q*8*281+:8*281]),
   .vm_rq(vm_rq[q*8*17+:8*17]),.vm_wq(vm_wq[q*8*281+:8*281]),
   .vm_rr(vm_rr[q*8*257+:8*257]),.su_rr(su_rr[q*8*257+:8*257]),
   .operand_load(operand_load[q]),.operand_data(operand_data[q*256+:256]),
   .operand_replay(operand_replay[q*8+:8]),.fault(fault[q]));
 end
endmodule
`default_nettype wire
