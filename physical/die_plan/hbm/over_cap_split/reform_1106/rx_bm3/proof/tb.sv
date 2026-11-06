`timescale 1ps/1fs
module tb;
reg clk=0;always #416.5 clk=~clk;
reg rs_n=0;reg[299:0]S=0;reg[3:0]ld[0:2];
wire[159:0]rl[0:2],nl[0:2];wire[149:0]ro[0:2],no_[0:2];
wire[4:0]rL[0:2],nL[0:2];wire ra[0:2],na[0:2];wire[3:0]rd[0:2],nd[0:2];reg[3:0]delayed[0:2];
integer mode=0,checks=0,valid=0,errors=0,loads=0,epochs=0;reg[31:0]seed=32'hca51d773;
function automatic[31:0]rnd(input[31:0]v);rnd={v[30:0],v[31]^v[21]^v[1]^v[0]};endfunction
for(genvar g=0;g<3;g=g+1)begin:engine
 wire[3:0]nld=(mode==2)?ld[(g+1)%3]:ld[g];
 wire[299:0]ns=S^((mode==1)?300'd1:300'd0);
 ot_s81_kp4_bm #(.NG(4),.NCD(4),.THC(1)) refbm(.clk(clk),.rs_n(rs_n),.ld(ld[g]),.S(S),.lam(rl[g]),.om(ro[g]),.L(rL[g]),.any(ra[g]),.done(rd[g]));
 ot_pdie_serdes_rx_bm_native #(.BMTHC(1)) nativebm(.clk(clk),.rs_n(rs_n),.ld(nld),.S(ns),.lam(nl[g]),.om(no_[g]),.L(nL[g]),.any(na[g]),.done(nd[g]));
 always @(posedge clk)delayed[g]<=nd[g];
end
initial begin
 if(!$value$plusargs("MUT=%d",mode))mode=0;
 for(integer g=0;g<3;g=g+1)begin ld[g]=0;delayed[g]=0;end
 for(integer cycle=0;cycle<3000;cycle=cycle+1)begin
  @(negedge clk);
  rs_n=!((cycle<4)||(cycle>=701&&cycle<705)||(cycle>=1501&&cycle<1505)||(cycle>=2301&&cycle<2305));
  if(!rs_n)epochs=epochs+1;
  for(integer b=0;b<10;b=b+1)begin seed=rnd(seed);S[30*b+:30]=seed[29:0];end
  for(integer g=0;g<3;g=g+1)ld[g]=rs_n&&cycle%10==0&&((cycle/10)%3)==g?4'b1111:4'b0000;
  @(posedge clk);#1;
  for(integer g=0;g<3;g=g+1)begin
   checks=checks+1;if(|ld[g])loads=loads+1;
   if(rd[g]!==((mode==3)?delayed[g]:nd[g]))errors=errors+1;
   if(|rd[g])begin valid=valid+1;if({rl[g],ro[g],rL[g],ra[g]}!=={nl[g],no_[g],nL[g],na[g]})errors=errors+1;end
  end
 end
 $display("BM3_COHORT mode=%0d checks=%0d valid=%0d loads=%0d reset_edges=%0d mismatches=%0d cycles_added=0",mode,checks,valid,loads,epochs,errors);
 if(checks!=9000||valid<200||loads<250)$fatal(1,"INSUFFICIENT");
 if(mode==0)begin if(errors!=0)$fatal(1,"FAIL");$display("PASS");end
 else begin if(errors==0)$fatal(1,"MUTANT_ESCAPED");$display("CAUGHT");end
 $finish;
end
endmodule
