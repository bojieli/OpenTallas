`timescale 1ns/1ps
// Private opt-in A0 helper copy. Original ot_qw_* modules/defaults untouched.
// External CB/vld ABI retained. Internal controls <=8 data bits, delay reset <=2 bits.
module ot_qw_lw_n32 #(parameter W=128,D=4,CB=24,C=(W+CB-1)/CB)(input ck,rsi,input [W-1:0] i,output [D*W-1:0] bank,output [D*C-1:0] vld);
 localparam NS=(CB+5)/6, NR=(C*NS+15)/16;
 wire [NR-1:0] rr;
 for(genvar r=0;r<NR;r=r+1) begin:g_rr
 (* keep *) reg rr_q; (* keep *) always @(posedge ck) rr_q<=rsi; assign rr[r]=rr_q;end
 for(genvar c=0;c<C;c=c+1) begin:g_c
  localparam CW=(W-c*CB<CB)?W-c*CB:CB;
  for(genvar a=0;a<(CW+5)/6;a=a+1) begin:g_a
   localparam BW=(CW-a*6<6)?CW-a*6:6;
   (* keep *) reg rq; (* keep *) reg rqd;
   (* keep *) reg [D-1:0] woh;
   reg [D-1:0] v;
   (* keep *) always @(posedge ck) rq<=rr[(c*NS+a)/16];
   (* keep *) always @(posedge ck) rqd<=rr[(c*NS+a)/16];
   (* keep *) always @(posedge ck) if(!rq) begin woh<=1;v<=0;end else begin woh<={woh[D-2:0],woh[D-1]};v<=v|woh;end
   for(genvar s=0;s<D;s=s+1) begin:g_s
    reg [BW-1:0] dq;
    (* keep *) always @(posedge ck) if(rqd&&woh[s]) dq<=i[c*CB+a*6+:BW];
    assign bank[s*W+c*CB+a*6+:BW]=dq;
   end
   if(a==0) assign vld[c*D+:D]=v;
  end
 end
endmodule
module ot_qw_lr_n32 #(parameter W=128,D=4,K=2,CB=24,C=(W+CB-1)/CB,AW=(D<=2)?1:$clog2(D))(input ck,rsi,input [D*W-1:0] bank,input [D*C-1:0] vld,output [W-1:0] o);
 localparam NS=(CB+7)/8,NR=(C*NS+15)/16;
 wire [NR-1:0] rr;
 for(genvar r=0;r<NR;r=r+1) begin:g_rr
 (* keep *) reg rr_q; (* keep *) always @(posedge ck) rr_q<=rsi; assign rr[r]=rr_q;end
 for(genvar c=0;c<C;c=c+1) begin:g_c
  localparam CW=(W-c*CB<CB)?W-c*CB:CB;
  for(genvar a=0;a<(CW+7)/8;a=a+1) begin:g_a
   localparam BW=(CW-a*8<8)?CW-a*8:8;
   (* keep *) reg rq;
   reg warm; reg [AW:0] rc; (* keep *) reg [D-1:0] roh;
   reg [BW-1:0] sel,q;reg sv;integer j;
   always @* begin sel=0;sv=0;for(j=0;j<D;j=j+1) begin sel=sel|(bank[j*W+c*CB+a*8+:BW]&{BW{roh[j]}});sv=sv|(vld[c*D+j]&roh[j]);end end
   (* keep *) always @(posedge ck) rq<=rr[(c*NS+a)/16];
   (* keep *) always @(posedge ck) if(!rq) begin rc<=0;warm<=0;for(j=0;j<D;j=j+1) roh[j]<=(j==((D-K)%D));end else begin rc<=rc+1'b1;if(rc==K-1) warm<=1;roh<={roh[D-2:0],roh[D-1]};end
   (* keep *) always @(posedge ck) q<=(warm&&sv)?sel:0;
   assign o[c*CB+a*8+:BW]=q;
  end
 end
endmodule
module ot_qw_ring_delay_n32 #(parameter W=128,D=3,CB=16,C=(W+CB-1)/CB)(input clk,rst_n,input [W-1:0] d,output [W-1:0] q);
 localparam S=D-1,PC=W,NR=(PC+15)/16;
 generate if(D<3) begin:g_short
  ot_hdc_delay #(.W(W),.D(D)) u_d(.clk(clk),.rst_n(rst_n),.d(d),.q(q));
 end else begin:g_ring
  wire [NR-1:0] rr;
  for(genvar r=0;r<NR;r=r+1) begin:g_rr
  (* keep *) reg rr_q; (* keep *) always @(posedge clk) rr_q<=rst_n; assign rr[r]=rr_q;end
  for(genvar c=0;c<PC;c=c+1) begin:g_c
   localparam BW=1;
   (* keep *) reg rq;(* keep *) reg [S-1:0] p;
   wire [BW*S-1:0] slot;reg [BW-1:0] sel,qq;integer j;
   always @* begin sel=0;for(j=0;j<S;j=j+1) sel=sel|(slot[j*BW+:BW]&{BW{p[j]}});end
   (* keep *) always @(posedge clk) rq<=rr[c/16];
   (* keep *) always @(posedge clk) if(!rq) p<=1;else p<={p[S-2:0],p[S-1]};
   for(genvar s=0;s<S;s=s+1) begin:g_s
    reg [BW-1:0] sq;
    (* keep *) always @(posedge clk) if(p[s]||!rq) sq<=d[c+:BW];
    assign slot[s*BW+:BW]=sq;
   end
   (* keep *) always @(posedge clk) qq<=sel;
   assign q[c+:BW]=qq;
  end
 end endgenerate
endmodule
