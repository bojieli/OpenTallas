`timescale 1ns/1ps
module tb;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,we=0,start=0;reg[15:0] bank=0;reg[6:0] row=0;reg[255:0] data=0;
wire busy,valid,done,fault;wire[15:0] edge_index;wire[2421:0] command;
reg[279:0] cfg[0:55];reg[2421:0] exp[0:43];integer cyc=-1,s=-1,n=0,first=-1;string fn;integer want_startup=9;
ot_hbm_su_programme_pslice_c5 dut(.clk(clk),.rst_n(rst_n),.cfg_we(we),.cfg_bank(bank),.cfg_row(row),.cfg_data(data),.start(start),.length(16'd44),.busy(busy),.valid(valid),.done(done),.fault(fault),.edge_index(edge_index),.command(command));
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
 $readmemh(fn,cfg);$readmemh("expected.mem",exp);
 repeat(3)@(negedge clk);rst_n=1;repeat(12)@(negedge clk);
 for(integer i=0;i<56;i=i+1)begin we=1;bank=cfg[i][279:264];row=cfg[i][262:256];data=cfg[i][255:0];@(negedge clk);end
 we=0;repeat(2)@(negedge clk);start=1;@(negedge clk);start=0;
 repeat(70)@(negedge clk);
 if(n!=44 || fault)$fatal(1,"PRODUCER FAIL count=%0d fault=%b",n,fault);
 $display("PRODUCER PASS commands=%0d startup_consumer=%0d",n,first-s);$finish;
end
endmodule
