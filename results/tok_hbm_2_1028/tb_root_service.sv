`timescale 1ps/1ps
// TOK-HBM-2: root-local service edges of the production native root wrapper ot_hnx_fused_hub_n4ext (DELIVERED_RESET=1).
// Measures, per (op, n, wsc): capture -> first SCRD / GO / last WGT beat on the root command bus (dtop), PRE root compute
// (last chunk sum at the t5 output ur -> r on dtop), fin at ur -> done.  The lower tree + 32 leaves are NOT in this bench:
// scalars are reflected at the n4 boundary on the edge they leave t5 (0 extra edges), chunk sums / fins are injected.
// Plusargs: +POST +N=<1..8> +WSC=<0..255> +RGAP=<0..255>
module tb_root_service;
 reg clk=0; initial forever begin #416 clk=1; #417 clk=0; end
 reg rst_n=0, job_v=0; reg [216:0] job=0; reg [270:0] unw=0, une=0; reg [7:0] wsc=0;
 wire [172:0] dnw, dne; wire done, fault, busy;
 ot_hnx_fused_hub_n4ext #(.DELIVERED_RESET(1)) dut(.clk(clk),.rst_n(rst_n),.job_v(job_v),.job(job),.done(done),.fault(fault),.busy(busy),
  .wsc(wsc),.pk5(6'd0),.pb5(1'b0),.up_nw(unw),.up_ne(une),.down_nw(dnw),.down_ne(dne));
 integer cyc=0, cap=-1, scrd0=-1, go=-1, lastbeat=-1, nbeats=0, nscrd=0, lastsum=-1, rout=-1, nr=0, finin=-1, dn=-1, isfault=0;
 integer post, n, rgap;
 always @(posedge clk) cyc <= cyc + 1;
 // root command bus probes (dtop = {pv, pop, px, pd, prv, prb})
 always @(negedge clk) if (cap >= 0) begin
  if (dut.u_native.pv && dut.u_native.pop==3'd2) begin nscrd=nscrd+1; if (scrd0<0) scrd0=cyc; end
  if (dut.u_native.pv && dut.u_native.pop==3'd1) begin nbeats=nbeats+1; lastbeat=cyc; end
  if (dut.u_native.pv && dut.u_native.pop==3'd3 && go<0) go=cyc;
  if (dut.u_native.prv) begin nr=nr+1; rout=cyc; end
  if (dut.u_native.ur[270] && dut.u_native.ur[269]) lastsum=cyc;
  if (dut.u_native.ur[258] && finin<0) finin=cyc;
  if ((done||fault) && dn<0) begin dn=cyc; isfault=fault; end
 end
 // scalar reflector at the n4 boundary: every SCRD seen on down_nw returns as one scalar on up_nw on the next edge
 reg rv=0; reg [9:0] rx=0;
 always @(posedge clk) begin rv <= dnw[172] && dnw[171:169]==3'd2; rx <= {2'b0, dnw[168:161]}; end
 task automatic tick; @(negedge clk); #1; endtask
 initial begin
  post=$test$plusargs("POST"); if(!$value$plusargs("N=%d",n)) n=1; if(!$value$plusargs("WSC=%d",rgap)) rgap=115; wsc=rgap[7:0];
  if(!$value$plusargs("RGAP=%d",rgap)) rgap=0;
  repeat(5) tick; rst_n=1; repeat(80) tick;
  job=0; job[0]=post; job[4:1]=4'(n-1); job[184:177]=8'(rgap); job[216:185]=32'h358637bd; job_v=1; cap=cyc; tick; job_v=0;
  // scalar returns until the GO edge
  while (go < 0) begin unw = rv ? {1'b1,1'b0,rx,3'b0,224'd0,32'h3f800000} : 271'd0; tick; end
  unw=0; repeat(4) tick;
  if (!post) for (integer p=0;p<n;p=p+1) begin   // one row = NB 20 aligned chunk sums from both hubs (t5 adds pairs)
   for (integer b=0;b<20;b=b+1) begin unw={1'b1,1'b1,10'd0,3'b0,224'd0,32'h3b5c19bf}; une={1'b1,1'b1,10'd0,3'b0,224'd0,32'h3dc58aba}; tick; end
   unw=0; une=0; repeat(140) tick;
  end
  while (post && nbeats < 5*n) tick;
  repeat(20) tick;
  unw={1'b0,1'b0,10'd0,3'b110,256'd0}; une={1'b0,1'b0,10'd0,3'b110,256'd0}; tick; unw=0; une=0;
  repeat(40) tick;
  $display("ROOT_SERVICE op=%s n=%0d wsc=%0d rgap=%0d nscrd=%0d scrd0=%0d go=%0d nbeats=%0d lastbeat=%0d nr=%0d sum_to_r=%0d fin_to_done=%0d end=%s scl=%0d nsc=%0d",
   post?"HC_POST":"HC_PRE", n, wsc, rgap, nscrd, scrd0-cap, go-cap, nbeats, lastbeat-cap, nr, (post||rout<0)?-1:rout-lastsum, dn-finin, isfault?"FAULT":(dn<0?"NONE":"DONE"),
   dut.u_native.scl, dut.u_native.nsc);
  $finish;
 end
endmodule
