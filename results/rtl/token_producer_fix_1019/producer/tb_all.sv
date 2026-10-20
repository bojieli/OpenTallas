`timescale 1ns/1ps
module tb;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,we=0,start=0;reg[15:0] bank=0;reg[6:0] row=0;reg[255:0] data=0;
wire busy,valid,done,fault;wire[15:0] edge_index;wire[2421:0] command;
reg[279:0] cfg[0:4095];reg[2421:0] exp[0:7110];integer cyc=-1,s=-1,n=0,first=-1;string fn;integer want_startup=9,N=44,W=56;string goldfile;
ot_hbm_su_programme_pslice_c5 dut(.clk(clk),.rst_n(rst_n),.cfg_we(we),.cfg_bank(bank),.cfg_row(row),.cfg_data(data),.start(start),.length(16'(N)),.busy(busy),.valid(valid),.done(done),.fault(fault),.edge_index(edge_index),.command(command));
always @(posedge clk) if(rst_n) begin
 cyc=cyc+1;
 if(start)s=cyc;
 if(valid)begin
  if(first<0)begin first=cyc;if(cyc-s!=want_startup)$fatal(1,"PRODUCER FAIL startup got=%0d expected=%0d",cyc-s,want_startup);end
  $display("CMD e=%0d delta=%0d got=%h",edge_index,cyc-s,command);
  if(edge_index!=n || command!==exp[n] || fault)$fatal(1,"PRODUCER FAIL edge=%0d n=%0d fault=%b",edge_index,n,fault);
  n=n+1;
 end
end
initial begin
 if(!$value$plusargs("CFG=%s",fn))$fatal;
 $value$plusargs("STARTUP=%d",want_startup);
 $value$plusargs("N=%d",N);$value$plusargs("W=%d",W);if(!$value$plusargs("GOLD=%s",goldfile))goldfile="expected.mem";
 $readmemh(fn,cfg);$readmemh(goldfile,exp);
 repeat(3)@(negedge clk);rst_n=1;repeat(12)@(negedge clk);
 for(integer i=0;i<W;i=i+1)begin we=1;bank=cfg[i][279:264];row=cfg[i][262:256];data=cfg[i][255:0];@(negedge clk);end
 we=0;repeat(2)@(negedge clk);start=1;@(negedge clk);start=0;
 repeat(N+30)@(negedge clk);
 if(n!=N || fault)$fatal(1,"PRODUCER FAIL count=%0d fault=%b",n,fault);
 $display("PRODUCER PASS commands=%0d startup_consumer=%0d",n,first-s);$finish;
end
endmodule
