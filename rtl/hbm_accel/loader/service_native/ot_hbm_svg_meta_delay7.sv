`default_nettype none
// Fixed seven-capture metadata alignment. Eight actual indexed slots, not a
// seven-register shift chain. W=35 stores280bits, plus35 output flops.
(* keep_hierarchy="yes" *) module ot_hbm_svg_meta_delay7 #(parameter integer W=35,MUT=0)(
 input wire clk,rst_n,input wire[W-1:0]data_in,output wire[W-1:0]data_out);
 genvar s;generate for(s=0;s<(W+15)/16;s=s+1)begin:g_slice
  localparam integer B=(W-s*16>=16)?16:W-s*16;
  reg[B-1:0]slots[0:7];reg[B-1:0]q;
  (* keep="true" *) reg[2:0]wp,rp,warm;
  always @(posedge clk or negedge rst_n)
   if(!rst_n)begin wp<=0;rp<=2;warm<=0;q<=0;end
   else begin
    slots[wp]<=data_in[s*16+:B];wp<=wp+1'b1;rp<=rp+1'b1;
    if(warm!=7)warm<=warm+1'b1;
    q<=warm>=6?slots[rp+(MUT!=0?3'd1:3'd0)]:{B{1'b0}};
   end
  assign data_out[s*16+:B]=q;
 end endgenerate
endmodule
`default_nettype wire
