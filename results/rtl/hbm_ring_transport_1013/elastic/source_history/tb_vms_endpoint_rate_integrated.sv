`timescale 1ns/1ps
// Minimum optimistic registered terminator: no wire relays, immediate downstream
// consumption. Uses actual rstop RTL defaults, including D3/HF2/EGC1.
module tb_vms_endpoint_rate;
 parameter integer D=3, HF=2, N=1000, FORWARD=0, S=0;
 reg clk=0, rst_n=0; always #1 clk=~clk;
 reg [289:0] pi='0; wire pi_cr; reg [2223:0] si='0;
 wire [2223:0] lo; reg [1:0] lc=0;
 wire [2223:0] f[0:S];wire [1:0] cr[0:S];
 assign lo=f[S];assign cr[S]=lc;
 for(genvar i=0;i<S;i=i+1) begin:g_station
  ot_vms_elastic #(.D(D)) u(.clk({10{clk}}),.rst_n(rst_n),.f_in(f[i]),.f_out(f[i+1]),.cr_in(cr[i+1]),.cr_out(cr[i]));
 end
 wire [1:0] ic; wire [7:0] eg_cr; wire [2207:0] xq;
 wire [287:0] rce; wire [263:0] cco; wire ri_cr,wki_cr,wko_cr,ack,busy; wire [2:0] wko;
 ot_vms_rstop #(.D(D),.HF(HF)) dut(.clk(clk),.rst_n(rst_n),.sid(2'd0),.dir(1'b0),
  .l_in(si),.l_in_cr(ic),.l_out(f[0]),.l_out_cr(cr[0]),.pi(pi),.pi_cr(pi_cr),
  .eg(2208'd0),.eg_cr(eg_cr),.xq(xq),.xq_cr(8'd0),.xq_done(8'd0),
  .rce(rce),.rce_cr(1'b0),.ri(266'd0),.ri_cr(ri_cr),.wko(wko),.wko_cr(1'b0),
  .wki(3'd0),.wki_cr(wki_cr),.cco(cco),.ack_o(ack),.ack_i(1'b0),.mirror_busy(busy));
 integer issued=0,received=0,credits=(FORWARD ? D : HF),cyc=0,first=-1,last=-1,returned=0;
 initial begin repeat(4) @(negedge clk);rst_n=1;end
 // Credit returned only after receiver captures/consumes the flit at its pin.
 always @(posedge clk) begin
  if(!rst_n) lc<=0;
  else begin
   lc<=lo[2223] ? (lo[2222] ? 2'b10 : 2'b01) : 2'b00;
   if(lo[2223]) begin
    if(lo[2222:2221]!==2'd0 || lo[2220:2217]!==4'b0010 || lo[263:8]!==256'(received)) $fatal(1,"ORDER received=%0d data=%0d",received,lo[263:8]);
    if(first<0) first=cyc;last=cyc;received=received+1;
   end
  end
 end
 always @(negedge clk) if(rst_n) begin
  cyc=cyc+1;
  if(FORWARD ? ic[0] : pi_cr) begin credits=credits+1;returned=returned+1;end
  if(credits<0 || credits>(FORWARD ? D : HF) || credits+issued-returned!=(FORWARD ? D : HF)) $fatal(1,"SOURCE_CREDIT");
  pi=0;si=0;
  if(issued<N && credits>0) begin
   if(FORWARD) begin si[2223]=1'b1;si[2220:2217]=4'b0010;si[263:8]=256'(issued);end
   else pi={1'b1,4'b0010,4'd0,2'(issued),1'b0,3'd0,11'd0,8'hff,256'(issued)};
   issued=issued+1;credits=credits-1;
  end
  if(received==N && returned==N) begin
   $display("PASS endpoint S=%0d FORWARD=%0d D=%0d HF=%0d count=%0d steady_cycles=%0d rate=%f total_cycles=%0d",S,FORWARD,D,HF,received,last-first+1,real'(N)/(last-first+1),cyc);$finish;
  end
  if(cyc>20000) $fatal(1,"TIMEOUT issued=%0d received=%0d",issued,received);
 end
endmodule
