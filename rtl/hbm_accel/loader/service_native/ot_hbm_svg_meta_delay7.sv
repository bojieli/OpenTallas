`default_nettype none
// Fixed seven/eight-capture metadata alignment using eight indexed slots.
// W=35 stores280 runtime bits,35 output bits,54 local pointer/counter bits.
// DELAY7 preserves the original byte/cycle contract; DELAY8 adds one capture.
(* keep_hierarchy="yes" *) module ot_hbm_svg_meta_delay7 #(parameter integer W=35,MUT=0,DELAY=7)(
 input wire clk,rst_n,input wire[W-1:0]data_in,output wire[W-1:0]data_out);
 initial begin if(DELAY!=7&&DELAY!=8)$fatal(1,"META_DELAY must be7 or8");end
 genvar s;generate for(s=0;s<(W+5)/6;s=s+1)begin:g_slice
  localparam integer B=(W-s*6>=6)?6:W-s*6;
  ot_hbm_svg_meta_delay7_slice #(.B(B),.MUT(MUT),.DELAY(DELAY)) u_slice(
   .clk(clk),.rst_n(rst_n),.d(data_in[s*6+:B]),.q(data_out[s*6+:B]));
 end endgenerate
endmodule
// Keep each actual pointer copy through ABC; flatten only after mapping,
// without opt_merge. A BUF or an alias does not replicate pointer state.
(* keep_hierarchy="yes" *) module ot_hbm_svg_meta_delay7_slice #(
 parameter integer B=6,MUT=0,DELAY=7)(
 input wire clk,rst_n,input wire[B-1:0]d,output reg[B-1:0]q);
 reg[B-1:0]slots[0:7];
 (* keep="true" *) reg[2:0]wp,rp,warm;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin wp<=0;rp<=3'(9-DELAY);warm<=0;q<=0;end
  else begin
   slots[wp]<=d;wp<=wp+1'b1;rp<=rp+1'b1;
   if(warm!=7)warm<=warm+1'b1;
   q<=warm>=DELAY-1?slots[rp+(MUT!=0?3'd1:3'd0)]:{B{1'b0}};
  end
endmodule
`default_nettype wire
