`timescale 1ns/1ps
module tb;
parameter integer IS=1, OS=1;
reg clk=0; always #5 clk=~clk;
reg rst_n=0;
reg [23:0] acc=0; reg idle=0; reg [15:0] prog=0, rows=0;
reg layer_start=0, package_start=0; reg [17:0] token=0,pos=0;reg [11:0] base=0;
reg issue=0;
wire [23:0] acc_o;wire idle_o;wire [15:0] prog_o,rows_o;
wire start_o;wire [17:0] tok_o,pos_o;wire [11:0] base_o;
ot_qfd_seq_su_boundary #(.IS(IS),.OS(OS)) dut(.clk(clk),.rst_n(rst_n),
 .h_start(package_start),.pi_su_acc(acc),.pi_su_idle(idle),.pi_su_progress(prog),.pi_su_progress_rows(rows),
 .su_acc_o(acc_o),.su_idle_o(idle_o),.su_prog_o(prog_o),.su_rows_o(rows_o),
 .me_start_o(start_o),.me_token_o(tok_o),.me_pos_o(pos_o),.me_prog_base_o(base_o));
reg [56:0] qs[0:8]; reg [48:0] qt[0:8];integer i,n,accepted=0;
initial begin
 // Only the sequencer/controller interiors are isolated. The emitted top's
 // real pin delay stations and their source wiring execute without stubs.
 force dut.core_start=layer_start;
 force dut.core_tokw=token; force dut.core_pos=pos; force dut.prog_base=base;
 force dut.b_po_su_go=issue;
 for(i=0;i<9;i=i+1)begin qs[i]=0;qt[i]=0;end
 repeat(4) @(negedge clk);rst_n=1;
 for(n=0;n<100;n=n+1)begin
  // Endpoint acceptance lags and sometimes ignores controller issue.
  // Nonzero unrelated package_start must never launch an ME layer.
  issue=(n%3==0);package_start=(n%7==0);layer_start=(n==9 || n==31 || n==73);
  if(n%11==0)accepted=accepted+1;
  acc=accepted; idle=(n%11==10);prog=n*17;rows=n*3;
  token=18'h1a000+n;pos=18'h25000+n;base=n*2;
  @(posedge clk);
  for(i=8;i>0;i=i-1)begin qs[i]=qs[i-1];qt[i]=qt[i-1];end
  qs[0]={acc,idle,prog,rows};qt[0]={layer_start,token,pos,base};
  #1;
  if({acc_o,idle_o,prog_o,rows_o} !== qs[(IS+OS==0)?0:IS+OS-1])
   $fatal(1,"snapshot mismatch n=%0d IS=%0d OS=%0d got=%h expected=%h",n,IS,OS,{acc_o,idle_o,prog_o,rows_o},qs[(IS+OS==0)?0:IS+OS-1]);
  if({start_o,tok_o,pos_o,base_o} !== qt[(OS==0)?0:OS-1])
   $fatal(1,"layer launch mismatch n=%0d",n);
  @(negedge clk);
 end
 rst_n=0;#1;
 if(IS+OS>0 && {acc_o,idle_o,prog_o,rows_o} !== 57'd0)$fatal(1,"snapshot reset incomplete");
 $display("PASS boundary IS=%0d OS=%0d 100 snapshots three independent layer launches",IS,OS);$finish;
end
endmodule
