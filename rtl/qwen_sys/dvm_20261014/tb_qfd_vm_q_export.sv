`timescale 1ns/1ps
module tb_qfd_vm_q_export;
 parameter integer MUT_BEAT=0,MUT_FENCE=0;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,epoch_begin=0,start_v=0;
 reg [511:0] commit_mask=0;
 wire ready,committed,rv;wire [19:0] row;reg rr=0;
 reg rsp_v=0;reg [511:0] rsp_data=0;wire [523:0] q;
 reg cr=0;wire done,fault;
 ot_qfd_vm_q_export #(.ENABLE(1),.MUT_BEAT(MUT_BEAT),.MUT_FENCE(MUT_FENCE)) dut
 (.clk(clk),.rst_n(rst_n),.epoch_begin(epoch_begin),.commit_mask(commit_mask),
 .start_v(start_v),.start_ready(ready),.qr_committed(committed),
 .read_v(rv),.read_row(row),.read_ready(rr),.rsp_v(rsp_v),.rsp_data(rsp_data),
 .q(q),.q_cr(cr),.emitted_done(done),.fault(fault));
 reg [31:0] bank_we=0;reg [511:0] wd=0;
 wire [32*512-1:0] bank_q;
 genvar b;
 generate for(b=0;b<32;b=b+1)begin:g_b
  ot_qfd_vm_rowbank #(.DEPTH(256),.LAW(8),.USE_MACRO(0)) mem
  (.clk(clk),.re(rv&&rr&&(row==856+b)),.raddr(8'd13),.q(bank_q[b*512+:512]),
   .we(bank_we[b]),.waddr(8'd13),.wmask(16'hffff),.wdata(wd));
 end endgenerate
 integer cyc=0,count=0,epoch=0,k,j,debt=0;reg pend=0;reg [4:0] rb;
 function automatic [31:0] word(input integer e,input integer beat,input integer lane);
  word=32'h3f000000^(e*32'h00100000)^(beat*32'h00010000)^(lane*32'h10203);
 endfunction
 always @(negedge clk)begin
  if(rst_n)begin
   cyc=cyc+1;rr=(cyc%5!=0);cr=0;
   if(q[523])begin
    if(q[522:512]!={3'b001,2'b00,1'b0,5'(count)})$fatal(1,"Q tag beat %0d",count);
    for(j=0;j<16;j=j+1)if(q[j*32+:32]!==word(epoch,count,j))$fatal(1,"Q bits epoch %0d beat %0d lane %0d",epoch,count,j);
    count=count+1;debt=debt+1;
   end
   if(debt!=0&&cyc%7==0)begin cr=1;debt=debt-1;end
   if(fault)$fatal(1,"unexpected exporter fault");
   if(cyc>2000)$fatal(1,"timeout");
  end
 end
 always @(posedge clk)begin
  rsp_v<=pend;
  if(pend)rsp_data<=bank_q[rb*512+:512];
  pend<=rv&&rr;
  if(rv&&rr)rb<=row-856;
 end
 task tick;begin @(posedge clk);#0.1;end endtask
 initial begin
  repeat(3)tick();rst_n=1;
  for(epoch=0;epoch<3;epoch=epoch+1)begin
   epoch_begin=1;tick();epoch_begin=0;count=0;start_v=1;
   // A held request cannot read partly committed Q or previous-epoch Q.
   for(k=0;k<32;k=k+1)begin
    if(ready||rv)$fatal(1,"Q fence allowed incomplete epoch at row %0d",k);
    for(j=0;j<16;j=j+1)wd[j*32+:32]=word(epoch,k,j);
    bank_we=32'd1<<k;commit_mask=512'd0;commit_mask[k*16+:16]=16'hffff;
    tick();bank_we=0;commit_mask=0;
   end
   if(!committed||!ready)$fatal(1,"all actual writes did not fence");
   tick();start_v=0;
   wait(done);tick();if(count!=32)$fatal(1,"wrong count %0d",count);
   // Returned credits may arrive after the completion pulse.
   wait(debt==0);repeat(3)tick();
  end
  $display("PASS Q export 3 production epochs,96x512 binary32 rows, commit fence and credit stalls");$finish;
 end
endmodule
