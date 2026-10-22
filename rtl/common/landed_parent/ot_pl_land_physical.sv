`timescale 1ns/1ps
// Explicit physical landing storage. Epoch diagnostics are absent from this
// interface; generic ot_pl_land_* simulation/default interfaces stay unchanged.
module ot_pl_land_phys_chunk_w #(parameter integer W=24,D=4,CHUNK_BITS=24)(
 input wire ck,rsi,input wire[W-1:0] i,output wire[D*W-1:0] bank,
 output wire[D*((W+CHUNK_BITS-1)/CHUNK_BITS)-1:0] vld);
 localparam integer C=(W+CHUNK_BITS-1)/CHUNK_BITS;
 generate if(W<1||CHUNK_BITS<1||CHUNK_BITS>24||(D!=2&&D!=4&&D!=8))begin:g_bad
 ot_pl_land_physical_requires_D2_4_8_chunks1_to24 u_fail();
 end
 for(genvar c=0;c<C;c=c+1)begin:g_chunk
  localparam integer CW=(W-c*CHUNK_BITS<CHUNK_BITS)?W-c*CHUNK_BITS:CHUNK_BITS;
  wire[D*CW-1:0] cb;wire[D-1:0] cv;
  (* keep_hierarchy="yes" *) ot_pl_land_phys_local_w #(.W(CW),.D(D),.ID(c)) u_local(.ck(ck),.rsi(rsi),.i(i[c*CHUNK_BITS+:CW]),.bank(cb),.vld(cv));
  for(genvar s=0;s<D;s=s+1)begin:g_slot assign bank[s*W+c*CHUNK_BITS+:CW]=cb[s*CW+:CW];end
  assign vld[c*D+:D]=cv;
 end endgenerate
endmodule
module ot_pl_land_phys_chunk_r #(parameter integer W=24,D=4,K=2,CHUNK_BITS=24,ID=0)(
 input wire ck,rsi,input wire[D*W-1:0] bank,
 input wire[D*((W+CHUNK_BITS-1)/CHUNK_BITS)-1:0] vld,output wire[W-1:0] o);
 localparam integer C=(W+CHUNK_BITS-1)/CHUNK_BITS;
 generate if(W<1||CHUNK_BITS<1||CHUNK_BITS>24||(D!=2&&D!=4&&D!=8)||K<1||K>=D)begin:g_bad
 ot_pl_land_physical_requires_valid_K_and_D u_fail();
 end
 for(genvar c=0;c<C;c=c+1)begin:g_chunk
  localparam integer CW=(W-c*CHUNK_BITS<CHUNK_BITS)?W-c*CHUNK_BITS:CHUNK_BITS;
  wire[D*CW-1:0] cb;
  for(genvar s=0;s<D;s=s+1)begin:g_slot assign cb[s*CW+:CW]=bank[s*W+c*CHUNK_BITS+:CW];end
  (* keep_hierarchy="yes" *) ot_pl_land_phys_local_r #(.W(CW),.D(D),.K(K),.ID(ID*1024+c)) u_local(.ck(ck),.rsi(rsi),.bank(cb),.vld(vld[c*D+:D]),.o(o[c*CHUNK_BITS+:CW]));
 end endgenerate
endmodule
module ot_pl_land_phys_local_w #(parameter integer W=24,D=4,ID=0)(
 input wire ck,rsi,input wire[W-1:0] i,output wire[D*W-1:0] bank,output wire[D-1:0] vld);
 reg rq;(* keep *) reg[D-1:0] write_oh;reg[D-1:0] valid;reg[W-1:0] data[0:D-1];
 always@(posedge ck)rq<=rsi;
 always@(posedge ck)if(!rq)begin write_oh<={{(D-1){1'b0}},1'b1};valid<=0;end
 else begin write_oh<={write_oh[D-2:0],write_oh[D-1]};valid<=valid|write_oh;end
 for(genvar s=0;s<D;s=s+1)begin:g_slot
  always@(posedge ck)if(rq&&write_oh[s])data[s]<=i;
  assign bank[s*W+:W]=data[s];
 end
 assign vld=valid;
endmodule
module ot_pl_land_phys_local_r #(parameter integer W=24,D=4,K=2,ID=0,AW=(D<=2)?1:$clog2(D))(
 input wire ck,rsi,input wire[D*W-1:0] bank,input wire[D-1:0] vld,output reg[W-1:0] o);
 reg rq,warm;reg[AW:0] rc;(* keep *)reg[D-1:0] read_oh;
 reg[W-1:0] selected;reg selected_valid;integer s;
 always@*begin selected=0;selected_valid=0;for(integer j=0;j<D;j=j+1)begin
 selected=selected|(bank[j*W+:W]&{W{read_oh[j]}});selected_valid=selected_valid|(vld[j]&read_oh[j]);end end
 always@(posedge ck)rq<=rsi;
 always@(posedge ck)if(!rq)begin rc<=0;warm<=0;for(s=0;s<D;s=s+1)read_oh[s]<=(s==((D-K)%D));end
 else begin rc<=rc+1'b1;if(rc==K-1)warm<=1;read_oh<={read_oh[D-2:0],read_oh[D-1]};end
 always@(posedge ck)o<=(warm&&selected_valid)?selected:{W{1'b0}};
endmodule
