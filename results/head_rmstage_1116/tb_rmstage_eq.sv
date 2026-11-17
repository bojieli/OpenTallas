`timescale 1ns/1ps
module tb;
parameter FAST=1, GAPS=0;
reg wc=0,rc=0,wrn=0,rrn=0;
always #0.416667 rc=~rc;
generate if(FAST) always #0.4162 wc=~wc; else always #0.41713 wc=~wc; endgenerate
reg v=0; reg [511:0] d=512'd2;
wire [511:0] b,s; wire bf,sf;
ot_s81_rate_match_base #(.RPC(32)) gold(wc,wrn,v,d,rc,rrn,b,bf);
ot_s81_rate_match_stage #(.RPC(32)) dut(wc,wrn,v,d,rc,rrn,s,sf);
integer n=0,reads=0,bad=0,flush=0,epochs=0;
reg [511:0] prev;
always @(negedge wc) begin
 if(!wrn) begin n=0;v=0;d=512'd2;end
 else begin
  n=n+1;v=(GAPS==0 || n%23!=0);
  d=(n%128==0) ? 512'd2 : {16{32'(n*4)}};
 end
end
always @(posedge rc) begin
 #0.001;
 if(!rrn) flush=0; else flush=flush+1;
 if(flush>64) begin
  reads=reads+1;
  if(s!==prev || sf!==bf) begin
   bad=bad+1;if(bad<4)$display("MISMATCH edge=%0d s=%h prev=%h sf=%b bf=%b",reads,s[31:0],prev[31:0],sf,bf);
  end
 end
 prev=b;
end
initial begin
 repeat(80) @(negedge rc);wrn=1;rrn=1;
 repeat(28000) @(negedge rc);wrn=0;rrn=0;epochs=epochs+1;
 repeat(80) @(negedge rc);wrn=1;rrn=1;
 repeat(28000) @(negedge rc);epochs=epochs+1;
 $display("RMSTAGE_EQ FAST=%0d comparisons=%0d epochs=%0d bad=%0d %s",FAST,reads,epochs,bad,bad==0?"PASS":"FAIL");
 if(bad!=0)$fatal(1,"not exact");
 $finish;
end
endmodule
