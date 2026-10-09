`timescale 1ps/1fs
module tb_hfd_mtp_x_stop #(parameter KIND=0);
 reg clk=0;always #417 clk=~clk;
 reg rst_n=0,start=0,e_ready=0;wire [19:0] p_addr,e_idx;wire [22:0] f_addr;
 wire e_v,done,cmd_v;wire [16:0] e_tok;wire [3:0] cmd_op,cmd_ncol;
 wire [7:0] cmd_idx;wire [31:0] cmd_pos;wire [16:0] cmd_tok1;wire [135:0] cmd_toks;
 reg eng_done=0,lg_v=0,lg_last=0;reg [7:0] lg_mask=0;reg [255:0] lg_vals=0;
 wire [31:0] n;wire [2:0] step_a,stop_status;wire [20:0] steps;
 hfd_mtp_x_stop dut(.clk(clk),.rst_n(rst_n),.start(start),.cfg_gamma(4'd5),.cfg_force(1'b1),
 .cfg_ngen(KIND==1?21'd4:21'd20),.cfg_plen(21'd2),.p_addr(p_addr),.p_tok(17'd5),
 .f_addr(f_addr),.f_tok(17'd100+f_addr),.e_v(e_v),.e_tok(e_tok),.e_idx(e_idx),.e_ready(e_ready),
 .cfg_eos_en(KIND==0),.cfg_eos(17'd102),.cfg_maxpos(KIND==2?21'd5:21'd1048576),.stop_status(stop_status),
 .done(done),.cmd_v(cmd_v),.cmd_ready(1'b1),.cmd_op(cmd_op),.cmd_idx(cmd_idx),.cmd_ncol(cmd_ncol),
 .cmd_pos(cmd_pos),.cmd_tok1(cmd_tok1),.cmd_toks(cmd_toks),.eng_done(eng_done),
 .lg_v(lg_v),.lg_last(lg_last),.lg_bias_en(1'b0),.lg_mask(lg_mask),.lg_vals(lg_vals),.lg_bias(256'd0),
 .sr_v(1'b0),.sr_kind(4'd0),.sr_idx(16'd0),.sr_pos(32'd0),.n_committed(n),
 .x_v(1'b0),.x_draft(1'b0),.x_ids(54'd0),.x_col(3'd0),
 .u_clr(1'b0),.u_flush(1'b0),.u_ready(1'b1),.step_a(step_a),.steps(steps));
 integer seen=0,eng_state=0,row=0,rows=0,headpass=0,cycles=0,cmds=0,beat=0,target=0;
 reg [16:0] held_tok;reg [19:0] held_idx;reg held=0;integer stall=0;
 always @(posedge clk) begin
  eng_done<=0;lg_v<=0;lg_last<=0;cycles=cycles+1;
  if(e_v && !e_ready) begin
   if(held && (e_tok!==held_tok || e_idx!==held_idx))$fatal(1,"native stalled output changed");held_tok<=e_tok;held_idx<=e_idx;held<=1;
  end else held<=0;
  if(e_v && e_ready) begin
   if(e_idx!==seen || e_tok!==((seen==0)?17'd7:17'd99+seen))$fatal(1,"native stop output reference");seen=seen+1;
  end
  if(cmd_v) begin
   if(cmd_op==0 && cmd_pos+cmd_ncol>(KIND==2?5:1048576))$fatal(1,"native verify beyond context");
   if(eng_state!=0)$fatal(1,"native duplicate command");cmds=cmds+1;
   if(cmd_op==1) begin eng_state=1;row=0;rows=cmd_ncol;headpass=headpass+1;beat=0;end
   else eng_state=2;
  end else if(eng_state==1) begin
   if(row<rows) begin
    target=(headpass<=2)?7:100+row;
    lg_v<=1;lg_vals<=0;lg_mask<=0;
    if(beat==target/8) begin lg_last<=1;lg_mask<=8'b1<<(target%8);lg_vals[(target%8)*32+:32]<=32'h3f800000;row=row+1;beat=0;end
    else beat=beat+1;
   end else begin eng_done<=1;eng_state=0;end
  end else if(eng_state==2) begin eng_done<=1;eng_state=0;end
  if(seen==1 && stall<50) begin e_ready<=0;stall=stall+1;end else e_ready<=1;
 end
 initial begin
  repeat(7) @(negedge clk);rst_n=1;repeat(5) @(negedge clk);
  start=1;@(negedge clk);start=0;
  wait(done);repeat(7) @(negedge clk);
  if(seen!=4 || n!=5 || step_a!=2 || steps!=1 || stop_status!=(KIND==0?1:(KIND==1?2:3)))$fatal(1,"native effective-prefix state");
  $display("PASS actualnativeMTP KIND=%0d tokens=%0d n=%0d cmds=%0d cycles=%0d",KIND,seen,n,cmds,cycles);$finish;
 end
 initial begin repeat(10000) @(posedge clk);$fatal(1,"native watchdog");end
endmodule
