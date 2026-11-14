`timescale 1ns/1ps
// Staged all-active-head H8 feedback; sixteen actual folded-SM instances share
// one protected master, eight active per head base. No native arithmetic clone.
module tb_svc_allhead_feedback;
 `include "dsdv_svc_rs_roles.svh"
 `include "dsdv_svc_sx_roles_h8.svh"
 localparam integer H=8,W=1076,GO=128,MAXB=160;
 integer rows=32,hb=0,nb=8,nv=2,pio=800,cyc=0,errors=0;
 integer roots=0,proots=0,headers=0,words=0,first_root=-1,last_root=-1,first_pr=-1,last_pr=-1,header_date=-1,first_word=-1,last_word=-1;
 integer taps[0:15],secount[0:15],writes[0:15],pfires[0:15],missing[0:15],first_se[0:15],last_se[0:15],first_sm[0:15],last_sm[0:15],first_pf[0:15],last_pf[0:15];
 reg ck=0;always #0.5 ck=~ck;reg rn=0;
 reg[W-1:0]src[0:MAXB-1];reg[31:0]dates[0:MAXB-1];string scorefile,datefile;
 wire[3:0]giv[0:15],gov[0:15],siv[0:15],sov[0:15];wire[4*W-1:0]gid[0:15],god[0:15],sid[0:15],sod[0:15];
 wire[15:0]rtv,tv,xf;wire[W-1:0]rtd[0:15];wire[19:0]ttag[0:15];wire[127:0]ty[0:15];wire[3:0]tf[0:15];reg[15:0]lv;reg[W-1:0]ld[0:15];
 wire[15:0]fire,pmissing,wv,fu,fo;wire[W-1:0]pbeat[0:15];reg[7:0]pk[0:15];reg[5:0]pn[0:15];
 wire[255:0]prw[0:15],pwd[0:15];wire[511:0]wd[0:15];wire[13:0]wa[0:15];wire[15:0]wm[0:15];
 reg[511:0]seacc[0:15],sed[0:15],senext[0:15];reg[15:0]sev;
 wire pwin=cyc>=pio-8;
 function automatic integer tileof(input integer s);reg[21:0]r;r=rs_role(4'(s));return r[3:0];endfunction
 function automatic integer neighbor(input integer s,input integer f);integer r,c;r=s%2;c=s/2;case(f)0:return r==0?2*c+1:-1;1:return c<7?2*(c+1)+r:-1;2:return r==1?2*c:-1;default:return c>0?2*(c-1)+r:-1;endcase endfunction
 function automatic[31:0]x16(input[31:0]x);return x==0?32'd0:{x[31],8'(x[30:23]+8'd4),x[22:0]};endfunction
 function automatic[15:0]bf16(input[31:0]x);reg[31:0]y;y=x+32'h7fff+32'(x[16]);return y[31:16];endfunction
 reg parv;reg[2:0]parj;reg[511:0]pard;
 always_comb begin
  parv=0;parj=0;pard=0;
  if(cyc==81)begin parv=1;pard[64+:7]=7'(nv);pard[96+:32]=32'h3b800000;pard[128+:3]=3'($clog2(nv));end
  if(cyc==82)begin parv=1;parj=1;pard={16{32'hc2000000}};end
 end
 genvar s,f,j;
 generate for(s=0;s<16;s++)begin:g_s
  localparam integer TILE=tileof(s);
  wire active_head=(TILE/8)==hb;
  for(f=0;f<4;f++)begin:g_f
   localparam integer N=neighbor(s,f),OF=(f+2)%4;
   if(N>=0)begin assign giv[s][f]=gov[N][OF];assign gid[s][W*f+:W]=god[N][W*OF+:W];assign siv[s][f]=sov[N][OF];assign sid[s][W*f+:W]=sod[N][W*OF+:W];end
   else begin assign giv[s][f]=0;assign gid[s][W*f+:W]=0;assign siv[s][f]=0;assign sid[s][W*f+:W]=0;end
  end
  dsdv_svc_sx_pl sx(.ck(ck),.rst(rn),.sid(4'(s)),.l_v(lv[s]),.l_d(ld[s]),.gi_v(giv[s]),.gi_d(gid[s]),.go_v(gov[s]),.go_d(god[s]),.si_v(siv[s]),.si_d(sid[s]),.so_v(sov[s]),.so_d(sod[s]),.rt_v(rtv[s]),.rt_d(rtd[s]),.t_v(tv[s]),.t_tag(ttag[s]),.t_y(ty[s]),.t_f(tf[s]),.fault(xf[s]));
  wire[15:0]tr=ttag[s][19:4];wire[3:0]tm=ttag[s][3:0];wire[2:0]tn=3'(tm[0])+3'(tm[1])+3'(tm[2])+3'(tm[3]);
  wire lastrow=tr[3:2]==3||32'(tr)+32'(tn)>=rows;
  wire vs=tv[s]&&!pwin&&active_head;
  always_comb begin senext[s]=seacc[s];for(integer r=0;r<4;r++)senext[s][32*(4*tr[3:2]+r)+:32]=tm[r]?ty[s][32*r+:32]:32'd0;end
  always@(posedge ck)if(!rn)begin seacc[s]<=0;sed[s]<=0;sev[s]<=0;end else begin sev[s]<=vs&&lastrow;if(vs)seacc[s]<=lastrow?512'd0:senext[s];if(vs&&lastrow)sed[s]<=senext[s];end
  ot_s81_su_sms_fold2_pl sm(.clk(ck),.rst_in(rn),.cfg_g(4'(TILE)),.j_st(cyc==80&&active_head),.j_kind(4'd4),.j_jid(8'd1),.r_v(active_head&&(sev[s]||parv)),.r_p(!sev[s]),.r_j(sev[s]?3'd0:parj),.r_d(sev[s]?sed[s]:pard),.w_v(wv[s]),.w_a(wa[s]),.w_m(wm[s]),.w_d(wd[s]),.o_fu(fu[s]),.o_fo(fo[s]),.o_alive(),.o_den(),.o_rjid());
  for(j=0;j<16;j++)assign pwd[s][16*j+:16]=bf16(wd[s][32*j+:32]);
  wire[7:0]pkn=fire[s]?pk[s]+1'b1:pk[s];wire pbw=wv[s]&&pn[s]<40;
  dsdv_svc_mem_ar #(.W(256),.DEPTH(40),.AW(6),.MACRO(1))pb(.clk(ck),.ra_n(pkn[7:2]),.we(pbw),.wa(pn[s]),.wd(pwd[s]),.rd(prw[s]));
  dsdv_svc_p_source #(.H(8))ps(.pon(rn&&pwin),.hsel(active_head),.pk(pk[s]),.tile(4'(TILE)),.tjob(10'(rows)),.jcs(16'(cyc)),.pio(16'(pio+sx_role_off(s))),.prw(prw[s]),.rows_ready(pn[s]),.fire(fire[s]),.missing(pmissing[s]),.beat(pbeat[s]));
  always@(posedge ck)if(!rn)begin pk[s]<=0;pn[s]<=0;end else begin if(fire[s])pk[s]<=pk[s]+1'b1;if(pbw)pn[s]<=pn[s]+1'b1;end
 end endgenerate
 always@(posedge ck)cyc<=cyc+1;
 always@(negedge ck)begin
  lv=0;
  for(integer z=0;z<16;z++)begin ld[z]=0;for(integer b=0;b<nb;b++)if(cyc==GO+dates[b]+sx_role_off(z))begin lv[z]=1;ld[z]=src[b];end
   if(fire[z])begin if(lv[z])errors++;lv[z]=1;ld[z]=pbeat[z];end
  end
 end
 function automatic[511:0]pack(input[W-1:0]b);reg[511:0]p;p=0;for(integer r=0;r<4;r++)for(integer h=0;h<8;h++)p[16*(8*r+h)+:16]=b[32+32*(8*r+h)+16+:16];return p;endfunction
 reg pph=0,phd=0,ppv=0;reg[9:0]pwc=0;reg[512:0]ppd=0;reg[511:0]holdp=0;wire rp=rtv[9]&&pwin;
 always@(posedge ck)begin
  if(!rn)begin pph<=0;phd<=0;pwc<=0;ppv<=0;end else begin ppv<=0;if(rp)begin if(!phd)begin ppv<=1;phd<=1;pph<=1;end else if(!pph)pph<=1;else errors++;end else if(pph)begin ppv<=pwc<nb;pwc<=pwc+1'b1;pph<=0;end end
  if(rp)holdp<=pack(rtd[9]);if(rp&&!phd)ppd<={1'b0,4'd5,1'b0,4'b0001,8'd1,3'd0,12'(nb),480'd0};else ppd<={1'b0,holdp};
 end
 always@(posedge ck)if(rn)begin
  reg[31:0]want;
  if(rtv[9]&&!pwin)begin
   if(first_root<0)first_root=cyc;last_root=cyc;
   if(roots>=nb)errors++;else begin if(rtd[9][W-1-:20]!==src[roots][W-1-:20]||rtd[9][31:0]!==0)errors++;for(integer k=0;k<32;k++)if(rtd[9][32+32*k+:32]!==x16(src[roots][32+32*k+:32]))errors++;end roots++;
  end
  for(integer z=0;z<16;z++)begin
   if(tv[z]&&!pwin&&(tileof(z)/8==hb))begin
    if(taps[z]>=nb)errors++;else begin if(ttag[z]!==src[taps[z]][W-1-:20]||tf[z]!==0)errors++;for(integer r=0;r<4;r++)if(ty[z][32*r+:32]!==x16(src[taps[z]][32+32*(8*r+tileof(z)%8)+:32]))errors++;end taps[z]++;
   end
   if(sev[z])begin if(first_se[z]<0)first_se[z]=cyc;last_se[z]=cyc;secount[z]++;end
   if(wv[z])begin
    if(first_sm[z]<0)first_sm[z]=cyc;last_sm[z]=cyc;
    if(tileof(z)/8!=hb||wa[z]!==14'(16*writes[z]+tileof(z))||wm[z]!==16'hffff)errors++;
    for(integer k=0;k<16;k++)if(wd[z][32*k+:32]!==32'h3f800000||pwd[z][16*k+:16]!==16'h3f80)errors++;
    writes[z]++;
   end
   if(fire[z])begin
    if(first_pf[z]<0)first_pf[z]=cyc;last_pf[z]=cyc;pfires[z]++;if(pmissing[z])missing[z]++;
    for(integer r=0;r<4;r++)for(integer h=0;h<8;h++)begin want=(tileof(z)/8==hb&&h==tileof(z)%8)?32'h3f800000:32'd0;if(pbeat[z][32+32*(8*r+h)+:32]!==want)errors++;end
   end
  end
  if(rp)begin
   if(first_pr<0)first_pr=cyc;last_pr=cyc;
   if(proots>=nb||rtd[9][W-1-:20]!=={16'(4*proots),4'hf}||rtd[9][31:0]!==0)errors++;
   for(integer k=0;k<32;k++)if(rtd[9][32+32*k+:32]!==32'h3f800000)errors++;
   proots++;
  end
  if(ppv)begin
   if(headers==0)begin headers++;header_date=cyc;if(ppd[511:508]!==5||ppd[491:480]!==12'(nb))errors++;end
   else begin if(first_word<0)first_word=cyc;last_word=cyc;if(ppd!=={1'b0,{32{16'h3f80}}})errors++;$display("ALLHEAD_P_WORD hb%0d rows%0d cycle%0d index%0d data%h",hb,rows,cyc,words,ppd[511:0]);words++;end
  end
 end
 initial begin
  void'($value$plusargs("hb=%d",hb));void'($value$plusargs("rows=%d",rows));void'($value$plusargs("pio=%d",pio));
  if(hb<0||hb>1||(rows!=32&&rows!=128))$fatal(1,"named rows32/128 HB0/1 only");nb=rows/4;nv=rows/16;
  if(!$value$plusargs("scores=%s",scorefile)||!$value$plusargs("dates=%s",datefile))$fatal(1,"missing actual/equality-checked producer trace");
  $readmemh(scorefile,src,0,nb-1);$readmemh(datefile,dates,0,nb-1);
  for(integer z=0;z<16;z++)begin pk[z]=0;pn[z]=0;ld[z]=0;taps[z]=0;secount[z]=0;writes[z]=0;pfires[z]=0;missing[z]=0;first_se[z]=-1;last_se[z]=-1;first_sm[z]=-1;last_sm[z]=-1;first_pf[z]=-1;last_pf[z]=-1;end
  repeat(64)@(negedge ck);rn=1;repeat(1200)@(negedge ck);
  for(integer z=0;z<16;z++)begin
   if(taps[z]!=(tileof(z)/8==hb?nb:0)||secount[z]!=(tileof(z)/8==hb?nv:0)||writes[z]!=(tileof(z)/8==hb?nv:0)||pfires[z]!=nb||missing[z])errors++;
   $display("ALLHEAD_HEAD hb%0d rows%0d sid%0d tile%0d taps%0d SE%0d SM%0d P%0d missing%0d SEDates%0d:%0d SMDates%0d:%0d PFireDates%0d:%0d",hb,rows,z,tileof(z),taps[z],secount[z],writes[z],pfires[z],missing[z],first_se[z],last_se[z],first_sm[z],last_sm[z],first_pf[z],last_pf[z]);
  end
  if(roots!=nb||proots!=nb||headers!=1||words!=nb||(|xf)||(|fu)||(|fo))errors++;
  $display("ALLHEAD_COUNTS hb%0d rows%0d roots%0d Proots%0d headers%0d words%0d errors%0d sxFault%h fu%h fo%h",hb,rows,roots,proots,headers,words,errors,xf,fu,fo);
  $display("ALLHEAD_DATES hb%0d rows%0d sourceGO%0d root%0d:%0d Proot%0d:%0d header%0d body%0d:%0d",hb,rows,GO,first_root,last_root,first_pr,last_pr,header_date,first_word,last_word);
  if(errors)$fatal(1,"ALLHEAD_FEEDBACK FAIL");else $display("ALLHEAD_FEEDBACK PASS hb%0d rows%0d",hb,rows);$finish;
 end
endmodule
