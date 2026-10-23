`timescale 1ns/1ps
`default_nettype none
// Selected SO local profile only: D32, K17. Independent groups own selectors;
// no dynamic root broadcasts a bank enable or read address across the word.
// Alternate folds epoch phase into a 64-state one-hot selector; data storage
// remains exactly 32 slots, with unchanged active age18 and reset4.
(* keep_hierarchy="yes" *)
module dsdv_pv_local_alt_group #(parameter integer W=4, ID=0)(
 input wire ck_f,ck,input wire[3:0] rs,input wire[W-1:0] i,
 output reg[W-1:0] o,output reg fault);
 (* keep *) reg[63:0] write_oh;
 (* keep *) reg[31:0] read_oh;
 reg[W-1:0] bank[0:31];reg[31:0] epoch_hi;
 reg[5:0] rc;reg warm;
 // The writer's two rotations encode both slot and epoch phase directly.
 // Each 32-bit reset leaf has the same real source release age.
 always @(posedge ck_f or negedge rs[0])
  if(!rs[0])write_oh[31:0]<=32'b1;
  else write_oh[31:0]<={write_oh[30:0],write_oh[63]};
 always @(posedge ck_f or negedge rs[3])
  if(!rs[3])write_oh[63:32]<=0;
  else write_oh[63:32]<={write_oh[62:32],write_oh[31]};
 always @(posedge ck or negedge rs[1])
  if(!rs[1])read_oh<=32'h00008000;else read_oh<={read_oh[30:0],read_oh[31]};
 for(genvar s=0;s<32;s=s+1)begin:g_slot
  always @(posedge ck_f)if(write_oh[s]||write_oh[s+32])begin bank[s]<=i;epoch_hi[s]<=write_oh[s+32];end
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
module dsdv_pv_local_land_n32alt_276(
 input wire ck_f,input wire[275:0] i,input wire ck,rs,input wire[5:0] k,
 output wire[275:0] o,output wire fault);
 localparam integer GROUPS=69;
 wire[4*GROUPS-1:0] rst_leaf;wire[GROUPS-1:0] gf;
 ot_pl_land_reset_forest #(.DEPTH(2),.LEAVES(4*GROUPS),.ROOT_LOADS(1)) rf(
  .ck(ck),.d(rs),.q(rst_leaf));
 for(genvar g=0;g<GROUPS;g=g+1)begin:g_group
  dsdv_pv_local_alt_group #(.W(4),.ID(g)) u_group(
   .ck_f(ck_f),.ck(ck),.rs(rst_leaf[4*g+:4]),.i(i[4*g+:4]),.o(o[4*g+:4]),.fault(gf[g]));
 end
 reg strap_fault;
 always @(posedge ck or negedge rs)if(!rs)strap_fault<=0;else if(k!=6'd17)strap_fault<=1;
 assign fault=(|gf)|strap_fault;
endmodule
`default_nettype wire
