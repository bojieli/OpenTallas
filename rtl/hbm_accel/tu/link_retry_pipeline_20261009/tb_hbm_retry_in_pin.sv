`timescale 1ns/1ps
// [link] 2026-10-10 IN_PIN mechanism bench (full W545/EW24/DEPTH512, TX/RX slot sampling + pin-registered rx/fb inputs):
// stale-session and UE beats are dropped/NAKed from the registered raw slot, a valid beat becomes visible exactly once,
// and while the raw slot / landing slot are occupied the rx pins change on every edge (hostile, including beats with
// the live session) without changing the visible payload, the ACK or the fault.  Mutant OT_RETRY_MUT_IN_PIN_HOLD fails.
module tb_hbm_retry_in_pin;
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
integer n,k,shown,naks; reg [W-1:0] keep;
task tick;begin @(posedge clk);#0.05;end endtask
// offer one beat; returns after the edge that accepted it (rx_valid && rx_ready)
task offer(input [EW-1:0] e,input u,input [SW-1:0] s,input [W-1:0] d);
begin @(negedge clk);rv=1;epoch=e;ue=u;seq=s;data=d;
 while(!rr) begin tick;@(negedge clk);data=~data;epoch=epoch^24'h5;end   // hostile while not ready (no accept)
 epoch=e;ue=u;seq=s;data=d;tick;@(negedge clk);rv=0;end
endtask
// slot held (ready=0) for 10 edges: rx pins hostile every edge (live-session beats with future seq, stale, UE);
// the visible payload must be exactly payload(m) once shown and ACK/fault must not move.
task hold(input integer m);
begin shown=0;
 for(k=0;k<10;k=k+1)begin
  @(negedge clk);rv=1;data=payload(m+700+k);seq=m+2+k;epoch=(k%3)?1:2;ue=k%4==0;tick;
  if(ov)begin shown=shown+1;if(od!==payload(m))$fatal(1,"held payload changed m=%0d k=%0d got %0d",m,k,od[31:0]);end
  if(ack!=m||fault)$fatal(1,"ack/fault changed while held m=%0d k=%0d",m,k);
 end
 @(negedge clk);rv=0;
 if(shown<8)$fatal(1,"valid beat not visible m=%0d (%0d)",m,shown);
end endtask
initial begin
repeat(2)tick;@(negedge clk);rst=1;repeat(4)tick;naks=0;
for(n=0;n<100;n=n+2)begin
 offer(24'd2,0,n,payload(n+999));                 // stale session: silently dropped
 repeat(3)begin tick;if(ov||ack!=n||fault)$fatal(1,"stale session made payload visible n=%0d",n);end
 offer(24'd1,1,n,payload(n+555));                 // UE: NAK, never visible
 repeat(3)begin tick;if(ov||ack!=n||fault)$fatal(1,"UE payload made visible n=%0d",n);end
 if(!dut.ack_nak)$fatal(1,"UE beat did not NAK n=%0d",n);
 offer(24'd1,0,n,payload(n));                     // valid n -> landing slot
 offer(24'd1,0,n+1,payload(n+1));                 // valid n+1 -> raw pin slot, held behind n
 hold(n);
 @(negedge clk);rv=0;ready=1;tick;@(negedge clk);ready=0;
 if(ack!=n+1)$fatal(1,"consume/ACK mismatch n=%0d",n);
 hold(n+1);                                       // n+1 must surface from the raw slot intact
 @(negedge clk);rv=0;ready=1;tick;@(negedge clk);ready=0;
 if(ack!=n+2)$fatal(1,"consume/ACK mismatch n=%0d",n+1);
 repeat(3)begin tick;if(ov)$fatal(1,"extra visible beat after n=%0d",n+1);end
end
$display("PASS_ALL IN_PIN 100 records, 1000 hostile held edges, full W545 EW24 DEPTH512");$finish;
end
initial begin #2000000;$fatal(1,"watchdog");end
endmodule
