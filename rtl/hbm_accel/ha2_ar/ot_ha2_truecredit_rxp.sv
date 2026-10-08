// Pipelined true-credit receiver (drive-1043-timing, 2026-10-08).
// Transaction-exact successor of ot_ha2_truecredit_receiver for the hardened rx block
// (W=544, INJ=2, 64-deep flop queue, ~73k flops). The original failed TT setup by -278 ps:
//   * arrival_tag pin -> tag compare -> push -> 35k-flop write enable (input budget 316 ps),
//   * rd pointer -> 64:1 x 560-bit read mux (reg2reg -219 ps),
//   * quiet/fault combinational to the output ports, rst_n pin -> 130 async flops.
// Changes (structural, no squeeze):
//   1. every arrival pin lands in a flop first (av_q/tag_q/data_q): +1 cycle on arrival;
//   2. queue write enable no longer waits for the tag compare: a slot is written whenever a
//      registered arrival is present and the queue is not full; the write pointer advances
//      only on a valid (tag-matching) arrival, so a rejected beat lands in a free slot that is
//      never read (slot wp is free unless full, and full is excluded);
//   3. one-hot write/read rings (registered) replace the binary decode; the read mux is AND-OR;
//   4. send_data loads the head every cycle (consumers sample it only with send_v);
//   5. quiet/fault are registered (lag one cycle; quiet stays covered by the sender's
//      outstanding credit, exactly as the original ignores a beat still on the arrival wire);
//   6. reset: rst_n asserts asynchronously, deasserts through one local flop per lane;
//      the arrival-valid flop keeps the raw reset so no beat after deassertion is lost.
// receiver_ready stays a same-cycle input (contract unchanged); it reaches ~100 control
// flops only (pop -> send_v/return_v/return_tag/rd ring/expect_retire/bad), not the data.
// MUTANT 2 corrupts the returned tag (as the original); MUTANT 4 misaligns the read ring.
module ot_ha2_truecredit_receiver_p #(
 parameter integer W=544, INJ=2, AW=6, TAGW=16, MUTANT=0
)(input wire clk,rst_n,
 input wire[INJ-1:0] arrival_v,receiver_ready,
 input wire[INJ*W-1:0] arrival_data,
 input wire[INJ*TAGW-1:0] arrival_tag,
 output reg[INJ-1:0] send_v,return_v,
 output reg[INJ*W-1:0] send_data,
 output reg[INJ*TAGW-1:0] return_tag,
 output reg quiet,fault);
 initial if(TAGW<=AW)$fatal(1,"HA2 truecredit tags must exceed slot address width");
 localparam integer D=1<<AW;
 localparam integer FW=W+TAGW;
 wire[INJ-1:0] bads,idle;
 for(genvar i=0;i<INJ;i=i+1)begin:g_lane
  // 6. local reset release
  reg rst_l;
  always @(posedge clk or negedge rst_n)if(!rst_n)rst_l<=1'b0;else rst_l<=1'b1;
  // 1. pin capture
  reg av_q;
  reg[TAGW-1:0] tag_q;
  reg[W-1:0] data_q;
  always @(posedge clk or negedge rst_n)if(!rst_n)av_q<=1'b0;else av_q<=arrival_v[i];
  always @(posedge clk)begin tag_q<=arrival_tag[i*TAGW+:TAGW];data_q<=arrival_data[i*W+:W];end
  // queue state
  reg[TAGW-1:0] expect_arrival,expect_retire;
  reg bad,ovf;
  reg[AW:0] wp,rp;
  reg[D-1:0] wr_oh,rd_oh;
  reg[FW-1:0] mem[0:D-1];
  wire empty=wp==rp;
  wire full=(wp[AW]!=rp[AW])&&(wp[AW-1:0]==rp[AW-1:0]);
  wire valid_arrival=av_q&&tag_q==expect_arrival&&!bad;
  wire pop=!empty&&receiver_ready[i]&&!bad;
  // 3. AND-OR read mux over the registered one-hot read ring
  wire[D-1:0] rd_sel=(MUTANT==4)?{rd_oh[D-2:0],rd_oh[D-1]}:rd_oh;
  reg[FW-1:0] head;
  always @* begin
   head={FW{1'b0}};
   for(integer r=0;r<D;r=r+1)head=head|({FW{rd_sel[r]}}&mem[r]);
  end
  wire[TAGW-1:0] head_tag=head[W+:TAGW];
  // 2. write enable: registered arrival present, not full, one-hot slot
  wire wr=av_q&&!full;
  for(genvar r=0;r<D;r=r+1)begin:g_slot
   always @(posedge clk)if(wr&&wr_oh[r])mem[r]<={tag_q,data_q};
  end
  assign bads[i]=bad||ovf;
  assign idle[i]=empty&&!av_q&&!send_v[i]&&!return_v[i];
  always @(posedge clk or negedge rst_l)
   if(!rst_l)begin
    expect_arrival<=0;expect_retire<=0;bad<=0;ovf<=0;wp<=0;rp<=0;
    wr_oh<={{(D-1){1'b0}},1'b1};rd_oh<={{(D-1){1'b0}},1'b1};
    send_v[i]<=0;return_v[i]<=0;return_tag[i*TAGW+:TAGW]<=0;
   end else begin
    send_v[i]<=pop;return_v[i]<=pop;
    if(av_q&&!valid_arrival)bad<=1;
    if(valid_arrival)begin
     expect_arrival<=expect_arrival+1'b1;
     if(full)ovf<=1'b1;
     else begin wp<=wp+1'b1;wr_oh<={wr_oh[D-2:0],wr_oh[D-1]};end
    end
    if(pop)begin
     if(head_tag!=expect_retire)bad<=1;
     return_tag[i*TAGW+:TAGW]<=head_tag ^ ((MUTANT==2)?TAGW'(1):TAGW'(0));
     expect_retire<=expect_retire+1'b1;
     rp<=rp+1'b1;rd_oh<={rd_oh[D-2:0],rd_oh[D-1]};
    end
   end
  // 4. head loads every cycle
  always @(posedge clk)send_data[i*W+:W]<=head[W-1:0];
 end
 // 5. registered status
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin quiet<=1'b1;fault<=1'b0;end
  else begin quiet<=&idle;fault<=|bads;end
endmodule
