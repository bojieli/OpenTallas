// QW-SRAM3 10-19: the kit binding shim (old master name -> <name>_p192_mir) is cycle-exact against the
// original master behaviour model. REF is the original .v renamed by run.sh; DUT is the shim + p192 .v.
`ifndef W
`define W 512
`endif
`ifndef AW
`define AW 6
`endif
module tb;
  reg clk=0; always #1 clk=~clk;
  reg r_ce,w_ce; reg [`AW-1:0] ra,wa; reg [`W-1:0] wd,wm;
  wire [`W-1:0] q_ref,q_dut;
  wire [`W-1:0] wm_dut = wm
`ifdef MUT
    & ~{{(`W-1){1'b0}},1'b1}
`endif
  ;
  `REF u_ref(.clk(clk),.r_ce_in(r_ce),.r_addr_in(ra),.rd_out(q_ref),.w_ce_in(w_ce),.w_addr_in(wa),.wd_in(wd),.w_mask_in(wm),
             .rr_en(2'b0),.rr_addr('0),.cr_en(2'b0),.cr_sel('0));
  `DUT u_dut(.clk(clk),.r_ce_in(r_ce),.r_addr_in(ra),.rd_out(q_dut),.w_ce_in(w_ce),.w_addr_in(wa),.wd_in(wd),.w_mask_in(wm_dut),
             .rr_en(2'b0),.rr_addr('0),.cr_en(2'b0),.cr_sel('0));
  integer i,k,checks=0,errs=0;
  function [`W-1:0] rnd; integer j; begin for(j=0;j<`W;j=j+32) rnd[j+:32]=$urandom; end endfunction
  initial begin
    r_ce=0;w_ce=0;ra=0;wa=0;wd=0;wm=0;
    for(i=0;i<(1<<`AW);i=i+1) begin @(negedge clk); w_ce=1; wa=i; wd=rnd(); wm={`W{1'b1}}; end
    @(negedge clk); w_ce=0;
    for(k=0;k<4000;k=k+1) begin
      @(negedge clk);
      if(k>2 && (q_ref!==q_dut)) begin errs=errs+1; if(errs<5) $display("P192_MISMATCH k=%0d",k); end
      checks=checks+1;
      r_ce=$urandom%4!=0; ra=$urandom; w_ce=$urandom%2; wa=$urandom; wd=rnd(); wm=rnd();
    end
    if(errs==0) $display("P192_EQUIV_PASS checks=%0d",checks); else begin $display("P192_EQUIV_FAIL errs=%0d",errs); $fatal(1); end
    $finish;
  end
endmodule
