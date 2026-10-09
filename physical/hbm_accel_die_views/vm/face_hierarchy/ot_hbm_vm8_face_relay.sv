`timescale 1ps/1fs
// Fixed full128-bit hardened elements. No reset or ready semantics are added:
// these are the existing unconditional face captures, partitioned physically.
(* keep_hierarchy = "yes" *)
module ot_hbm_vm8_face_relay_d1(input wire clk,input wire [127:0] d,output reg [127:0] q);
 always @(posedge clk)q<=d;
endmodule

(* keep_hierarchy = "yes" *)
module ot_hbm_vm8_face_relay_d3(input wire clk,input wire [127:0] d,output reg [127:0] q);
 reg [127:0] s0,s1;
 always @(posedge clk)begin s0<=d;s1<=s0;q<=s1;end
endmodule

// Static slicing only. Tail padding remains part of the full128-bit physical
// element, so the inventory prices it rather than presenting a smaller pilot.
module ot_hbm_vm8_face_bus #(parameter integer W=128,D=1)(
 input wire clk,input wire [W-1:0] d,output wire [W-1:0] q
);
 localparam integer NB=(W+127)/128;
 wire [NB*128-1:0] padded_d={{(NB*128-W){1'b0}},d};
 wire [NB*128-1:0] padded_q;
 initial if(D!=1&&D!=3)$fatal(1,"actual face hierarchy supports D1 or D3");
 for(genvar n=0;n<NB;n=n+1)begin:bank
  if(D==1)begin:input_capture
   ot_hbm_vm8_face_relay_d1 u(.clk(clk),.d(padded_d[n*128+:128]),.q(padded_q[n*128+:128]));
  end else begin:output_launch
   ot_hbm_vm8_face_relay_d3 u(.clk(clk),.d(padded_d[n*128+:128]),.q(padded_q[n*128+:128]));
  end
 end
 assign q=padded_q[W-1:0];
endmodule
