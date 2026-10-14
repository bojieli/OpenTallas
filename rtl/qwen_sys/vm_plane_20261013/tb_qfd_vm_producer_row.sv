`timescale 1ns/1ps
module tb_qfd_vm_producer_row;
parameter integer MUT=0;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,request_v=0; wire request_ready;
reg [2:0] bank=0; reg [7:0] row=0;
wire [7:0] re; wire [63:0] ra; wire rq; wire [2:0] rqb;
wire [511:0] ro,data; wire response_v,commit,pending;
reg [7:0] we=0; reg [63:0] wl=0; reg [127:0] wm=0; reg [4095:0] wd=0;
wire [4095:0] xo; wire [3071:0] so; wire ovf;
integer b,a,i,elapsed,reads=0,commits=0;
function automatic [511:0] pattern(input integer bank_i,input integer row_i);
 integer j; begin for(j=0;j<512;j=j+1) pattern[j]=((j+bank_i*7+row_i*13)%5)<2; end
endfunction
ot_qfd_vm_producer_row_binding #(.MUT(MUT)) binding(
.clk(clk),.rst_n(rst_n),.request_v(request_v),.request_ready(request_ready),.decoded_bank(bank),.decoded_row(row),
.re(re),.ra(ra),.rq(rq),.rqb(rqb),.native_ro(ro),.response_v(response_v),.response_ready(1'b1),.response_data(data),
.accepted_write(|we),.commit_v(commit),.commit_pending(pending));
ot_qfd_vm_region_leaf #(.DEPTH(174),.LAW(8),.DEPTHS(695),.LAWS(10),.USE_MACRO(0)) native(
.clk(clk),.leaf_clocks(72'b0),.rst_entries(17'b0),.me_entries(25'b0),.xv_entries(9'b0),.pop_entries(9'b0),
.sv_entries(6'b0),.swe_entries(6'b0),.swl_entries(60'b0),.swm_entries(96'b0),.swd_entries(3072'b0),.rqb_entries(4'b0),
.rst_n(rst_n),.me_in(1'b0),.re(re),.ra(ra),.we(we),.wl(wl),.wm(wm),.wd(wd),.xv(1'b0),.rq(rq),.rqb(rqb),
.sre(6'b0),.sra(60'b0),.sv(3'b0),.swe(2'b0),.swl(20'b0),.swm(32'b0),.swd(1024'b0),.pop(1'b0),.xo(xo),.ro(ro),.so(so),.ovf(ovf));
task tick; begin @(posedge clk); #1; @(negedge clk); end endtask
always @(posedge clk) if(rst_n&&commit) commits=commits+1;
initial begin
 repeat(4) tick(); rst_n=1; repeat(16) tick();
 for(a=0;a<2;a=a+1) begin
  for(b=0;b<8;b=b+1) begin wl[b*8+:8]=a; wd[b*512+:512]=pattern(b,a); end
  wm={128{1'b1}}; we=8'hff; tick(); we=0; wm=0; repeat(12) tick();
 end
 if(commits!=2||pending) $fatal(1,"actual commit observer mismatch");
 for(i=0;i<64;i=i+1) begin
  bank=i%8; row=(i/8)%2; request_v=1; tick(); request_v=0; elapsed=0;
  while(!response_v) begin tick(); elapsed=elapsed+1; if(elapsed>16) $fatal(1,"native read timeout"); end
  if(data!==pattern(bank,row)) $fatal(1,"ROW all512 mismatch bank%0d row%0d latency%0d",bank,row,elapsed);
  if(elapsed!=10) $fatal(1,"ROW latency mismatch %0d",elapsed);
  reads=reads+1; tick(); repeat(i%5) tick();
 end
 $display("PASS native ROW %0d reads all512bits, 8banks x2addresses, exact10CLOCK accepted-query response, commits=%0d",reads,commits); $finish;
end
initial begin #1000000; $fatal(1,"timeout"); end
endmodule
