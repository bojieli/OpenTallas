module tb;
 reg clk=0,rst_n=0; always #5 clk=~clk;
 reg [513:0] rx=0;reg[511:0]tx=0;
 wire[513:0] oldrx,newrx;wire[511:0]oldtx,newtx;
 reg[513:0] d1=0,d2=0;
 reg[513:0] actual_rx_hist[0:3];reg[511:0] actual_tx_hist[0:3];
 integer n,flush=0,checks=0,diffs=0;integer mut=0;
 initial if($value$plusargs("MUT=%d",mut)) begin end
 wire[513:0] cand_in=(mut==1)?{rx[513:512],rx[255:0],rx[511:256]}:rx;
 ot_hbm_spb0_regs #(.W(514),.N(2),.CW(2)) u_oldrx(clk,rst_n,rx,oldrx);
 SPB0_source dut(.clk(clk),.rst_n(rst_n),.provider_rx(cand_in[511:0]),.provider_st(cand_in[513:512]),.provider_tx(tx),.observed_rx(newrx[511:0]),.observed_st(newrx[513:512]),.observed_phy_tx(newtx));
 ot_hbm_spb0_regs #(.W(512),.N(4),.CW(0)) u_oldtx(clk,rst_n,tx,oldtx);

 always@(posedge clk)begin d1<=oldrx;d2<=d1;actual_rx_hist[0]<=rx;actual_tx_hist[0]<=tx;
 for(integer h=1;h<4;h=h+1)begin actual_rx_hist[h]<=actual_rx_hist[h-1];actual_tx_hist[h]<=actual_tx_hist[h-1];end
 end
 initial begin
  for(n=0;n<12000;n=n+1)begin
   @(negedge clk);
   rst_n=(n>5)&&!(n>=4000&&n<4007)&&!(n>=8000&&n<8004);
   for(integer k=0;k<16;k=k+1)begin rx[k*32+:32]=$urandom;tx[k*32+:32]=$urandom;end
   rx[513:512]=$urandom;
   @(posedge clk);#1;
   if(!rst_n)flush=0;else flush=flush+1;
   if(flush>7)begin
    checks=checks+1;
    if(newrx!==((mut==2)?actual_rx_hist[2]:actual_rx_hist[3])||newrx!==d2||newtx!==actual_tx_hist[3]||newtx!==oldtx)diffs=diffs+1;
   end
  end
  if(mut==0&&diffs!=0)$fatal(1,"SPB native positive mismatch %0d",diffs);
  if(mut!=0&&diffs==0)$fatal(1,"SPB native mutant escaped");
  $display("SPB_NATIVE %s mut=%0d checks=%0d diffs=%0d ACTUAL_RTL_ADDED_RX_ST=4 ACTUAL_RTL_ADDED_TX=4 MODEL_ADDED_RX_ST=2 MODEL_ADDED_TX=0",mut==0?"PASS":"CAUGHT",mut,checks,diffs);$finish;
 end
endmodule
