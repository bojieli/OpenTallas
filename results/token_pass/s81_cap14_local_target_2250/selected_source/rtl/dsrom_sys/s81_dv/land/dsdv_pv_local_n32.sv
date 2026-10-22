`timescale 1ns/1ps
`default_nettype none
// Selected SO local profile only: D32, K17. Independent groups own selectors;
// no dynamic root broadcasts a bank enable or read address across the word.
(* keep_hierarchy="yes" *)
module dsdv_pv_local_phase #(parameter integer ID=0)(input wire ck,rs,advance,output reg q);
 always @(posedge ck or negedge rs) if(!rs)q<=0;else if(advance)q<=~q;
endmodule

(* keep_hierarchy="yes" *)
module dsdv_pv_local_group #(parameter integer W=4, ID=0)(
 input wire ck_f,ck,input wire[3:0] rs,input wire[W-1:0] i,
 output reg[W-1:0] o,output reg fault);
 (* keep *) reg[31:0] write_oh,read_oh;
 reg[W-1:0] bank[0:31];reg[31:0] epoch_hi;
 reg[5:0] rc;reg warm;wire[1:0] phase;
 dsdv_pv_local_phase #(.ID(2*ID)) p0(.ck(ck_f),.rs(rs[3]),.advance(write_oh[31]),.q(phase[0]));
 dsdv_pv_local_phase #(.ID(2*ID+1)) p1(.ck(ck_f),.rs(rs[3]),.advance(write_oh[31]),.q(phase[1]));
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

// Two real internal reset distribution edges are additional to kit reset2.
// All leaf releases have identical age. The selected clock book must start
// the forwarded epoch only after this release, and book the actual R0/G.
module dsdv_pv_local_land_n32_276(
 input wire ck_f,input wire[275:0] i,input wire ck,rs,input wire[5:0] k,
 output wire[275:0] o,output wire fault);
 localparam integer GROUPS=69;
 wire[4*GROUPS-1:0] rst_leaf;wire[GROUPS-1:0] gf;
 ot_pl_land_reset_forest #(.DEPTH(2),.LEAVES(4*GROUPS),.ROOT_LOADS(1)) rf(
  .ck(ck),.d(rs),.q(rst_leaf));
 for(genvar g=0;g<GROUPS;g=g+1)begin:g_group
  dsdv_pv_local_group #(.W(4),.ID(g)) u_group(
   .ck_f(ck_f),.ck(ck),.rs(rst_leaf[4*g+:4]),.i(i[4*g+:4]),.o(o[4*g+:4]),.fault(gf[g]));
 end
 reg strap_fault;
 always @(posedge ck or negedge rs)if(!rs)strap_fault<=0;else if(k!=6'd17)strap_fault<=1;
 assign fault=(|gf)|strap_fault;
endmodule
`default_nettype wire
