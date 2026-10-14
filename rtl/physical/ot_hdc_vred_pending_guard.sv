// Control-body fence for a regional reducer whose tail busy starts after its regional pipeline.
// Counts accepted completed segments until their real output writes; ready/chaining policy remains upstream.
module ot_hdc_vred_pending_guard #(parameter integer CW=19)(
 input wire clk,rst_n,input wire vector_v,vector_last,output_v,tail_busy,
 output wire busy,output reg fault
);
 reg[CW-1:0] pending;
 wire begin_segment=vector_v&&vector_last;
 assign busy=vector_v||tail_busy||(pending!=0);
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin pending<=0;fault<=0;end
  else begin
   if(output_v&&pending==0)fault<=1;
   case({begin_segment,output_v})
    2'b10:begin if(&pending)fault<=1;pending<=pending+1'b1;end
    2'b01:if(pending!=0)pending<=pending-1'b1;
    default:begin end
   endcase
  end
 end
endmodule
