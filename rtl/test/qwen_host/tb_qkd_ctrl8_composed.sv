`timescale 1ns/1ps
// Original ND8 package controller driven by packet transport, not a surrogate
// completion model. Forty generations cross wrap and per-peer packet sequences.
module tb_qkd_ctrl8_composed;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,rx_v=0,tx_cr=0;reg[511:0]rx_d=0;reg[92:0]local_tk=0;reg[9:0]local_boot=10'h3ff;
 wire tx_v,rx_cr,cmd_cr,fault;wire[511:0]tx_d;wire[181:0]hc;wire[743:0]tk8;wire[79:0]boot8;wire[7:0]seen;
 reg eng_start=0;reg[17:0]eng_token=0,eng_pos=0;
 wire eng_done,eng_fault;wire[17:0]eng_next_token;wire[31:0]eng_next_val,eng_cycles,n_steps;
 wire d_start;wire[17:0]d_token,d_pos;wire[23:0]d_kv_base;wire[1:0]d_gen;
 wire disagree,wdog_fault,start_unready,die_fault;
 wire[181:0]cmd_hc={143'd0,d_start,d_gen,d_token,d_pos};
 qkd_host_ctrl_packet #(.DIE(0),.MUT(MUT)) transport(.ck(ck),.rst_n(rst_n),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(rx_cr),
 .tx_v(tx_v),.tx_d(tx_d),.tx_cr(tx_cr),.local_tk(local_tk),.local_boot(local_boot),.cmd_v(d_start),.cmd_hc(cmd_hc),.cmd_cr(cmd_cr),
 .hc(hc),.tk8(tk8),.boot8(boot8),.seen(seen),.fault(fault));
 wire[7:0]dn,dr,df;wire[15:0]dg;wire[143:0]nt;wire[255:0]nv;
 for(genvar d=0;d<8;d++)begin
  assign dn[d]=tk8[d*93+92];assign dg[d*2+:2]=tk8[d*93+90+:2];assign dr[d]=tk8[d*93+89];assign df[d]=tk8[d*93+88];
  assign nt[d*18+:18]=tk8[d*93+64+:18];assign nv[d*32+:32]=tk8[d*93+32+:32];
 end
 ot_qfd_pkgctl #(.D(8),.DONE_REG(1),.WDOG(10000))pkg(
 .clk(ck),.rst_n(rst_n),.ready(&seen&&!fault),.eng_start(eng_start),.eng_token(eng_token),.eng_pos(eng_pos),.eng_kv_base(24'd0),
 .eng_done(eng_done),.eng_next_token(eng_next_token),.eng_next_val(eng_next_val),.eng_cycles(eng_cycles),.eng_fault(eng_fault),
 .d_start(d_start),.d_token(d_token),.d_pos(d_pos),.d_kv_base(d_kv_base),.d_gen(d_gen),
 .d_done(dn),.d_done_gen(dg),.d_next_token(nt),.d_next_val(nv),.d_drained(dr),.d_fault(df),
 .disagree(disagree),.wdog_fault(wdog_fault),.start_unready(start_unready),.die_fault(die_fault),.n_steps(n_steps));
 always @(posedge ck)tx_cr<=tx_v;
 integer checks=0,seq[0:7];reg[92:0]tk;reg[511:0]p;
 task tick;begin @(posedge ck);#1;end endtask
 task check(input bit ok,input string why);begin checks++;if(!ok)$fatal(1,"%s",why);end endtask
 task status(input integer d,input[92:0]status_tk);begin
  p=512'h01000121|(512'(d)<<16)|(512'(seq[d])<<32)|(512'(status_tk)<<48)|(512'(10'h3ff)<<141);seq[d]++;
  @(negedge ck);rx_v=1;rx_d=p;@(negedge ck);rx_v=0;repeat(2)tick();
 end endtask
 task all_status(input[1:0]gen,input[17:0]token,input bit drain7);begin
  tk={1'b1,gen,1'b1,1'b0,4'd0,1'b0,1'b1,token,32'h3f800000,32'd123};local_tk=tk;
  for(integer d=1;d<8;d++)begin tk[89]=(d!=7)||drain7;status(d,tk);end
  repeat(6)tick();
 end endtask
 initial begin
  for(integer d=0;d<8;d++)seq[d]=0;
  repeat(4)tick();rst_n=1;all_status(0,18'd15,1);check(seen==8'hff,"boot peers present");
  for(integer step=0;step<40;step++)begin
   @(negedge ck);eng_token=18'(step+17);eng_pos=18'(step);eng_start=1;@(negedge ck);eng_start=0;
   repeat(5)tick();check(!eng_done,"stale generation cannot complete");
   all_status(d_gen,18'(step+100),0);check(!eng_done,"die7 undrained cannot complete");
   tk[89]=1;status(7,tk);repeat(10)tick();
   check(eng_done&&!eng_fault&&!fault,"ND8 real pkgctl completion");
   check(eng_next_token==18'(step+100)&&eng_next_val==32'h3f800000,"ND8 exact token/value");
  end
  check(n_steps==40,"all40 transported steps");
  $display("PASS CTRL8_COMPOSED checks=%0d steps=%0d",checks,n_steps);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
