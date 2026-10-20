`timescale 1ns/1ps
// Candidate boundary only. Requires exact phase-zero 3:4 common epoch.
// Clock compensation and phase/reset establishment are integration obligations.
// Every transfer uses compiler-reserved slots; faults never alter issue timing.
// HBM-BANKLAT-SU 2026-10-19: READ_RETURN / WRITE_RETURN = the stream LG round trip (LG samples the request at stream
// edge j+1, presents the read answer at j+1+READ_RETURN / the write done at j+1+WRITE_RETURN; default 10/7 = the
// zero-lane non-pin bank). The serial presentation edge is derived, not a free constant:
//   SRD = ceil((3*READ_RETURN+18)/4), SWD = ceil((3*WRITE_RETURN+18)/4)   (12 / 10 at the defaults)
// i.e. the first serial edge at least 6 quanta after the latest stream capture 3(j+RT+2) <= 4n+3RT+12; the next
// same-slot capture (source n+4) is >= 4n+3RT+26, so the slot-overwrite guard stays >= 5 quanta for every RT.
// Every register width/index reduces to the 10/7 structure at the defaults (bit-identical netlist).
module ot_hbm_su_multirate_bridge #(
 parameter integer RQ_BITS=17,WQ_BITS=281,RR_BITS=257,
 parameter integer MUT_SLOT=0,
 parameter integer READ_RETURN=10,
 parameter integer WRITE_RETURN=7
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
 localparam integer SRD=(3*READ_RETURN+18+3)/4, SWD=(3*WRITE_RETURN+18+3)/4;
 localparam integer RP=READ_RETURN+2, WP=WRITE_RETURN+2;          // stream capture edge after the register event
 localparam integer WW=$clog2(SRD+1)>$clog2(SWD+1)?$clog2(SRD+1):$clog2(SWD+1);
 initial if(READ_RETURN<10||WRITE_RETURN<7||WRITE_RETURN>READ_RETURN)$fatal(1,"bridge: LG round trip below the 10/7 zero-lane contract (or write > read)");
 reg [WW-1:0] serial_warm;
 reg [3:0] phase;
 reg [4:0] stream_warm;
 reg [RP-1:0] active_pipe,read_pipe;
 reg [WP-1:0] write_pipe;
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
 wire [1:0] read_slot=slot_for_phase(phase-4'(RP));
 wire [1:0] done_slot_index=slot_for_phase(phase-4'(WP));
 integer k;
 always @(posedge serial_clk or negedge rst_n)begin
  if(!rst_n)begin
   serial_slot<=0;serial_warm<=0;serial_rr<=0;serial_done<=0;
   for(integer i=0;i<4;i=i+1)begin rq_slot[i]<=0;wq_slot[i]<=0;end
  end else begin
   rq_slot[serial_slot]<=serial_rq;wq_slot[serial_slot]<=serial_wq;
   // source n-SRD sits in slot (n-SRD) mod4 (SRD 12: the same slot); n-SWD in (n-SWD) mod4 (SWD 10: n+2).
   serial_rr <= serial_warm>=WW'(SRD) ? rr_slot[serial_slot-2'(SRD)] : '0;
   serial_done <= serial_warm>=WW'(SWD) ? done_slot[serial_slot-2'(SWD)] : 1'b0;
   serial_slot<=serial_slot+1'b1;
   if(serial_warm<WW'(SRD>SWD?SRD:SWD))serial_warm<=serial_warm+1'b1;
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
   active_pipe<={active_pipe[RP-2:0],active};
   read_pipe<={read_pipe[RP-2:0],active && rq_slot[launch_slot][RQ_BITS-1]};
   write_pipe<={write_pipe[WP-2:0],active && wq_slot[launch_slot][WQ_BITS-1]};
   // LG response is presented after issue+READ_RETURN; capture one full stream cycle
   // later, then hold this slot until its fixed serial n+SRD read.
   if(active_pipe[RP-1])rr_slot[read_slot]<=stream_rr;
   if(active_pipe[WP-1])done_slot[done_slot_index]<=stream_done;
   if(stream_rr[RR_BITS-1]!==read_pipe[RP-1] || stream_done!==write_pipe[WP-1])fault<=1;
  end
 end
endmodule
