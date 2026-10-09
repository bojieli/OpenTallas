`timescale 1ps/1fs
module tb_dshbm_dspark_ctl_stop #(parameter KIND=0,MUT=0);
 reg clk=0;always #417 clk=~clk;
 reg rst_n=0,start=0,e_ready=0;wire [19:0] p_addr,e_idx;wire [22:0] f_addr;
 wire e_v,done,cmd_v;wire [16:0] e_tok;wire [3:0] cmd_op,cmd_ncol;
 wire [7:0] cmd_idx;wire [31:0] cmd_pos;wire [16:0] cmd_tok1;wire [135:0] cmd_toks;
 reg eng_done=0,am_v=0;reg [16:0] am_idx=0;
 reg [31:0] n=0;wire n_set,tw_v,step_v;wire [31:0] n_val,tw_pos;wire [16:0] tw_tok;
 wire [2:0] step_a,stop_status;wire [3:0] step_g;wire [20:0] steps;
 wire [31:0] cyc_total,cyc_engine,cyc_markov;
 ot_dshbm_dspark_ctl_stop #(.STOP_EN(1),.FAST(1),.MAXPOS(1048576),.MUT(MUT)) dut(
 .clk(clk),.rst_n(rst_n),.start(start),.cfg_gamma(4'd5),.cfg_force(1'b1),
 .cfg_ngen(KIND==1?21'd4:21'd20),.cfg_plen(21'd2),.p_addr(p_addr),.p_tok(17'd5),
 .f_addr(f_addr),.f_tok(17'd100+f_addr),.e_v(e_v),.e_tok(e_tok),.e_idx(e_idx),.e_ready(e_ready),
 .cfg_eos_en(KIND==0),.cfg_eos(17'd102),.cfg_maxpos(KIND==2?21'd5:21'd1048576),.stop_status(stop_status),
 .done(done),.cmd_v(cmd_v),.cmd_ready(1'b1),.cmd_op(cmd_op),.cmd_idx(cmd_idx),.cmd_ncol(cmd_ncol),
 .cmd_pos(cmd_pos),.cmd_tok1(cmd_tok1),.cmd_toks(cmd_toks),.eng_done(eng_done),.am_v(am_v),.am_idx(am_idx),
 .n(n),.n_set(n_set),.n_val(n_val),.tw_v(tw_v),.tw_pos(tw_pos),.tw_tok(tw_tok),
 .step_v(step_v),.step_a(step_a),.step_g(step_g),.steps(steps),.cyc_total(cyc_total),.cyc_engine(cyc_engine),.cyc_markov(cyc_markov));
 integer seen=0,eng_state=0,row=0,rows=0,headpass=0,cycles=0,cmds=0;
 reg [16:0] held_tok;reg held=0;integer stall=0;
 always @(posedge clk) begin
  if(n_set)n<=n_val;
  eng_done<=0;am_v<=0;cycles=cycles+1;
  if(e_v && !e_ready) begin
   if(held && e_tok!==held_tok)$fatal(1,"stall mutated token");held_tok<=e_tok;held<=1;
  end else held<=0;
  if(e_v && e_ready) begin
   if(e_idx!==seen || e_tok!==((seen==0)?17'd7:17'd99+seen))$fatal(1,"stop-aware output reference");
   seen=seen+1;
  end
  if(cmd_v) begin
   if(cmd_op==0 && cmd_pos+cmd_ncol>(KIND==2?5:1048576))$fatal(1,"verify outside job context");
   if(eng_state!=0)$fatal(1,"duplicate command");cmds=cmds+1;
   if(cmd_op==1) begin eng_state=1;row=0;rows=cmd_ncol;headpass=headpass+1;end
   else eng_state=2;
  end else if(eng_state==1) begin
   if(row<rows) begin am_v<=1;am_idx<=(headpass<=2)?17'd7:((row<5)?17'd100+row:17'd200);row=row+1;end
   else begin eng_done<=1;eng_state=0;end
  end else if(eng_state==2) begin eng_done<=1;eng_state=0;end
  if(seen==1 && stall<30) begin e_ready<=0;stall=stall+1;end else e_ready<=1;
 end
 initial begin
  repeat(5) @(negedge clk);rst_n=1;
  @(negedge clk);start=1;@(negedge clk);start=0;
  wait(done);repeat(5) @(negedge clk);
  if(seen!=4 || n!=5 || step_a!=2 || steps!=1 || stop_status!=(KIND==0?1:(KIND==1?2:3)))$fatal(1,"effective accepted-prefix state");
  if($bits(p_addr)!=20 || $bits(f_addr)!=23 || $bits(steps)!=21)$fatal(1,"full context ABI");
  $display("PASS stop-aware nativeMTP KIND=%0d tokens=%0d n=%0d cmds=%0d cycles=%0d",KIND,seen,n,cmds,cycles);$finish;
 end
 initial begin repeat(10000) @(posedge clk);$fatal(1,"watchdog");end
endmodule
