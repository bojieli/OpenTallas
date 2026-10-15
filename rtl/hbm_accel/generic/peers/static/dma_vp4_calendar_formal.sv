// For all 2^64 captured-cycle/target pairs, including wrap. The one
// arbitrary target covers issue, drain, prefetch, fill and end deadlines.
module dma_vp4_calendar_formal(input [31:0] cycle_q,target,input en,output ok);
wire [31:0] cycle=cycle_q+32'd1;
wire [31:0] pre=target-32'd1;
wire [31:0] next_step=target+32'(en),pre_step=pre+32'(en);
wire [31:0] old_lead=target-cycle,new_lead=pre-cycle_q;
assign ok=((cycle==target)==(cycle_q==pre)) &&
 (pre_step+32'd1==next_step) && (old_lead==new_lead) &&
 (($signed(old_lead)>=1)==($signed(new_lead)>=1));
endmodule
