`timescale 1ns/1ps
module tb_hbm_su_f2_native_banks;
 parameter MUT_ROUTE=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 reg[543:0]rq=0;reg[8991:0]wq=0;
 wire[543:0]vrq;wire[8991:0]vwq;
 wire[8223:0]rr,sr;wire[3:0]fault;
 reg[3:0]load=0;reg[1023:0]operand=0;reg[31:0]replay=0;
 wire[575:0]status;
 ot_hbm_su_f2_static_link #(.RD_LAT(7),.MUT_ROUTE(MUT_ROUTE))d(
 .quarter_clk({4{clk}}),.rst_n(rst_n),.su_rq(rq),.su_wq(wq),.vm_rq(vrq),.vm_wq(vwq),.vm_rr(rr),.su_rr(sr),
 .operand_load(load),.operand_data(operand),.operand_replay(replay),.fault(fault));
 for(genvar q=0;q<4;q=q+1)begin:g_q
  localparam RG=q<2?3:5,WG=q<2?1:3;
  for(genvar b=0;b<8;b=b+1)begin:g_b
   localparam I=q*8+b;
   wire[RG*17-1:0]brq={{(RG-1)*17{1'b0}},vrq[I*17+:17]};
   wire[WG*281-1:0]bwq={{(WG-1)*281{1'b0}},vwq[I*281+:281]};
   wire[RG*257-1:0]brr;
   ot_vms_bank_static #(.RG(RG),.WG(WG))bank(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'(q)),
    .rslot_v(1'b1),.rslot(0),.wslot_v(1'b1),.wslot(0),.rq(brq),.rr(brr),.wq(bwq),.wq_done(),
    .dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
    .eg(),.pq(285'd0),.pr(),.status(status[I*18+:18]));
   assign rr[I*257+:257]=brr[256:0];
  end
 end
 integer q,b,c,i,k,errors=0,checks=0,cycle=0;
 integer rdrow=0,received=0;reg checking=0;
 function automatic[15:0]addr(input integer quadrant,input integer bank,input integer row);
 addr=(16'(quadrant)<<13)|(16'(row)<<3)|16'(bank);endfunction
 function automatic[255:0]data(input integer row,input integer lane);
 integer k;begin for(k=0;k<8;k=k+1)data[k*32+:32]=32'(row*4096+lane*8+k);end endfunction
 always @(posedge clk)begin
  cycle=cycle+1;
  #2;
  if(checking&&sr[256])begin
   for(i=0;i<32;i=i+1)begin
    checks=checks+1;
    if(sr[i*257+256]!==1'b1||sr[i*257+:256]!==((rdrow%3==0)?data(900,i/8):data(rdrow,i)))begin
     if(errors<5)$display("ERR row=%0d lane=%0d actual=%h",rdrow,i,sr[i*257+:256]);errors=errors+1;
    end
   end
   rdrow=rdrow+1;received=received+32;
  end
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;load=15;
  for(q=0;q<4;q=q+1)operand[q*256+:256]=data(900,q);
  @(negedge clk);load=0;
  for(c=0;c<512;c=c+1)begin
   for(q=0;q<4;q=q+1)for(b=0;b<8;b=b+1)begin
    i=q*8+b;wq[i*281+:281]={1'b1,addr(q,b,c),data(c,i),8'hff};replay[i]=(c%3==0);
   end
   @(negedge clk);
  end
  wq=0;replay=0;repeat(12)@(negedge clk);checking=1;
  for(c=0;c<512;c=c+1)begin
   for(q=0;q<4;q=q+1)for(b=0;b<8;b=b+1)rq[(q*8+b)*17+:17]={1'b1,addr(q,b,c)};
   @(negedge clk);
  end
  rq=0;repeat(15)@(negedge clk);checking=0;
  if(received!=16384)begin $display("ERR received=%0d",received);errors=errors+1;end
  if(fault!==0)begin $display("ERR link_fault=%h",fault);errors=errors+1;end
  if(status!==0)begin $display("ERR bank_status=%h",status);errors=errors+1;end
  if(errors)$fatal(1,"F2_NATIVE FAIL checks=%0d errors=%0d",checks,errors);
  $display("F2_NATIVE PASS checks=%0d actual_banks=32 actual_sram_macros=96 sectors=16384 words=131072 read_and_write_sectors_per_edge=32",checks);$finish;
 end
endmodule
