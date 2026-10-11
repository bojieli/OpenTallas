`timescale 1ns/1ps
module tb_hbm_retry_rx_slot;
localparam W=545,SW=12,EW=24;
reg clk=0; always #0.416667 clk=~clk;
reg rst=0,rv=0,ue=0,ready=0;
reg [W-1:0] data=0; reg [SW-1:0] seq=0; reg [EW-1:0] epoch=1;
wire rr,ov; wire [W-1:0] od; wire [SW-1:0] ack; wire fault;
ot_hbm_link_retry_pipeline #(.ENABLE(1),.RSTR(1),.W(W),.SW(SW),.EW(EW),.DEPTH(512),.TIMEOUT(8192)) dut(
.clk(clk),.rst_n(rst),.session(24'd1),.in_valid(1'b0),.in_data(545'd0),.tx_ready(1'b1),
.rx_valid(rv),.rx_ready(rr),.rx_ue(ue),.rx_data(data),.rx_seq(seq),.rx_session(epoch),
.out_valid(ov),.out_ready(ready),.out_data(od),.ack_seq(ack),
.fb_valid(1'b0),.fb_good(1'b0),.fb_nak(1'b0),.fb_seq(12'd0),.fb_session(24'd1),.fault(fault));
function [W-1:0] payload(input integer n);
integer j;begin for(j=0;j<W;j=j+1)payload[j]=((j*17+n*31)^(n>>(j%7)))&1;payload[31:0]=n;end
endfunction
integer n,k; reg [W-1:0] keep;
task tick;begin @(posedge clk);#0.05;end endtask
initial begin
repeat(2)tick;@(negedge clk);rst=1;repeat(4)tick;
for(n=0;n<100;n=n+1)begin
 // Invalid identity or uncorrectable input may fill raw empty-slot flops,
 // but can never assert output visibility or advance cumulative ACK.
 @(negedge clk);rv=1;seq=n;data=payload(n+999);epoch=2;ue=0;tick;
 if(ov||ack!=n||fault)$fatal(1,"stale session made payload visible");
 @(negedge clk);epoch=1;ue=1;tick;
 if(ov||ack!=n||fault)$fatal(1,"UE payload made visible");
 @(negedge clk);ue=0;data=payload(n);if(!rr)$fatal(1,"slot not ready");tick;
 keep=payload(n);if(!ov||od!==keep||ack!=n)$fatal(1,"valid capture mismatch");
 // The external pins change on every held edge, including apparently
 // valid traffic. The occupied landing payload must remain bit-identical.
 for(k=0;k<8;k=k+1)begin
 @(negedge clk);data=payload(n+700+k);seq=n+1+k;epoch=(k%2)?1:2;ue=k%3==0;tick;
 if(!ov||od!==keep||rr||ack!=n||fault)$fatal(1,"occupied-slot payload changed n=%0d k=%0d",n,k);
 end
 @(negedge clk);rv=0;ready=1;tick;
 if(ov||ack!=n+1)$fatal(1,"consume/ACK mismatch");
 @(negedge clk);ready=0;tick;
end
$display("PASS_ALL RX_SLOT 100 records, 800 hostile held edges, full W545 EW24 DEPTH512");$finish;
end
initial begin #100000;$fatal(1,"watchdog");end
endmodule
