`timescale 1ns/1ps
module tb_idx_tail_score_fault;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg iv=0;reg[3:0]ikv=0,ikeep=0;reg[511:0]isum=0;reg[15:0]ifault=0;
 wire ov;wire[3:0]okv,ofault;wire[63:0]oscore;wire fatal;integer checked=0;
 ot_hbm_idx_tail_native tail(.clk(clk),.rst_n(rst_n),.i_v(iv),.i_kv(ikv),.i_keep(ikeep),.i_sum(isum),.i_fault(ifault),.o_v(ov),.o_kv(okv),.o_score(oscore),.o_fault(ofault));
 ot_hbm_idx_score_fault_static checker_i(.clk(clk),.rst_n(rst_n),.score_status({4'd0,okv,4'd0,ofault,1'b0,ov}),.protocol_fault(4'd0),.fault(fatal));
 task tick;begin @(posedge clk);#1;end endtask
 task run_case(input integer kind);
 integer saw;bit expected_fault;
 begin
  @(negedge clk);rst_n=0;iv=0;ikv=0;ikeep=0;isum=0;ifault=0;repeat(8)tick();
  @(negedge clk);rst_n=1;repeat(8)tick();
  @(negedge clk);iv=1;ikv=(kind==3)?4'd0:4'd1;ikeep=4'hf;ifault=(kind==1||kind==3)?16'd1:16'd0;
  for(integer c=0;c<16;c++)isum[c*32+:32]=(kind==2)?32'h7f7fffff:32'h3f800000;
  expected_fault=(kind==1||kind==2);saw=0;
  for(integer age=0;age<40;age++)begin
   tick();
   if(ov)begin
    saw++;
    if(kind!=3 && okv!==4'd1)$fatal(1,"IDX_TAIL_FAULT_FAIL kv kind=%0d",kind);
    if(kind==0 && (ofault[0]||oscore[15:0]!==16'h4080))$fatal(1,"IDX_TAIL_FAULT_FAIL finite golden4.0");
    if(kind!=0 && (!ofault[0]||oscore[15:0]!==16'h0000))$fatal(1,"IDX_TAIL_FAULT_FAIL failclosed zero/flag kind=%0d",kind);
   end
   if(age==0)begin @(negedge clk);iv=0;end
  end
  if(saw!=1||fatal!==expected_fault)$fatal(1,"IDX_TAIL_FAULT_FAIL kind=%0d saw=%0d fatal=%b expected=%b",kind,saw,fatal,expected_fault);
  checked++;
 end endtask
 initial begin
  for(integer k=0;k<4;k++)run_case(k);
  $display("IDX_TAIL_FAULT_PASS cases=%0d finite4.0 fault-to-zero actual-overflow invalid-key-ignored",checked);$finish;
 end
endmodule
