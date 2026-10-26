`timescale 1ns/1ps
// Compositional source cut: actual XFIN collectors/ring stops/finish. Inputs
// are captured actual VN partial words, retimed to this explicit component
// epoch. One registered link per ring edge is a bench transport model; none
// of these cycles qualify the G8 die's physical ring/clock/global schedule.
module tb_norm_xfin_source;
 localparam integer NS=16,NVL=5,KW=173;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,go=0,sv=0;reg[7:0]si=0;
 reg[31:0]partials[0:79],eps[0:0];
 reg[KW-1:0]wi[0:15],ei[0:15];
 wire[KW-1:0]eo[0:15],wo[0:15];
 wire[15:0]rbv,flt;wire[31:0]rbd[0:15];
 integer cyc=0,mut=0,nr=0,bad=0;reg[15:0]seen=0;reg[31:0]r0=0;
 string dir;
 genvar g;
 generate for(g=0;g<16;g=g+1)begin:sl
  wire[3:0]sid=(mut==1&&g==3)?4'd4:4'(g);
  ot_s81dv_xfin #(.NS(16),.NVL(5),.LM(5),.LA(6),.SIW(8)) xf(
   .clk(clk),.rst_n(rst_n),.go(go),.mode(1'b0),.sid(sid),.eps(eps[0]),
   .s_v(sv),.s_i(si),.s(partials[5*g+si]),
   .wi_v(wi[g][172]),.wi_h(wi[g][171:168]),.wi_b(wi[g][167:160]),.wi_d(wi[g][159:0]),
   .ei_v(ei[g][172]),.ei_h(ei[g][171:168]),.ei_b(ei[g][167:160]),.ei_d(ei[g][159:0]),
   .eo_v(eo[g][172]),.eo_h(eo[g][171:168]),.eo_b(eo[g][167:160]),.eo_d(eo[g][159:0]),
   .wo_v(wo[g][172]),.wo_h(wo[g][171:168]),.wo_b(wo[g][167:160]),.wo_d(wo[g][159:0]),
   .rb_v(rbv[g]),.rb_d(rbd[g]),.e_v(),.e_c(),.e_hh(),.e_kk(),.e_dd(),.fault(flt[g]));
  always @(posedge clk)begin
   if(!rst_n)begin wi[(g+1)%16]<=0;ei[g]<=0;end
   else begin wi[(g+1)%16]<=eo[g];ei[g]<=wo[(g+1)%16];end
  end
 end endgenerate
 integer i;
 always @(negedge clk)begin
  if(cyc==32)rst_n=1;
  go=(cyc==64);sv=0;si=0;
  for(i=0;i<5;i=i+1)if(cyc==96+2*i)begin sv=1;si=i;end
 end
 always @(posedge clk)begin
  if(rst_n)for(i=0;i<16;i=i+1)if(rbv[i])begin
   if(seen[i])bad++;seen[i]=1;
   if(nr==0)r0=rbd[i];else if(rbd[i]!==r0)bad++;
   nr++;$display("ACTUAL_XFIN_RSTD sid=%0d cycle=%0d data=%08h eps=%08h",i,cyc,rbd[i],eps[0]);
  end
  if(cyc==4000)begin
   if(nr!=16||seen!=16'hffff||bad||(|flt))
    $fatal(1,"XFIN_SOURCE_FAIL count=%0d seen=%h disagreement=%0d faults=%h mut=%0d",nr,seen,bad,flt,mut);
   $display("XFIN_SOURCE_PASS rstd=%08h NS16 NVL5 component_ring_registers=1",r0);$finish;
  end
  cyc<=cyc+1;
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"NO_SOURCE_PARTIALS_DIR");
  void'($value$plusargs("MUT=%d",mut));
  $readmemh({dir,"/actual_partials80.hex"},partials);$readmemh({dir,"/eps_actual_config.hex"},eps);
 end
endmodule
