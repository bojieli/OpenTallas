`timescale 1ns/1ps
`default_nettype none
// Private completion root. PAY snapshot and committed ACKs each first capture
// at their face. Every ACK captures directly before any completion logic;
// output launch and private queue-pop state use distinct reset regions.
// Counter arithmetic is modulo256; maximum outstanding per lane must be <128.
module ot_hgi_qdq_wr_fin #(parameter integer RQ=16, MUT=0)(
 input wire clk,rst_n,
 input wire snapshot_v,input wire [63:0] snapshot,
 input wire [7:0] wwq_done,
 output reg o_fin,output reg o_bad,output reg o_idle
);
 localparam QW=$clog2(RQ);
 reg f_rst,s_v;reg [63:0] s;reg [7:0] ack;
 always @(posedge clk)begin f_rst<=rst_n;s<=snapshot;ack<=MUT==1?8'hff:wwq_done;end
 wire [1:0] rr_n;
 ot_rst_relay #(.REGIONS(2)) u_rst(.clk(clk),.rst_n_in(f_rst),.rst_n(rr_n));
 always @(posedge clk or negedge rr_n[0])if(!rr_n[0])s_v<=0;else s_v<=snapshot_v;
 reg [63:0] sq[0:RQ-1];reg [QW-1:0] tail,head;reg [QW:0] count;
 reg [63:0] sh;reg has_snapshot;reg [7:0] dc[0:7];reg [7:0] neg0,neg1,neg2;
 wire [QW-1:0] head1=head+1'b1;
 (* keep=1 *) wire [63:0] hs0=sq[head],hs1=sq[head1];
 (* keep="true",dont_touch="true" *) reg pop_pending;
 (* keep=1 *) wire [7:0] captured_bad=(neg0&~ack)|(neg1&ack);
 wire fin=has_snapshot&&!pop_pending&&!(|captured_bad);
 wire pop=pop_pending;
 wire pushed_head=s_v&&count==(QW+1)'(pop);
 for(genvar b=0;b<8;b=b+1)begin:g_lane
     wire [7:0] dn=dc[b]+8'(ack[b]);
     (* keep=1 *) wire [7:0] d00=dn-hs0[b*8+:8],d10=dn-hs1[b*8+:8],dp0=dn-s[b*8+:8];
     (* keep=1 *) wire [7:0] d01=d00+8'd1,d11=d10+8'd1,dp1=dp0+8'd1;
     (* keep=1 *) wire [7:0] d02=d00+8'd2,d12=d10+8'd2,dp2=dp0+8'd2;
     always @(posedge clk)begin
         neg0[b]<=pushed_head?dp0[7]:pop?d10[7]:d00[7];
         neg1[b]<=pushed_head?dp1[7]:pop?d11[7]:d01[7];
         neg2[b]<=pushed_head?dp2[7]:pop?d12[7]:d02[7];
     end
     always @(posedge clk or negedge rr_n[0])if(!rr_n[0])dc[b]<=0;else dc[b]<=dc[b]+8'(ack[b]);
`ifndef SYNTHESIS
     always @(negedge clk)if(rr_n[0]&&count!=0)begin
         reg [7:0] chk0,chk1,chk2;
         chk0=dc[b]-sh[b*8+:8];chk1=chk0+8'd1;chk2=chk0+8'd2;
         if({neg2[b],neg1[b],neg0[b]}!={chk2[7],chk1[7],chk0[7]})$fatal(1,"FIN flag mismatch lane%0d",b);
     end
`endif
 end
 always @(posedge clk or negedge rr_n[0])begin
     if(!rr_n[0])begin tail<=0;head<=0;count<=0;has_snapshot<=0;pop_pending<=0;o_bad<=0;o_idle<=0;end
     else begin
         if(s_v)tail<=tail+1'b1;
         if(pop)head<=head+1'b1;
         count<=count+(QW+1)'(s_v)-(QW+1)'(pop);
         has_snapshot <= (count+(QW+1)'(s_v)-(QW+1)'(pop))!=0;
         pop_pending<=fin;
         if(s_v&&count==(QW+1)'(RQ)&&!pop)o_bad<=1;
         o_idle<=count==0&&!s_v; // idle reports captured obligations; no raw input path
     end
 end
 // Separate physical launch flop at E face; internal pop feedback stays private.
 always @(posedge clk or negedge rr_n[1])if(!rr_n[1])o_fin<=0;else o_fin<=fin;
 always @(posedge clk)begin
     if(s_v)sq[tail]<=MUT==2?s^64'd1:s;
     if(pushed_head)sh<=s;
     else sh<=pop?hs1:hs0;
`ifndef SYNTHESIS
     if(rr_n[0]&&has_snapshot!==(count!=0))$fatal(1,"FIN nonempty state mismatch");
     if(rr_n[0]&&count!=0&&sh!==sq[head])$fatal(1,"FIN head diverged");
`endif
 end
 initial if(RQ<2||(RQ&(RQ-1))!=0)$fatal(1,"FIN RQ must be power2 >=2");
endmodule
`default_nettype wire
