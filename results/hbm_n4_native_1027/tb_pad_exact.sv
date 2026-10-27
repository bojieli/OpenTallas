`timescale 1ps/1ps
module tb_pad_exact;
 reg clk=0;initial forever begin #416 clk=1;#417 clk=0;end
 reg rst_n=0,active=0,mutate=0;reg[14:0]dc=0;reg[255:0]dd=0;
 reg[14:0]refc[0:32];reg[255:0]refd[0:32];wire[14:0]qc[0:32],mc[0:32];wire[255:0]qd[0:32],md[0:32];
 for(genvar k=0;k<=32;k=k+1)begin:g
 ot_hnx_fused_pad dut(.clk(clk),.rst_n(rst_n),.k(6'(k)),.dc(dc),.dd(dd),.qc(qc[k]),.qd(qd[k]));
 ot_hnx_fused_pad_original original(.clk(clk),.rst_n(rst_n),.k(6'(k)),.dc(dc),.dd(dd),.qc(mc[k]),.qd(md[k]));
 end
 always @(posedge clk)begin refc[0]<=dc;refd[0]<=dd;for(integer i=1;i<=32;i=i+1)begin refc[i]<=refc[i-1];refd[i]<=refd[i-1];end end
 integer checks=0,errors=0;
 always @(negedge clk)if(active)begin
 for(integer k=0;k<=32;k=k+1)begin
 checks=checks+1;
 if((mutate?mc[k]:qc[k]) !== (k==0?dc:refc[k-1]))begin errors=errors+1;if(errors<5)$display("PAD_CONTROL_MISMATCH k=%0d expected=%h actual=%h",k,k==0?dc:refc[k-1],mutate?mc[k]:qc[k]);end
 if((k==0?dc:refc[k-1])!=0 && (mutate?md[k]:qd[k]) !== (k==0?dd:refd[k-1]))begin errors=errors+1;if(errors<5)$display("PAD_DATA_MISMATCH k=%0d",k);end
 end end
 task automatic tick;@(negedge clk);#1;endtask
 initial begin
 for(integer i=0;i<=32;i=i+1)begin refc[i]=0;refd[i]=0;end
 mutate=$test$plusargs("MUT_ORIGINAL");repeat(5)tick;rst_n=1;repeat(80)tick;active=1;
 for(integer j=1;j<=200;j=j+1)begin dc=15'(j);dd={8{32'(j*65537)}};tick;end
 dc=0;dd=0;repeat(45)tick;active=0;
 $display("PAD_EXACT_RESULT checks=%0d errors=%0d depths=33 warm=80 MUT_ORIGINAL=%0d clock_ps=833",checks,errors,mutate);
 if(errors)$fatal(1,"PAD_EXACT FAIL");$display("PAD_EXACT PASS");$finish;
 end
endmodule
