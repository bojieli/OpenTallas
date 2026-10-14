`timescale 1ns/1ps
module tb_hgi_hc_win;
`ifndef WMUT
`define WMUT 0
`endif
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0,start=0,rel=0,hr_v=0,re=0,hq_cr=0;reg[5:0]nwords=0;
 reg[10:0]hr_tag=0;reg[1:0]hr_beat=0;reg[255:0]hr_data=0;reg[15:0]addr=0;
 wire rv,hqv,ready,fault;wire[1023:0]rom;wire[34:0]ha;wire[2:0]hl;wire[10:0]ht;
`ifdef HC_WIN_PARTITIONED
 ot_hgi_hc_win_partitioned #(.MUT(`WMUT))dut(.clk_ctl(clk),.clk_mem0(clk),.clk_mem1(clk),.clk_mem2(clk),.clk_mem3(clk),
`else
 ot_hgi_hc_win #(.MUT(`WMUT))dut(.clk(clk),
`endif
 .rst_n(rst_n),.c_start(start),.c_rel(rel),
  .c_base(35'd123),.c_soff(35'd77),.c_nwords(nwords),.c_bound(16'd64),.c_limit(16'd96),
  .hr_v(hr_v),.hr_tag(hr_tag),.hr_beat(hr_beat),.hr_data_lo(hr_data[127:0]),.hr_data_hi(hr_data[255:128]),.rom_re(re),.rom_addr(addr),
  .rom_v(rv),.rom_0(rom[127:0]),.rom_1(rom[255:128]),.rom_2(rom[383:256]),.rom_3(rom[511:384]),
  .rom_4(rom[639:512]),.rom_5(rom[767:640]),.rom_6(rom[895:768]),.rom_7(rom[1023:896]),.hq_v(hqv),.hq_addr(ha),.hq_len(hl),.hq_tag(ht),.hq_cr(hq_cr),.ready(ready),.fault(fault));
 reg[34:0]requests[0:31];reg[10:0]tags[0:31];
 integer req=0,errors=0,seats=1,credit_wait=0,checks=0,t,word_,beat;
 reg[1023:0]expected[0:31];
 function automatic[255:0]pattern(input integer row,input integer b);
  reg[255:0]d;begin for(integer k=0;k<8;k=k+1)d[k*32+:32]=32'h3f800000^(row*32+b*8+k);pattern=d;end
 endfunction
 always @(negedge clk)begin
  hq_cr=0;
  if(rst_n)begin
   if(credit_wait>0)begin credit_wait=credit_wait-1;if(credit_wait==0)begin hq_cr=1;seats=seats+1;end end
   if(hqv)begin
    if(seats<=0)begin errors=errors+1;$display("ERR request without receiver credit");end
    seats=seats-1;credit_wait=7;
    if(req>=32)$fatal(1,"request overflow");
    requests[req]=ha;tags[req]=ht;
    if(hl!=4||ha!=200+req*4||ht!=req)begin errors=errors+1;$display("ERR request mapping row %0d addr %0d tag %0d",req,ha,ht);end
    req=req+1;
   end
  end
 end
 initial begin
  for(word_=0;word_<32;word_=word_+1)for(beat=0;beat<4;beat=beat+1)expected[word_][beat*256+:256]=pattern(word_,beat);
  repeat(4)@(negedge clk);rst_n=1;repeat(6)@(negedge clk);
 `ifdef HC_WIN_PARTITIONED
  // Small rows leave striped windows empty. Releasing those windows is a no-op.
  rel=1;@(negedge clk);rel=0;repeat(8)@(negedge clk);
  if(fault||hqv)begin errors++;$display("ERR empty window release");end
 `endif
  nwords=32;repeat(4)@(negedge clk);start=1;@(negedge clk);start=0;
  t=0;while(req<32&&t<2000)begin @(posedge clk);t=t+1;end
  if(req!=32)$fatal(1,"request timeout %0d",req);
  // Response order is reverse row and reverse beat, independent of request order.
  for(word_=31;word_>=0;word_=word_-1)for(beat=3;beat>=0;beat=beat-1)begin
   @(negedge clk);hr_v=1;hr_tag=tags[word_];hr_beat=2'(beat);hr_data=pattern(word_,beat);
  end
  @(negedge clk);hr_v=0;t=0;while(!ready&&t<100)begin @(posedge clk);t=t+1;end
  if(!ready||fault)$fatal(1,"window not ready/fault after fill %0d %0d",ready,fault);
  // Exercise every actual 128x256 macro row occupied by the window, with gaps.
  for(word_=0;word_<32;word_=word_+1)begin
   @(negedge clk);re=1;addr=16'(64+word_);@(negedge clk);re=0;t=0;
   while(!rv&&t<20)begin @(negedge clk);t=t+1;end
   if(!rv||rom!==expected[word_])begin errors=errors+1;$display("ERR ROM row %0d latency %0d",word_,t);end
   checks=checks+1;repeat(3)@(negedge clk);
  end
  // Out-of-bound read must never expose another window's payload.
  re=1;addr=16'd96;@(negedge clk);re=0;repeat(6)@(negedge clk);
  if(rv||rom!=0)begin errors=errors+1;$display("ERR unselected ROM leaks data");end
  $display("HC_WIN summary req=%0d rows=%0d errors=%0d fault=%0d",req,checks,errors,fault);
  if(errors==0&&!fault)$display("HC_WIN PASS");else $display("HC_WIN FAIL");
  $finish;
 end
endmodule
