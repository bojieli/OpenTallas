`default_nettype none
// Separate opt-in component. Canonical frontend is unchanged.
// Input admission promises target capacity THREE edges later; this is not ready/credit flow.
// All roots must have qualified common frequency/phase; this component is not an async CDC.
(* keep_hierarchy = "yes" *)
module ot_hbm_owner_link_first_reset(input wire clk,rst_n,output reg q);
 always @(posedge clk or negedge rst_n)if(!rst_n)q<=0;else q<=1;
endmodule

(* keep_hierarchy = "yes" *)
module ot_hbm_owner_link_slice #(parameter integer W=6)(
 input wire clk,first_rst_n,input wire [W-1:0] d,
 output reg [W-1:0] q,output wire [W-1:0] preview
);
 (* keep = "yes" *) reg reset_q;
 always @(posedge clk or negedge first_rst_n)
  if(!first_rst_n)reset_q<=0;else reset_q<=1;
 (* keep = "yes" *) reg [1:0] wp,rp;
 reg [W-1:0] slots[0:3];
 reg [W-1:0] input_q;
 always @(posedge clk)input_q<=d;
 always @(posedge clk or negedge reset_q)
  if(!reset_q)begin wp<=0;rp<=3;end
  else begin wp<=wp+1'b1;rp<=rp+1'b1;end
 // Data is deliberately unreset. Only qualified/reset-cleared valid exposes it.
 assign preview=slots[rp];
 always @(posedge clk)begin slots[wp]<=input_q;q<=slots[rp];end
endmodule

(* keep_hierarchy = "yes" *)
module ot_hbm_owner_pair_link #(parameter integer J=0,MUT=0)(
 input wire clk,rst_n,in_v,stop,input wire [284:0] in_packet,
 input wire in_target,input wire [1:0] target_reserved,
 output wire [284:0] out_packet,output wire out_target,
 output reg out_v,output reg fault
);
 // Exactly two release edges, with raw reset driving only two first-stage FFs.
 wire [1:0] first_rst;
 for(genvar b=0;b<2;b=b+1)begin:g_first_reset
  ot_hbm_owner_link_first_reset u_first(.clk(clk),.rst_n(rst_n),.q(first_rst[b]));
 end
 wire [287:0] incoming={target_reserved,in_target,in_packet};
 wire [287:0] outgoing,selected;
 for(genvar k=0;k<48;k=k+1)begin:g_slice
  ot_hbm_owner_link_slice #(.W(6)) u_slice(
   .clk(clk),.first_rst_n(first_rst[k/24]),.d(incoming[6*k+:6]),.q(outgoing[6*k+:6]),.preview(selected[6*k+:6]));
 end
 (* keep = "yes" *) reg ctrl_rst;
 always @(posedge clk or negedge first_rst[0])
  if(!first_rst[0])ctrl_rst<=0;else ctrl_rst<=1;
 reg [1:0] wp,rp;reg [3:0] valid;reg input_valid_q,stop_q;
 // This duplicate narrow ring follows the exact data slice phase.
 // Validate the selected ring word BEFORE its output FF edge, never external inputs.
 wire lane_ok=selected[275:274]==2'(J); // ordinal is packet[284:274]
 wire target_ok=selected[285]==selected[276];
 wire reserved_ok=selected[286+selected[285]];
 assign out_packet=outgoing[284:0];
 assign out_target=(MUT==2)?~outgoing[285]:outgoing[285];
 always @(posedge clk or negedge ctrl_rst)
  if(!ctrl_rst)begin wp<=0;rp<=3;valid<=0;input_valid_q<=0;stop_q<=0;out_v<=0;fault<=0;end
  else begin
   wp<=wp+1'b1;rp<=rp+1'b1;
   input_valid_q<=in_v;stop_q<=stop;valid[wp]<=input_valid_q;
   out_v<=valid[rp]&&(lane_ok||MUT==1)&&(target_ok||MUT==3)&&reserved_ok&&!fault&&!stop_q;
   if(valid[rp]&&(!lane_ok||!target_ok||!reserved_ok))fault<=1;
   if(MUT==4)out_v<=valid[wp];
  end
endmodule

module ot_hbm_svc_four_owner_links #(parameter integer MUT=0)(
 input wire [3:0] clk,input wire rst_n,
 input wire [3:0] in_v,input wire [1139:0] in_packet,
 input wire [3:0] in_target,input wire [7:0] target_reserved,
 output wire [3:0] out_v,out_target,fault,output wire [1139:0] out_packet
);
 for(genvar j=0;j<4;j=j+1)begin:g_link
  ot_hbm_owner_pair_link #(.J(j),.MUT(MUT)) u_link(
   .clk(clk[j]),.rst_n(rst_n),.in_v(in_v[j]),.stop(1'b0),.in_packet(in_packet[285*j+:285]),
   .in_target(in_target[j]),.target_reserved(target_reserved[2*j+:2]),
   .out_v(out_v[j]),.out_target(out_target[j]),.fault(fault[j]),.out_packet(out_packet[285*j+:285]));
 end
endmodule
`default_nettype wire
