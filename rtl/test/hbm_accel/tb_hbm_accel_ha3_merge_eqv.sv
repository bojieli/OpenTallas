`timescale 1ns/1ps
// HA3: random equivalence of the port's COLLX merge, loop form (old_port = ot_hbm_accel_coll_port at bd3c47743, renamed) vs the
// barrel-shift form; 3000 random contributions incl. overlapping/illegal ones: dat, lane_ok, resid, contrib, fault.
module tb_eqv;
  reg clk=0, rst_n=0; always #1 clk=~clk;
  reg [1:0] rv, mode, x, fuse; reg [15:0] cnt, off, nown; reg [8191:0] data, resid;
  wire [1:0] r0, r1, v0, v1; wire [4095:0] d0, d1; wire [31:0] ss0, ss1, c0, c1; wire e0, e1, f0, f1, t0, t1; wire [545:0] tr0, tr1;
  old_port #(.ENABLE(1)) uo(.clk_sm(clk),.rst_sm_n(rst_n),.s_req_v(rv),.s_req_rdy(r0),.s_mode(mode),.s_count(cnt),.s_data(data),.s_x(x),.s_off(off),.s_nown(nown),.s_fuse(fuse),.s_resid(resid),.s_rsp_v(v0),.s_rsp_rdy(2'b0),.s_rsp_data(d0),.s_rsp_ss(ss0),.s_rsp_err(e0),.fault(f0),.st_coll(c0),.clk_link(clk),.rst_link_n(rst_n),.lk_tx_v(t0),.lk_tx_rec(tr0),.lk_rx_v(1'b0),.lk_rx_rec(546'd0));
  ot_hbm_accel_coll_port #(.ENABLE(1)) un(.clk_sm(clk),.rst_sm_n(rst_n),.s_req_v(rv),.s_req_rdy(r1),.s_mode(mode),.s_count(cnt),.s_data(data),.s_x(x),.s_off(off),.s_nown(nown),.s_fuse(fuse),.s_resid(resid),.s_rsp_v(v1),.s_rsp_rdy(2'b0),.s_rsp_data(d1),.s_rsp_ss(ss1),.s_rsp_err(e1),.fault(f1),.st_coll(c1),.clk_link(clk),.rst_link_n(rst_n),.lk_tx_v(t1),.lk_tx_rec(tr1),.lk_rx_v(1'b0),.lk_rx_rec(546'd0));
  integer it, bad=0, k;
  initial begin
    for (it=0; it<3000; it++) begin
      rst_n=0; rv=0; @(posedge clk); @(posedge clk); rst_n=1; @(negedge clk);
      for (k=0;k<256;k++) begin data[32*k+:32]=$urandom; resid[32*k+:32]=$urandom; end
      cnt = {8'($urandom_range(1,128)), 8'd0}; cnt[7:0]=cnt[15:8];
      off[7:0]=$urandom_range(0,cnt[7:0]); nown[7:0]=$urandom_range(0,cnt[7:0]-off[7:0]);
      off[15:8]=$urandom_range(0,cnt[7:0]); nown[15:8]=$urandom_range(0,cnt[7:0]-off[15:8]);
      if ($urandom%8==0) nown[15:8]=nown[15:8]+8'($urandom%20);   // sometimes illegal
      mode=0; fuse=0; x=2'b11; rv = 2'($urandom_range(1,3));
      @(negedge clk); // first accept
      if ($urandom%2) begin rv = ~rv & 2'b11; @(negedge clk); end
      rv=0; @(negedge clk);
      if (uo.g_on.dat !== un.g_on.dat || uo.g_on.lane_ok !== un.g_on.lane_ok || uo.g_on.resid !== un.g_on.resid || f0 !== f1 || uo.g_on.contrib !== un.g_on.contrib) begin
        bad++; if (bad<5) $display("MISMATCH it %0d cnt %0d off %h nown %h ok %h/%h f %b/%b", it, cnt[7:0], off, nown, uo.g_on.lane_ok, un.g_on.lane_ok, f0, f1);
      end
    end
    $display("EQV iterations 3000 mismatches %0d", bad);
    if (bad != 0) $fatal(1, "EQUIVALENCE_TERMINAL_FAIL");
    $finish;
  end
endmodule
