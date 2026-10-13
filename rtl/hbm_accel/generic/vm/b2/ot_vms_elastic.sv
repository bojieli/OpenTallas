`timescale 1ns/1ps
`default_nettype none
// Source-only local credit terminator candidate. Not a closed hard view.
// Fixed native flit encoding; no destination interpretation or arithmetic.
// Payload chunks are separate hardening units; no reset on payload.
module ot_vms_elastic_chunk #(parameter integer W=276,D=8,B=$clog2(D),SUBW=16)(
 input wire clk, input wire rst_n, input wire [W-1:0] din,
 input wire put, input wire putvc, input wire [B-1:0] wp,
 input wire take, input wire takevc, input wire [B-1:0] rp,
 output wire [W-1:0] dout);
 // Physical fanout repair (2026-10-13). Each <= SUBW-bit payload subslice owns kept, registered
 // ONE-HOT write-enable and read-select copies (2*D each) plus its take copy: every control flop
 // drives <= SUBW loads and the read path is one AND-OR plane. The old binary pointer copy drove
 // 4,416 loads per 276-bit chunk; a per-16-bit binary copy still left 128-256 loads on an x1 flop
 // (-145 ps before placement). Same registered function of the same inputs: latency unchanged.
 localparam integer NS=(W+SUBW-1)/SUBW, E=2*D;
 for(genvar s=0;s<NS;s=s+1) begin:g_sub
  localparam integer LO=s*SUBW, SW=(LO+SUBW>W)?(W-LO):SUBW;
  reg [SW-1:0] pin_d, delayed_d, dout_r;
  (* keep="true" *) reg [E-1:0] wen_r, rsel_r;
  (* keep="true" *) reg take_r;
`ifdef RING_SUB_MUT
  // Bench-only negative: one replicated read-select copy (last subslice) disagrees.
  wire [B-1:0] rp_x=(s==NS-1)?(rp^1'b1):rp;
`else
  wire [B-1:0] rp_x=rp;
`endif
  always @(posedge clk or negedge rst_n)
   if(!rst_n) begin wen_r<=0;rsel_r<=0;take_r<=0;end
   else begin
    take_r<=take;
    for(integer i=0;i<E;i=i+1) begin
     wen_r[i]<=put && (putvc==(i>=D)) && (wp==(i%D));
     rsel_r[i]<=take && (takevc==(i>=D)) && (rp_x==(i%D));
    end
   end
  reg [SW-1:0] mem [0:E-1];
  reg [SW-1:0] rd;
  always @* begin
   rd={SW{1'b0}};
   for(integer i=0;i<E;i=i+1) rd=rd|({SW{rsel_r[i]}} & mem[i]);
  end
  always @(posedge clk) begin
   pin_d<=din[LO+:SW];delayed_d<=pin_d;
   for(integer i=0;i<E;i=i+1) if(wen_r[i]) mem[i]<=delayed_d;
   if(take_r) dout_r<=rd;
  end
  assign dout[LO+:SW]=dout_r;
 end
endmodule
// Credit / pointer control of one station. The station instantiates one PRIMARY copy (drives the
// valid and returned-credit pins) and one identical copy per payload chunk on that chunk's regional
// clock, so no control net crosses a regional root or fans out over the whole 2,224-bit face.
// Every copy registers the same three boundary inputs and steps the same state: they are
// cycle-identical by construction; the exact payload bench fails if any copy diverges.
module ot_vms_elastic_ctl #(parameter integer D=8, MUT=0, B=$clog2(D))(
 input wire clk,input wire rst_n,
 input wire in_v,input wire in_vc,input wire [1:0] cr_in,
 output wire put,output wire putvc,output wire [B-1:0] writep,
 output wire take,output wire vc,output wire [B-1:0] readp,
 output reg out_v,output reg [1:0] cr_out);
 (* keep="true", dont_touch="true" *) reg pin_v,pin_vc;
 (* keep="true", dont_touch="true" *) reg [1:0] pin_cr;
 reg take_r;
 reg [B-1:0] head[0:1],tail[0:1];
 reg [B:0] count[0:1],credit[0:1];
 wire available0=(count[0]!=0 && credit[0]!=0);
 wire available1=(count[1]!=0 && credit[1]!=0);
 assign take=available0 || available1;
 assign vc=available1;
 assign readp=head[vc];
 assign writep=tail[pin_vc];
 assign put=pin_v;
 assign putvc=pin_vc;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   pin_v<=0;pin_vc<=0;out_v<=0;take_r<=0;pin_cr<=0;cr_out<=0;
   for(integer v=0;v<2;v=v+1) begin head[v]<=0;tail[v]<=0;count[v]<=0;credit[v]<=D;end
  end else begin
   pin_v<=in_v;pin_vc<=in_vc;pin_cr<=cr_in;take_r<=take;out_v<=take_r;
   cr_out<=take ? (MUT==2 ? (vc ? 2'b01:2'b10) : (vc ? 2'b10:2'b01)) : 2'b00;
   for(integer v=0;v<2;v=v+1) begin
    count[v]<=count[v]+(pin_v && pin_vc==v)-(take && vc==v);
    credit[v]<=credit[v]+pin_cr[v]-(take && vc==v);
    if(pin_v && pin_vc==v) tail[v]<=(tail[v]==D-1)?0:tail[v]+1'b1;
    if(take && vc==v) head[v]<=(head[v]==D-1)?0:head[v]+1'b1;
   end
  end
 end
endmodule
module ot_vms_elastic #(parameter integer D=8, MUT=0)(
 input wire [9:0] clk,input wire rst_n,
 input wire [2223:0] f_in,output wire [2223:0] f_out,
 input wire [1:0] cr_in,output wire [1:0] cr_out);
 localparam integer B=$clog2(D);
 ot_vms_elastic_ctl #(.D(D),.MUT(MUT)) u_ctl(.clk(clk[0]),.rst_n(rst_n),
  .in_v(f_in[2223]),.in_vc(f_in[2222]),.cr_in(cr_in),
  .put(),.putvc(),.writep(),.take(),.vc(),.readp(),.out_v(f_out[2223]),.cr_out(cr_out));
 for(genvar c=0;c<9;c=c+1) begin:g_chunk
  localparam integer LO=c*276, W=(c==8)?15:276;
  wire put,putvc,take,vc; wire [B-1:0] writep,readp;
  ot_vms_elastic_ctl #(.D(D),.MUT(0)) u_lctl(.clk(clk[c+1]),.rst_n(rst_n),
   .in_v(f_in[2223]),.in_vc(f_in[2222]),.cr_in(cr_in),
   .put(put),.putvc(putvc),.writep(writep),.take(take),.vc(vc),.readp(readp),.out_v(),.cr_out());
  ot_vms_elastic_chunk #(.W(W),.D(D)) u(.clk(clk[c+1]),.rst_n(rst_n),.din(f_in[LO+:W]),
   .put(put),.putvc(putvc),.wp(writep),.take(take),.takevc(vc),.rp(readp),.dout(f_out[LO+:W]));
 end
endmodule
`default_nettype wire
