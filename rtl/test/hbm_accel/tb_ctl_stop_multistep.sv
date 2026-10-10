`timescale 1ps/1fs
// fork J (mtp-lead 2026-10-09): multi-step transaction log of ot_dshbm_dspark_ctl_stop. The engine / emit models
// respond to commands and handshakes only (no wall-clock schedule), so two RTL versions that differ only in
// latency must write identical logs. Engine model = tb_dshbm_dspark_ctl_stop's (forced drafts 100+f_addr,
// head rows 100+row for row<5 else 200, prefill head 7).
module tb_ctl_stop_multistep #(parameter NGEN=20, EOS_EN=0, EOS=103, MAXPOS_CFG=1048576, PRL=0, FORCE=1);
 reg clk=0;always #417 clk=~clk;
 reg rst_n=0,start=0,e_ready=0;wire [19:0] p_addr,e_idx;wire [22:0] f_addr;
 wire e_v,done,cmd_v;wire [16:0] e_tok;wire [3:0] cmd_op,cmd_ncol;
 wire [7:0] cmd_idx;wire [31:0] cmd_pos;wire [16:0] cmd_tok1;wire [135:0] cmd_toks;
 reg eng_done=0,am_v=0;reg [16:0] am_idx=0;
 reg [31:0] n=0;wire n_set,tw_v,step_v;wire [31:0] n_val,tw_pos;wire [16:0] tw_tok;
 wire [2:0] step_a,stop_status;wire [3:0] step_g;wire [20:0] steps;
 wire [31:0] cyc_total,cyc_engine,cyc_markov;
 ot_dshbm_dspark_ctl_stop #(.STOP_EN(1),.PRL(PRL),.FAST(1),.MAXPOS(1048576),.MUT(0)) dut(
 .clk(clk),.rst_n(rst_n),.start(start),.cfg_gamma(4'd5),.cfg_force(FORCE[0]),
 .cfg_ngen(NGEN[20:0]),.cfg_plen(21'd2),.p_addr(p_addr),.p_tok(17'd5),
 .f_addr(f_addr),.f_tok(17'd100+f_addr),.e_v(e_v),.e_tok(e_tok),.e_idx(e_idx),.e_ready(e_ready),
 .cfg_eos_en(EOS_EN[0]),.cfg_eos(EOS[16:0]),.cfg_maxpos(MAXPOS_CFG[20:0]),.stop_status(stop_status),
 .done(done),.cmd_v(cmd_v),.cmd_ready(1'b1),.cmd_op(cmd_op),.cmd_idx(cmd_idx),.cmd_ncol(cmd_ncol),
 .cmd_pos(cmd_pos),.cmd_tok1(cmd_tok1),.cmd_toks(cmd_toks),.eng_done(eng_done),.am_v(am_v),.am_idx(am_idx),
 .n(n),.n_set(n_set),.n_val(n_val),.tw_v(tw_v),.tw_pos(tw_pos),.tw_tok(tw_tok),
 .step_v(step_v),.step_a(step_a),.step_g(step_g),.steps(steps),.cyc_total(cyc_total),.cyc_engine(cyc_engine),.cyc_markov(cyc_markov));
 reg mk=0;reg [16:0] mtok=0;
 integer seen=0,eng_state=0,row=0,rows=0,headpass=0,cycles=0,cmds=0,stall=0;
 always @(posedge clk) begin
  if(n_set) begin n<=n_val; $display("TX NSET %0d", n_val); end
  if(tw_v) $display("TX TW %0d %0d", tw_pos, tw_tok);
  if(step_v) $display("TX STEP a=%0d g=%0d", step_a, step_g);
  eng_done<=0;am_v<=0;cycles=cycles+1;
  if(e_v && e_ready) begin $display("TX EMIT %0d %0d", e_idx, e_tok); seen=seen+1; end
  if(cmd_v) begin
   $display("TX CMD op=%0d idx=%0d ncol=%0d pos=%0d t1=%0d", cmd_op, cmd_idx, cmd_ncol, cmd_pos, cmd_tok1);
   if(eng_state!=0)$fatal(1,"duplicate command");cmds=cmds+1;
   if(cmd_op==1) begin eng_state=1;mk=0;row=0;rows=cmd_ncol;headpass=headpass+1;end
   else if(cmd_op==5) begin eng_state=1;mk=1;row=0;rows=1;mtok=17'd100+cmd_idx+(cmd_pos%3);end
   else eng_state=2;
  end else if(eng_state==1) begin
   if(row<rows) begin am_v<=1;am_idx<=mk?mtok:((headpass<=2)?17'd7:((row<5)?17'd100+row:17'd200));row=row+1;end
   else begin eng_done<=1;eng_state=0;end
  end else if(eng_state==2) begin eng_done<=1;eng_state=0;end
  if(seen%3==1 && stall<4) begin e_ready<=0;stall=stall+1;end else begin e_ready<=1; if(seen%3!=1) stall=0; end
 end
 initial begin
  repeat(5) @(negedge clk);rst_n=1;
  @(negedge clk);start=1;@(negedge clk);start=0;
  wait(done);repeat(5) @(negedge clk);
  $display("TX END seen=%0d n=%0d steps=%0d stop=%0d", seen, n, steps, stop_status);
  $display("CYCLES %0d", cycles);
  $finish;
 end
 initial begin repeat(400000) @(posedge clk);$fatal(1,"watchdog");end
endmodule
