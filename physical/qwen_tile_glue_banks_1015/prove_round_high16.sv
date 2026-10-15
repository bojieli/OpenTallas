module prove_round_high16(input wire[31:0]x,output wire exact);
 wire[31:0]old=x+32'h7fff+{31'b0,x[16]};wire[15:0]compact;
 ot_qwen_bf16_round_high16 dut(.x(x),.y(compact));
 assign exact=compact==old[31:16];
endmodule
