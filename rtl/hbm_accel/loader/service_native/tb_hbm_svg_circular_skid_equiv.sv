`timescale 1ns/1ps
// Compare actual sliced skid against the original exact two-entry FIFO.
// Reference sees the same registered reset leaf as the DUT. New reset landing +1 edge;
// external ready is held low until that leaf releases. Normal transaction timing is unchanged.
module tb;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,in_v=0,out_r=0;reg [340:0]in_data=0;
 reg [31:0]rng=32'h135bc940;
 integer checks=0,full=0,stalled=0;
 for(genvar g=0;g<2;g=g+1)begin:widths
   localparam W=g==0?51:277;
   wire ar,av,br,bv;wire ar_raw;wire [W-1:0]ad,bd;
   ot_hbm_svc_pin_skid2 #(.WIDTH(W)) a(.clk(clk),.rst_n(b.rn[0]),.in_v(in_v),.in_r(ar_raw),.in_data(in_data[W-1:0]),.out_v(av),.out_r(out_r),.out_data(ad));
   ot_hbm_svc_pin_skid2_r32 #(.WIDTH(W)) b(.clk(clk),.rst_n(rst_n),.in_v(in_v),.in_r(br),.in_data(in_data[W-1:0] ^ W'(MUT)),.out_v(bv),.out_r(out_r),.out_data(bd));
   assign ar=b.rn[0]&&ar_raw;
   always @(posedge clk)begin
     #1;
     if({ar,av} !== {br,bv} || (av && ad!==bd))$fatal(1,"SVG_CIRCULAR_SKID_MISMATCH width=%0d check=%0d",W,checks);
   end
 end
 initial begin
   repeat(3)@(negedge clk);
   for(integer t=0;t<32768;t=t+1)begin
     @(negedge clk);
     rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
     rst_n=(t%257!=0);in_v=rng[0]||rng[4];out_r=rng[1]||rng[6];
     for(integer s=0;s<10;s=s+1)in_data[s*32+:32]=32'(t*139+s)^rng;
     in_data[340:320]=21'(t);
     @(posedge clk);#2;
     if(rst_n)begin checks=checks+1;if(!widths[0].ar)full=full+1;if(widths[0].av&&!out_r)stalled=stalled+1;end
   end
   if(checks<32000||full<2000||stalled<2000)$fatal(1,"SVG_CIRCULAR_SKID_VACUOUS");
   $display("SVG_CIRCULAR_SKID_EQUIV PASS checks=%0d full=%0d stalled=%0d widths=51,277 data_edges=0 reset_landing_edges=1",checks,full,stalled);$finish;
 end
endmodule
