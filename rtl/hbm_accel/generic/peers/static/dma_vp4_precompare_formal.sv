module dma_vp4_precompare_formal(input [31:0] cycle_q,next_drain,input en,output ok);
wire [31:0] cycle=cycle_q+32'd1;
wire [31:0] pre=next_drain-32'd1;
wire [31:0] next_step=next_drain+32'(en);
wire [31:0] pre_step=pre+32'(en);
assign ok=((cycle==next_drain)==(cycle_q==pre)) && (pre_step+32'd1==next_step);
endmodule
