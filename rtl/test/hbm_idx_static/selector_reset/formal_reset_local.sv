module formal_reset_local(input wire clk,input wire rn);
 reg d1,d2;wire w,e;
 `ifdef RESET_MUTANT
 localparam integer MUT=1;
 `else
 localparam integer MUT=0;
 `endif
 ot_hbm_idx_selector_reset_local #(.MUT(MUT)) dut(.clk(clk),.rst_i_n(rn),.rst_w_n(w),.rst_e_n(e));
 always @(posedge clk)begin d1<=rn;d2<=d1;end
 always @*begin assert(w==d2);assert(e==d2);end
endmodule
