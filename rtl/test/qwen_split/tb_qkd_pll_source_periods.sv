`timescale 1ps/1fs
module tb_qkd_pll_source_periods;
 reg refclk=0;always #500 refclk=~refclk;
 wire core,hbm,host,ingest,phy;
 qkd_pll_analog_model dut(.refclk(refclk),.por_n(1'b1),.pll_c(core),.pll_hbm_WS(hbm),
 .pll_host(host),.pll_ingest(ingest),.pll_phy(phy));
 real last_core=0,last_hbm=0,last_host=0,last_ingest=0,last_phy=0;
 integer nc=0,nh=0,no=0,ni=0,np=0;
 task check(input real delta,input real expected);
  if(delta<expected-0.0001||delta>expected+0.0001)$fatal(1,"source period mismatch actual=%0.6fps expected=%0.6fps",delta,expected);
 endtask
 always @(posedge core)begin if(nc>0)check($realtime-last_core,833.334);last_core=$realtime;nc=nc+1;end
 always @(posedge hbm)begin if(nh>0)check($realtime-last_hbm,1024.0);last_hbm=$realtime;nh=nh+1;end
 always @(posedge host)begin if(no>0)check($realtime-last_host,1000.0);last_host=$realtime;no=no+1;end
 always @(posedge ingest)begin if(ni>0)check($realtime-last_ingest,1666.668);last_ingest=$realtime;ni=ni+1;end
 always @(posedge phy)begin if(np>0)check($realtime-last_phy,1043.0);last_phy=$realtime;np=np+1;end
 initial begin
 #10000;if(nc<10||nh<8||no<8||ni<5||np<8)$fatal(1,"clock events missing");
 $display("PASS actual five clock source periods in fs precision");$finish;
 end
endmodule
