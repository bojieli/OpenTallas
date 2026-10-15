`timescale 1ns/1ps
module tb_s81_head_gain_stream;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0,draft=0;
 wire ce,v,busy,done,fault;wire[11:0]addr;wire[13:0]row;wire[15:0]mask;wire[511:0]data;
 wire[287:0]pq;wire[255:0]rd={pq[216+:64],pq[144+:64],pq[72+:64],pq[0+:64]};
 reg[3:0]due=0;
 wire commit=due[3] && !(MUT==1);
 ot_s81_head_gain_stream #(.MUT_GAIN(MUT==2)) dut(.clk(clk),.rst_n(rst_n),.start(start),.draft(draft),.vm_base_row(14'd4096),
  .rom_ce(ce),.rom_addr(addr),.rom_data(rd),.wq_v(v),.wq_row(row),.wq_mask(mask),.wq_d(data),.wq_commit(commit),.busy(busy),.done(done),.fault(fault));
 for(genvar m=0;m<4;m=m+1)begin:g_rom
  ot_rom_4096x72_m8 #(.INSTANCE($sformatf("hcx_post_p%0d",m)))rom(.clk(clk),.ce_in(ce),.addr_in(addr),.rd_out(pq[72*m+:72]));
 end
 reg[31:0]expected0[0:5119],expected1[0:5119];
 reg[8191:0]dir;integer i,n,age,errors,total;
 always@(posedge clk)if(!rst_n)due<=0;else due<={due[2:0],v};
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIRmissing");
  $readmemh({dir,"/gain0.mem"},expected0);$readmemh({dir,"/gain1.mem"},expected1);
  errors=0;total=0;repeat(4)@(negedge clk);rst_n=1;
  for(integer mode=0;mode<2;mode=mode+1)begin
   @(negedge clk);draft=mode;start=1;@(negedge clk);start=0;n=0;age=0;
   while(!done && age<400)begin
    if(v)begin
     if(row!=4096+n || mask!=16'hffff)errors=errors+1;
     for(i=0;i<16;i=i+1)if(data[32*i+:32]!=(mode?expected1[16*n+i]:expected0[16*n+i]))errors=errors+1;
     n=n+1;
    end
    @(negedge clk);age=age+1;
   end
   if(n!=320 || age!=326 || (fault!=(MUT==1)))errors=errors+1;
   total=total+n;
   repeat(4)@(negedge clk);
  end
  $display("S81_GAIN_STREAM %s rows=%0d errors=%0d fault=%0d mut=%0d",errors==0?"PASS":"FAIL",total,errors,fault,MUT);
  if(errors)$fatal(1,"gain stream mismatch");$finish;
 end
endmodule
