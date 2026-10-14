`timescale 1ns/1ps
`default_nettype none
// Private completion root. PAY snapshot and committed ACKs each first capture
// at their face. Raw ACK lookahead is consumed only by the registered done pin.
// Counter arithmetic is modulo256; maximum outstanding per lane must be <128.
module ot_hgi_qdq_wr_fin #(parameter integer RQ=16, MUT=0)(
 input wire clk,rst_n,
 input wire snapshot_v,input wire [63:0] snapshot,
 input wire [7:0] wwq_done,
 output reg o_fin,output reg o_bad,output reg o_idle
);
 localparam QW=$clog2(RQ);
 reg f_rst,s_v;reg [63:0] s;reg [7:0] ack;
 always @(posedge clk)begin f_rst<=rst_n;s<=snapshot;ack<=wwq_done;end
 wire [0:0] rr_n;
 ot_rst_relay #(.REGIONS(1)) u_rst(.clk(clk),.rst_n_in(f_rst),.rst_n(rr_n));
 always @(posedge clk or negedge rr_n[0])if(!rr_n[0])s_v<=0;else s_v<=snapshot_v;
 reg [63:0] sq[0:RQ-1];reg [QW-1:0] tail,head;reg [QW:0] count;
 reg [63:0] sh;reg [7:0] dc[0:7];reg [7:0] neg0,neg1,neg2;
 wire [QW-1:0] head1=head+1'b1;
 (* keep=1 *) wire [63:0] hs0=sq[head],hs1=sq[head1];
 wire [7:0] raw_ack=MUT==1?8'hff:wwq_done;
 wire [7:0] selected_neg=(neg0&~(ack|raw_ack))|(neg1&(ack^raw_ack))|(neg2&ack&raw_ack);
 wire fin=(count!=0)&&!(|selected_neg);
 wire pushed_head=s_v&&count==(QW+1)'(fin);
 for(genvar b=0;b<8;b=b+1)begin:g_lane
     wire [7:0] dn=dc[b]+8'(ack[b]);
     (* keep=1 *) wire [7:0] d00=dn-hs0[b*8+:8],d10=dn-hs1[b*8+:8],dp0=dn-s[b*8+:8];
     (* keep=1 *) wire [7:0] d01=d00+8'd1,d11=d10+8'd1,dp1=dp0+8'd1;
     (* keep=1 *) wire [7:0] d02=d00+8'd2,d12=d10+8'd2,dp2=dp0+8'd2;
     always @(posedge clk)begin
         neg0[b]<=pushed_head?dp0[7]:fin?d10[7]:d00[7];
         neg1[b]<=pushed_head?dp1[7]:fin?d11[7]:d01[7];
         neg2[b]<=pushed_head?dp2[7]:fin?d12[7]:d02[7];
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
     if(!rr_n[0])begin tail<=0;head<=0;count<=0;o_fin<=0;o_bad<=0;o_idle<=0;end
     else begin
         if(s_v)tail<=tail+1'b1;
         if(fin)head<=head+1'b1;
         count<=count+(QW+1)'(s_v)-(QW+1)'(fin);
         o_fin<=fin;
         if(s_v&&count==RQ&&!fin)o_bad<=1;
         o_idle<=count==0&&!s_v&&!snapshot_v;
     end
 end
 always @(posedge clk)begin
     if(s_v)sq[tail]<=MUT==2?s^64'd1:s;
     if(pushed_head)sh<=s;
     else sh<=fin?hs1:hs0;
`ifndef SYNTHESIS
     if(rr_n[0]&&count!=0&&sh!==sq[head])$fatal(1,"FIN head diverged");
`endif
 end
 initial if(RQ<2||(RQ&(RQ-1))!=0)$fatal(1,"FIN RQ must be power2 >=2");
endmodule
`default_nettype wire
