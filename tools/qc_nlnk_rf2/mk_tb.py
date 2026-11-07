import re,sys
s=open(sys.argv[1]).read()
s=s.replace("module tb_a0_lqr;","module tb_a0_rstp;")
s=s.replace("`define REF_LQR\n","`define REF_RSTP\n").replace("`define REF_LQR .LQR(0),\n","`define REF_RSTP .RSTP(0),\n")
s=s.replace("`REF_LQR .ROM_TILE(48)","`REF_RSTP .LQR(`TB_LQR), .ROM_TILE(48)").replace("`REF_LQR .ROM_TILE","`REF_RSTP .LQR(`TB_LQR), .ROM_TILE")
s=s.replace("  `REF_LQR .ROM_TILE(48)","  `REF_RSTP .LQR(`TB_LQR), .ROM_TILE(48)")
s=s.replace(".LQR(`TB_LQR), .ROM_TILE(48)) u_dut",".LQR(`TB_LQR), .RSTP(`TB_RSTP), .ROM_TILE(48)) u_dut")
s=s.replace("  .LQR(`TB_LQR), .RSTP(`TB_RSTP)","  .LQR(`TB_LQR), .RSTP(`TB_RSTP)")
assert "REF_LQR" not in s
s=s.replace("`ifndef TB_LQR\n`define TB_LQR 1\n`endif\n","`ifndef TB_LQR\n`define TB_LQR 25\n`endif\n`ifndef TB_RSTP\n`define TB_RSTP 3\n`endif\n")
s=s.replace("// QC-A0C-B5 11-06 vB bench","// QC-NLNK-RF2 11-06 vR bench: ref RSTP 0 vs dut RSTP `TB_RSTP (same LQR); t_out delta must be 0 and every sink-side reset edge exactly +RSTP.\n// derived from: QC-A0C-B5 11-06 vB bench")
# reset edge monitors
mon='''
// vR: reset edges at the sink net u_g.reset_q, ref vs dut, in clock edges; every copy of each tree stage equal every edge.
integer re_r[0:7], re_d[0:7], fe_r[0:7], fe_d[0:7], nre_r=0, nre_d=0, nfe_r=0, nfe_d=0, copyerr=0, rstchk=0, tick=0;
reg pr=1'bx, pd=1'bx;
always @(negedge ck) begin
  tick = tick + 1;
  if (pr === 1'b0 && u_ref.u_g.reset_q === 1'b1 && nre_r < 8) begin re_r[nre_r] = tick; nre_r = nre_r + 1; end
  if (pd === 1'b0 && u_dut.u_g.reset_q === 1'b1 && nre_d < 8) begin re_d[nre_d] = tick; nre_d = nre_d + 1; end
  if (pr === 1'b1 && u_ref.u_g.reset_q === 1'b0 && nfe_r < 8) begin fe_r[nfe_r] = tick; nfe_r = nfe_r + 1; end
  if (pd === 1'b1 && u_dut.u_g.reset_q === 1'b0 && nfe_d < 8) begin fe_d[nfe_d] = tick; nfe_d = nfe_d + 1; end
  pr = u_ref.u_g.reset_q; pd = u_dut.u_g.reset_q;
`ifndef TB_OLD
`ifdef TB_RSTP_ON
  if (tick > 8) begin
    if (u_dut.u_g.g_rst_native.g_rp.s1__ot_rl1v != {4{u_dut.u_g.g_rst_native.g_rp.s1__ot_rl1v[0]}}) copyerr = copyerr + 1;
    if (u_dut.u_g.g_rst_native.g_rp.s2__ot_rl2v != {32{u_dut.u_g.g_rst_native.g_rp.s2__ot_rl2v[0]}}) copyerr = copyerr + 1;
    if (u_dut.u_g.g_rst_native.g_rp.s3__ot_rl3v != {256{u_dut.u_g.g_rst_native.g_rp.s3__ot_rl3v[0]}}) copyerr = copyerr + 1;
  end
`endif
`endif
end
'''
s=s.replace("function automatic [378:0] command",mon+"function automatic [378:0] command",1)
chk='''  for (k = 0; k < nre_r && k < nre_d; k = k + 1) if (re_d[k] - re_r[k] != `TB_RSTP) rstchk = rstchk + 1;
  for (k = 0; k < nfe_r && k < nfe_d; k = k + 1) if (fe_d[k] - fe_r[k] != `TB_RSTP) rstchk = rstchk + 1;
  if (nre_r != nre_d || nfe_r != nfe_d || nre_r < 2 || nfe_r < 1) rstchk = rstchk + 1;
  $display("A0RSTP_RESET release edges ref=%0d dut=%0d first delta=%0d second delta=%0d assert edges ref=%0d dut=%0d delta=%0d mismatches=%0d copyerr=%0d",
    nre_r, nre_d, re_d[0]-re_r[0], (nre_d>1 && nre_r>1) ? re_d[1]-re_r[1] : -1, nfe_r, nfe_d, (nfe_d>0 && nfe_r>0) ? fe_d[0]-fe_r[0] : -1, rstchk, copyerr);
'''
s=s.replace('  $display("A0LQR_FAULT',chk+'  $display("A0LQR_FAULT',1)
s=s.replace("|| (FINJ != 0 && nrf == 0) || dmin != dmax)","|| (FINJ != 0 && nrf == 0) || dmin != 0 || dmax != 0 || rstchk != 0 || copyerr != 0)")
old_ny = "    if (rn[513:512] !== dn[513:512] || (rn[512] && rn[511:0] !== dn[511:0]) || rhi !== dhi || rlo !== dlo) begin\n      nerr = nerr + 1; if (nfirst < 0) nfirst = cyc; end\n"
assert old_ny in s
new_ny = '''    // vR: the only allowed n_y difference is the sticky fault bit [513] clearing exactly RSTP edges later at the reset
    // assert (7000 pulse, ref clears at 7002). Same valid, same ties, dut still 1, ref already 0, only inside that window.
    if (rn[513:512] !== dn[513:512] || (rn[512] && rn[511:0] !== dn[511:0]) || rhi !== dhi || rlo !== dlo) begin
      if (nmis < 8) begin $display("A0RSTP_NY cyc %0d ref[513:512]=%b dut[513:512]=%b ties %b/%b %b/%b", cyc, rn[513:512], dn[513:512], rhi, dhi, rlo, dlo); nmis = nmis + 1; end
      if (cyc >= 7002 && cyc < 7002 + `TB_RSTP && rn[513] === 1'b0 && dn[513] === 1'b1 && rn[512] === dn[512] && !rn[512] && rhi === dhi && rlo === dlo) rstwin = rstwin + 1;
      else begin nerr = nerr + 1; if (nfirst < 0) nfirst = cyc; end
    end
'''
s=s.replace(old_ny,new_ny,1)
s=s.replace("integer nstrict = 0, nval = 0;","integer nstrict = 0, nval = 0, nmis = 0, rstwin = 0;",1)
s=s.replace('dmin != 0 || dmax != 0 || rstchk != 0 || copyerr != 0)','dmin != 0 || dmax != 0 || rstchk != 0 || copyerr != 0 || (TILE == "nk" && rstwin != `TB_RSTP))',1)
assert "rstwin != `TB_RSTP" in s
s=s.replace("A0LQR_","A0RSTP_").replace("LQR=%0d MUT=%0d","RSTP=`TB_RSTP LQR=%0d MUT=%0d")
s=s.replace("`ifdef OT_LQR_MUT\nlocalparam integer MUT = `OT_LQR_MUT;","`ifdef OT_RSTP_MUT\nlocalparam integer MUT = `OT_RSTP_MUT;")
open(sys.argv[2],"w").write(s)
