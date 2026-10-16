`timescale 1ns/1ps
module tb_qkd_replay_hit_0253;
  localparam W=137;
  reg ck=0; always #5 ck=~ck;
  reg we=0; reg[5:0] wa=0,ra=0; reg[W-1:0] din=0;
  wire[W-1:0] actual,prior;
  ot_qkvd_llr_replay_sram_leaf #(.W(W)) dut(ck,we,wa,ra,din,actual);
  qkd_replay_sram_prior_0253 #(.W(W)) ref_expected(ck,we,wa,ra,din,prior);
  integer i,j,checks=0,age0=0,age1=0; reg[5:0] lastwa=0; reg lastwe=0;
  task drive(input integer n,input integer mode);
    begin
      @(negedge ck);
      if(mode==0)begin we=1;wa=n;ra=n;end
      else begin
        we=(n%5)!=0;wa=(n*7+13)%64;
        case(n%4)0:ra=wa;1:ra=lastwa;2:ra=(wa+1)%64;3:ra=(n*19+3)%64;endcase
      end
      for(j=0;j<W;j=j+1)din[j]=((n*17+j*3+(j/7))%11)<5;
      if(we && wa==ra)age0=age0+1;
      if(lastwe && lastwa==ra)age1=age1+1;
      lastwe=we;lastwa=wa;
      @(posedge ck); #1;
      if(n>=68)begin
        if((^actual)===1'bx || (^prior)===1'bx)$fatal(1,"REPLAY_HIT_FAIL unknown output n=%0d",n);
        if(actual!==prior)$fatal(1,"REPLAY_HIT_FAIL cycle=%0d actual=%h prior=%h",n,actual,prior);
        checks=checks+1;
      end
    end
  endtask
  initial begin
    for(i=0;i<68;i=i+1)drive(i,0);
    for(i=68;i<580;i=i+1)drive(i,1);
    if(checks!=512 || age0<100 || age1<80)$fatal(1,"REPLAY_HIT_FAIL vacuous");
    $display("REPLAY_HIT_PASS W=%0d QD=64 checks=%0d age0=%0d age1=%0d cycles_unchanged=1",W,checks,age0,age1);
    $finish;
  end
endmodule
