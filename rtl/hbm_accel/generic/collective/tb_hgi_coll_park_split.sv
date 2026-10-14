`timescale 1ns/1ps
module tb_hgi_coll_park_split;
localparam EQ=4, DEL=4, PWT=545;
reg clk=0; always #5 clk=~clk;
reg rst_n=0;
reg [DEL-1:0] pv=0;
reg [DEL*2-1:0] pq=0,ps=0;
reg [DEL*PWT-1:0] pd=0;
reg [EQ-1:0] pop=0;
wire [EQ-1:0] hv,hvf;
wire [EQ*PWT-1:0] hd,hdf;
wire ovf,ovff;
`ifdef MUT_PARK
localparam MUT=1;
`else
localparam MUT=0;
`endif
ot_hgi_coll_park #(.MUT_PARK(MUT)) dut(.clk(clk),.clk_q({EQ{clk}}),.rst_n(rst_n),.pv(pv),.pq(pq),.ps(ps),.pd(pd),.pop(pop),.hv(hv),.hd(hd),.ovf(ovf));
ot_hgi_coll_park_flat_ref gold(.clk(clk),.rst_n(rst_n),.pv(pv),.pq(pq),.ps(ps),.pd(pd),.pop(pop),.hv(hvf),.hd(hdf),.ovf(ovff));
integer seq[EQ],cnt[EQ],lastpop[EQ];
integer cycle,q,l,n,checked=0,pushed=0,popped=0,errors=0,seed=77;
reg [31:0] rng=32'h125def;
reg [PWT-1:0] word;
function [31:0] step(input [31:0] a);step=(a<<13)^a;step=(step>>17)^step;step=(step<<5)^step;endfunction
initial begin
 for(q=0;q<EQ;q=q+1)begin seq[q]=0;cnt[q]=0;lastpop[q]=0;end
 repeat(8)@(negedge clk);rst_n=1;
 repeat(8)@(negedge clk);
 for(cycle=0;cycle<16000;cycle=cycle+1)begin
  pv=0;pop=0;
  for(q=0;q<EQ;q=q+1)begin
   rng=step(rng);
   if(hvf[q] && !lastpop[q] && (cycle>11000 || rng[1:0]!=0))begin pop[q]=1;cnt[q]=cnt[q]-1;popped=popped+1;end
   lastpop[q]=pop[q];
  end
  q=(cycle/157)%EQ;
  for(l=0;l<DEL;l=l+1)begin
   rng=step(rng);
   if(cycle<11000 && cnt[q]<448 && (cycle<5000 || rng[1:0]!=0))begin
    pv[l]=1;pq[l*2+:2]=q;ps[l*2+:2]=seq[q]%DEL;
    for(n=0;n<PWT;n=n+1)begin rng=step(rng);word[n]=rng[0];end
    pd[l*PWT+:PWT]=word;seq[q]=seq[q]+1;cnt[q]=cnt[q]+1;pushed=pushed+1;
   end
  end
  @(posedge clk);#1;
  checked=checked+1;
  if(hv!==hvf || ovf!==ovff)begin errors=errors+1;if(errors<5)$display("flags mismatch cycle=%0d hv=%b golden=%b",cycle,hv,hvf);end
  for(q=0;q<EQ;q=q+1)if(hvf[q] && hd[q*PWT+:PWT]!==hdf[q*PWT+:PWT])begin errors=errors+1;if(errors<5)$display("payload mismatch cycle=%0d queue=%0d",cycle,q);end
  @(negedge clk);
 end
 if(pushed!=popped)begin errors=errors+1;$display("not drained pushed=%0d popped=%0d",pushed,popped);end
 if(errors)$fatal(1,"PARK_SPLIT FAIL errors=%0d checked=%0d pushed=%0d popped=%0d",errors,checked,pushed,popped);
 $display("PARK_SPLIT PASS checked=%0d pushed=%0d popped=%0d",checked,pushed,popped);$finish;
end
endmodule
