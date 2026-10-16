`timescale 1ns/1ps
// Source-native fixed fused PC11 command producer. HOST owns epoch/token/position/
// stage: this module neither allocates nor infers them. Compiler calendar loading
// is a separate required programme input of the static controller. Outputs are
// registered; controller load must be descriptor_valid (one edge after issue).
module qkd_native59_descriptor_producer(
 input wire ck,rst_n,issue,authority_valid,
 input wire [15:0] authority_epoch,
 input wire [17:0] authority_token,authority_position,
 input wire [5:0] authority_stage,
 output reg descriptor_valid,output reg [379:0] descriptor,
 output reg [58:0] tag,output reg fault
);
 localparam [379:0] NATIVE59={24'd0,1'b0,1'b0,1'b1,1'b1,
 24'd1,24'd1,24'd3167,1'b0,24'd0,4'd0,3'd0,
 24'd0,24'd0,24'd1,24'd13696,24'd0,24'd0,24'd0,24'd0,
 1'b1,18'd128,18'd1,18'd512,1'b1};
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin descriptor_valid<=0;descriptor<=0;tag<=0;fault<=0;end
  else begin
   descriptor_valid<=0;
   if(issue&&!fault)begin
    if(!authority_valid||authority_token>=151936||authority_position>=8192||authority_stage<1||authority_stage>36)fault<=1;
    else begin
     descriptor_valid<=1;descriptor<=NATIVE59;
     tag<={authority_epoch,authority_stage,authority_token,authority_position[12:0],6'd0};
    end
   end
  end
 end
endmodule
