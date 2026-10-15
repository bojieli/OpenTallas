`timescale 1ns/1ps
`default_nettype none
// Finite 16-entry ordered completion buffer. Fast S2 retires through the actual
// S3 register at the original SPANPIPE0 edge. General S3 gains one edge.
module ot_hgi_qdq_fr_retire #(parameter integer MUT_ORDER=0, MUT_END=0) (
 input wire clk, rst_n,
 input wire accept, accept_one,
 input wire fast_v, fast_one, input wire [332:0] fast_s2,
 input wire general_v, input wire [189:0] general_s3,
 output reg s3_v, output reg [189:0] s3, output reg overflow
);
 reg f_rst;
 always @(posedge clk) f_rst <= rst_n;
 wire [0:0] rr_n;
 ot_rst_relay #(.REGIONS(1)) u_rst(.clk(clk),.rst_n_in(f_rst),.rst_n(rr_n));
 reg [3:0] head, tail, tags[0:7];
 reg [4:0] count;
 reg [15:0] ready, classes;
 reg [189:0] payload[0:15];
 wire fld, fast, same;
 wire [63:0] ae, oe;
 wire [39:0] ab, ob;
 wire [19:0] n,m;
 wire [31:0] ars,ors;
 wire [17:0] hd;
 assign {fld,fast,same,ae,oe,ab,ob,n,m,ars,ors,hd} = fast_s2;
 wire eligible = fld && fast && ae < 64'd262144 && oe < 64'd262144 &&
                  (ae < 64'(ob) || oe < 64'(ab) || (same && ab == ob));
 wire [189:0] incoming = {eligible,ab[17:0],(ae[17:0] ^ 18'(MUT_END)),ob[17:0],oe[17:0],
                         ab[17:3],ob[17:3],ars[17:3],ors[17:3],16'((n+20'd31)>>5),
                         ((n[4:0]==0)?3'd4:{1'b0,n[4:3]}),m,hd};
 wire fv = fast_v && fast_one;
 wire gv = general_v && !classes[tags[7]];
 wire fh = fv && (tags[0] == head || MUT_ORDER != 0);
 wire gh = gv && tags[7] == head;
 wire pop = count != 0 && (ready[head] || fh || gh);
 integer k;
 always @(posedge clk or negedge rr_n[0]) begin
  if (!rr_n[0]) begin
   head<=0;tail<=0;count<=0;ready<=0;classes<=0;s3_v<=0;overflow<=0;
   for(k=0;k<8;k=k+1) tags[k]<=0;
  end else begin
   tags[0]<=tail;
   for(k=1;k<8;k=k+1) tags[k]<=tags[k-1];
   s3_v<=pop;
   if(pop) begin
    s3<=ready[head]?payload[head]:(fh?incoming:general_s3);
    ready[head]<=0;head<=head+4'd1;
   end
   if(fv && !fh) begin payload[tags[0]]<=incoming;ready[tags[0]]<=1;end
   if(gv && !gh) begin payload[tags[7]]<=general_s3;ready[tags[7]]<=1;end
   if(accept) begin
    tail<=tail+4'd1;classes[tail]<=accept_one;
    if(count==16 && !pop) overflow<=1;
   end
   case({accept,pop})
    2'b10: count<=count+5'd1;
    2'b01: count<=count-5'd1;
    default: count<=count;
   endcase
  end
 end
endmodule
`default_nettype wire
