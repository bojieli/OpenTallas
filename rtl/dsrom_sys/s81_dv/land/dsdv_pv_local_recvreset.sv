`timescale 1ns/1ps
`default_nettype none
// Selected SO local profile only: D32, K17. Independent groups own selectors;
// no dynamic root broadcasts a bank enable or read address across the word.
(* keep_hierarchy="yes" *)
module dsdv_pv_local_rr_phase #(parameter integer ID=0)(input wire ck,rs,advance,output reg q);
 always @(posedge ck or negedge rs) if(!rs)q<=0;else if(advance)q<=~q;
endmodule

(* keep_hierarchy="yes" *)
module dsdv_pv_local_rr_group #(parameter integer W=4, ID=0)(
 input wire ck_f,ck,input wire[3:0] rs,input wire[W-1:0] i,
 output reg[W-1:0] o,output reg fault);
 (* keep *) reg[31:0] write_oh,read_oh;
 reg[W-1:0] bank[0:31];reg[31:0] epoch_hi;
 reg[5:0] rc;reg warm;wire[1:0] phase;
 dsdv_pv_local_rr_phase #(.ID(2*ID)) p0(.ck(ck_f),.rs(rs[3]),.advance(write_oh[31]),.q(phase[0]));
 dsdv_pv_local_rr_phase #(.ID(2*ID+1)) p1(.ck(ck_f),.rs(rs[3]),.advance(write_oh[31]),.q(phase[1]));
 always @(posedge ck_f or negedge rs[0])
  if(!rs[0])write_oh<=32'b1;else write_oh<={write_oh[30:0],write_oh[31]};
 always @(posedge ck or negedge rs[1])
  if(!rs[1])read_oh<=32'h00008000;else read_oh<={read_oh[30:0],read_oh[31]};
 for(genvar s=0;s<32;s=s+1)begin:g_slot
  always @(posedge ck_f)if(write_oh[s])begin bank[s]<=i;epoch_hi[s]<=phase[s/16];end
 end
 reg[W-1:0] selected;reg selected_epoch;
 integer s;
 always @*begin
  selected=0;selected_epoch=0;
  for(integer j=0;j<32;j=j+1)begin
   selected=selected | (bank[j]&{W{read_oh[j]}});
   selected_epoch=selected_epoch | (epoch_hi[j]&read_oh[j]);
  end
 end
 wire[5:0] expected=rc-6'd17;
 always @(posedge ck or negedge rs[2])
  if(!rs[2])begin rc<=0;warm<=0;fault<=0;end
  else begin
   rc<=rc+1'b1;if(rc==6'd16)warm<=1;
   if(warm && selected_epoch!=expected[5])fault<=1;
  end
 always @(posedge ck)o<=warm?selected:{W{1'b0}};
endmodule

// EXPERIMENTAL, UNSELECTED: receiving-clock reset ownership. Writer reset
// releases only after two real ck_f edges, reader after four ck edges. The
// required forwarded preamble and pointer/calendar alignment are unqualified.
module dsdv_pv_local_land_recvreset_276(
 input wire ck_f,input wire[275:0] i,input wire ck,rs,input wire[5:0] k,
 output wire[275:0] o,output wire fault);
 localparam integer GROUPS=69;
 wire[4*GROUPS-1:0] rst_leaf;wire[GROUPS-1:0] gf;
 wire[2*GROUPS-1:0] wr_reset,rd_reset;
 // Clock-gated writer requires asynchronous assertion, then two actual
 // forwarded-clock release edges. These edges need a booked preamble.
 dsdv_pv_local_recvreset #(.LEAVES(2*GROUPS)) wr_rf(
  .ck(ck_f),.rs(rs),.q(wr_reset));
 ot_pl_land_reset_forest #(.DEPTH(4),.LEAVES(2*GROUPS),.ROOT_LOADS(1)) rd_rf(
  .ck(ck),.d(rs),.q(rd_reset));
 for(genvar r=0;r<GROUPS;r=r+1)begin:g_reset_map
  assign rst_leaf[4*r+0]=wr_reset[2*r];
  assign rst_leaf[4*r+3]=wr_reset[2*r+1];
  assign rst_leaf[4*r+1]=rd_reset[2*r];
  assign rst_leaf[4*r+2]=rd_reset[2*r+1];
 end
 for(genvar g=0;g<GROUPS;g=g+1)begin:g_group
  dsdv_pv_local_rr_group #(.W(4),.ID(g)) u_group(
   .ck_f(ck_f),.ck(ck),.rs(rst_leaf[4*g+:4]),.i(i[4*g+:4]),.o(o[4*g+:4]),.fault(gf[g]));
 end
 reg strap_fault;
 always @(posedge ck or negedge rs)if(!rs)strap_fault<=0;else if(k!=6'd17)strap_fault<=1;
 assign fault=(|gf)|strap_fault;
endmodule

(* keep_hierarchy="yes" *)
module dsdv_pv_local_async_release_bit #(parameter integer ID=0)(
 input wire ck,rs,output reg q);
 always @(posedge ck or negedge rs)if(!rs)q<=0;else q<=1;
endmodule

(* keep_hierarchy="yes" *)
module dsdv_pv_local_recvreset #(parameter integer LEAVES=138)(
 input wire ck,rs,output wire[LEAVES-1:0] q);
 localparam integer BRANCHES=(LEAVES+27)/28;
 for(genvar b=0;b<BRANCHES;b=b+1)begin:g_branch
  wire branch;
  dsdv_pv_local_async_release_bit #(.ID(b)) root(.ck(ck),.rs(rs),.q(branch));
  for(genvar j=0;j<28;j=j+1)begin:g_leaf
   if(28*b+j<LEAVES)begin:g_used
    dsdv_pv_local_async_release_bit #(.ID(1024+28*b+j)) leaf(
     .ck(ck),.rs(branch),.q(q[28*b+j]));
   end
  end
 end
endmodule
`default_nettype wire
