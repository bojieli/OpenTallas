// Isolated full-width candidate. Every hardened stage has its own clock pin.
module s81_area_benes_stage #(parameter W=16, DIST=1)(
 input wire ck, input wire [128*W-1:0] i_data,
 input wire [63:0] i_sw, output reg [128*W-1:0] o_data
);
 reg [128*W-1:0] pin_data;
 reg [63:0] pin_sw;
 always @(posedge ck) begin
   pin_data <= i_data;
   pin_sw <= i_sw;
 end
 genvar j;
 generate for(j=0;j<64;j=j+1) begin: sw
   localparam A=(j/DIST)*2*DIST+j%DIST;
   localparam B=A+DIST;
   always @(posedge ck) begin
     o_data[A*W+:W] <= pin_sw[j] ? pin_data[B*W+:W] : pin_data[A*W+:W];
     o_data[B*W+:W] <= pin_sw[j] ? pin_data[A*W+:W] : pin_data[B*W+:W];
   end
 end endgenerate
endmodule

module s81_area_benes_rail #(parameter W=16)(
 input wire [12:0] ck_stage, input wire [128*W-1:0] i_data,
 input wire [831:0] i_stage_sw, output wire [128*W-1:0] o_data
);
 wire [128*W-1:0] data [0:13];
 assign data[0]=i_data;
 assign o_data=data[13];
 genvar s;
 generate for(s=0;s<13;s=s+1) begin: stage
   localparam DIST=(s<=6) ? (1<<s) : (1<<(12-s));
   s81_area_benes_stage #(.W(W),.DIST(DIST)) u_stage(
     .ck(ck_stage[s]), .i_data(data[s]),
     .i_sw(i_stage_sw[s*64+:64]), .o_data(data[s+1]));
 end endgenerate
endmodule
