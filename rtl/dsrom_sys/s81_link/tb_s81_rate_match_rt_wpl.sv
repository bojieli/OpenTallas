`timescale 1ns/1ps
// FABLE-FIX-S81-SERDES-0000 11-20: OT_S81_SERDES_RM_WPL8 (LOCAL_WP) on the full-shape 8x512 rate matcher.
//  (1) exact: banked form (RPC 8, LOCAL_EMPTY 1, LOCAL_WP 1) == unbanked three-stage form (RPC 1, LOCAL_WP 1) on r_d and
//      fault in every rclk cycle, with split control / bank resets;
//  (2) contract vs the base form (LOCAL_WP 0): the same non-IDLE beats in the same order, no fault where the base has
//      none; every beat leaves exactly 1 rclk later than in the base while the writer is the slower side, and never
//      more than 1 rclk later when the writer is faster (the dut then sheds an IDLE beat earlier).
module tb_s81_rate_match_rt_wpl;
    reg wclk=0, rclk=0;
`ifdef WPL_FAST_W
    always #0.4155 wclk=~wclk;      // writer faster: IDLE shedding
`else
    always #0.4175 wclk=~wclk;      // writer slower: reader runs empty
`endif
    always #0.4165 rclk=~rclk;
    reg wrst_n=0, rrst_nc=0;
    reg [7:0] rrst_nd=0;
    reg w_v=0;
    reg [511:0] w_d=512'd2;
    wire [511:0] base_d, g3_d, dut_d;
    wire base_f, g3_f, dut_f;
    ot_s81_rate_match_rt #(.NRD(8),.RPC(1),.LOCAL_EMPTY(0),.LOCAL_WP(0)) base_rm
      (.wclk(wclk),.wrst_n(wrst_n),.w_v(w_v),.w_d(w_d),.rclk(rclk),.rrst_nc(rrst_nc),.rrst_nd(rrst_nd),.r_d(base_d),.fault(base_f));
    ot_s81_rate_match_rt #(.NRD(8),.RPC(1),.LOCAL_EMPTY(0),.LOCAL_WP(1)) g3_rm
      (.wclk(wclk),.wrst_n(wrst_n),.w_v(w_v),.w_d(w_d),.rclk(rclk),.rrst_nc(rrst_nc),.rrst_nd(rrst_nd),.r_d(g3_d),.fault(g3_f));
    ot_s81_rate_match_rt #(.NRD(8),.RPC(8),.LOCAL_EMPTY(1),.LOCAL_WP(1)) dut_rm
      (.wclk(wclk),.wrst_n(wrst_n),.w_v(w_v),.w_d(w_d),.rclk(rclk),.rrst_nc(rrst_nc),.rrst_nd(rrst_nd),.r_d(dut_d),.fault(dut_f));
    integer wc=0, rc=0, checks=0, resets=0;
    function automatic [511:0] beat(input integer n);
      integer j;
      begin
        for(j=0;j<16;j=j+1) beat[j*32+:32]=(n*32'h9e3779b9)^(j*32'h452109ab)^32'h5a3c0901;
        beat[1:0]=2'b00;
        beat[63:32]=n;
      end
    endfunction
    always @(negedge wclk) begin
      wc=wc+1;
      w_v=(wc%19!=0);
      w_d=(wc%7==0 || wc%43==0) ? 512'd2 : beat(wc);
    end
    always @(negedge rclk) rc=rc+1;
    // One reset sequence for both domains on absolute time (the two clocks drift several cycles in 3000): all asserted
    // together; bank resets release first, then the read control, then the writer, so no beat is read into a held bank.
    task automatic rst_seq; begin
      wrst_n=0; rrst_nc=0; rrst_nd=0; rec=0; #20;
      @(negedge rclk) rrst_nd=8'hff; @(negedge rclk) rrst_nc=1;
      repeat (4) @(negedge wclk); wrst_n=1; bn=0; dn=0; rec=1; resets=resets+1;
    end endtask
    reg rec=0;
    initial begin rst_seq; #2500; rec=0; #20; chk_epoch; rst_seq; #4500; rec=0; #20; chk_epoch; fin; end
    // scoreboard: non-IDLE beats of the base and of the dut, by arrival order
    reg [511:0] bq [0:8191]; integer bt [0:8191]; reg [511:0] dq [0:8191]; integer dt [0:8191]; integer total=0, bn=0, dn=0, maxlag=0, minlag=1000, lag, sumlag=0;
    wire base_idle = (base_d==512'd2), dut_idle = (dut_d==512'd2);
    // epoch check: the same non-IDLE beats in the same order; outstanding beats bounded by the FIFO depth
    task automatic chk_epoch; integer k, n; begin
      n = (bn < dn) ? bn : dn;
      if(bn-dn>8 || dn-bn>8) $fatal(1,"RM_RT_WPL FAIL beats base=%0d dut=%0d", bn, dn);
      for(k=0;k<n;k=k+1) begin
        if(bq[k]!==dq[k]) $fatal(1,"RM_RT_WPL FAIL beat %0d differs", k);
        lag=dt[k]-bt[k]; if(lag>maxlag) maxlag=lag; if(lag<minlag) minlag=lag; sumlag=sumlag+lag;
      end
      total=total+n;
    end endtask
    task automatic fin; begin
      if(total<5000) $fatal(1,"RM_RT_WPL stimulus insufficient: beats=%0d", total);
`ifdef WPL_FAST_W
      // writer fast: the dut holds one beat more, so it sheds an IDLE earlier and a beat may leave up to the depth earlier
      if(minlag<-8 || maxlag!=1) $fatal(1,"RM_RT_WPL FAIL lag min=%0d max=%0d", minlag, maxlag);
`else
      if(minlag!=1 || maxlag!=1) $fatal(1,"RM_RT_WPL FAIL lag min=%0d max=%0d", minlag, maxlag);
`endif
      $display("RM_RT_WPL PASS checks=%0d beats=%0d lag_min=%0d lag_max=%0d lag_sum=%0d resets=%0d copies=8 cycles_added=1",
        checks, total, minlag, maxlag, sumlag, resets);
      $finish;
    end endtask
    always @(posedge rclk) begin
      #0.001;
      checks=checks+1;
      if(g3_d!==dut_d || g3_f!==dut_f)
        $fatal(1,"RM_RT_WPL FAIL exact cycle=%0d fault=%b/%b", rc, g3_f, dut_f);
      if(rec) begin
        if(!base_idle) begin bq[bn]=base_d; bt[bn]=rc; bn=bn+1; end
        if(!dut_idle)  begin dq[dn]=dut_d;  dt[dn]=rc; dn=dn+1; end
        if(base_f!==1'b0 || dut_f!==1'b0) $fatal(1,"RM_RT_WPL FAIL fault base=%b dut=%b cycle=%0d", base_f, dut_f, rc);
      end
    end
endmodule
