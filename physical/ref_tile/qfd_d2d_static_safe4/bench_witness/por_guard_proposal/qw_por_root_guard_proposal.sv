// Review-only root-POR guard: not connected to any production kit.
// Requires a qualified physical POR assertion; FLUSH is source/native certified.
module qw_por_root_guard_proposal #(
 parameter integer FLUSH=31,
 parameter integer MUT_EARLY=0,
 localparam integer CW=(FLUSH>1)?$clog2(FLUSH):1
)(input wire ck,input wire por_n,output reg armed,output wire guarded_rst_n);
 reg [CW-1:0] count;
 always @(posedge ck or negedge por_n) begin
  if (!por_n) begin count<='0;armed<=1'b0;end
  else if (!armed) begin
   if (count == CW'(FLUSH-1-(MUT_EARLY!=0))) armed<=1'b1;
   else count<=count+1'b1;
  end
 end
 assign guarded_rst_n=por_n & armed;
`ifndef SYNTHESIS
 initial if(FLUSH<2) $fatal(1,"FLUSH requires a certified bound >=2");
`endif
endmodule
