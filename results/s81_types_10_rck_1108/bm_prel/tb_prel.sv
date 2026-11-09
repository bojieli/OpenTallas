`timescale 1ns/1ps
// S81-TYPES-10-RCK: lockstep proof of ot_s81_kp4_bm PREL=1 (load one cycle early into the state registers) against the
// PREL=0 form (reference), same NG/THC.  Reference gets ld/S; the DUT gets ldp/Sp one cycle earlier and the same ld.
// Compared: done, L, any every cycle after the first load; lam/om in every cycle from the first done, not only the
// done cycle (they are the same registers' worth of value by construction).  Load cadence: 30-cycle round-robin slots with
// random extra gaps, zero-syndrome loads, single-symbol loads, warm resets.
module tb;
reg clk=0; always #0.4165 clk=~clk;
reg rs_n=0, ldp=0, ld=0; reg [299:0] Sp=0, S=0;
wire [159:0] la,lb;wire [149:0] oa,ob;wire [4:0] La,Lb;wire aa,ab;wire [3:0] da,db;
parameter NG=46;
ot_s81_kp4_bm #(.NG(NG),.THC(1),.PREL(0)) a(.clk(clk),.rs_n(rs_n),.ld({NG{ld}}),.S(S),.lam(la),.om(oa),.L(La),.any(aa),.done(da),.ldp({NG{1'b0}}),.Sp(300'd0));
ot_s81_kp4_bm #(.NG(NG),.THC(1),.PREL(1)) b(.clk(clk),.rs_n(rs_n),.ld({NG{ld}}),.S(300'd0),.lam(lb),.om(ob),.L(Lb),.any(ab),.done(db),.ldp({NG{ldp}}),.Sp(Sp));
always @(posedge clk) begin ld<=ldp; S<=Sp; end
integer c,j,gap=0,checks=0,errors=0,frames=0,lamchecks=0,loads=0,zero_loads=0,upd=0; reg seen=0, seend=0;
integer rstn=0;
initial begin
 for(c=0;c<60000;c=c+1) begin
  @(negedge clk);
  rstn=(c%5000);
  rs_n=rstn>=6;
  ldp=0;
  if(rs_n) begin
   if(gap==0) begin
    ldp=1; loads=loads+1;
    gap=30+(($urandom%10==0)?($urandom%40):0);
    for(j=0;j<10;j=j+1) Sp[j*30+:30]=$urandom;
    case($urandom%8)
     0: begin Sp=0; zero_loads=zero_loads+1; end
     1: Sp[299:10]=0;
     2: Sp[9:0]=0;
     3: begin Sp=0; Sp[$urandom%30*10+:10]=$urandom; end
     default: ;
    endcase
   end else gap=gap-1;
  end else gap=8;
  @(posedge clk); #0.001;
  if(seen) begin
   checks=checks+1;
   if({da,aa,La}!=={db,ab,Lb}) begin errors=errors+1; if(errors<5) $display("ctl mismatch c=%0d",c); end
  end
  if(seend) begin
   lamchecks=lamchecks+1;
   if({la,oa}!=={lb,ob}) begin errors=errors+1; if(errors<5) $display("lam/om mismatch c=%0d",c); end
   if(da[0]) frames=frames+1;
  end
  // set after the compare: the load takes effect at the next posedge (L/any are unloaded until then)
  if(rs_n && ld) seen=1;
  if(da[0]) seend=1;
 end
 $display("BM_PREL loads=%0d zero_loads=%0d",loads,zero_loads);
 $display("BM_PREL checks=%0d lamchecks=%0d frames=%0d errors=%0d",checks,lamchecks,frames,errors);
 if(errors||frames<500||zero_loads<50) $fatal(1,"BM_PREL FAILED");
 $finish;
end
endmodule
