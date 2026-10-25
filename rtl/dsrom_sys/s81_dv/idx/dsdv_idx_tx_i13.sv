`timescale 1ns/1ps
// S81 TP4 candidate transmitter, sized by tools/uarch_model.py --s81-tp4-i13.
// Exact score+original-index transport; no arithmetic. Same vi/vo/lo pins as n32.
// TX CTL: legacy fields through99; I13[103]=1, QSHIFT[108:104], LOOKUP[109].
// LOOKUP0 uses the original dense store; LOOKUP1 uses exact tagged candidate CAM.
// Candidate banks alternate by input tag[0], preserving the previous job while
// the next exchange arrives. Miss, duplicate, overflow, descending rank fault.
// Packet/header buffering and all datapath memories have NO reset; only control.
module dsdv_idx_tx_i13 #(
    parameter integer V=276, D=8192, C=1024, PF=128, IF=64, GF=8,
    parameter bit SRAM_MACRO=0,
    parameter integer MUT=0
)(input wire ck,rst,input wire[V-1:0]vi,vo,output reg[V-1:0]lo,output reg[15:0]st);
    localparam integer AW=$clog2(D),PW=$clog2(PF),IW=$clog2(IF),GW=$clog2(GF),CW=$clog2(C+1);
    reg[V-1:0]vr,orr;
    always @(posedge ck)begin vr[V-1:1]<=vi[V-1:1];orr[V-1:1]<=vo[V-1:1];end
    always @(posedge ck or negedge rst)if(!rst)begin vr[0]<=0;orr[0]<=0;end else begin vr[0]<=vi[0];orr[0]<=vo[0];end
    wire[185:0]cp=orr[21+:186];
    wire job=orr[0]&&orr[3:1]==0&&cp[7:0]==8'h5c&&cp[10:8]==2;
    reg armed,done;reg[7:0]j_pt,j_ot;reg[9:0]j_k;reg[19:0]j_hb;reg[15:0]j_dly;reg[2:0]j_r;
    reg[11:0]j_sm;reg[1:0]j_l;reg[4:0]j_shift;reg j_cam;reg[20:0]tick;reg[11:0]slots;
    reg f_cfg,f_cap,f_idx,f_lookup,f_pack,f_out;
    always @(posedge ck or negedge rst)if(!rst)begin
        j_pt<=0;j_ot<=0;j_k<=0;j_hb<=0;j_dly<=0;j_r<=1;j_sm<=0;j_l<=0;j_shift<=0;j_cam<=0;tick<=0;f_cfg<=0;
    end else begin
        if(job)begin
            if((armed&&!done)||!cp[103]||cp[108:104]>19||cp[87:85]==0||cp[40:31]==0||cp[40:31]>512)f_cfg<=1;
            j_l<=cp[22:21];j_pt<=cp[30:23];j_k<=cp[40:31];j_hb<=cp[60:41];j_ot<=cp[68:61];
            j_dly<=cp[84:69];j_r<=cp[87:85];j_sm<=cp[99:88];j_shift<=cp[108:104];j_cam<=cp[109];tick<=0;
        end else if(armed)tick<=tick+1'b1;
    end
    // Dense score-store capture, preserving the original 16-score masked write.
    reg[255:0]vilow[0:3];reg[19:0]cursor[0:3];reg[3:0]vhave;
    wire cv=vr[0]&&vr[3:1]==4;wire[1:0]vl=vr[5:4];wire[511:0]vw={vr[275:20],vilow[vl]};
    reg dwe;reg[AW-1:0]dwa;reg[255:0]dwd,dwm;reg[15:0]dmask;
    always @(posedge ck)begin
        if(cv&&!vr[6])vilow[vl]<=vr[275:20];
        dwe<=cv&&vr[6]&&vhave[vl]&&vw[511:508]==2;
        dwa<=AW'(cursor[vl]>>4);dwd<=vilow[vl];dmask<=vw[271:256];
        for(integer x=0;x<16;x=x+1)dwm[16*x+:16]<={16{vw[256+x]}};
        if(cv&&!vr[6]&&vr[7]&&(vr[19:16]==1||vr[19:16]==6))cursor[vl]<=vr[39:20];
        else if(cv&&vr[6]&&vw[511:508]==2)cursor[vl]<=cursor[vl]+16;
    end
    always @(posedge ck or negedge rst)if(!rst)vhave<=0;else if(cv)begin
        if(!vr[6])vhave[vl]<=!vr[7];else vhave[vl]<=0;
    end
    wire req;wire[19:0]req_id;wire[255:0]dense_rd;
    dsdv_idx_txm_n32 #(.D(D),.SRAM_MACRO(SRAM_MACRO))u_dense(.ck(ck),.re(req&&!j_cam),.ra(AW'(req_id>>4)),.rd(dense_rd),
        .we(dwe),.wa(dwa),.wd(dwd),.wm(dwm),.wm_next(vw[271:256]),.we_b(1'b0),.wa_b({AW{1'b0}}),.wd_b(256'd0));
    // Incoming indexed13 words are bounded packets, then one exact cache write/edge.
    reg[519:0]pkt[0:PF-1];reg[PW:0]pw,pr;reg pv;reg[511:0]pd;reg[7:0]pt;reg[12:0]pm;
    reg[19:0]cpos[0:1][0:C-1];reg[15:0]cscore[0:1][0:C-1];
    reg[CW-1:0]cn[0:1];reg[7:0]ctag[0:1];reg[1:0]ctagv;
    wire packet=cv&&vr[6]&&vhave[vl]&&vw[511:508]==8;
    integer pi;reg pfound;always @*begin pi=0;pfound=0;for(integer q=0;q<13;q=q+1)if(pm[q]&&!pfound)begin pi=q;pfound=1;end end
    reg dup;always @*begin dup=0;for(integer q=0;q<C;q=q+1)if(ctagv[pt[0]]&&ctag[pt[0]]==pt&&q<cn[pt[0]]&&cpos[pt[0]][q]==pd[36*pi+16+:20])dup=1;end
    always @(posedge ck or negedge rst)if(!rst)begin
        pw<=0;pr<=0;pv<=0;pm<=0;ctagv<=0;cn[0]<=0;cn[1]<=0;f_cap<=0;
    end else begin
        if(packet)begin
            if(pw-pr>=PF)f_cap<=1;else begin pkt[pw[PW-1:0]]<={vw[507:500],vw};pw<=pw+1'b1;end
        end
        if(!pv&&pr!=pw)begin {pt,pd}<=pkt[pr[PW-1:0]];pm<=pkt[pr[PW-1:0]][480:468];pr<=pr+1'b1;pv<=1;end
        else if(pv&&pfound)begin
            if(dup)f_cap<=1;
            if(!ctagv[pt[0]]||ctag[pt[0]]!=pt)begin
                ctag[pt[0]]<=pt;ctagv[pt[0]]<=1;cn[pt[0]]<=1;
                cpos[pt[0]][0]<=pd[36*pi+16+:20];cscore[pt[0]][0]<=pd[36*pi+:16];
            end else if(cn[pt[0]]>=C)f_cap<=1;
            else begin cpos[pt[0]][cn[pt[0]]]<=pd[36*pi+16+:20];cscore[pt[0]][cn[pt[0]]]<=pd[36*pi+:16];cn[pt[0]]<=cn[pt[0]]+1'b1;end
            pm[pi]<=0;
        end else if(pv)pv<=0;
    end
    // Selected-ID capture; no source scores or IDs are fabricated on a miss.
    reg[255:0]olow;reg oh;wire oe=orr[0]&&orr[3:1]==5;wire[511:0]ow={orr[275:20],olow};
    reg[335:0]ibuf[0:IF-1];reg[IW:0]iw,ir;reg iv,input_done;reg[319:0]ids;reg[15:0]im;
    wire pushidx=oe&&orr[6]&&oh&&ow[511:508]==3&&ow[507:500]==j_ot;
    integer ii;reg ifound;always @*begin ii=0;ifound=0;for(integer q=0;q<16;q=q+1)if(im[q]&&!ifound)begin ii=q;ifound=1;end end
    always @(posedge ck)if(oe&&!orr[6])olow<=orr[275:20];
    wire[GW:0]group_fill;reg[2:0]lpv;
    assign req=armed&&!done&&iv&&ifound&&group_fill<GF-4;
    assign req_id=ids[20*ii+:20];
    always @(posedge ck or negedge rst)if(!rst)begin iw<=0;ir<=0;iv<=0;im<=0;oh<=0;input_done<=0;f_idx<=0;end
    else begin
        if(job)begin iw<=0;ir<=0;iv<=0;im<=0;input_done<=0;end
        if(oe)begin if(!orr[6])oh<=1;else oh<=0;end
        if(pushidx)begin
            if(iw-ir>=IF)f_idx<=1;else begin ibuf[iw[IW-1:0]]<={ow[335:320],ow[319:0]};iw<=iw+1'b1;end
        end
        if(oe&&orr[6]&&oh&&ow[511:508]==4&&ow[507:500]==j_ot)input_done<=1;
        if(!iv&&ir!=iw)begin {im,ids}<=ibuf[ir[IW-1:0]];ir<=ir+1'b1;iv<=1;end
        else if(req)im[ii]<=0;
        else if(iv&&!ifound)iv<=0;
    end
    // 16 local CAM reduction groups, two capture levels, then a pack register.
    localparam integer NG=16,CS=(C+NG-1)/NG;
    reg[15:0]gs[0:NG-1];reg[NG-1:0]gh,gd;reg[15:0]cs1,cs2,ds2;reg ch1,ch2,cd1,cd2;
    reg[19:0]ip0,ip1,ip2;reg[15:0]ctmp;reg htmp,dtmp;integer counttmp;
    always @(posedge ck)begin
        ip0<=req_id;ip1<=ip0;ip2<=ip1;
        for(integer g=0;g<NG;g=g+1)begin
            ctmp=0;htmp=0;dtmp=0;
            for(integer q=0;q<CS;q=q+1)if(g*CS+q<C&&ctagv[j_ot[0]]&&ctag[j_ot[0]]==j_ot&&g*CS+q<cn[j_ot[0]]&&cpos[j_ot[0]][g*CS+q]==req_id)begin
                if(htmp)dtmp=1;htmp=1;ctmp=ctmp|cscore[j_ot[0]][g*CS+q];
            end
            gs[g]<=ctmp;gh[g]<=htmp;gd[g]<=dtmp;
        end
        ctmp=0;counttmp=0;dtmp=|gd;
        for(integer g=0;g<NG;g=g+1)begin ctmp=ctmp|gs[g];counttmp=counttmp+integer'(gh[g]);end
        cs1<=ctmp;ch1<=counttmp!=0;cd1<=dtmp||(counttmp>1);
        cs2<=cs1;ch2<=ch1;cd2<=cd1;ds2<=dense_rd[16*ip1[3:0]+:16];
    end
    always @(posedge ck or negedge rst)if(!rst)begin lpv<=0;f_lookup<=0;end else begin
        lpv<={lpv[1:0],req};if(job)lpv<=0;
        if(lpv[2]&&j_cam&&(!ch2||cd2))f_lookup<=1;
    end
    // Rank-preserving groups: flush/LAST at rank boundary, emit a new HDR before
    // the next rank's type8 word. Quarter order is global index order.
    reg[483:0]gf[0:GF-1];reg[GW:0]gw,gr;reg[467:0]pack;reg[3:0]np;reg[1:0]pq;
    reg pack_done;reg[9:0]nlook;reg[19:0]previous;reg previous_v;
    wire[1:0]rankq=2'(ip2>>j_shift);wire[15:0]score=j_cam?cs2:ds2;
    assign group_fill=gw-gr;
    always @(posedge ck or negedge rst)if(!rst)begin
        gw<=0;np<=0;pack_done<=0;nlook<=0;previous_v<=0;f_pack<=0;
    end else begin
        if(job)begin gw<=0;np<=0;pack_done<=0;nlook<=0;previous_v<=0;end
        else if(lpv[2])begin
            if((previous_v&&ip2<=previous)||nlook>=j_k)f_pack<=1;
            previous<=ip2;previous_v<=1;nlook<=nlook+1'b1;
            if(np!=0&&(np==13||rankq!=pq))begin
                if(gw-gr>=GF)f_pack<=1;else begin gf[gw[GW-1:0]]<={rankq!=pq,pq,13'((14'd1<<np)-1),pack};gw<=gw+1'b1;end
                pack<=468'({ip2,score});np<=1;pq<=rankq;
            end else begin if(np==0)pack<=468'({ip2,score});else pack[36*np+:36]<={ip2,score};np<=np+1'b1;pq<=rankq;end
        end else if(input_done&&iw==ir&&!iv&&lpv==0&&!pack_done)begin
            if(np!=0)begin
                if(gw-gr>=GF)f_pack<=1;else begin gf[gw[GW-1:0]]<={1'b1,pq,13'((14'd1<<np)-1),pack};gw<=gw+1'b1;end
            end
            np<=0;pack_done<=1;
        end
    end
    wire[483:0]front=gf[gr[GW-1:0]];wire[1:0]fq=front[482:481];
    wire[511:0]i13w={4'd8,j_pt,18'd0,front[483],front[480:468],front[467:0]};
    wire[511:0]hdrw={4'd1,j_pt,468'd0,fq,j_k,j_hb};
    reg phase,haveq;reg[1:0]outq;reg[2:0]rphase;
    wire grid=armed&&tick>=j_dly+2&&rphase==0;
    always @(posedge ck or negedge rst)if(!rst)rphase<=0;else if(job)rphase<=0;
    else if(armed&&tick>=j_dly+2)rphase<=(rphase==j_r-1)?3'd0:rphase+1'b1;
    reg[511:0]emitw;reg[V-1:0]emitb;
    always @*begin
        emitw=i13w;emitb=0;
        if(!haveq||outq!=fq)begin
            emitw=hdrw;emitb=1|276'(4<<1)|(276'(j_l)<<4)|276'(1<<7)|(276'(emitw[511:500])<<8)|(276'(emitw[255:0])<<20);
        end else if(!phase)emitb=1|276'(4<<1)|(276'(j_l)<<4)|(276'(emitw[511:500])<<8)|(276'(emitw[255:0])<<20);
        else emitb=1|276'(4<<1)|(276'(j_l)<<4)|276'(1<<6)|(276'(emitw[511:256])<<20);
        if(MUT==1&&(!haveq||outq!=fq))emitb[51:50]=2'd2;
        if(MUT==2&&j_cam)emitb[20]=~emitb[20];
    end
    always @(posedge ck or negedge rst)if(!rst)begin armed<=0;done<=0;lo[0]<=0;slots<=0;phase<=0;gr<=0;haveq<=0;outq<=0;f_out<=0;end
    else begin
        lo[0]<=0;
        if(job)begin armed<=1;done<=0;slots<=0;phase<=0;gr<=0;haveq<=0;end
        else if(armed)begin
            if(grid)begin
                slots<=slots+1'b1;
                if(slots>=j_sm)f_out<=1;
                if(gr!=gw)begin
                    lo[0]<=1;
                    if(!haveq||outq!=fq)begin haveq<=1;outq<=fq;end
                    else if(!phase)phase<=1;
                    else begin phase<=0;gr<=gr+1'b1;end
                end
            end
            if(pack_done&&gr==gw&&!phase)begin armed<=0;done<=1;end
        end
    end
    always @(posedge ck)if(grid&&gr!=gw)lo[V-1:1]<=emitb[V-1:1];
    wire fault=f_cfg|f_cap|f_idx|f_lookup|f_pack|f_out;
    always @(posedge ck or negedge rst)if(!rst)st<=0;else st<={6'd0,f_out,f_pack,f_lookup,f_idx,f_cap,f_cfg,done,armed,1'b0,fault};
endmodule
