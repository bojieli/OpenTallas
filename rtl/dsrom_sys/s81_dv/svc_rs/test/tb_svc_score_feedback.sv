`timescale 1ns/1ps
// Staged partition: real native SCORE trace -> actual 16-node protected SX
// -> active head0's production row glue -> actual fold2 -> SRAM -> P source
// -> actual SX -> production P packet glue. Other SM heads are zero providers.
// Trace source replication and rs_c glue are explicit; no full die/PIO claim.
module tb_svc_score_feedback;
 `include "dsdv_svc_rs_roles.svh"
 `include "dsdv_svc_sx_roles_h8.svh"
 localparam integer H=8,W=1076,SRC_GO=128,PIO=800,SEL=10;
 reg ck=0;always #0.5 ck=~ck;reg rn=0;
 integer cyc=0,drop=0,errors=0,root_scores=0,taps=0,serows=0,writes=0,nzrows=0,pfires=0,proots=0,pheaders=0,pwords=0,missing_n=0;
 integer first_root=-1,last_root=-1,first_tap=-1,last_tap=-1,first_se=-1,last_se=-1,first_sm=-1,last_sm=-1,first_pf=-1,last_pf=-1,first_pr=-1,last_pr=-1,header_date=-1,first_pw=-1,last_pw=-1;
 reg[W-1:0]src[0:7];reg[31:0]dates[0:7];string scores_file,dates_file;
 wire[3:0]gi_v[0:15],go_v[0:15],si_v[0:15],so_v[0:15];
 wire[4*W-1:0]gi_d[0:15],go_d[0:15],si_d[0:15],so_d[0:15];
 wire[15:0]rt_v,t_v,xf;wire[W-1:0]rt_d[0:15];wire[19:0]t_tag[0:15];wire[127:0]t_y[0:15];wire[3:0]t_f[0:15];
 reg[15:0]lv;reg[W-1:0]ld[0:15];
 wire[15:0]pfire,pmissing;wire[W-1:0]pbeat[0:15];reg[7:0]pk[0:15];
 wire pwin=cyc>=PIO-8;
 function automatic integer neighbor(input integer s,input integer f);integer r,c;r=s%2;c=s/2;case(f)0:return r==0?2*c+1:-1;1:return c<7?2*(c+1)+r:-1;2:return r==1?2*c:-1;default:return c>0?2*(c-1)+r:-1;endcase endfunction
 function automatic integer tile_of(input integer s);reg[21:0]r;r=rs_role(4'(s));return r[3:0];endfunction
 function automatic[31:0]times16(input[31:0]x);if(x==0)return 0;return {x[31],8'(x[30:23]+8'd4),x[22:0]};endfunction
 function automatic[15:0]bf16(input[31:0]x);reg[31:0]y;y=x+32'h7fff+32'(x[16]);return y[31:16];endfunction
 wire[255:0]prw,pb_wd;reg[5:0]pb_n=0;
 reg[255:0]expected[0:39];
 wire[7:0]pk_n=pfire[SEL]?pk[SEL]+1'b1:pk[SEL];
 genvar s,f;
 generate for(s=0;s<16;s++)begin:g_s
  for(f=0;f<4;f++)begin:g_f
   localparam integer NB=neighbor(s,f),OF=(f+2)%4;
   if(NB>=0)begin assign gi_v[s][f]=go_v[NB][OF];assign gi_d[s][W*f+:W]=go_d[NB][W*OF+:W];assign si_v[s][f]=so_v[NB][OF];assign si_d[s][W*f+:W]=so_d[NB][W*OF+:W];end
   else begin assign gi_v[s][f]=0;assign gi_d[s][W*f+:W]=0;assign si_v[s][f]=0;assign si_d[s][W*f+:W]=0;end
  end
  dsdv_svc_sx_pl u(.ck(ck),.rst(rn),.sid(4'(s)),.l_v(lv[s]),.l_d(ld[s]),.gi_v(gi_v[s]),.gi_d(gi_d[s]),.go_v(go_v[s]),.go_d(go_d[s]),.si_v(si_v[s]),.si_d(si_d[s]),.so_v(so_v[s]),.so_d(so_d[s]),.rt_v(rt_v[s]),.rt_d(rt_d[s]),.t_v(t_v[s]),.t_tag(t_tag[s]),.t_y(t_y[s]),.t_f(t_f[s]),.fault(xf[s]));
  dsdv_svc_p_source #(.H(8))u_p(.pon(rn&&pwin),.hsel(tile_of(s)<8),.pk(pk[s]),.tile(4'(tile_of(s))),.tjob(10'd32),.jcs(16'(cyc)),.pio(16'(PIO+sx_role_off(s))),.prw(s==SEL?prw:256'd0),.rows_ready(s==SEL?pb_n:6'd2),.fire(pfire[s]),.missing(pmissing[s]),.beat(pbeat[s]));
 end endgenerate
 always@(posedge ck)begin
  cyc<=cyc+1;
  for(integer s2=0;s2<16;s2++)if(!rn)pk[s2]<=0;else if(pfire[s2])pk[s2]<=pk[s2]+1'b1;
 end
 always@(negedge ck)begin
  lv=0;
  for(integer s2=0;s2<16;s2++)begin
   ld[s2]=0;
   for(integer b=0;b<8;b++)if(cyc==SRC_GO+dates[b]+sx_role_off(s2))begin lv[s2]=!(drop&&s2==0&&b==0);ld[s2]=src[b];end
   if(pfire[s2])begin if(lv[s2])errors++;lv[s2]=1;ld[s2]=pbeat[s2];end
  end
 end
 // Exact production SE row assembly, selected sid10/tile0, pass0.
 reg[511:0]se_acc=0,se_d=0,se_nxt;reg se_v=0;
 wire[15:0]trow=t_tag[SEL][19:4];wire[3:0]tm=t_tag[SEL][3:0];
 wire[2:0]tn=3'(tm[0])+3'(tm[1])+3'(tm[2])+3'(tm[3]);
 wire tlast=trow[3:2]==3||32'(trow)+32'(tn)>=32;
 wire tvs=t_v[SEL]&&!pwin;
 always_comb begin se_nxt=se_acc;for(integer i=0;i<4;i++)se_nxt[32*(4*trow[3:2]+i)+:32]=tm[i]?t_y[SEL][32*i+:32]:32'd0;end
 always@(posedge ck)begin
  if(!rn)begin se_acc<=0;se_d<=0;se_v<=0;end
  else begin se_v<=tvs&&tlast;if(tvs)se_acc<=tlast?512'd0:se_nxt;if(tvs&&tlast)se_d<=se_nxt;end
 end
 reg par_v,par_p;reg[2:0]par_j;reg[511:0]par_d;
 always_comb begin
  par_v=0;par_p=1;par_j=0;par_d=0;
  if(cyc==81)begin par_v=1;par_d[64+:7]=2;par_d[96+:32]=32'h3e800000;par_d[128+:3]=1;end
  if(cyc==82)begin par_v=1;par_j=1;par_d={16{32'h3f000000}};end
 end
 wire wv,fu,fo;wire[13:0]wa;wire[15:0]wm;wire[511:0]wd;
 ot_s81_su_sms_fold2 u_sm(.clk(ck),.rst_in(rn),.cfg_g(4'd0),.j_st(cyc==80),.j_kind(4'd4),.j_jid(8'd1),.r_v(se_v||par_v),.r_p(se_v?1'b0:par_p),.r_j(se_v?3'd0:par_j),.r_d(se_v?se_d:par_d),.w_v(wv),.w_a(wa),.w_m(wm),.w_d(wd),.o_fu(fu),.o_fo(fo),.o_alive(),.o_den(),.o_rjid());
 wire pb_w=wv&&pb_n<40;
 for(genvar j=0;j<16;j++)assign pb_wd[16*j+:16]=bf16(wd[32*j+:32]);
 dsdv_svc_mem_ar #(.W(256),.DEPTH(40),.AW(6),.MACRO(1))u_pb(.clk(ck),.ra_n(pk_n[7:2]),.we(pb_w),.wa(pb_n),.wd(pb_wd),.rd(prw));
 always@(posedge ck)if(!rn)pb_n<=0;else if(pb_w)pb_n<=pb_n+1'b1;
 // Production H8 P-return packet assembly. This is copied rs_c glue, not
 // a model of host/tree delivery; its exported words define that boundary.
 function automatic[511:0]pack_p(input[W-1:0]b);reg[511:0]p;p=0;for(integer r=0;r<4;r++)for(integer h=0;h<8;h++)p[16*(8*r+h)+:16]=b[32+32*(8*r+h)+16+:16];return p;endfunction
 reg pph=0,phd=0,pp_v=0;reg[9:0]pwc=0;reg[512:0]pp_d=0;reg[511:0]phold=0;
 wire rtp=rt_v[9]&&pwin;
 always@(posedge ck)begin
  if(!rn)begin pph<=0;phd<=0;pwc<=0;pp_v<=0;end
  else begin pp_v<=0;
   if(rtp)begin if(!phd)begin pp_v<=1;phd<=1;pph<=1;end else if(!pph)pph<=1;else errors++;end
   else if(pph)begin pp_v<=pwc<8;pwc<=pwc+1'b1;pph<=0;end
  end
  if(rtp)phold<=pack_p(rt_d[9]);
  if(rtp&&!phd)pp_d<={1'b0,4'd5,1'b0,4'b0001,8'd1,3'd0,12'd8,480'd0};else pp_d<={1'b0,phold};
 end
 always@(posedge ck)if(rn)begin
  reg[31:0]got,want;integer ix;reg[511:0]want_p;
  if(se_v&&par_v)errors++;
  if(rt_v[9]&&!pwin)begin
   if(first_root<0)first_root=cyc;last_root=cyc;
   if(root_scores>=8)errors++;
   else begin
    if(rt_d[9][W-1-:20]!==src[root_scores][W-1-:20]||rt_d[9][31:0]!==0)errors++;
    for(integer k=0;k<32;k++)begin got=rt_d[9][32+32*k+:32];want=times16(src[root_scores][32+32*k+:32]);if(got!==want)errors++;end
   end
   root_scores++;
  end
  if(tvs)begin
   if(first_tap<0)first_tap=cyc;last_tap=cyc;
   if(taps>=8)errors++;
   else begin if(t_tag[SEL]!==src[taps][W-1-:20]||t_f[SEL]!==0)errors++;for(integer r=0;r<4;r++)if(t_y[SEL][32*r+:32]!==times16(src[taps][32+32*(8*r)+:32]))errors++;end
   taps++;
  end
  if(se_v)begin if(first_se<0)first_se=cyc;last_se=cyc;serows++;$display("SE_ROW cycle%0d data%h",cyc,se_d);end
  if(pb_w)begin
   if(first_sm<0)first_sm=cyc;last_sm=cyc;
   expected[writes]=pb_wd;if(|pb_wd)nzrows++;
   for(integer i=0;i<16;i++)if(wd[32*i+:32]!==32'h3f800000||pb_wd[16*i+:16]!==16'h3f80)errors++;
   if(wa!==14'(16*writes)||wm!==16'hffff)errors++;
   $display("SM_WRITE cycle%0d row%0d data%h",cyc,writes,pb_wd);writes++;
  end
  if(pfire[SEL])begin
   if(first_pf<0)first_pf=cyc;last_pf=cyc;pfires++;
   if(pmissing[SEL])missing_n++;
   else for(integer r=0;r<4;r++)for(integer h=0;h<8;h++)begin
    want=h==0?{expected[pk[SEL]/4][16*(4*(pk[SEL]%4)+r)+:16],16'd0}:32'd0;
    if(pbeat[SEL][32+32*(8*r+h)+:32]!==want)errors++;
   end
   $display("P_FIRE cycle%0d pk%0d missing%0d",cyc,pk[SEL],pmissing[SEL]);
  end
  if(rtp)begin
   if(first_pr<0)first_pr=cyc;last_pr=cyc;
   if(proots>=8)errors++;
   else begin
    if(rt_d[9][W-1-:20]!=={16'(4*proots),4'hf}||rt_d[9][31:0]!==0)errors++;
    for(integer r=0;r<4;r++)for(integer h=0;h<8;h++)begin want=h==0?{expected[proots/4][16*(4*(proots%4)+r)+:16],16'd0}:32'd0;if(rt_d[9][32+32*(8*r+h)+:32]!==want)errors++;end
   end
   proots++;
  end
  if(pp_v)begin
   if(pheaders==0)begin pheaders++;header_date=cyc;if(pp_d[511:508]!==5||pp_d[491:480]!==8)errors++;end
   else begin
    if(first_pw<0)first_pw=cyc;last_pw=cyc;want_p=0;
    for(integer r=0;r<4;r++)want_p[16*(8*r)+:16]=expected[pwords/4][16*(4*(pwords%4)+r)+:16];
    if(pp_d!=={1'b0,want_p})errors++;
    $display("P_WORD cycle%0d index%0d data%h",cyc,pwords,pp_d[511:0]);pwords++;
   end
  end
 end
 initial begin
  void'($value$plusargs("drop=%d",drop));
  if(!$value$plusargs("scores=%s",scores_file)||!$value$plusargs("dates=%s",dates_file))$fatal(1,"missing trace files");
  $readmemh(scores_file,src);$readmemh(dates_file,dates);
  for(integer k=0;k<16;k++)begin pk[k]=0;ld[k]=0;end
  repeat(64)@(negedge ck);rn=1;
  repeat(1200)@(negedge ck);
  if(root_scores!=8||taps!=8||serows!=2||writes!=2||nzrows!=2||pfires!=8||proots!=8||pheaders!=1||pwords!=8||missing_n||fu||fo||(|xf))errors++;
  $display("FEEDBACK_DATES sourceGO%0d root%0d:%0d tap%0d:%0d SE%0d:%0d SM%0d:%0d Pfire%0d:%0d Proot%0d:%0d Pheader%0d Pbody%0d:%0d",SRC_GO,first_root,last_root,first_tap,last_tap,first_se,last_se,first_sm,last_sm,first_pf,last_pf,first_pr,last_pr,header_date,first_pw,last_pw);
  $display("FEEDBACK_COUNTS drop%0d roots%0d taps%0d SE%0d SM%0d nonzero%0d Pfire%0d Proot%0d headers%0d words%0d missing%0d errors%0d sxFault%h fu%0d fo%0d",drop,root_scores,taps,serows,writes,nzrows,pfires,proots,pheaders,pwords,missing_n,errors,xf,fu,fo);
  if(drop)begin if(errors==0)$fatal(1,"FEEDBACK_DROP MISSED");$display("SCORE_FEEDBACK NEGATIVE_CAUGHT");end
  else if(errors)$fatal(1,"SCORE_FEEDBACK FAIL");else $display("SCORE_FEEDBACK PASS");
  $finish;
 end
endmodule
