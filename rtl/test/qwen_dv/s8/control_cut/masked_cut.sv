`timescale 1ns/1ps
module s8_masked_cut #(parameter D=4)(input ck,output reg done=0);
localparam W=12,FW=4,FLO=8,AW=$clog2(D);
reg[W-1:0]data=12'h15a;reg[2:0]rsi=7;integer cyc=0,checks=0,negative_hits=0,bank_mutant_hits=0;
wire[D-1:0]oh[0:2];wire[D*FW-1:0]masked,badmasked;
wire[D*W-1:0]ob[0:2],nb[0:2];wire[D*(AW+1)-1:0]oe[0:2],ne[0:2];wire[D-1:0]ov[0:2],nv[0:2];
for(genvar s=0;s<D;s=s+1)begin:g_gate
 qfd_dv_s8_lp_flags_mask_gate #(.FW(FW),.ID(s)) gate(data[FLO+:FW],oh[0][s],oh[1][s],oh[2][s],masked[s*FW+:FW]);
 assign badmasked[s*FW+:FW]=(oh[0][s]&oh[1][s]&oh[2][s])?data[FLO+:FW]:4'b0;
end
for(genvar w=0;w<3;w=w+1)begin:g_writer
 ot_pl_land_n32_local_w #(.W(W),.D(D)) oldw(ck,rsi[w],data,ob[w],oe[w],ov[w]);
 qfd_dv_s8_lp_flags_mask_local_w #(.W(W),.D(D),.FW(FW),.FLO(FLO)) neww(ck,rsi[w],data,masked,oh[w],nb[w],ne[w],nv[w]);
 wire[D*W-1:0]mb;wire[D*(AW+1)-1:0]me;wire[D-1:0]mv,moh;
 qfd_dv_s8_lp_flags_mask_local_w #(.W(W),.D(D),.FW(FW),.FLO(FLO)) mutw(ck,rsi[w],data,badmasked,moh,mb,me,mv);
 // Arbitrary independent actual selector cold states (binary/X/Z), same old/new.
 initial begin
  oldw.g_oh[0].u_oh.r={D{1'bx}};neww.g_oh[0].u_oh.r={D{1'bx}};mutw.g_oh[0].u_oh.r={D{1'bx}};
  oldw.g_oh[0].u_oh.r[w]=1;neww.g_oh[0].u_oh.r[w]=1;mutw.g_oh[0].u_oh.r[w]=1;
  oldw.g_oh[0].u_oh.r[(w+1)%D]=1'bz;neww.g_oh[0].u_oh.r[(w+1)%D]=1'bz;mutw.g_oh[0].u_oh.r[(w+1)%D]=1'bz;
 end
 for(genvar s=0;s<D;s=s+1)begin:g_cold
  initial begin
   oldw.g_slot[s].g_grp[0].dq=12'(w*17+s*31);
   neww.g_slot[s].g_grp[0].dq=12'(w*17+s*31);mutw.g_slot[s].g_grp[0].dq=12'(w*17+s*31);
   oldw.g_slot[s].g_grp[0].dq[10]=1'bx;neww.g_slot[s].g_grp[0].dq[10]=1'bx;mutw.g_slot[s].g_grp[0].dq[10]=1'bx;
   oldw.g_slot[s].g_grp[0].dq[11]=1'bz;neww.g_slot[s].g_grp[0].dq[11]=1'bz;mutw.g_slot[s].g_grp[0].dq[11]=1'bz;
  end
 end
 always @(posedge ck)begin #1;
  if(ob[w]!==mb)bank_mutant_hits=bank_mutant_hits+1;
  if(ob[w]!==nb[w]||ov[w]!==nv[w]||oe[w]!==ne[w]||oldw.rq!==neww.rq||oldw.g_oh[0].u_oh.r!==neww.g_oh[0].u_oh.r)
   $fatal(1,"MASKED_EQ_MISMATCH D%0d writer%0d cycle%0d",D,w,cyc);
 end
end
always @(negedge ck)begin
 cyc=cyc+1;data=$random;
 case(cyc%4)0:data[FLO+:FW]=4'b01xz;1:data[FLO+:FW]=4'bzx10;2:data[FLO+:FW]=4'bzzzz;endcase
 for(integer w=0;w<3;w=w+1)rsi[w]=!((cyc%(24+w))>=8&&(cyc%(24+w))<12);
end
always @(posedge ck)begin #2;
 checks=checks+1;
 // Causal OR->AND mutant: whenever a real writer is enabled, the wrong
 // conjunction can zero its D. This must be observed on actual source OH.
 for(integer s=0;s<D;s=s+1)begin
  if((oh[0][s]===1'b1||oh[1][s]===1'b1||oh[2][s]===1'b1) && ((oh[0][s]&oh[1][s]&oh[2][s])!==1'b1))begin
   if(masked[s*FW+:FW] !== ((oh[0][s]&oh[1][s]&oh[2][s])?data[FLO+:FW]:4'b0))negative_hits=negative_hits+1;
  end
 end
 if(cyc==255)begin
  if(checks<250||negative_hits<1||bank_mutant_hits<1)$fatal(1,"MASKED_EQ_COVERAGE");
  $display("MASKED_EQ_PASS D%0d checks%0d actual_writer_allbank_state_XZ independent_OH coldbanks resetreassert ANDmutant_differences%0d actual_bank_mutant_differences%0d",D,checks,negative_hits,bank_mutant_hits);done=1;
 end
end
endmodule
module tb_s8_control_cut;
reg ck=0;always #5 ck=~ck;reg rst=0;integer c=0;
always @(negedge ck)begin c=c+1;rst=!(c<8||(c>=160&&c<168));end
wire a,b,d;
s8_guard_cut guards(ck,rst,a);
s8_masked_cut #(.D(4)) masks4(ck,b);
s8_masked_cut #(.D(8)) masks8(ck,d);
initial begin wait(a&&b&&d);$display("S8_CONTROL_CUT_PASS required_bounded_actual_source_only");$finish;end
endmodule
