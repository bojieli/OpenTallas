`timescale 1ns/1ps
// S81-RCK-10: OT_S81_KP4_SYN_LOCAL + OT_S81_LPL_CHUNK decoder vs the vI decoder, same encoded + corrupted stream.
// New outputs = reference outputs exactly 2 ck later (declared PIN CYCLES); lock / n_relock and the landed word
// (dly input) unchanged; the k_* words at the Chien tile = reference 2 ck later.
module tb;
reg clk=0; always #0.4165 clk=~clk;
reg rst=0, erst=0; reg [511:0] tx; reg [543:0] pe, pd; reg pv;
wire ev; wire [543:0] ed; wire ef;
enc_r E(.clk(clk), .rst_n(erst), .tx_v(erst), .tx_d(tx), .p_v(ev), .p_d(ed), .fault(ef));
integer nerr_rate = 0, i, b;
always @(posedge clk) begin
  tx <= {16{$urandom}};
  pe = 0;
  if (nerr_rate > 0) for (b = 0; b < 4; b++) if (($urandom % 100) < nerr_rate) pe[$urandom % 544] = 1'b1;
  if (nerr_rate > 40) for (b = 0; b < 30; b++) pe[($urandom % 54) * 10 +: 10] = $urandom;   // burst: uncorrectable
  pv <= ev; pd <= ed ^ pe;
end
`define DECP(n) wire n``_qv, n``_qf, n``_qu, n``_lk; wire [511:0] n``_qd; wire [4:0] n``_qn; wire [7:0] n``_qs; wire [31:0] n``_nc, n``_nu, n``_nr;
`DECP(r) `DECP(n)
dec_r R(.rst_n(rst), .p_v(pv), .p_d(pd), .q_v(r_qv), .q_d(r_qd), .q_first(r_qf), .q_unc(r_qu), .q_nerr(r_qn), .q_seq(r_qs),
  .lock(r_lk), .n_corr(r_nc), .n_unc(r_nu), .n_relock(r_nr), .ck_syn(clk), .ck_dly(clk), .ck_chn(clk), .ck_out(clk));
dec_n N(.rst_n(rst), .p_v(pv), .p_d(pd), .q_v(n_qv), .q_d(n_qd), .q_first(n_qf), .q_unc(n_qu), .q_nerr(n_qn), .q_seq(n_qs),
  .lock(n_lk), .n_corr(n_nc), .n_unc(n_nu), .n_relock(n_nr), .ck_syn(clk), .ck_dly(clk), .ck_chn(clk), .ck_out(clk));
wire [511+1+1+1+5+8+32+32+4+310+5+1+544+544:0] rv = {r_qd, r_qv, r_qf, r_qu, r_qn, r_qs, r_nc, r_nu, R.k_v__l_chn, R.k_lo__l_chn, R.k_L__l_chn, R.k_any__l_chn, R.d_q__l_out, R.cw__l_out};
wire [511+1+1+1+5+8+32+32+4+310+5+1+544+544:0] nv = {n_qd, n_qv, n_qf, n_qu, n_qn, n_qs, n_nc, n_nu, N.k_v__l_chn, N.k_lo__l_chn, N.k_L__l_chn, N.k_any__l_chn, N.d_q__l_out, N.cw__l_out};
reg [$bits(rv)-1:0] rv1, rv2;
integer cyc=0, checks=0, err=0, kv=0, unc=0, qv=0;
always @(posedge clk) begin
  rv1 <= rv; rv2 <= rv1; cyc <= rst ? cyc + 1 : 0;
  if (rst && cyc > 4) begin
    checks++;
    // q_* / counters / k_* from the 5th edge; the unreset datapaths behind the dly SRAM and the Chien tile (d_q, cw)
    // hold stale words of the previous epoch until the first new word arrives, so they are compared from edge 100.
    if ({nv[1999:1088], cyc > 100 ? nv[1087:0] : 1088'd0} !== {rv2[1999:1088], cyc > 100 ? rv2[1087:0] : 1088'd0}) begin err++; if (err < 40) $display("BAD delayed cyc=%0d qd%0d qv%0d qf%0d qu%0d qn%0d qs%0d nc%0d nu%0d kv%0d klo%0d kL%0d kany%0d dq%0d cw%0d", cyc, nv[1999:1488]!==rv2[1999:1488], nv[1487:1487]!==rv2[1487:1487], nv[1486:1486]!==rv2[1486:1486], nv[1485:1485]!==rv2[1485:1485], nv[1484:1480]!==rv2[1484:1480], nv[1479:1472]!==rv2[1479:1472], nv[1471:1440]!==rv2[1471:1440], nv[1439:1408]!==rv2[1439:1408], nv[1407:1404]!==rv2[1407:1404], nv[1403:1094]!==rv2[1403:1094], nv[1093:1089]!==rv2[1093:1089], nv[1088:1088]!==rv2[1088:1088], nv[1087:544]!==rv2[1087:544], nv[543:0]!==rv2[543:0]); end
    if (n_lk !== r_lk || n_nr !== r_nr || N.x_q__l_dly !== R.x_q__l_dly) begin err++; if (err < 40) $display("BAD undelayed cyc=%0d lk%0d nr%0d xq%0d", cyc, n_lk !== r_lk, n_nr !== r_nr, N.x_q__l_dly !== R.x_q__l_dly); end
    if (R.k_v__l_chn[0]) kv++; if (R.k_v__l_chn[0] && R.k_any__l_chn) unc++; if (r_qv) qv++;
  end
end
initial begin
  for (i = 0; i < 4; i++) begin
    nerr_rate = (i == 0) ? 0 : (i == 1) ? 30 : (i == 2) ? 90 : 60;
    rst = 0; erst = 0; repeat (80) @(posedge clk); erst = 1; repeat (3) @(posedge clk); rst = 1;
    repeat (2500) @(posedge clk);
  end
  $display("DEC_RESULT checks=%0d errors=%0d kv_loads=%0d k_any=%0d q_v=%0d lock=%b n_relock=%0d", checks, err, kv, unc, qv, r_lk, r_nr);
  if (err || kv < 100 || unc < 10 || !r_lk) $fatal(1, "DEC lockstep FAILED");
  $finish;
end
endmodule
