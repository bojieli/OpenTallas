`timescale 1ns/1ps
`default_nettype none
// RTL-BUILD-HBM/stk 2026-10-18: LOCKSTEP of the d4g per-quadrant refresh-phase producer (ot_hbm_pc_refresh_cfg NPC 16,
// one per quadrant: refcfg_<q>, its own F20 target) against today's per-stack master (NPC 32) on the quadrant's PCs.
// W (PCs 0..15) and E (PCs 16..31) instances; reference per quadrant = the NPC 32 master fed the quadrant's 16 bytes at
// their stack positions and a legal fill (118) in the other half.  Every frame reaches the quadrant instance and its
// reference on the same stream edge (separate F20 buses: the die shares one bus, frames to different targets are
// serial).  Compared on EVERY HBM edge: refresh_reload (quadrant bytes), pc_rst_n; on every stream edge ready/active/fault.
// Phases (each after a reset): P0 legal row (random bytes in [118,236], the run6 phase formula in phase 0), late frame so an
// early release would show; P1 legal row then a rewrite (refused, bytes kept); P2 a row with one quadrant byte out of
// range (refused, never released); P3 a frame to a wrong address (fault); P4 bytes outside the quadrant's 16 positions of
// the 32-byte frame are garbage (0x00 / 0xff): ignored by NPC 16.  MUT (quadrant instances only): 1..4 as the master.
module tb_hbm_pc_refresh_cfg_q;
 parameter integer MUT=0;
 reg clk=0;always #0.4165 clk=~clk;reg hclk=0;always #0.5 hclk=~hclk;
 reg rst_n=0,hrst_n=0;
 reg cv=0;reg[11:0]ca=0;reg[255:0]dq[0:1],dm[0:1];
 wire[127:0]rq[0:1];wire[255:0]rm[0:1];wire pq[0:1],pm[0:1];wire yq[0:1],aq[0:1],fq[0:1],ym[0:1],am[0:1],fm[0:1];
 genvar g;
 generate for(g=0;g<2;g=g+1)begin:h
  ot_hbm_pc_refresh_cfg #(.NPC(16),.MUT(MUT)) q(.clk(clk),.rst_n(rst_n),.clk_hbm(hclk),.rst_hbm_n(hrst_n),.tgt(8'(120+g)),
   .cfg_v(cv),.cfg_target(8'(120+g)),.cfg_addr(ca),.cfg_data(dq[g]),.refresh_reload(rq[g]),.pc_rst_n(pq[g]),.ready(yq[g]),.active(aq[g]),.fault(fq[g]));
  ot_hbm_pc_refresh_cfg #(.NPC(32),.MUT(0)) m(.clk(clk),.rst_n(rst_n),.clk_hbm(hclk),.rst_hbm_n(hrst_n),.tgt(8'd126),
   .cfg_v(cv),.cfg_target(8'd126),.cfg_addr(ca),.cfg_data(dm[g]),.refresh_reload(rm[g]),.pc_rst_n(pm[g]),.ready(ym[g]),.active(am[g]),.fault(fm[g]));
 end endgenerate
 integer errors=0,hchk=0,schk=0,rel=0,ph,i,b;
 always @(negedge hclk) if(hrst_n) begin
  hchk=hchk+1;
  if(rq[0]!==rm[0][127:0]||pq[0]!==pm[0]||rq[1]!==rm[1][255:128]||pq[1]!==pm[1])begin
   errors=errors+1;if(errors<10)$display("PC_REFCFG_Q_MISMATCH phase %0d hbm: W rel %b/%b E rel %b/%b",ph,pq[0],pm[0],pq[1],pm[1]);end
  if(pq[0]||pq[1])rel=rel+1;
 end
 always @(negedge clk) if(rst_n) begin
  schk=schk+1;
  if({yq[0],aq[0],fq[0],yq[1],aq[1],fq[1]}!=={ym[0],am[0],fm[0],ym[1],am[1],fm[1]})begin
   errors=errors+1;if(errors<10)$display("PC_REFCFG_Q_MISMATCH phase %0d status W %b%b%b/%b%b%b E %b%b%b/%b%b%b",ph,yq[0],aq[0],fq[0],ym[0],am[0],fm[0],yq[1],aq[1],fq[1],ym[1],am[1],fm[1]);end
 end
 function automatic [7:0] rl(input integer p);integer rp;begin rp=(p*118/32)%118;rl=8'(118+rp+((rp+118+p)%2));end endfunction
 reg[7:0]by[0:31];integer g_i;
 task automatic mkrow(input integer mode,input integer badp);integer p;begin
  for(p=0;p<32;p=p+1)by[p]=(mode==0)?rl(p):8'(118+$urandom%119);
  if(badp>=0)by[badp]=($urandom%2)?8'd50:8'd240;
  for(g_i=0;g_i<2;g_i=g_i+1)begin
   dq[g_i]={256{1'b0}};dm[g_i]={32{8'd118}};
   for(p=0;p<16;p=p+1)begin dq[g_i][8*p+:8]=by[16*g_i+p];dm[g_i][8*(16*g_i+p)+:8]=by[16*g_i+p];end
   for(p=16;p<32;p=p+1)dq[g_i][8*p+:8]=($urandom%2)?8'h00:8'hff;   // ignored half of the frame
  end
 end endtask
 task automatic frame(input [11:0] a);begin @(negedge clk);cv=1;ca=a;@(negedge clk);cv=0;repeat(3)@(negedge clk);end endtask
 task automatic boot;begin rst_n=0;hrst_n=0;repeat(4)@(negedge clk);rst_n=1;hrst_n=1;repeat(30+$urandom%60)@(negedge clk);end endtask
 initial begin
  for(ph=0;ph<12;ph=ph+1)begin
   boot;
   case(ph%6)
    0:begin mkrow(ph==0?0:1,-1);frame(12'h800);end
    1:begin mkrow(1,-1);frame(12'h800);repeat(40)@(negedge clk);mkrow(1,-1);frame(12'h800);end
    2:begin mkrow(1,$urandom%16);frame(12'h800);end
    3:begin mkrow(1,16+$urandom%16);frame(12'h800);end
    4:begin mkrow(1,-1);frame(12'h801);end
    default:begin mkrow(1,-1);frame(12'h800);end
   endcase
   repeat(200)@(negedge hclk);
  end
  if(rel<500||hchk<2000)begin errors=errors+1;$display("PC_REFCFG_Q_VACUOUS releases %0d hbm checks %0d",rel,hchk);end
  if(errors==0)$display("PC_REFCFG_Q PASS phases=12 hbm_checks=%0d stream_checks=%0d release_edges=%0d MUT=%0d",hchk,schk,rel,MUT);
  else $fatal(1,"PC_REFCFG_Q FAIL errors=%0d MUT=%0d",errors,MUT);
  $finish;
 end
endmodule
`default_nettype wire
