`timescale 1ns/1ps
// Verification state only; this module never drives the design.
module kva_authority_path #(parameter integer DEPTH=1, ID=0)(
 input wire clk, source_rst_n, source_valid, source_alias,
 input wire [DEPTH-1:0] hop_q,
 output wire known, output wire [31:0] errors
);
 reg source_known=0;
 reg [DEPTH-1:0] knowledge='0, expected='0;
 reg sampled=0;
 integer async_errors=0, capture_errors=0;
 assign known=knowledge[DEPTH-1];
 assign errors=async_errors+capture_errors;
 initial if(DEPTH<1) $fatal(1,"AUTHORITY_FAIL unsupported depth");
 // An async assertion initializes the source after NBA, before a later edge.
 // A reset first asserted on an edge cannot initialize old D at that edge.
 always @(posedge clk or negedge source_rst_n)
   if(source_rst_n === 1'b0) source_known <= 1'b1;
 always @(negedge source_rst_n) begin
   #0.001;
   if(source_valid !== 1'b0) begin
     async_errors=async_errors+1;
     $display("AUTHORITY_FAIL id=%0d asynchronous source reset did not clear qualifier",ID);
   end
 end
 always @(posedge clk) begin
   knowledge[0] <= source_known;
   expected[0] <= source_alias;
   for(integer j=1;j<DEPTH;j=j+1) begin
     knowledge[j] <= knowledge[j-1];
     expected[j] <= hop_q[j-1];
   end
   sampled<=1;
 end
 // Consumer samples at negedge, after all design and tag NBA updates.
 // Knowledge is monotonic: repeated reset never opens another blind window.
 always @(negedge clk) begin
   if(source_valid !== source_alias) begin
     capture_errors=capture_errors+1;
     $display("AUTHORITY_FAIL id=%0d source alias",ID);
   end
   if(source_rst_n === 1'b0 && source_valid !== 1'b0) begin
     capture_errors=capture_errors+1;
     $display("AUTHORITY_FAIL id=%0d sampled source reset",ID);
   end
   if(sampled) for(integer j=0;j<DEPTH;j=j+1) begin
     if(hop_q[j] !== expected[j]) begin
       capture_errors=capture_errors+1;
       $display("AUTHORITY_FAIL id=%0d hop=%0d old-D capture",ID,j);
     end
     if(knowledge[j] && $isunknown(hop_q[j])) begin
       capture_errors=capture_errors+1;
       $display("AUTHORITY_FAIL id=%0d hop=%0d unknown authoritative qualifier",ID,j);
     end
   end
 end
endmodule
