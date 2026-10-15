`timescale 1ns/1fs
// Numerical composition diagnostic on a declared ideal same-frequency family.
// Window reservations are fixed; measured FEC age is used ONLY by the checker,
// never by DUT issue logic. Physical phases/production epoch remain separate.
module tb_fec_static_window;
 parameter integer DMUT=0;
 localparam integer N=2048,CS=600,RS=608;
 reg clk=0,rst_n=0;
 always #0.416667 clk=~clk;
 reg [486:0] tx=0;
 wire [486:0] rx;wire rv,padding;
 wire [1:0] st;wire [543:0] pads;wire pck;
 reg [543:0] channel;
 integer cycle=0,age=-1,diag=0,checked=0;
 reg cap_start=0,cap_take=0,cap_last=0,read_start=0,read_take=0,read_last=0;
 hfd_serdes487_static_window #(.DMUT(DMUT),.WINDOW_WORDS(N)) u(
 .clk(clk),.clk_collect(clk),.clk_encode(clk),.clk_codeword(clk),
 .rclk_syndrome(clk),.rclk_bm0(clk),.rclk_bm1(clk),.rclk_bm2(clk),.rclk_bm3(clk),.rclk_chien(clk),.rclk_emit(clk),
 .rst_n(rst_n),.tx(tx),.capture_start(cap_start),.capture_take(cap_take),.capture_last(cap_last),
 .read_start(read_start),.read_take(read_take),.read_last(read_last),.rx(rx),.rx_v(rv),.st(st),.padding_fault(padding),
 .pma_tx(pads),.pma_tck(pck),.pma_rx(channel),.pma_rck(clk));
 function automatic [486:0] pattern(input integer index);
  integer k;begin
   pattern=0;
   for(k=32;k<487;k=k+1)pattern[k]=((index*17+k*71)>>(k%13))&1;
   pattern[31:0]=index;
   if(index%13==0)pattern=487'd2;
  end
 endfunction
 always @(negedge clk)begin
  tx=pattern(cycle+1);
  cap_start=(cycle+1==CS);
  cap_take=(cycle+1>=CS+1 && cycle+1<=CS+N);
  cap_last=(cycle+1==CS+N);
  read_start=(cycle+1==RS);
  read_take=(cycle+1>=RS+1 && cycle+1<=RS+N);
  read_last=(cycle+1==RS+N);
  channel=pads;
  // At most a few erroneous symbols per codeword, inside KP4 t=15.
  if(cycle%3==0)channel[101]=~pads[101];
 end
 always @(posedge clk)begin:fec_check
  integer incoming_id;
  reg [486:0] sampled;
  reg had_word;
  sampled=u.qd[486:0];had_word=u.qv;
  cycle=cycle+1;
  if(rst_n && cycle>300 && had_word)begin
   if(age<0 && sampled!=487'd2)begin
    incoming_id=sampled[31:0];age=cycle-incoming_id;
    if(age<1 || age>299)$fatal(1,"invalid measured FEC age %0d",age);
   end
   if(age>=0)begin
    if(sampled!==pattern(cycle-age))$fatal(1,"FEC word error at cycle%0d age%0d",cycle,age);
    diag=diag+1;
   end
  end
  #0.000001;
  if(rst_n && (st[0] || padding))$fatal(1,"FEC/window fault cycle%0d st%b",cycle,st);
  if(cycle>=RS+1 && cycle<=RS+N)begin
   if(!rv || age<0 || rx!==pattern(CS+(cycle-RS)-age))$fatal(1,"window word error cycle%0d age%0d",cycle,age);
   checked=checked+1;
  end
  if(cycle==RS+N+20)begin
   if(checked!=N || diag<N || !st[1])$fatal(1,"coverage checked%0d diag%0d",checked,diag);
   $display("PASS actual FEC static-window words=%0d corrected_channel age=%0d diagnostic_words=%0d",checked,age,diag);$finish;
  end
 end
 initial begin repeat(8)@(negedge clk);rst_n=1;end
 initial begin #10000;$fatal(1,"timeout");end
endmodule
