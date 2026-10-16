module check_rel;
reg clk=0; reg [31:0] rng=32'h9e3779b9; integer cycle,j; reg [127:0] yb_n, yb_s; reg [255:0] prev; wire [255:0] yb_rel;
ot_s81_hc_ctra_columns #(.NG(256),.D(5120),.NCOL(3),.GS(8),.S_RD(2),.S_RT(4),.ML(5),.AL(4),.CHAIN_STEP(6),.READ_STAGE(1),.YB_STAGE(1)) dut(
 .clk_col({4{clk}}),.rst_in(1'b1),.tid(8'd0),.last(1'b0),.fv(7'd0),.fdx(104'd0),.rv_in(8'd0),.rd_in(1132'd0),.rvm(),.rdm(),.rq_q(),.hs_run(),.hs_c(),
 .rq_q_c1(),.rq_q_c2(),.rq_q_c3(),.hs_run_c1(),.hs_run_c2(),.hs_run_c3(),.hs_c_c1(),.hs_c_c2(),.hs_c_c3(),.hrq_n(1024'd0),.hrq_s(1024'd0),
 .yb_n(yb_n),.yb_s(yb_s),.cs(128'd0),.nflt_n(8'd0),.nflt_s(8'd0),.hov_d(1'b0),.hnz_n(4'd0),.hnz_s(4'd0),.pflt_n(4'd0),.pflt_s(4'd0),.yb_rel(yb_rel));
initial begin yb_n=0; yb_s=0;
 for(cycle=0;cycle<2500;cycle=cycle+1) begin clk=0; #1;
  for(j=0;j<128;j=j+1) begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);yb_n[j]=rng[0];rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);yb_s[j]=rng[0]; end
  prev={yb_s,yb_n}; #1; clk=1; #1;
  if(cycle>2 && yb_rel!==prev) $fatal(1,"rel mismatch cycle=%0d",cycle);
 end
 $display("PASS rel 2500 cycles yb_rel = y beat one cycle late, 256 bits"); $finish; end
endmodule
