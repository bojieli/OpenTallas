`timescale 1ns/1ps
// S81 TP4 candidate transmitter (rank-aware indexed13), sized by tools/uarch_model.py --s81-tp4-i13.
// Exact score+original-index transport; no arithmetic. Same vi/vo/lo/st pins as n32, every pin registered.
// TX CTL: legacy fields through99; I13[103]=1, QSHIFT[108:104], LOOKUP[109].
// LOOKUP0 uses the original dense store; LOOKUP1 uses the tagged candidate row store.
//
// S81-I13 restructure 2026-10-25 (accelerator form; replaces the 2x1024-entry flop CAM whose 1024-way duplicate scan
// and 1024-way lookup compare did not elaborate in yosys 0.68):
//  * Candidate store = SRAM rows, one indexed13 type8 word (13 x {score16,id20} + prefix mask + row max id) per row,
//    two tag banks (tag[0]) x RW rows, flat {bank,row} address.  One row write per word, no packet FIFO.
//  * Per bank and qslot (HDR qslot of the word's lane) the rows form an append-only linked list (head/tail/next).
//  * Duplicate/order check at write = O(1): the word must be a non-empty prefix, strictly ascending inside, and its
//    first id must exceed the qslot's last id (dup or descending -> f_cap).  The encoder contract (lower_bk
//    lane_words_indexed13) already requires strictly ascending positions per qslot.
//  * Lookup = streaming merge-join of two strictly increasing key streams {rank,id}: selected ids (ascending, as
//    the old f_pack check already required) against the rank-ordered row stream.  Compare window = 2 rows
//    (26 entries); each cycle consumes one lookup and/or retires one row; a miss is detected the moment the lookup
//    key falls inside the window without a match or the stream ends.  Never a 1024-way compare.
//  * Selected-id buffer = SRAM (IF words) with a 2-word show-ahead stage.
//  * Static schedule: no backpressure on any pin; internal bounded pacing only; output on the reserved grid (f_out
//    if the reserved slots are exceeded).  Banks alternate by tag[0]: the next job's exchange may land in the other
//    bank while this job transmits; a foreign tag on the busy bank, or a late write into the job's own bank once its
//    walk started, faults (f_cap).
// Packet/header buffering and all datapath memories have NO reset; only control.
module dsdv_idx_tx_i13 #(
    parameter integer V=276, D=8192, C=1024, RW=128, IF=128, GF=8,
    parameter bit SRAM_MACRO=0,
    // dense store macro landing (as closed TX n32x): RDL rd_out capture, WDL write-port landing, RIL read-port landing;
    // with SRAM_MACRO=1 the lookup result pipe grows by RDL+RIL edges (both modes, same edge for dense and candidate).
    parameter integer RDL=1, WDL=1, RIL=1,
    parameter integer MUT=0   // bench mutants: 1 HDR qslot, 2 id bit, 3 no write-time order/duplicate check
)(input wire ck,rst,input wire[V-1:0]vi,vo,output reg[V-1:0]lo,output reg[15:0]st);
    localparam integer AW=$clog2(D),IW=$clog2(IF),GW=$clog2(GF),CW=$clog2(C+1),RB=$clog2(RW);
    localparam integer RDW=20+481;
    localparam integer DX=SRAM_MACRO?(RDL+RIL):0, LP=3+DX;   // lookup issue -> pack stage edges   // candidate row: {max id20, mask13, 13 x {id20,score16}}
    // ---------------------------------------------------------------- reset forest (control / valid bits only)
    // S81-I13 census 2026-10-25: the port feeds only ot_rst_relay; each region <= 32 reset flops.
    // rl[0] pins + ingress valids + bank valids, rl[1] faults + status, rl[2] selected-id FIFO control,
    // rl[3] walk / lookup pipe / output control, rl[4] pack + grid control.
    wire[4:0]rl;
    ot_rst_relay #(.REGIONS(5),.SYNC_STAGES(2),.TREE_STAGES(1))u_rr(.clk(ck),.rst_n_in(rst),.rst_n(rl));
    // ---------------------------------------------------------------- pin registers
    reg[V-1:0]vr,orr;
    always @(posedge ck)begin vr[V-1:1]<=vi[V-1:1];orr[V-1:1]<=vo[V-1:1];end
    always @(posedge ck or negedge rl[0])if(!rl[0])begin vr[0]<=0;orr[0]<=0;end else begin vr[0]<=vi[0];orr[0]<=vo[0];end
    wire[185:0]cp=orr[21+:186];
    wire job=orr[0]&&orr[3:1]==0&&cp[7:0]==8'h5c&&cp[10:8]==2;
    reg armed,done;reg[7:0]j_pt,j_ot;reg[9:0]j_k;reg[19:0]j_hb;reg[15:0]j_dly;reg[2:0]j_r;
    reg[11:0]j_sm;reg[1:0]j_l;reg[4:0]j_shift;reg j_cam;reg[20:0]tick;reg[11:0]slots;
    reg f_cfg,f_cap,f_idx,f_lookup,f_pack,f_out;
    // job fields: loaded by the job word before any use (armed), no reset
    (* keep *)reg jbw,jbh;   // j_ot[0] copies: candidate write side (wbusy) / walk side (head/tail select)
    always @(posedge ck or negedge rl[1])if(!rl[1])f_cfg<=0;
    else if(job&&((armed&&!done)||!cp[103]||cp[108:104]>19||cp[87:85]==0||cp[40:31]==0||cp[40:31]>512))f_cfg<=1;
    always @(posedge ck)begin
        if(job)begin
            jbw<=cp[61];jbh<=cp[61];
            j_l<=cp[22:21];j_pt<=cp[30:23];j_k<=cp[40:31];j_hb<=cp[60:41];j_ot<=cp[68:61];
            j_dly<=cp[84:69];j_r<=cp[87:85];j_sm<=cp[99:88];j_shift<=cp[108:104];j_cam<=cp[109];tick<=0;
        end else if(armed)tick<=tick+1'b1;
    end
    // ---------------------------------------------------------------- dense score store (unchanged function)
    // Lane staging: 4 lanes x (256-b part-0 + 20-b cursor).  The lane select is a kept 2-b copy per 16-b (10-b) read
    // slice, registered from the vi pins on the same edge as vr (= vr[5:4]); the part-0 write enable is a kept
    // one-hot copy per {lane, 16-b column} (as dsdv_idx_tx_n32 hsw).  No select drives more than 32 pins.
    reg[255:0]vilow[0:3];reg[19:0]cursor[0:3];reg[3:0]vhave;
    wire cv=vr[0]&&vr[3:1]==4;wire[1:0]vl=vr[5:4];
    wire[255:0]vlo;wire[19:0]vcur;
    for(genvar c=0;c<16;c=c+1)begin:g_vs
        dsdv_i13_lsel #(.W(16),.ID(c))u(.ck(ck),.s_n(vi[5:4]),
            .d({vilow[3][16*c+:16],vilow[2][16*c+:16],vilow[1][16*c+:16],vilow[0][16*c+:16]}),.q(vlo[16*c+:16]));
    end
    for(genvar c=0;c<2;c=c+1)begin:g_cs
        dsdv_i13_lsel #(.W(10),.ID(16+c))u(.ck(ck),.s_n(vi[5:4]),
            .d({cursor[3][10*c+:10],cursor[2][10*c+:10],cursor[1][10*c+:10],cursor[0][10*c+:10]}),.q(vcur[10*c+:10]));
    end
    wire[511:0]vw={vr[275:20],vlo};
    (* keep *)reg[63:0]vlw;   // [16 l + c]: vilow[l][16 c +: 16] load
    always @(posedge ck)for(integer l=0;l<4;l=l+1)for(integer c=0;c<16;c=c+1)
        vlw[16*l+c]<=vi[0]&&vi[3:1]==4&&!vi[6]&&vi[5:4]==2'(l);
    reg dwe;reg[AW-1:0]dwa;reg[255:0]dwd,dwm;reg[15:0]dmask;
    always @(posedge ck)begin
        for(integer l=0;l<4;l=l+1)for(integer c=0;c<16;c=c+1)if(vlw[16*l+c])vilow[l][16*c+:16]<=vr[20+16*c+:16];
        dwe<=cv&&vr[6]&&vhave[vl]&&vw[511:508]==2;
        dwa<=AW'(vcur>>4);dwd<=vlo;dmask<=vw[271:256];
        for(integer x=0;x<16;x=x+1)dwm[16*x+:16]<={16{vw[256+x]}};
        if(cv&&!vr[6]&&vr[7]&&(vr[19:16]==1||vr[19:16]==6))cursor[vl]<=vr[39:20];
        else if(cv&&vr[6]&&vw[511:508]==2)cursor[vl]<=vcur+16;
    end
    always @(posedge ck or negedge rl[0])if(!rl[0])vhave<=0;else if(cv)begin
        if(!vr[6])vhave[vl]<=!vr[7];else vhave[vl]<=0;
    end
    wire req;wire[19:0]req_id;wire[255:0]dense_rd;
    // WDC=0: the column-B write copy carries the same write (no tied inputs).
    dsdv_idx_txm_n32 #(.D(D),.SRAM_MACRO(SRAM_MACRO),.RDL(RDL),.WDL(WDL),.RIL(RIL))u_dense(.ck(ck),.re(req&&!j_cam),.ra(AW'(req_id>>4)),.rd(dense_rd),
        .we(dwe),.wa(dwa),.wd(dwd),.wm(dwm),.wm_next(vw[271:256]),.we_b(dwe),.wa_b(dwa),.wd_b(dwd));
    // ---------------------------------------------------------------- candidate ingress: HDR qslot per lane
    reg[7:0]lqf;reg[3:0]lqv;
    wire hdr1=cv&&!vr[6]&&vr[7]&&vr[19:16]==1;
    always @(posedge ck)if(hdr1)lqf[2*vl+:2]<=vr[51:50];   // valid in lqv
    always @(posedge ck or negedge rl[0])if(!rl[0])lqv<=0;else if(hdr1)lqv[vl]<=1'b1;
    // type8 word -> W0: per-word checks computed from the pin/staging registers (13-entry local, not 1024-way)
    wire packet=cv&&vr[6]&&vhave[vl]&&vw[511:508]==8;
    wire[12:0]pmask=vw[480:468];
    reg pok;reg[19:0]pmax;reg[3:0]pn;
    always @*begin
        pok=pmask!=0&&((pmask&(pmask+13'd1))==0);pmax=vw[16+:20];pn=0;
        for(integer e=0;e<13;e=e+1)if(pmask[e])begin pmax=vw[36*e+16+:20];pn=4'(e+1);end
        for(integer e=1;e<13;e=e+1)if(pmask[e]&&!(vw[36*e+16+:20]>vw[36*(e-1)+16+:20]))pok=0;
    end
    reg w0v,w0ok,w0qv;reg[7:0]w0tag;reg[1:0]w0q;reg[19:0]w0first,w0max;reg[3:0]w0n;reg[480:0]w0d;
    always @(posedge ck or negedge rl[0])if(!rl[0])w0v<=0;else w0v<=packet;
    always @(posedge ck)if(packet)begin
        w0ok<=pok;w0qv<=lqv[vl];w0q<=lqf[2*vl+:2];w0tag<=vw[507:500];w0first<=vw[16+:20];w0max<=pmax;w0n<=pn;w0d<=vw[480:0];
    end
    // bank state: tag, row count, entry count; per {bank,qslot}: head/tail/last id; per row: next (flat arrays)
    reg[15:0]ctag;reg[1:0]ctagv;reg[2*(RB+1)-1:0]nrow;reg[2*(CW+1)-1:0]nent;
    reg[8*RB-1:0]headf,tailf;reg[8*20-1:0]lastf;reg[7:0]hv,lastv;
    reg wk_on;  // the armed job's merge walk started
    wire wb=w0tag[0];wire[2:0]wqi={wb,w0q};
    wire wnew=!ctagv[wb]||ctag[8*wb+:8]!=w0tag;
    wire[RB:0]wrow=wnew?{(RB+1){1'b0}}:nrow[(RB+1)*wb+:(RB+1)];
    wire[CW:0]went=(wnew?{(CW+1){1'b0}}:nent[(CW+1)*wb+:(CW+1)])+(CW+1)'(w0n);
    wire wlast=!wnew&&lastv[wqi];
    wire wbad=!w0ok||!w0qv||(MUT!=3&&wlast&&w0first<=lastf[20*wqi+:20])||wrow>=RW||went>C;
    wire wbusy=armed&&!done&&j_cam&&jbw==wb;
    wire wconf=wbusy&&((w0tag!=j_ot)||wk_on);
    wire wacc=w0v&&!wbad&&!wconf;
    reg cwe;reg[RB:0]cwa;reg[RDW-1:0]cwd;
    always @(posedge ck)begin cwa<={wb,wrow[RB-1:0]};cwd<={w0max,w0d};end
    // per-row next pointer: banked link table, write landed one edge later, registered per-bank read address copies
    // (replaces one 2*RW x RB flop array read through one wk_row register)
    wire[RB-1:0]lnk_rd;reg[RB-1:0]wk_row_n;
    dsdv_i13_lnk #(.N(2*RW),.W(RB))u_lnk(.ck(ck),.we(wacc&&!wnew&&hv[wqi]),.wa({wb,tailf[RB*wqi+:RB]}),.wd(wrow[RB-1:0]),
        .ra_n({jbh,wk_row_n}),.rd(lnk_rd));
    reg f_wr;
    // bank tag / row / entry counts and per-qslot head/tail/last are qualified by ctagv / hv / lastv: no reset
    always @(posedge ck)if(wacc)begin
        if(wnew)ctag[8*wb+:8]<=w0tag;
        if(wnew||!hv[wqi])headf[RB*wqi+:RB]<=wrow[RB-1:0];
        tailf[RB*wqi+:RB]<=wrow[RB-1:0];lastf[20*wqi+:20]<=w0max;
        nrow[(RB+1)*wb+:(RB+1)]<=wrow+1'b1;nent[(CW+1)*wb+:(CW+1)]<=went;
    end
    always @(posedge ck or negedge rl[0])if(!rl[0])begin
        cwe<=0;ctagv<=0;hv<=0;lastv<=0;f_wr<=0;
    end else begin
        cwe<=wacc;
        if(w0v&&!wacc)f_wr<=1;
        if(wacc)begin
            if(wnew)begin
                ctagv[wb]<=1'b1;
                hv[4*wb+:4]<=4'd1<<w0q;lastv[4*wb+:4]<=4'd1<<w0q;
            end else begin hv[wqi]<=1'b1;lastv[wqi]<=1'b1;end
        end
    end
    // candidate row store (SRAM: 2 x 256x256 macros at SRAM_MACRO=1)
    wire rre;wire[RB:0]rra;wire[RDW-1:0]rrd;
    dsdv_i13_ram #(.DEPTH(2*RW),.W(RDW),.SRAM_MACRO(SRAM_MACRO))u_crow(.ck(ck),.re(rre),.ra(rra),.rd(rrd),
        .we(cwe),.wa(cwa),.wd(cwd));
    // ---------------------------------------------------------------- selected ids: SRAM FIFO + 2-word show-ahead
    reg[255:0]olow;reg oh;wire oe=orr[0]&&orr[3:1]==5;wire[511:0]ow={orr[275:20],olow};
    reg[IW:0]iw,ir;reg input_done;
    wire pushidx=oe&&orr[6]&&oh&&ow[511:508]==3&&ow[507:500]==j_ot;
    always @(posedge ck)if(oe&&!orr[6])olow<=orr[275:20];
    reg[1:0]pqc;reg pqi;reg[335:0]pq0,pq1;
    wire ire=ir!=iw&&(pqc+pqi)<2;
    wire[335:0]ird;
    dsdv_i13_ram #(.DEPTH(IF),.W(336),.SRAM_MACRO(SRAM_MACRO))u_ids(.ck(ck),.re(ire),.ra(ir[IW-1:0]),.rd(ird),
        .we(pushidx&&(iw-ir)<IF),.wa(iw[IW-1:0]),.wd({ow[335:320],ow[319:0]}));
    // head word serializer -> X (one lookup key register)
    wire[15:0]im=pq0[335:320];
    integer ii;reg ifound;always @*begin ii=0;ifound=0;for(integer q=0;q<16;q=q+1)if(im[q]&&!ifound)begin ii=q;ifound=1;end end
    wire hasid=pqc!=0&&ifound;
    reg xv,xrok;reg[19:0]xid;reg[1:0]xr;
    wire xload=hasid&&(!xv||req);
    wire[15:0]im_next=xload?(im&~(16'd1<<ii)):im;
    wire pqpop=pqc!=0&&im_next==0;
    wire[19:0]sid=pq0[20*ii+:20];wire[19:0]srk=sid>>j_shift;
    always @(posedge ck)begin
        if(xload)begin xid<=sid;xr<=srk[1:0];xrok<=srk[19:2]==0;end
        if(pqpop)pq0<=pq1;else pq0[335:320]<=im_next;
        if(pqi)begin if((pqc-pqpop)==0)pq0<=ird;else pq1<=ird;end
    end
    always @(posedge ck or negedge rl[2])if(!rl[2])begin iw<=0;ir<=0;oh<=0;input_done<=0;f_idx<=0;pqc<=0;pqi<=0;xv<=0;end
    else begin
        if(oe)begin if(!orr[6])oh<=1;else oh<=0;end
        if(pushidx)begin if(iw-ir>=IF)f_idx<=1;else iw<=iw+1'b1;end
        if(oe&&orr[6]&&oh&&ow[511:508]==4&&ow[507:500]==j_ot)input_done<=1;
        if(ire)ir<=ir+1'b1;
        pqi<=ire;pqc<=pqc-pqpop+pqi;
        if(xload)xv<=1;else if(req)xv<=0;
        if(job)begin iw<=0;ir<=0;input_done<=0;pqc<=0;pqi<=0;xv<=0;end
    end
    // ---------------------------------------------------------------- candidate walk: rank-ordered row stream
    // The walk's qslot select is a kept copy (wk_qh) for the head/tail/valid reads; the qslot tail is captured at the
    // head load (the bank is closed to writes while the walk runs: wconf), so the row-end compare is register-local.
    wire jb=j_ot[0];wire bank_ok=ctagv[jb]&&ctag[8*jb+:8]==j_ot;
    reg wk_done,wk_cur;reg[1:0]wk_q,wk_q_n;reg[RB-1:0]wk_row,wk_tail;
    (* keep *)reg[1:0]wk_qh;
    reg[2:0]rqc;reg rqi;reg[1:0]rqiq;
    reg[RDW-1:0]rq0,rq1,rq2,rq3;reg[1:0]rk0,rk1,rk2,rk3;
    wire[2:0]wqj={jbh,wk_qh};
    assign rre=wk_on&&!wk_done&&bank_ok&&wk_cur&&(rqc+rqi)<4;
    assign rra={jb,wk_row};
    wire wk_hd=wk_on&&!wk_done&&bank_ok&&!wk_cur&&hv[wqj];
    always @*begin
        wk_row_n=wk_row;wk_q_n=wk_q;
        if(job)wk_q_n=0;
        else if(wk_on&&!wk_done&&bank_ok)begin
            if(!wk_cur)begin
                if(hv[wqj])wk_row_n=headf[RB*wqj+:RB];
                else if(wk_q!=3)wk_q_n=wk_q+1'b1;
            end else if(rre)begin
                if(wk_row==wk_tail)begin if(wk_q!=3)wk_q_n=wk_q+1'b1;end
                else wk_row_n=lnk_rd;
            end
        end
    end
    always @(posedge ck)begin wk_row<=wk_row_n;if(wk_hd)wk_tail<=tailf[RB*wqj+:RB];end
    always @(posedge ck or negedge rl[3])if(!rl[3])begin wk_on<=0;wk_done<=0;wk_cur<=0;wk_q<=0;wk_qh<=0;end
    else begin
        wk_q<=wk_q_n;wk_qh<=wk_q_n;
        if(job)begin wk_on<=0;wk_done<=0;wk_cur<=0;end
        else begin
            if(armed&&!done&&j_cam&&xv)wk_on<=1;
            if(wk_on&&!wk_done)begin
                if(!bank_ok)wk_done<=1;
                else if(!wk_cur)begin
                    if(hv[wqj])wk_cur<=1;
                    else if(wk_q==3)wk_done<=1;
                end else if(rre)begin
                    if(wk_row==wk_tail)begin wk_cur<=0;if(wk_q==3)wk_done<=1;end
                end
            end
        end
    end
    // merge-join on X against the two head rows (R0 = rq0, R1 = rq1)
    wire r0v=rqc!=0,r1v=rqc>1;
    reg[12:0]eq0,eq1;reg[15:0]jsc;
    always @*begin
        jsc=0;
        for(integer e=0;e<13;e=e+1)begin
            eq0[e]=r0v&&rq0[468+e]&&rk0==xr&&rq0[36*e+16+:20]==xid;
            eq1[e]=r1v&&rq1[468+e]&&rk1==xr&&rq1[36*e+16+:20]==xid;
            if(eq0[e])jsc=jsc|rq0[36*e+:16];
            if(eq1[e])jsc=jsc|rq1[36*e+:16];
        end
    end
    wire jhit=xrok&&(|eq0||(|eq1));
    wire gt0=r0v&&{xr,xid}>{rk0,rq0[RDW-1-:20]};
    wire send=wk_done&&!rqi&&rqc==0;
    wire jmiss=!jhit&&(!xrok||(r0v&&!gt0)||send);
    wire jtake=xv&&(jhit||jmiss);
    wire rqpop=xv&&xrok&&gt0&&armed&&!done&&j_cam;
    always @(posedge ck)begin
        if(rqpop)begin rq0<=rq1;rk0<=rk1;rq1<=rq2;rk1<=rk2;rq2<=rq3;rk2<=rk3;end
        if(rqi)case(3'(rqc-rqpop))
            3'd0:begin rq0<=rrd;rk0<=rqiq;end
            3'd1:begin rq1<=rrd;rk1<=rqiq;end
            3'd2:begin rq2<=rrd;rk2<=rqiq;end
            default:begin rq3<=rrd;rk3<=rqiq;end
        endcase
    end
    always @(posedge ck)rqiq<=wk_q;
    always @(posedge ck or negedge rl[3])if(!rl[3])begin rqc<=0;rqi<=0;end
    else if(job)begin rqc<=0;rqi<=0;end
    else begin rqi<=rre;rqc<=rqc-rqpop+rqi;end
    // ---------------------------------------------------------------- lookup issue and LP-edge result pipe
    wire[GW:0]group_fill;reg[LP-1:0]lpv;
    assign req=armed&&!done&&xv&&group_fill<GF-4&&(!j_cam||jtake);
    assign req_id=xid;
    reg[20*LP-1:0]ipp;reg[17*LP-1:0]csp;reg[15:0]ds2;
    wire[19:0]ip1=ipp[20*(LP-2)+:20],ip2=ipp[20*(LP-1)+:20];
    wire[15:0]cs2=csp[17*(LP-1)+:16];wire ch2=csp[17*(LP-1)+16];
    always @(posedge ck)begin
        ipp<={ipp[20*(LP-1)-1:0],req_id};
        csp<={csp[17*(LP-1)-1:0],jhit,jhit?jsc:16'd0};
        ds2<=dense_rd[16*ip1[3:0]+:16];
    end
    always @(posedge ck or negedge rl[3])if(!rl[3])lpv<=0;else begin lpv<={lpv[LP-2:0],req};if(job)lpv<=0;end
    always @(posedge ck or negedge rl[1])if(!rl[1])f_lookup<=0;else begin
        if(lpv[LP-1]&&j_cam&&!ch2)f_lookup<=1;
    end
    // Rank-preserving groups: flush/LAST at rank boundary, emit a new HDR before
    // the next rank's type8 word. Quarter order is global index order.
    reg[483:0]gf[0:GF-1];reg[GW:0]gw,gr;reg[467:0]pack;reg[3:0]np;reg[1:0]pq;
    reg pack_done;reg[9:0]nlook;reg[19:0]previous;reg previous_v;
    wire[1:0]rankq=2'(ip2>>j_shift);wire[15:0]score=j_cam?cs2:ds2;
    assign group_fill=gw-gr;
    wire ids_idle=input_done&&iw==ir&&!pqi&&pqc==0&&!xv;
    // control (reset leaf rl[4]) and data (no reset) halves of the same group packer
    wire e_lk=!job&&lpv[LP-1];
    wire e_fw=np!=0&&(np==13||rankq!=pq);
    wire e_fin=!job&&!lpv[LP-1]&&ids_idle&&lpv==0&&!pack_done;
    wire gfull=gw-gr>=GF;
    always @(posedge ck or negedge rl[4])if(!rl[4])begin
        gw<=0;np<=0;pack_done<=0;previous_v<=0;f_pack<=0;
    end else begin
        if(job)begin gw<=0;np<=0;pack_done<=0;previous_v<=0;end
        else if(e_lk)begin
            if((previous_v&&ip2<=previous)||nlook>=j_k)f_pack<=1;
            previous_v<=1;
            if(e_fw)begin if(gfull)f_pack<=1;else gw<=gw+1'b1;np<=1;end
            else np<=np+1'b1;
        end else if(e_fin)begin
            if(np!=0)begin if(gfull)f_pack<=1;else gw<=gw+1'b1;end
            np<=0;pack_done<=1;
        end
    end
    always @(posedge ck)begin
        if(job)nlook<=0;
        else if(e_lk)begin
            previous<=ip2;nlook<=nlook+1'b1;pq<=rankq;
            if(e_fw)begin
                if(!gfull)gf[gw[GW-1:0]]<={rankq!=pq,pq,13'((14'd1<<np)-1),pack};
                pack<=468'({ip2,score});
            end else begin if(np==0)pack<=468'({ip2,score});else pack[36*np+:36]<={ip2,score};end
        end else if(e_fin&&np!=0&&!gfull)gf[gw[GW-1:0]]<={1'b1,pq,13'((14'd1<<np)-1),pack};
    end
    wire[483:0]front=gf[gr[GW-1:0]];wire[1:0]fq=front[482:481];
    wire[511:0]i13w={4'd8,j_pt,18'd0,front[483],front[480:468],front[467:0]};
    wire[511:0]hdrw={4'd1,j_pt,468'd0,fq,j_k,j_hb};
    reg phase,haveq;reg[1:0]outq;reg[2:0]rphase;
    wire grid=armed&&tick>=j_dly+2&&rphase==0;
    always @(posedge ck or negedge rl[4])if(!rl[4])rphase<=0;else if(job)rphase<=0;
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
    always @(posedge ck or negedge rl[3])if(!rl[3])begin armed<=0;done<=0;lo[0]<=0;phase<=0;gr<=0;haveq<=0;outq<=0;f_out<=0;end
    else begin
        lo[0]<=0;
        if(job)begin armed<=1;done<=0;phase<=0;gr<=0;haveq<=0;end
        else if(armed)begin
            if(grid)begin
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
    always @(posedge ck)if(job)slots<=0;else if(armed&&grid)slots<=slots+1'b1;
    always @(posedge ck)if(grid&&gr!=gw)lo[V-1:1]<=emitb[V-1:1];
    always @(posedge ck or negedge rl[1])if(!rl[1])f_cap<=0;else if(f_wr)f_cap<=1;
    wire fault=f_cfg|f_cap|f_idx|f_lookup|f_pack|f_out;
    always @(posedge ck or negedge rl[1])if(!rl[1])st<=0;else st<={6'd0,f_out,f_pack,f_lookup,f_idx,f_cap,f_cfg,done,armed,1'b0,fault};
endmodule

// One flat 1R1W array, read data registered (1 edge), read-before-write on the same edge (as the ASAP7 macros).
// SRAM_MACRO=1: ceil(W/256) ASAP7 macros side by side (DEPTH 256 -> 256x256_m2, DEPTH 128 -> 128x256_m1).
module dsdv_i13_ram #(parameter integer DEPTH=256, W=512, parameter bit SRAM_MACRO=0)(
    input wire ck,input wire re,input wire[$clog2(DEPTH)-1:0]ra,output wire[W-1:0]rd,
    input wire we,input wire[$clog2(DEPTH)-1:0]wa,input wire[W-1:0]wd);
    localparam integer NM=(W+255)/256;
    generate if(SRAM_MACRO)begin:g_m
        initial if(DEPTH!=256&&DEPTH!=128)$fatal(1,"dsdv_i13_ram: DEPTH must be 128 or 256");
        wire[NM*256-1:0]wdf;wire[NM*256-1:0]rdf;
        assign wdf=wd;
        for(genvar m=0;m<NM;m=m+1)begin:g_c
            if(DEPTH==256)begin:g_256
                ot_sram_1r1w_256x256_m2_r2c2 u_mem(.clk(ck),.r_ce_in(re),.r_addr_in(ra),.rd_out(rdf[256*m+:256]),
                    .w_ce_in(we),.w_addr_in(wa),.wd_in(wdf[256*m+:256]),.w_mask_in({256{1'b1}}),
                    .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
            end
            if(DEPTH==128)begin:g_128
                ot_sram_1r1w_128x256_m1_r2c2 u_mem(.clk(ck),.r_ce_in(re),.r_addr_in(ra),.rd_out(rdf[256*m+:256]),
                    .w_ce_in(we),.w_addr_in(wa),.wd_in(wdf[256*m+:256]),.w_mask_in({256{1'b1}}),
                    .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
            end
        end
        assign rd=rdf[W-1:0];
    end endgenerate
    generate if(!SRAM_MACRO)begin:g_f
        reg[W-1:0]mem[0:DEPTH-1];reg[W-1:0]q;
        always @(posedge ck)begin if(re)q<=mem[ra];if(we)mem[wa]<=wd;end
        assign rd=q;
    end endgenerate
endmodule

// S81-I13 census 2026-10-25: lane read slice. Kept 2-b lane select registered from the pins (same edge as vr[5:4]);
// select bit 0 drives 2*W <= 32 mux pins.
(* keep_hierarchy="yes" *)
module dsdv_i13_lsel #(parameter integer W=16,ID=0)(input wire ck,input wire[1:0]s_n,input wire[4*W-1:0]d,output wire[W-1:0]q);
    (* keep *)reg[1:0]s;
    always @(posedge ck)s<=s_n;
    assign q=d[W*s+:W];
endmodule

// S81-I13 census 2026-10-25: per-row next-pointer table (N x W), banked.  Writes land one edge after we/wa/wd in
// 32-entry write banks (each with its own kept write staging: valid, address, data -> <=32 entry loads); reads are
// combinational from registered per-bank read-address copies (ra = ra_n of the previous edge): 64-entry read slices
// of one bit each (address bit 0 -> 32 mux pins), then a 4:1 group select from its own kept copy.
module dsdv_i13_lnk #(parameter integer N=256,W=7)(input wire ck,we,input wire[$clog2(N)-1:0]wa,input wire[W-1:0]wd,
    input wire[$clog2(N)-1:0]ra_n,output wire[W-1:0]rd);
    localparam integer AB=$clog2(N),NH=N/32,NG=N/64;
    initial if(N%64!=0||N<128)$fatal(1,"dsdv_i13_lnk: N must be a multiple of 64, >= 128");
    wire[N*W-1:0]q;
    for(genvar h=0;h<NH;h=h+1)begin:g_w
        dsdv_i13_lnk_w #(.W(W),.H(h),.AB(AB))u(.ck(ck),.we(we),.wa(wa),.wd(wd),.q(q[32*W*h+:32*W]));
    end
    wire[NG*W-1:0]gq;
    for(genvar g=0;g<NG;g=g+1)begin:g_g
        for(genvar b=0;b<W;b=b+1)begin:g_b
            wire[63:0]col;
            for(genvar e=0;e<64;e=e+1)begin:g_e assign col[e]=q[W*(64*g+e)+b];end
            dsdv_i13_lnk_r #(.ID(W*g+b))u(.ck(ck),.ra_n(ra_n[5:0]),.d(col),.q(gq[W*g+b]));
        end
    end
    (* keep *)reg[AB-7:0]ghi;
    always @(posedge ck)ghi<=ra_n[AB-1:6];
    assign rd=gq[W*ghi+:W];
endmodule
(* keep_hierarchy="yes" *)
module dsdv_i13_lnk_w #(parameter integer W=7,H=0,AB=8)(input wire ck,we,input wire[AB-1:0]wa,input wire[W-1:0]wd,
    output wire[32*W-1:0]q);
    (* keep *)reg v;(* keep *)reg[4:0]a;(* keep *)reg[W-1:0]d;
    reg[W-1:0]m[0:31];
    always @(posedge ck)begin v<=we&&wa[AB-1:5]==(AB-5)'(H);a<=wa[4:0];d<=wd;if(v)m[a]<=d;end
    for(genvar e=0;e<32;e=e+1)begin:g_q assign q[W*e+:W]=m[e];end
endmodule
(* keep_hierarchy="yes" *)
module dsdv_i13_lnk_r #(parameter integer ID=0)(input wire ck,input wire[5:0]ra_n,input wire[63:0]d,output wire q);
    (* keep *)reg[5:0]a;
    always @(posedge ck)a<=ra_n;
    assign q=d[a];
endmodule
