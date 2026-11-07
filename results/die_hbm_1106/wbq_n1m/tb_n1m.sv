`timescale 1ns/1ps
// DIE-HBM-82-EP6 11-06: ot_wbq_root lock-step, r2c2 payload (old_wbq_root) vs OT_WBQ_N1M (new_wbq_root). Same random
// stimulus to both; every output compared every hbm_clk and fifo_clk edge with !==. Resets every RST cycles.
module tb;
  reg hbm_clk=0, fifo_clk=0; always #0.417 hbm_clk=~hbm_clk; always #0.53 fifo_clk=~fifo_clk;
  reg srn=0, hrn=0; reg [1:0] rid; reg rv, rb; reg [11:0] rt; reg [29:0] rbase; reg fs, fsb;
  reg [255:0] wd[0:7]; reg [7:0] wdv; reg con, cb, ss, hs; reg [1:0] gc;
  wire rr0, rr1; wire [1:0] gv0, gv1; wire [571:0] gd0, gd1;
  old_wbq_root u0(.hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(srn),.hbm_rst_n(hrn),.root_id(rid),.reserve_v(rv),.reserve_bank(rb),
    .reserve_total(rt),.reserve_base(rbase),.fill_start(fs),.fill_start_bank(fsb),.wd0(wd[0]),.wd1(wd[1]),.wd2(wd[2]),.wd3(wd[3]),.wd4(wd[4]),
    .wd5(wd[5]),.wd6(wd[6]),.wd7(wd[7]),.wd_v(wdv),.copy_on(con),.copy_bank(cb),.s_stop(ss),.h_stop(hs),.g_credit(gc),.root_ready(rr0),.g_v(gv0),.g_d(gd0));
  new_wbq_root u1(.hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(srn),.hbm_rst_n(hrn),.root_id(rid),.reserve_v(rv),.reserve_bank(rb),
    .reserve_total(rt),.reserve_base(rbase),.fill_start(fs),.fill_start_bank(fsb),.wd0(wd[0]),.wd1(wd[1]),.wd2(wd[2]),.wd3(wd[3]),.wd4(wd[4]),
    .wd5(wd[5]),.wd6(wd[6]),.wd7(wd[7]),.wd_v(wdv),.copy_on(con),.copy_bank(cb),.s_stop(ss),.h_stop(hs),.g_credit(gc),.root_ready(rr1),.g_v(gv1),.g_d(gd1));
  integer cyc=0, errs=0, gvn=0, i, ph=0;
  function [255:0] rnd256(input integer dummy); integer k; begin for(k=0;k<8;k=k+1) rnd256[32*k+:32]=$urandom; end endfunction
  // stream-side stimulus on fifo_clk
  always @(negedge fifo_clk) begin
    cyc<=cyc+1;
    if (cyc % `RST < 3) begin srn<=0; hrn<=0; rid<=$urandom; end else begin srn<=1; hrn<=1; end
    ph = (cyc % `RST);
    rv  <= ($urandom%40==0); rb<=$urandom; rt<=($urandom%2) ? $urandom%512 : $urandom; rbase<=$urandom;
    fs  <= ($urandom%60==0); fsb<=$urandom;
    for(i=0;i<8;i=i+1) wd[i]<=rnd256(0);
    wdv <= $urandom; cb <= (ph<200) ? 0 : 1;
    con <= (ph%150) > 70; ss <= ($urandom%23==0);
  end
  always @(negedge hbm_clk) begin hs <= ($urandom%19==0); gc <= $urandom; end
  always @(posedge hbm_clk or posedge fifo_clk) begin
    #0.05;
    if (rr0!==rr1 || gv0!==gv1 || gd0!==gd1) begin errs=errs+1; if (errs<4) $display("MISMATCH t=%0t gv %b %b", $time, gv0, gv1); end
    if (|gv0) gvn=gvn+1;
    if (cyc>=`CYC) begin $display("N1M LOCKSTEP %s errs=%0d g_v_cycles=%0d of %0d", errs==0?"PASS":"FAIL", errs, gvn, cyc); $finish; end
  end
endmodule
