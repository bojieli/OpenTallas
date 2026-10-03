`timescale 1ns/1ps
module tb_dsrom_credit_return;
 reg clk=0,rst_n=0; always #5 clk=~clk;
 reg av=0; reg [31:0] at,ad,bt,bd; wire ar,br;
 wire nv,ne,nc,bc,f1,f2,quiet1,quiet2;wire [31:0] nt,nd,ot,od;wire ov,oe;
 wire [31:0] pa,pb,stalls,pa2,pb2,stalls2;
 ot_v41_retn_credit n1(.clk(clk),.rst_n(rst_n),.a_v(av),.a_t(at),.a_d(ad),.a_e(1'b0),
 .b_v(av),.b_t(bt),.b_d(bd),.b_e(1'b0),.a_ready(ar),.b_ready(br),.a_credit(),.b_credit(),
 .o_credit(nc),.o_v(nv),.o_t(nt),.o_d(nd),.o_e(ne),.fault(f1),.quiet(quiet1),.peak_a(pa),.peak_b(pb),.credit_stalls(stalls));
 ot_v41_retn_credit #(.OUTD(128)) n2(.clk(clk),.rst_n(rst_n),.a_v(nv),.a_t(nt),.a_d(nd),.a_e(ne),
 .b_v(1'b0),.b_t(32'd0),.b_d(32'd0),.b_e(1'b0),.a_ready(),.b_ready(),.a_credit(nc),.b_credit(),
 .o_credit(bc),.o_v(ov),.o_t(ot),.o_d(od),.o_e(oe),.fault(f2),.quiet(quiet2),.peak_a(pa2),.peak_b(pb2),.credit_stalls(stalls2));
 // Final consumer consumes every valid word and returns its registered credit.
 reg refund=0; always @(posedge clk) refund<=rst_n && ov; assign bc=refund;
 reg rav=0;reg [31:0] rat,rbt;wire rnv,rne,rov,roe;wire [31:0] rnt,rnd,rot,rod;wire rf1,rf2;
 ot_v41_retn_w17w10 ref1(.clk(clk),.rst_n(rst_n),.a_v(rav),.a_t(rat),.a_d(ad),.a_e(1'b0),
 .b_v(rav),.b_t(rbt),.b_d(bd),.b_e(1'b0),.o_v(rnv),.o_t(rnt),.o_d(rnd),.o_e(rne),.fault(rf1),.quiet());
 ot_v41_retn_w17w10 ref2(.clk(clk),.rst_n(rst_n),.a_v(rnv),.a_t(rnt),.a_d(rnd),.a_e(rne),
 .b_v(1'b0),.b_t(32'd0),.b_d(32'd0),.b_e(1'b0),.o_v(rov),.o_t(rot),.o_d(rod),.o_e(roe),.fault(rf2),.quiet());
 integer cycle=0, sent=0,rsent=0,got=0,rgot=0,last=0,rlast=0;
 reg [255:0] seen=0,rseen=0;
 function [31:0] tag(input integer row,input integer lo);
 tag={3'd0,16'(row),5'(lo),3'd0,5'd2};endfunction
 always @(posedge clk) begin
 if(rst_n) begin
  cycle=cycle+1;
  if(av && ar && br) sent=sent+1;
  if(rav) rsent=rsent+1;
  if(n1.u_n.pop_a || n1.u_n.pop_b) $display("LAUNCH %0d %0d",cycle,n1.u_n.ta[28:13]);
  if(n2.u_n.pop_a) $display("PARENT_POP %0d %0d",cycle,n2.u_n.ta[28:13]);
  if(nc) $display("REFUND %0d",cycle);
  if(ov) begin
   if(od!=32'h40000000 || oe || seen[ot[28:13]]) $fatal(1,"credit value/duplicate");
   seen[ot[28:13]]=1;got=got+1;last=cycle;
  end
  if(rov) begin
   if(rod!=32'h40000000 || roe || rseen[rot[28:13]]) $fatal(1,"reference value/duplicate");
   rseen[rot[28:13]]=1;rgot=rgot+1;rlast=cycle;
  end
  if(f1||f2||rf1||rf2) $fatal(1,"overflow/credit fault");
  if(got==256 && rgot==256) begin
   $display("RESULT nodes count=%0d credit_last=%0d reference_last=%0d peak_a=%0d peak_b=%0d parent_peak=%0d stalls=%0d",got,last,rlast,pa,pb,pa2,stalls);
   if(seen!=rseen) $fatal(1,"reference set mismatch"); $finish;
  end
 end
 end
 always @(negedge clk) if(rst_n) begin
  av=(sent<256 && ar && br);at=tag(sent,0);bt=tag(sent,1);
  rav=rsent<256;rat=tag(rsent,0);rbt=tag(rsent,1);
 end
 initial begin ad=32'h3f800000;bd=32'h3f800000;#22;rst_n=1;end
 // Cycle bound follows finite directed workload, not a wall-time/host cap.
 initial begin repeat(4096) @(posedge clk); $fatal(1,"finite directed test did not drain");end
endmodule
