`timescale 1ns/1ps
// S81-RCK-10: OT_S81_CLAND_WCHK landing vs the vI landing, same forwarded clock / data / reset.
// Data q must be identical at every clk edge once both are ready; ready / fault of the new form = the old one, one clk later.
module tb;
parameter real PH = 0.29;
reg clk=0, fclk=0, rst=0; reg [512:0] d=0;
always #0.4165 clk=~clk;
initial begin #PH; forever #0.4165 fclk=~fclk; end
always @(posedge fclk) begin d[511:0] <= {16{$urandom}}; d[512] <= $urandom; end
wire [512:0] qr, qn; wire rr, rn, fr, fn;
cl_ref R(.fclk(fclk),.clk(clk),.rst_n(rst),.d(d),.q(qr),.ready(rr),.fault(fr));
cl_new N(.fclk(fclk),.clk(clk),.rst_n(rst),.d(d),.q(qn),.ready(rn),.fault(fn));
reg rr1, fr1; integer checks=0, err=0, readies=0, ep;
always @(posedge clk) begin rr1<=rr; fr1<=fr; end
always @(posedge clk) begin #0.001;
  if (rst) begin
    if (rn!==rr1 || fn!==fr1) begin err++; if(err<5)$display("BAD ready/fault t=%0t rn%b rr1%b fn%b fr1%b",$time,rn,rr1,fn,fr1); end
    if (rn && rr) begin checks++; if (qn!==qr) begin err++; if(err<5)$display("BAD q t=%0t",$time); end end
  end
end
initial begin
  for (ep=0; ep<5; ep++) begin
    rst=0; repeat(10+ep) @(posedge clk); rst=1;
    repeat(600) @(posedge clk);
    if (rr) readies++;
  end
  $display("CLAND_RESULT ph=%0.3f checks=%0d errors=%0d ready_epochs=%0d fault_ref=%b", PH, checks, err, readies, fr);
  if (err || readies!=5 || fr) $fatal(1, "CLAND lockstep FAILED");
  $finish;
end
endmodule
