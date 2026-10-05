`timescale 1ns/1ps
module tb_w5_ao_protection;
 reg clk=0;always #0.5 clk=~clk;
 reg por_n=0,cv=0,sv=0,external_stop=0;reg [4:0] ca=0;reg [47:0] cd=0;
 wire [3:0] se;reg [3:0] sa=0;
 wire sc,arst,rq,ready,pgready,pgfault,busy,ef;
 wire [4:0] rpa;wire [47:0] rpd;
 wire dbusy,dack,ack,rdy,erst,ecv,ego;wire [4:0] eca;wire [47:0] ecd;
 ot_w5_ao_checked #(.PROTECT(1),.RETENTION_EDGE_WRITE(1)) dut(
 .external_quarantine(external_stop),.clk(clk),.aon_clk(clk),.rst_n(por_n),.cfg_v(cv),.cfg_a(ca),.cfg_d(cd),.go(1'b0),
 .pg_en(1'b1),.sched_v(sv),.sched_gap(24'd32),.pg_lead(24'd400),.pg_bet(24'd64),.pg_idle(8'd0),
 .pg_step(16'd8),.pg_rst(8'd4),.pg_ack_to(16'd200),.sw_en(se),.sw_ack(sa),.s_clk(sc),.arst_n(arst),
 .e_pv(2'b0),.e_pval(64'b0),.e_prow(32'b0),.e_pseg(10'b0),.e_pnseg(10'b0),.e_perr(2'b0),
 .e_ppos(6'b0),.e_busy(1'b0),.e_fault(1'b0),.dbusy(dbusy),.dack(dack),.ack(ack),.rdy(rdy),
 .rq(rq),.rp_a(rpa),.rp_d(rpd),.ready_a(ready),.pg_ready(pgready),.pg_fault(pgfault),.busy(busy),.fault(ef));
 ot_w5_pg_dif dif(.e_clk(sc),.arst_n(arst),.cfg_v(1'b0),.cfg_a(5'b0),.cfg_d(48'b0),.go(1'b0),
 .rq(rq),.rp_a(rpa),.rp_d(rpd),.ready_a(ready),.e_busy(1'b0),.e_pv(2'b0),.e_rst_n(erst),
 .e_cfg_v(ecv),.e_cfg_a(eca),.e_cfg_d(ecd),.e_go(ego),.dbusy(dbusy),.dack(dack),.ack(ack),.rdy(rdy));
 always @(negedge clk) sa<=se;
 integer f,i,cycles;
 reg [24:0] v0,d0;reg [1322:0] snap;
 initial begin
 for(f=0;f<9;f=f+1)begin
  @(negedge clk);por_n=0;cv=0;sv=0;external_stop=0;
  repeat(4)@(negedge clk);por_n=1;
  for(i=0;i<25;i=i+1)begin
   @(negedge clk);cv=1;ca=5'(i);cd=48'h53edacefabcd^i;
  end
  @(negedge clk);cv=0;
  if(dut.quarantine || dut.u_p.g_e[0].u_eao.valid!==25'h1ffffff) $fatal(1,"healthy fullmap lost");
  sv=1;@(negedge clk);sv=0;
  cycles=0;
  while(!dut.u_p.g_e[0].u_eao.infl && cycles<200)begin @(negedge clk);cycles=cycles+1;end
  if(!dut.u_p.g_e[0].u_eao.infl) $fatal(1,"no real replay debt");
  case(f)
  0:dut.u_p.g_e[0].u_eao.g_sh[0].r[3]=~dut.u_p.g_e[0].u_eao.g_sh[0].r[3];
  1:dut.u_p.g_e[0].u_eao.valid[24]=~dut.u_p.g_e[0].u_eao.valid[24];
  2:dut.u_p.g_e[0].u_eao.dirty[24]=~dut.u_p.g_e[0].u_eao.dirty[24];
  3:dut.u_p.g_e[0].u_eao.cdc_rp_d[3]=~dut.u_p.g_e[0].u_eao.cdc_rp_d[3];
  4:dut.u_p.g_e[0].u_eao.rq=~dut.u_p.g_e[0].u_eao.rq;
  5:dut.u_p.u_ctl.u_sched.cnt[3]=~dut.u_p.u_ctl.u_sched.cnt[3];
  6:dut.u_p.u_ctl.u_sched.u_pg.cnt[3]=~dut.u_p.u_ctl.u_sched.u_pg.cnt[3];
  7:dut.u_p.g_e[0].u_eao.iso_q=~dut.u_p.g_e[0].u_eao.iso_q;
  8:external_stop=1;
  endcase
  #0.01;
  if(!pgfault || pgready || !busy || arst) $fatal(1,"fault failed exclusion f=%0d",f);
  v0=dut.u_p.g_e[0].u_eao.valid;d0=dut.u_p.g_e[0].u_eao.dirty;
  snap=dut.u_p.g_e[0].u_eao.snapshot;
  cv=1;ca=5'd12;cd=0;sv=1;
  repeat(16)@(negedge clk);
  if(dut.u_p.g_e[0].u_eao.snapshot!==snap || !pgfault || pgready || ecv)
   $fatal(1,"quarantine cleared/changed accepted debt f=%0d",f);
  cv=0;sv=0;
  $display("FAULT_PASS family=%0d retained_valid=%h retained_dirty=%h",f,v0,d0);
 end
 $display("PASS protected full25 AO 9 fault families retained debt/no fake ACK/cold-only recovery");$finish;
 end
endmodule
