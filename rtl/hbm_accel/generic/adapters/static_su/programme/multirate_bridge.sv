`timescale 1ns/1ps
// Candidate boundary only. Requires exact phase-zero 3:4 common epoch.
// Clock compensation and phase/reset establishment are integration obligations.
// Every transfer uses compiler-reserved slots; faults never alter issue timing.
module ot_hbm_su_multirate_bridge #(
 parameter integer RQ_BITS=17,WQ_BITS=281,RR_BITS=257,
 parameter integer MUT_SLOT=0
)(input wire serial_clk,stream_clk,rst_n,
 input wire [RQ_BITS-1:0] serial_rq,input wire [WQ_BITS-1:0] serial_wq,
 output reg [RR_BITS-1:0] serial_rr,output reg serial_done,
 output reg [RQ_BITS-1:0] stream_rq,output reg [WQ_BITS-1:0] stream_wq,
 input wire [RR_BITS-1:0] stream_rr,input wire stream_done,
 output reg fault);
 // These are explicit register banks, not an asynchronous FIFO or a behavioral
 // memory substitution. Four slots prevent cross-clock read/write overlap.
 reg [RQ_BITS-1:0] rq_slot[0:3];reg [WQ_BITS-1:0] wq_slot[0:3];
 reg [RR_BITS-1:0] rr_slot[0:3];reg done_slot[0:3];
 reg [1:0] serial_slot;
 reg [3:0] serial_warm;
 reg [3:0] phase;
 reg [4:0] stream_warm;
 reg [11:0] active_pipe,read_pipe;
 reg [8:0] write_pipe;
 // Request-register event j: j mod4=2 -> n=3floor(j/4),
 // mod4=3 -> n=3floor(j/4)+1, mod4=0 -> n=3floor(j/4)-1.
 // j=0 is suppressed at epoch startup. Low four j bits identify n mod4.
 function automatic [1:0] slot_for_phase(input [3:0] p);
  reg [3:0] n;
  begin
   n=3*{2'b0,p[3:2]};
   if(p[1:0]==3)n=n+1;
   if(p[1:0]==0)n=n-1;
   slot_for_phase=n[1:0];
  end
 endfunction
 wire active=phase[1:0]!=1 && stream_warm>=2;
 wire [1:0] launch_slot=slot_for_phase(phase)+2'(MUT_SLOT);
 wire [1:0] read_slot=slot_for_phase(phase-4'd12);
 wire [1:0] done_slot_index=slot_for_phase(phase-4'd9);
 integer k;
 always @(posedge serial_clk or negedge rst_n)begin
  if(!rst_n)begin
   serial_slot<=0;serial_warm<=0;serial_rr<=0;serial_done<=0;
   for(integer i=0;i<4;i=i+1)begin rq_slot[i]<=0;wq_slot[i]<=0;end
  end else begin
   rq_slot[serial_slot]<=serial_rq;wq_slot[serial_slot]<=serial_wq;
   // n-12 and n use the same modulo-four slot; n-10 is n+2 mod4.
   serial_rr <= serial_warm>=12 ? rr_slot[serial_slot] : '0;
   serial_done <= serial_warm>=10 ? done_slot[serial_slot+2'd2] : 1'b0;
   serial_slot<=serial_slot+1'b1;
   if(serial_warm<12)serial_warm<=serial_warm+1'b1;
  end
 end
 always @(posedge stream_clk or negedge rst_n)begin
  if(!rst_n)begin
   phase<=0;stream_warm<=0;stream_rq<=0;stream_wq<=0;
   active_pipe<=0;read_pipe<=0;write_pipe<=0;fault<=0;
   for(integer i=0;i<4;i=i+1)begin rr_slot[i]<=0;done_slot[i]<=0;end
  end else begin
   phase<=phase+1'b1;if(stream_warm<16)stream_warm<=stream_warm+1'b1;
   stream_rq<=active ? rq_slot[launch_slot] : '0;
   stream_wq<=active ? wq_slot[launch_slot] : '0;
   active_pipe<={active_pipe[10:0],active};
   read_pipe<={read_pipe[10:0],active && rq_slot[launch_slot][RQ_BITS-1]};
   write_pipe<={write_pipe[7:0],active && wq_slot[launch_slot][WQ_BITS-1]};
   // LG response is presented after issue+10; capture one full stream cycle
   // later, then hold this slot until its fixed serial n+12 read.
   if(active_pipe[11])rr_slot[read_slot]<=stream_rr;
   if(active_pipe[8])done_slot[done_slot_index]<=stream_done;
   if(stream_rr[RR_BITS-1]!==read_pipe[11] || stream_done!==write_pipe[8])fault<=1;
  end
 end
endmodule
