`timescale 1ps/1fs
// Full-stack, default-off protected R5a successor. No pinned predecessor is edited.
// Coded HBM returns: four SECDED64 payload words plus a SECDED64 {PC,sequence}.
// The bank tag binds SM,quarter,absolute stream line; output is corrected before
// publication. Credits32 and quarter/line order are unchanged.
module ot_hbm_accel_expert_fetch_p2 #(
 parameter ENABLE=0,REF_MODE=1,PHASE=0,NSM=8,NPC=32,NSECT=49,IW=9,ROW_BASE=0,DEPTH=512
)(
 input wire clk,hclk,rst_n,hrst_n,
 input wire[NSM*16-1:0] cfg_lines,input wire[NSECT*NPC/4*16-1:0] cfg_lut,
 input wire e_valid,input wire[71:0] e_code,output wire e_ready,input wire notice,
 output wire[NPC-1:0] row_v,col_v,output wire[NPC*3-1:0] row_op,
 output wire[NPC*5-1:0] row_bank,col_bank,col_col,output wire[NPC*19-1:0] row_row,
 input wire[NPC-1:0] rd_v,input wire[NPC*360-1:0] rd_code,
 output wire[NSM-1:0] s_valid,input wire[NSM-1:0] s_ready,
 output wire[NSM*1024-1:0] s_data,output wire fault);
 import ot_gpu_w6_secded_pkg::*;
 import ot_hbm_accel_r5a_ecc_pkg::*;
 generate if(!ENABLE)begin:off
  assign e_ready=0;assign row_v=0;assign col_v=0;assign row_op=0;assign row_bank=0;
  assign col_bank=0;assign col_col=0;assign row_row=0;assign s_valid=0;assign s_data=0;assign fault=0;
 end else begin:on
  localparam NI=NPC/4,SW=9,MW=$clog2(NSM),PERIOD=REF_MODE?118:3808;
  if(NPC!=32||NSM!=8||DEPTH!=512)begin:shape $error("P2 requires the modeled full32PC/8SM/512 shape");end
  // One-slot elastic accepted-ID cut: input valid never drives the FIFO pointer.
  (* keep = 1 *) reg iv,iv_n;(* keep = 1 *) reg[71:0] ic;
  wire idfull,idempty,idpop,idwf,idrf;wire[71:0] idword;
  (* keep = 1 *) reg ingress_poison;
  wire ibad=iv!=~iv_n;
  assign e_ready=(!iv||!idfull)&&!ibad&&!ingress_poison;
  always @(posedge clk or negedge rst_n)
   if(!rst_n)begin iv<=0;iv_n<=1;ic<=0;ingress_poison<=0;end
   else begin
    if(e_ready)begin iv<=e_valid;iv_n<=~e_valid;if(e_valid)ic<=e_code;end
    if(ibad)ingress_poison<=1;
   end
  ot_hbm_accel_cdc_fifo_p2 #(.W(72),.AW(3)) u_ids(
   .wclk(clk),.wrst_n(rst_n),.we(iv&&!ibad&&!ingress_poison),.wdata(ic),.full(idfull),.rd_freed(),.w_fault(idwf),
   .rclk(hclk),.rrst_n(hrst_n),.re(idpop),.rdata(idword),.empty(idempty),.r_fault(idrf));
  wire[65:0] iddecode=decode64(idword);
  (* keep = 1 *) reg[3:0] count,count_n;
  wire[NPC-1:0] done,pcbad,dspbad,lr,lf,le,lwf,lrf;
  wire[NPC*360-1:0] lq;
  wire[NPC*3-1:0] freed;
  (* keep = 1 *) reg hpoison;
  wire all_done=&done;
  wire retire=count!=0&&all_done&&idempty;
  assign idpop=!idempty&&count<8&&!retire&&!hpoison&&!iddecode[65]&&iddecode[63:IW]==0;
  always @(posedge hclk or negedge hrst_n)
   if(!hrst_n)begin count<=0;count_n<='1;hpoison<=0;end
   else begin
    if(retire)begin count<=0;count_n<='1;end
    else if(idpop)begin count<=count+1'b1;count_n<=~(count+1'b1);end
    if(count!=~count_n||idrf||(!idempty&&(iddecode[65]||iddecode[63:IW]!=0))||(|pcbad)||(|dspbad)||(|lwf)||(|(rd_v&lf)))hpoison<=1;
   end
  for(genvar p=0;p<NPC;p++)begin:pc
   // The descriptor lookup, ECC check and row offset terminate in PC-local
   // registers; global ptr/table select never drives the sequencer row flops.
   (* keep = 1 *) reg[71:0] tab[0:7];(* keep = 1 *) reg[3:0] ptr,ptr_n;(* keep = 1 *) reg pre,pre_n,dv,dv_n;
   (* keep = 1 *) reg[71:0] precode;(* keep = 1 *) reg[18:0] drow,drow_n;(* keep = 1 *) reg local_bad;
   wire ready,busy;
   wire[65:0] td=decode64(precode);
   wire dbad=ptr!=~ptr_n||pre!=~pre_n||dv!=~dv_n||drow!=~drow_n;
   assign dspbad[p]=local_bad||dbad||(notice_r!=~notice_n);
   assign done[p]=ptr==count&&!busy&&!dv&&!pre;
   always @(posedge hclk or negedge hrst_n)
    if(!hrst_n)begin ptr<=0;ptr_n<='1;pre<=0;pre_n<=1;dv<=0;dv_n<=1;drow<=0;drow_n<='1;local_bad<=0;precode<=0;end
    else begin
     if(idpop)tab[count[2:0]]<=encode64(64'(19'(ROW_BASE)+19'(iddecode[IW-1:0])));
     if(retire)begin ptr<=0;ptr_n<='1;end
     if(dv&&ready)begin dv<=0;dv_n<=1;ptr<=ptr+1'b1;ptr_n<=~(ptr+1'b1);end
     if(!dv&&!pre&&ptr<count&&!local_bad&&!hpoison)begin precode<=tab[ptr[2:0]];pre<=1;pre_n<=0;end
     if(pre)begin
      pre<=0;pre_n<=1;
      if(td[65]||td[63:19]!=0) local_bad<=1;
      else begin drow<=td[18:0];drow_n<=~td[18:0];dv<=1;dv_n<=0;end
     end
     if(dbad)local_bad<=1;
   end
   (* keep = 1 *) reg notice_r,notice_n;
   always @(posedge hclk or negedge hrst_n)if(!hrst_n)begin notice_r<=0;notice_n<=1;end else begin notice_r<=notice;notice_n<=~notice;end
   ot_hbm_accel_expert_stream_pc_p2 #(.ENABLE(1),.REF_MODE(REF_MODE),.PC(p),.CRED(32),
    .REF_PHASE((PHASE+p*PERIOD/32)%PERIOD),.IDLE0(0),.IDLE1(3),.IDLE2(4),.IDLE3(2),.IDLE4(5),.IDLE5(1),.IDLE6(6),.IDLE7(7)) u(
    .clk(hclk),.rst_n(hrst_n),.desc_v(dv&&!dbad&&!local_bad&&!hpoison),.desc_r(ready),.desc_row(drow),.desc_n(11'(NSECT)),
    .go(1'b1),.next_posted(1'b0),.notice(notice_r),.row_v(row_v[p]),.row_prio(),.row_gnt(1'b1),
    .row_op(row_op[p*3+:3]),.row_bank(row_bank[p*5+:5]),.row_row(row_row[p*19+:19]),
    .col_v(col_v[p]),.col_bank(col_bank[p*5+:5]),.col_col(col_col[p*5+:5]),
    .cred_ret(freed[p*3+:3]),.busy(busy),.ref_fault(pcbad[p]));
   ot_hbm_accel_cdc_fifo_p2 #(.W(360),.AW(5)) land(
    .wclk(hclk),.wrst_n(hrst_n),.we(rd_v[p]&&!hpoison),.wdata(rd_code[p*360+:360]),.full(lf[p]),.rd_freed(freed[p*3+:3]),.w_fault(lwf[p]),
    .rclk(clk),.rrst_n(rst_n),.re(lr[p]),.rdata(lq[p*360+:360]),.empty(le[p]),.r_fault(lrf[p]));
  end
  // Source-owned LUT/base staging and one-hot destination, independently local
  // to each PC. A, B and C have one lookup/add class apiece.
  wire[NPC-1:0] cv,grant,locbad;
  wire[NSM-1:0] dest[0:NPC-1];wire[31:0] index[0:NPC-1];wire[15:0] seq[0:NPC-1];
  for(genvar p=0;p<NPC;p++)begin:loc
   (* keep = 1 *) reg[NSM*16-1:0] lines,lines_n;(* keep = 1 *) reg[NSECT*16-1:0] lut,lut_n;
   always @(posedge clk)begin
    lines<=cfg_lines;lines_n<=~cfg_lines;
    for(integer j=0;j<NSECT;j++)begin lut[j*16+:16]<=cfg_lut[(j*NI+p/4)*16+:16];lut_n[j*16+:16]<=~cfg_lut[(j*NI+p/4)*16+:16];end
   end
   (* keep = 1 *) reg[5:0] gj,gj_n;(* keep = 1 *) reg[NSM*32-1:0] base,base_n,abase;
   (* keep = 1 *) reg av,bv,v;(* keep = 1 *) reg[2:0] asm,bsm;(* keep = 1 *) reg[7:0] aln,bln;
   (* keep = 1 *) reg[31:0] bbase,ix,ix_n;(* keep = 1 *) reg[7:0] dst,dst_n;(* keep = 1 *) reg[15:0] sq,sq_n,asq,bsq,csq;
   (* keep = 1 *) reg bad;
(* keep = 1 *) reg[0:0] av_bar;
(* keep = 1 *) reg[0:0] bv_bar;
(* keep = 1 *) reg[0:0] v_bar;
(* keep = 1 *) reg[2:0] asm_bar;
(* keep = 1 *) reg[2:0] bsm_bar;
(* keep = 1 *) reg[7:0] aln_bar;
(* keep = 1 *) reg[7:0] bln_bar;
(* keep = 1 *) reg[255:0] abase_bar;
(* keep = 1 *) reg[31:0] bbase_bar;
(* keep = 1 *) reg[15:0] asq_bar;
(* keep = 1 *) reg[15:0] bsq_bar;
(* keep = 1 *) reg[15:0] csq_bar;
   wire advance=grant[p]||!v;
   wire[15:0] ent=lut[gj*16+:16];
   wire statebad=(av!=~av_bar)||(bv!=~bv_bar)||(v!=~v_bar)||(asm!=~asm_bar)||(bsm!=~bsm_bar)||(aln!=~aln_bar)||(bln!=~bln_bar)||(abase!=~abase_bar)||(bbase!=~bbase_bar)||(asq!=~asq_bar)||(bsq!=~bsq_bar)||(csq!=~csq_bar)||(gj!=~gj_n)||(base!=~base_n)||(ix!=~ix_n)||(dst!=~dst_n)||(sq!=~sq_n);
   assign locbad[p]=bad||statebad;
   assign cv[p]=v&&!bad&&!statebad;assign dest[p]=dst;assign index[p]=ix;assign seq[p]=csq;
   always @(posedge clk or negedge rst_n)
    if(!rst_n)begin gj<=0;gj_n<='1;base<=0;base_n<='1;begin av<=0;av_bar<=~(0);end begin bv<=0;bv_bar<=~(0);end begin v<=0;v_bar<=~(0);end begin asm<=0;asm_bar<=~(0);end begin begin bsm<=0;bsm_bar<=~(0);end bsm_bar<=~(0);end begin aln<=0;aln_bar<=~(0);end begin bln<=0;bln_bar<=~(0);end begin abase<=0;abase_bar<=~(0);end begin begin bbase<=0;bbase_bar<=~(0);end bbase_bar<=~(0);end ix<=0;ix_n<='1;dst<=0;dst_n<='1;sq<=0;sq_n<='1;begin asq<=0;asq_bar<=~(0);end begin bsq<=0;bsq_bar<=~(0);end begin csq<=0;csq_bar<=~(0);end bad<=0;end
    else begin
     if(statebad)bad<=1;
     if(advance)begin
      begin v<=bv;v_bar<=~(bv);end ix<=bbase+32'(bln);ix_n<=~(bbase+32'(bln));dst<=8'(1)<<bsm;dst_n<=~(8'(1)<<bsm);begin csq<=bsq;csq_bar<=~(bsq);end
      begin begin bv<=av;bv_bar<=~(av);end bv_bar<=~(av);end begin bsm<=asm;bsm_bar<=~(asm);end begin bln<=aln;bln_bar<=~(aln);end begin bbase<=abase[asm*32+:32];bbase_bar<=~(abase[asm*32+:32]);end begin begin bsq<=asq;bsq_bar<=~(asq);end bsq_bar<=~(asq);end
      begin av<=1;av_bar<=~(1);end begin asm<=ent[10:8];asm_bar<=~(ent[10:8]);end begin begin aln<=ent[7:0];aln_bar<=~(ent[7:0]);end aln_bar<=~(ent[7:0]);end begin abase<=base;abase_bar<=~(base);end begin asq<=sq;asq_bar<=~(sq);end
      sq<=sq+1'b1;sq_n<=~(sq+1'b1);
      if(gj==NSECT-1)begin gj<=0;gj_n<='1;for(integer m=0;m<NSM;m++)begin base[m*32+:32]<=base[m*32+:32]+32'(lines[m*16+:16]);base_n[m*32+:32]<=~(base[m*32+:32]+32'(lines[m*16+:16]));end end
      else begin gj<=gj+1'b1;gj_n<=~(gj+1'b1);end
      if(ent!=~lut_n[gj*16+:16]||lines!=~lines_n||ent[15:8]>=NSM||ent[7:0]>=lines[ent[10:8]*16+:16])bad<=1;
     end
    end
  end
  wire[NSM*4*NI-1:0] winners;
  // Every bank arbitrates just its eight already-decoded candidates.
  for(genvar m=0;m<NSM;m++)begin:arbsm
   for(genvar c=0;c<4;c++)begin:arbq
    (* keep = 1 *) reg[2:0] rot,rot_n;wire[7:0] req,win;
    for(genvar i=0;i<NI;i++)begin:candidate
     assign req[i]=cv[4*i+c]&&!le[4*i+c]&&dest[4*i+c][m];
     wire[7:0] lose;
     for(genvar j=0;j<NI;j++)begin:prioritycmp
      assign lose[j]=(j!=i)&&req[j]&&((3'(j)-rot)<(3'(i)-rot));
     end
     assign win[i]=req[i]&&!(|lose)&&(rot==~rot_n);
    end
    assign winners[(m*4+c)*NI+:NI]=win;
    always @(posedge clk or negedge rst_n)if(!rst_n)begin rot<=0;rot_n<='1;end else begin rot<=rot+1'b1;rot_n<=~(rot+1'b1);end
   end
  end
  for(genvar p=0;p<NPC;p++)begin:pop
   wire[NSM-1:0] g;
   for(genvar m=0;m<NSM;m++)assign g[m]=winners[(m*4+p%4)*NI+p/4];
   assign grant[p]=|g;assign lr[p]=grant[p];
  end
  // First capture is PC-local. Registered4:1 halves then2:1 full-bank
  // reduction keep arbitration and long bank mux off the same edge.
  (* keep = 1 *) reg[359:0] pq[0:NPC-1];(* keep = 1 *) reg[31:0] pix[0:NPC-1],pix_n[0:NPC-1];(* keep = 1 *) reg pbad[0:NPC-1];
  for(genvar p=0;p<NPC;p++)begin:capture
   wire[65:0] tag=decode64(lq[p*360+288+:72]);
   always @(posedge clk)if(grant[p])begin
    pq[p]<=lq[p*360+:360];pix[p]<=index[p];pix_n[p]<=~index[p];pbad[p]<=tag[65]||tag[63:21]!=0||tag[20:16]!=5'(p)||tag[15:0]!=seq[p];
   end
  end
  wire[NSM*4-1:0] write_v;wire[8:0] write_a[0:NSM*4-1];wire[255:0] write_d[0:NSM*4-1];wire[127:0] write_s[0:NSM*4-1];
  wire[NSM*4-1:0] bankbad;
  for(genvar m=0;m<NSM;m++)begin:bankwrite
   for(genvar c=0;c<4;c++)begin:q
    localparam B=m*4+c;
    (* keep = 1 *) reg[7:0] sel,sel_n;(* keep = 1 *) reg[359:0] halfdata[0:1];(* keep = 1 *) reg[31:0] halfix[0:1],halfix_n[0:1];(* keep = 1 *) reg[1:0] hv,herr,hv_n,herr_n;
    (* keep = 1 *) reg[359:0] finaldata;(* keep = 1 *) reg[31:0] finalix,finalix_n;(* keep = 1 *) reg fv,fe,fv_n,fe_n;
    always @(posedge clk or negedge rst_n)if(!rst_n)begin sel<=0;sel_n<='1;begin hv<=0;hv_n<=~(0);end begin herr<=0;herr_n<=~(0);end begin fv<=0;fv_n<=~(0);end begin fe<=0;fe_n<=~(0);end finalix<=0;finalix_n<='1;end
    else begin
     sel<=winners[B*NI+:NI];sel_n<=~winners[B*NI+:NI];
     for(integer h=0;h<2;h++)begin
      (* keep = 1 *) reg[359:0] d;(* keep = 1 *) reg[31:0] x;(* keep = 1 *) reg err;d=0;x=0;err=0;
      for(integer i=0;i<4;i++)if(sel[4*h+i])begin d|=pq[4*(4*h+i)+c];x|=pix[4*(4*h+i)+c];err|=pbad[4*(4*h+i)+c]||(pix[4*(4*h+i)+c]!=~pix_n[4*(4*h+i)+c]);end
      halfdata[h]<=d;begin halfix[h]<=x;halfix_n[h]<=~(x);end begin hv[h]<=|sel[4*h+:4];hv_n[h]<=~(|sel[4*h+:4]);end begin herr[h]<=err||(sel!=~sel_n);herr_n[h]<=~(err||(sel!=~sel_n));end 
     end
     finaldata<=halfdata[0]|halfdata[1];begin finalix<=halfix[0]|halfix[1];finalix_n<=~(halfix[0]|halfix[1]);end begin fv<=|hv;fv_n<=~(|hv);end begin fe<=|herr;fe_n<=~(|herr);end 
    end
    (* keep = 1 *) reg wv,wv_n;(* keep = 1 *) reg[8:0] wa,wa_n;(* keep = 1 *) reg[255:0] wd;(* keep = 1 *) reg[127:0] ws;
    wire bankstatebad=(sel!=~sel_n)||(hv!=~hv_n)||(herr!=~herr_n)||(fv!=~fv_n)||(fe!=~fe_n)||(finalix!=~finalix_n)||(wv!=~wv_n)||(wa!=~wa_n)||((halfix[0]!=~halfix_n[0])&&hv[0])||((halfix[1]!=~halfix_n[1])&&hv[1]);
    // Intentional physical half-cycle, with real opposite-edge timing arcs.
    always @(negedge clk or negedge rst_n)if(!rst_n)begin begin wv<=0;wv_n<=~(0);end begin wa<=0;wa_n<=~(0);end wd<=0;ws<=0;end
    else begin
     begin wv<=fv&&!fe&&!bankstatebad;wv_n<=~(fv&&!fe&&!bankstatebad);end begin wa<=finalix[8:0];wa_n<=~(finalix[8:0]);end 
     for(integer k=0;k<4;k++)begin wd[k*64+:64]<=raw64(finaldata[k*72+:72]);ws[k*8+:8]<=parity64(finaldata[k*72+:72]);end
     ws[103:32]<=encode64({27'd0,3'(m),2'(c),finalix});ws[127:104]<=0;
    end
    assign write_v[B]=wv&&!bankstatebad;assign write_a[B]=wa;assign write_d[B]=wd;assign write_s[B]=ws;assign bankbad[B]=(fv&&fe)||bankstatebad;
   end
  end
  wire[NSM-1:0] smbad;
  for(genvar m=0;m<NSM;m++)begin:sm
   (* keep = 1 *) reg[31:0] cs,cs_n;(* keep = 1 *) reg[3:0] reserved,reserved_n,queued,queued_n;
   (* keep = 1 *) reg[2:0] wp,wp_n,rp,rp_n;(* keep = 1 *) reg poison;
   wire[DEPTH-1:0] fullbits,overbits,maskbad;
   wire issue,consume;
   wire ctrlbad=readbad||cs!=~cs_n||reserved!=~reserved_n||queued!=~queued_n||wp!=~wp_n||rp!=~rp_n;
   wire[NSM*4-1:0] unused=0;
   for(genvar d=0;d<DEPTH;d++)begin:slot
    (* keep = 1 *) reg[3:0] mk,mk_n;
    wire[3:0] setbits;
    for(genvar c=0;c<4;c++)assign setbits[c]=write_v[m*4+c]&&write_a[m*4+c]==9'(d);
    wire clear=issue&&cs[8:0]==9'(d);
    wire[3:0] nextmask=(clear?4'd0:mk)|setbits;
    always @(posedge clk or negedge rst_n)if(!rst_n)begin mk<=0;mk_n<='1;end else begin mk<=nextmask;mk_n<=~nextmask;end
    assign fullbits[d]=&mk;assign maskbad[d]=mk!=~mk_n;
    assign overbits[d]=|(mk&setbits)&&!clear;
   end
   // Four tagged look-ahead requests. Decode, local32-row reduction and final
   // reduction are registered separately. Tags prevent stale mask permission.
   wire[3:0] ready;
   for(genvar q=0;q<4;q++)begin:look
    (* keep = 1 *) reg[511:0] oh,oh_n;(* keep = 1 *) reg[31:0] tag0,tag1,tag2,tag0_n,tag1_n,tag2_n;
    (* keep = 1 *) reg[15:0] partial,partial_n;(* keep = 1 *) reg good,good_n;
    wire[31:0] future=cs+32'(q);
    always @(posedge clk or negedge rst_n)if(!rst_n)begin oh<=0;oh_n<='1;begin tag0<=0;tag0_n<=~(0);end begin tag1<=0;tag1_n<=~(0);end begin tag2<=0;tag2_n<=~(0);end partial<=0;partial_n<='1;good<=0;good_n<=1;end
    else begin
     oh<=512'(1)<<future[8:0];oh_n<=~(512'(1)<<future[8:0]);begin tag0<=future;tag0_n<=~(future);end begin tag1<=tag0;tag1_n<=~(tag0);end begin tag2<=tag1;tag2_n<=~(tag1);end 
     for(integer g=0;g<16;g++)begin partial[g]<=|(fullbits[g*32+:32]&oh[g*32+:32]);partial_n[g]<=~(|(fullbits[g*32+:32]&oh[g*32+:32]));end
     good<=(|partial)&&(oh==~oh_n)&&(partial==~partial_n);good_n<=~((|partial)&&(oh==~oh_n)&&(partial==~partial_n));
    end
    assign ready[q]=(tag0==~tag0_n)&&(tag1==~tag1_n)&&(tag2==~tag2_n)&&good&&(good==~good_n)&&tag2==cs;
   end
   (* keep = 1 *) reg[8:0] ra,ra_n;
   always @(negedge clk or negedge rst_n)if(!rst_n)begin ra<=0;ra_n<=~(0);end else begin ra<=cs[8:0];ra_n<=~(cs[8:0]);end 
   wire[1023:0] rawdata;wire[511:0] sidecar;
   for(genvar c=0;c<4;c++)begin:bank
    for(genvar h=0;h<2;h++)begin:half
     ot_sram_1r1w_512x128_m4_r2c2 u_ram(
      .clk(clk),.r_ce_in(1'b1),.r_addr_in(ra),.rd_out(rawdata[c*256+h*128+:128]),
      .w_ce_in(write_v[m*4+c]),.w_addr_in(write_a[m*4+c]),.wd_in(write_d[m*4+c][h*128+:128]),
      .w_mask_in({128{1'b1}}),.rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(14'd0));
    end
    ot_sram_1r1w_512x128_m4_r2c2 ecc_ram(
     .clk(clk),.r_ce_in(1'b1),.r_addr_in(ra),.rd_out(sidecar[c*128+:128]),
     .w_ce_in(write_v[m*4+c]),.w_addr_in(write_a[m*4+c]),.wd_in(write_s[m*4+c]),
     .w_mask_in({128{1'b1}}),.rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(14'd0));
   end
   (* keep = 1 *) reg v0,v1,v2,v0_n,v1_n,v2_n;(* keep = 1 *) reg[31:0] ix0,ix1,ix2,ix0_n,ix1_n,ix2_n;
   wire readbad=(ra!=~ra_n)||(v0!=~v0_n)||(v1!=~v1_n)||(v2!=~v2_n)||(ix0!=~ix0_n)||(ix1!=~ix1_n)||(ix2!=~ix2_n);
   (* keep = 1 *) reg[1439:0] packet1,packet2;(* keep = 1 *) reg[159:0] synd;
   wire[1023:0] corrected;wire[19:0] ue;wire[3:0] tagbad;
   for(genvar c=0;c<4;c++)begin:decodebank
    for(genvar k=0;k<4;k++)begin:word
     localparam J=c*5+k;
     wire[71:0] code=join64(rawdata[c*256+k*64+:64],sidecar[c*128+k*8+:8]);
     always @(posedge clk)begin
      packet1[J*72+:72]<=code;packet2[J*72+:72]<=packet1[J*72+:72];synd[J*8+:8]<=syndrome64(packet1[J*72+:72]);
     end
     wire[65:0] dec=finish64(packet2[J*72+:72],synd[J*8+:8]);
     assign corrected[c*256+k*64+:64]=dec[63:0];assign ue[J]=dec[65];
    end
    localparam J=c*5+4;
    always @(posedge clk)begin packet1[J*72+:72]<=sidecar[c*128+32+:72];packet2[J*72+:72]<=packet1[J*72+:72];synd[J*8+:8]<=syndrome64(packet1[J*72+:72]);end
    wire[65:0] dec=finish64(packet2[J*72+:72],synd[J*8+:8]);
    assign ue[J]=dec[65];assign tagbad[c]=dec[63:0]!={27'd0,3'(m),2'(c),ix2};
   end
   (* keep = 1 *) reg[1023:0] outdata[0:7];(* keep = 1 *) reg[15:0] outpar[0:7];
   wire[1023:0] head=outdata[rp];wire[15:0] headpar=outpar[rp];
   wire[15:0] headerr;
   for(genvar k=0;k<16;k++)assign headerr[k]=(^head[k*64+:64])!=headpar[k];
   wire packetbad=(|ue)||(|tagbad);
   wire push=v2&&!packetbad&&!poison;
   assign s_data[m*1024+:1024]=head;
   assign s_valid[m]=queued!=0&&!poison&&!ctrlbad&&!(|headerr);
   assign consume=s_valid[m]&&s_ready[m];
   assign issue=(|ready)&&(reserved<8||consume)&&!poison&&!ctrlbad&&!(|maskbad);
   assign smbad[m]=poison||ctrlbad;
   always @(posedge clk or negedge rst_n)
    if(!rst_n)begin cs<=0;cs_n<='1;reserved<=0;reserved_n<='1;queued<=0;queued_n<='1;wp<=0;wp_n<='1;rp<=0;rp_n<='1;poison<=0;begin v0<=0;v0_n<=~(0);end begin v1<=0;v1_n<=~(0);end begin v2<=0;v2_n<=~(0);end begin ix0<=0;ix0_n<=~(0);end begin ix1<=0;ix1_n<=~(0);end begin ix2<=0;ix2_n<=~(0);end end
    else begin
     begin v0<=issue;v0_n<=~(issue);end begin v1<=v0;v1_n<=~(v0);end begin v2<=v1;v2_n<=~(v1);end begin ix0<=cs;ix0_n<=~(cs);end begin ix1<=ix0;ix1_n<=~(ix0);end begin ix2<=ix1;ix2_n<=~(ix1);end 
     if(issue)begin cs<=cs+1'b1;cs_n<=~(cs+1'b1);end
     case({issue,consume})
      2'b10:begin reserved<=reserved+1'b1;reserved_n<=~(reserved+1'b1);end
      2'b01:begin reserved<=reserved-1'b1;reserved_n<=~(reserved-1'b1);end
      default:;
     endcase
     case({push,consume})
      2'b10:begin queued<=queued+1'b1;queued_n<=~(queued+1'b1);end
      2'b01:begin queued<=queued-1'b1;queued_n<=~(queued-1'b1);end
      default:;
     endcase
     if(push)begin outdata[wp]<=corrected;for(integer k=0;k<16;k++)outpar[wp][k]<=^corrected[k*64+:64];wp<=wp+1'b1;wp_n<=~(wp+1'b1);end
     if(consume)begin rp<=rp+1'b1;rp_n<=~(rp+1'b1);end
     if(ctrlbad||(|maskbad)||(|overbits)||(v2&&packetbad)||(queued!=0&&|headerr)||(|bankbad[m*4+:4]))poison<=1;
    end
  end
  (* async_reg="true" *)(* keep = 1 *) reg hp1,hp2;
  always @(posedge clk or negedge rst_n)if(!rst_n)begin hp1<=0;hp2<=0;end else begin hp1<=hpoison;hp2<=hp1;end
  assign fault=ingress_poison||ibad||idwf||hp2||(|locbad)||(|lrf)||(|smbad);
 end endgenerate
endmodule
