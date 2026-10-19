`timescale 1ns/1ps
module authority_case #(parameter integer D=4, EDGE_RESET=0, MUT=0)(output reg done=0);
 reg clk=0, rn=1, src=1;
 reg [D-1:0] hops='1;
 wire known; wire [31:0] errors;
 integer cycle=0, raw=0, consumed=0;
 reg ever_known=0;
 reg launch=0;
 always #5 clk=~clk;
 always @(posedge clk or negedge rn) if(!rn) src<=0; else src<=launch;
 always @(posedge clk) begin
   hops[0]<=src;
   for(integer j=1;j<D;j=j+1) hops[j]<=hops[j-1];
 end
 kva_authority_path #(.DEPTH(D),.ID(D*10+EDGE_RESET)) mon(
   .clk(clk),.source_rst_n(rn),.source_valid(src),.source_alias(src),
   .hop_q(hops),.known(known),.errors(errors));
 initial begin
   if(EDGE_RESET) begin @(posedge clk); rn<=0; end
   else begin #2; rn=0; end
   // Keep reset for three target edges then release between edges.
   repeat(3) @(negedge clk);
   #1; rn=1; launch=1;
 end
 always @(negedge clk) begin
   cycle=cycle+1;
   #0.002;
   if(hops[D-1]) raw=raw+1;
   if((MUT==1 || known) && hops[D-1]) consumed=consumed+1;
   if(known !== (cycle >= D+EDGE_RESET))
     $fatal(1,"CONTROL_FAIL old-D frontier D=%0d edge=%0d cycle=%0d known=%b",D,EDGE_RESET,cycle,known);
   if(!known && consumed!=0) $fatal(1,"CONTROL_FAIL arbitrary startup mutated transaction");
   if(ever_known && !known) $fatal(1,"CONTROL_FAIL repeat reset blind window");
   if(known) ever_known=1;
   if(cycle==D+EDGE_RESET+5) begin
     // Repeat actual asynchronous reset with already known downstream state.
     #1;rn=0;launch=0;
     if(!known) $fatal(1,"CONTROL_FAIL reset erased knowledge");
     #1;rn=1;
   end
   if(cycle==2*D+EDGE_RESET+12) begin
     if(errors!=0 || raw==0 || consumed==0 || !ever_known)
       $fatal(1,"CONTROL_FAIL D=%0d errors=%0d raw=%0d consumed=%0d",D,errors,raw,consumed);
     done=1;
   end
 end
endmodule
module tb_authority;
 localparam integer N=18;
 wire [2*N-1:0] done;
 parameter integer MUT=0;
 for(genvar i=0;i<N;i=i+1) begin:g
   localparam integer D=(i==0)?9:(i==1)?5:(i==2 || i==3)?69:(i==4)?67:(i==5)?63:(i==6)?56:(i==7)?47:(i==8)?34:(i==9)?51:(i%2==0)?6:4;
   authority_case #(.D(D),.EDGE_RESET(0),.MUT(MUT)) a(done[2*i]);
   authority_case #(.D(D),.EDGE_RESET(1),.MUT(MUT)) b(done[2*i+1]);
 end
 initial begin
   wait(&done); $display("AUTHORITY_CONTROL_PASS paths=18 reset_modes=2 repeat_reset=1"); $finish;
 end
 initial begin #5000; $fatal(1,"CONTROL_FAIL no terminal completion"); end
endmodule
