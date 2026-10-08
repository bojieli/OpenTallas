`timescale 1ns/1ps
module tb_qwen_ctrl_pc_protected;
 parameter integer PC=0, INJECT=-1, NEG=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,cmd_v=0;reg[31:0]cmd=0;reg[2:0]read_credit=0;
 wire cmd_credit,row_v,col_v,col_we,busy,fault;
 wire[2:0]row_op;wire[4:0]row_bank,col_bank,col_col;wire[18:0]row_row;
 ot_qwen_ctrl_pc_protected #(.ENABLE(1),.PC(PC)) dut(.*);
 wire gc,grv,gcv,gwe,gb,gf;wire[2:0]gro;wire[4:0]grb,gcb,gcc;wire[18:0]grr;
 // Independent unmodified golden controller, driven by the same external input.
 ot_qwen_ctrl_pc #(.ENABLE(1),.PC(PC)) gold(
  .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd(cmd),.read_credit(read_credit),
  .cmd_credit(gc),.row_v(grv),.row_op(gro),.row_bank(grb),.row_row(grr),
  .col_v(gcv),.col_bank(gcb),.col_col(gcc),.col_we(gwe),.busy(gb),.fault(gf));
 integer cycles=0,sent=0,acked=0,reads=0,writes=0,pending=0,ret=0;
 integer accepted_rows=0,accepted_cols=0,first_ref=-1,golden_first_ref=-1;
 integer injected_at=-1,fault_at=-1;reg injected=0,finished=0;
 task fail(input[255:0]why);
  begin $display("FAIL protected %s PC=%0d INJECT=%0d cycle=%0d",why,PC,INJECT,cycles);$fatal(1);end
 endtask
 always @(posedge clk) if(rst_n) begin
  // Sample exactly at the receiving clock edge, before either producer's
  // nonblocking updates. A later fault indication cannot excuse this check.
  if(row_v && (!grv || {row_op,row_bank,row_row}!=={gro,grb,grr})) fail("accepted wrong row command");
  if(col_v && (!gcv || {col_we,col_bank,col_col}!=={gwe,gcb,gcc})) fail("accepted wrong column command");
  if(cmd_credit && !gc)fail("accepted wrong credit");
  if(fault && {cmd_credit,row_v,row_op,row_bank,row_row,col_v,col_bank,col_col,col_we,busy}!==0)fail("accepted command after halt");
  if(cmd_v)sent=sent+1;
  if(cmd_credit)acked=acked+1;
 end
 // These are the stream_ack interface's actual acceptance predicates. A bad
 // packet is a failure even if an internal checker would detect it later.
 always @(negedge clk) if(rst_n) begin
  #0.01;cycles=cycles+1;
  if(row_v && (!grv || {row_op,row_bank,row_row}!=={gro,grb,grr})) fail("wrong row command escaped");
  if(col_v && (!gcv || {col_we,col_bank,col_col}!=={gwe,gcb,gcc})) fail("wrong column command escaped");
  if(cmd_credit && !gc)fail("wrong credit escaped");
  if(!injected && fault!==0)begin $display("DEBUG packets %h %h rails %b%b ft%b",dut.packet[0],dut.packet[1],dut.trip_seen,dut.permit_state,dut.ft);fail("healthy unknown/fault");end
  if(fault)begin
   if(fault_at<0)fault_at=cycles;
   if({cmd_credit,row_v,row_op,row_bank,row_row,col_v,col_bank,col_col,col_we,busy}!==0)fail("fault not fail closed");
  end
  if(!injected && !fault && {cmd_credit,row_v,col_v,col_we,busy}!=={gc,grv,gcv,(gcv&&gwe),gb})fail("fault-free cycle difference");
  if(fault_at>=0 && !fault)fail("halt escaped");
  if(row_v)accepted_rows=accepted_rows+1;
  if(col_v)accepted_cols=accepted_cols+1;
  if(row_v && row_op==6 && first_ref<0)first_ref=cycles;
  if(grv && gro==6 && golden_first_ref<0)golden_first_ref=cycles;
  if(gcv)begin if(gwe)writes=writes+1;else begin reads=reads+1;pending=pending+1;end end
  ret=(cycles%19==0)?(pending>7?7:pending):0;read_credit=3'(ret);pending=pending-ret;
 end
 task send(input[31:0]p);
  begin @(negedge clk);cmd_v=0;while(sent-acked>=8 && !fault)@(negedge clk);
    if(!fault)begin cmd=p;cmd_v=1;end
    @(negedge clk);cmd_v=0;
  end
 endtask
 integer x;
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  send({2'b00,11'd1024,19'd7});send({2'b01,30'd0});
  wait(reads==1024);
  for(x=0;x<64;x=x+1)send({2'b10,20'd0,5'(x),5'(x%32)});
  wait(writes==64 || fault);
  if(!fault)begin send({2'b00,11'd1024,19'd8});send({2'b01,30'd0});wait(reads==2048);end
  repeat(500)@(negedge clk);
  if(INJECT<0)begin
   if(fault!==0 || gf!==0 || sent!=acked || reads!=2048 || writes!=64 || first_ref!=golden_first_ref)fail("healthy final gate");
   $display("PASS protected PC=%0d reads=%0d writes=%0d rows=%0d columns=%0d first_ref=%0d credits=%0d",PC,reads,writes,accepted_rows,accepted_cols,first_ref,acked);$finish;
  end
 end
 initial begin
  wait(rst_n);
  if(INJECT>=0)begin
   if(NEG)force dut.agree=1'b1;
   case(INJECT)
    0:begin wait(dut.g_replica[0].u.count!=0);@(negedge clk);#0.1;
      dut.g_replica[0].u.head=dut.g_replica[0].u.head ^ 32'b1;end
    1:begin wait(dut.g_replica[0].u.core.on.wr_ok && dut.g_replica[0].u.core.on.hb==0);@(negedge clk);#0.1;
      dut.g_replica[0].u.core.on.write_ready_bank=dut.g_replica[0].u.core.on.write_ready_bank ^32'b1;end
    2:begin wait(dut.g_replica[0].u.core.on.wq_n>1);@(negedge clk);#0.1;
      dut.g_replica[0].u.core.on.wq_oh[0]=dut.g_replica[0].u.core.on.wq_oh[0] ^ 32'b1;end
    3:begin wait(dut.g_replica[0].u.core.on.ref_c==8);@(negedge clk);#0.1;
      dut.g_replica[0].u.core.on.ref_c=dut.g_replica[0].u.core.on.ref_c ^ 4;end
    4:begin repeat(12)@(negedge clk);#0.1;dut.g_replica[0].u.cmd_credit=~dut.g_replica[0].u.cmd_credit;end
    5:begin repeat(12)@(negedge clk);#0.1;dut.trip_seen=1;end
    6:begin repeat(12)@(negedge clk);#0.1;dut.permit_state=0;end
    7:begin repeat(12)@(negedge clk);#0.1;dut.g_replica[1].u.cmd_credit=~dut.g_replica[1].u.cmd_credit;end
   endcase
   injected=1;injected_at=cycles;
   wait(fault);repeat(5)@(negedge clk);
   // After a latched halt, corrupt either sticky bit toward release. Its other
   // independent rail must continue to prohibit every command and credit.
   #0.1;dut.trip_seen=0;#0.1;if(!fault)fail("trip rail release");
   repeat(2)@(negedge clk);#0.1;dut.permit_state=1;#0.1;if(!fault)fail("permit rail release");
   repeat(8)@(negedge clk);
   $display("PASS protected upset PC=%0d target=%0d injected=%0d fault=%0d accepted_rows=%0d accepted_cols=%0d wrong_accepted=0",PC,INJECT,injected_at,fault_at,accepted_rows,accepted_cols);$finish;
  end
 end
 initial begin #2000000;fail("watchdog");end
endmodule
