`timescale 1ns/1ps
// Opt-in one-stack merge. svc serializes physical writes; ack_n is its true
// completion counter delta, never FIFO-pop credits. Input packets {data256,addr30,pc5}.
// Ledger identity remains reserved until completion. One slot is reserved for WB.
module ot_hbm_write_merge #(parameter integer ENABLE=0) (
 input wire ck,rst_n,
 input wire [2:0] src_v, input wire [3*291-1:0] src_d, output wire [2:0] src_r,
 output wire svc_v, output wire [290:0] svc_d, input wire svc_r,
 input wire [7:0] ack_n, output reg [17:0] src_ack_n,
 output reg fault
);
 generate if (!ENABLE) begin:g_off
  assign src_r=0; assign svc_v=0; assign svc_d=0;
  always @(*) begin src_ack_n=0; fault=0; end
 end else begin:g_on
  reg pending; reg [290:0] payload; reg [1:0] owner;
  reg rr; reg [1:0] ids[0:7]; reg [2:0] wp,rp; reg [3:0] count;
  wire issue=pending && svc_r;
  wire ack_ok=ack_n <= count;
  wire room=(count + pending) < 8;
  wire bg_room=(count + pending) < 7;
  reg [1:0] chosen; reg choose_v;
  always @(*) begin
   chosen=0; choose_v=0;
   if (room && src_v[0]) begin chosen=0; choose_v=1; end
   else if (!src_v[0] && bg_room) begin
    if (src_v[1] && src_v[2]) begin chosen=rr?2:1; choose_v=1; end
    else if (src_v[1]) begin chosen=1; choose_v=1; end
    else if (src_v[2]) begin chosen=2; choose_v=1; end
   end
  end
  wire take=(!pending || issue) && choose_v && !fault;
  assign src_r=take ? (3'b001 << chosen) : 3'b000;
  assign svc_v=pending && !fault;
  assign svc_d=payload;
  integer k; reg [5:0] a0,a1,a2;
  always @(*) begin
   a0=0;a1=0;a2=0;
   for (integer j=0;j<8;j=j+1) if (ack_ok && j < ack_n) begin
    case (ids[(rp+j)&7])
     0:a0=a0+1'b1; 1:a1=a1+1'b1; 2:a2=a2+1'b1;
    endcase
   end
  end
  always @(posedge ck or negedge rst_n) begin
   if (!rst_n) begin pending<=0; payload<=0; owner<=0; rr<=0;
    wp<=0;rp<=0;count<=0;src_ack_n<=0;fault<=0;
   end else begin
    src_ack_n<=0;
    if (!ack_ok) fault<=1;
    if (!fault && ack_ok) begin
     src_ack_n<={a2,a1,a0};
     rp<=rp+ack_n[2:0];
     count<=count + (issue?4'd1:4'd0) - ack_n[3:0];
     if (issue) begin ids[wp]<=owner;wp<=wp+1'b1;pending<=0;end
     if (take) begin
      pending<=1;payload<=src_d[chosen*291 +:291];owner<=chosen;
      if (chosen!=0) rr<=chosen==1;
     end
    end
   end
  end
 end endgenerate
endmodule
