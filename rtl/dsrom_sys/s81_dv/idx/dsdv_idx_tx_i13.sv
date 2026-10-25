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
    wire job_a=orr[0]&&orr[3:1]==0,job_b=cp[7:0]==8'h5c&&cp[10:8]==2;   // terms, for slices that re-form job locally
    wire job=job_a&&job_b;
    // job, decoded again in keep_hierarchy holders for the slice groups (rq / pq / gf windows)
    wire[2:0]jobs;
    for(genvar k=0;k<3;k=k+1)begin:g_jd dsdv_i13_jdec #(.ID(k))u(.h(orr[3:0]),.c(cp[10:0]),.job(jobs[k]));end
    reg armed,done;reg[7:0]j_pt,j_ot;reg[9:0]j_k;reg[19:0]j_hb;reg[15:0]j_dly;reg[2:0]j_r;
    reg[11:0]j_sm;reg[1:0]j_l;reg j_cam;reg[20:0]tick;reg[11:0]slots;
    reg f_cfg,f_cap,f_idx,f_lookup,f_pack,f_out;
    // job fields: loaded by the job word before any use (armed), no reset
    (* keep *)reg jbw,jbh,jbt;   // j_ot[0] copies: candidate write side (wbusy) / walk head select / walk tail select
    (* keep *)reg j_cam2;   // mode copy for the score pick / issue
    // S81-I13 census pass 5: rank-shift copies in keep_hierarchy holders (one per shifter output bit), loaded by the job
    wire[4:0]jsx0,jsx1,jsk,jsz0,jsz1;
    always @(posedge ck or negedge rl[1])if(!rl[1])f_cfg<=0;
    else if(job&&((armed&&!done)||!cp[103]||cp[108:104]>19||cp[87:85]==0||cp[40:31]==0||cp[40:31]>512))f_cfg<=1;
    always @(posedge ck)begin
        if(job)begin
            jbw<=cp[61];jbh<=cp[61];jbt<=cp[61];j_cam2<=cp[109];
            j_l<=cp[22:21];j_pt<=cp[30:23];j_k<=cp[40:31];j_hb<=cp[60:41];j_ot<=cp[68:61];
            j_dly<=cp[84:69];j_r<=cp[87:85];j_sm<=cp[99:88];j_cam<=cp[109];tick<=0;
        end else if(armed)tick<=tick+1'b1;
    end
    dsdv_i13_kreg #(.W(5),.ID(0))u_jsx0(.ck(ck),.en(job),.d(cp[108:104]),.q(jsx0));   // xr[0]
    dsdv_i13_kreg #(.W(5),.ID(1))u_jsx1(.ck(ck),.en(job),.d(cp[108:104]),.q(jsx1));   // xr[1]
    dsdv_i13_kreg #(.W(5),.ID(2))u_jsk(.ck(ck),.en(job),.d(cp[108:104]),.q(jsk));     // xrok
    dsdv_i13_kreg #(.W(5),.ID(3))u_jsz0(.ck(ck),.en(job),.d(cp[108:104]),.q(jsz0));   // rankq[0]
    dsdv_i13_kreg #(.W(5),.ID(4))u_jsz1(.ck(ck),.en(job),.d(cp[108:104]),.q(jsz1));   // rankq[1]
    // ---------------------------------------------------------------- dense score store (unchanged function)
    // Lane staging: 4 lanes x (256-b part-0 + 20-b cursor).  The lane select is a kept 2-b copy per 16-b (10-b) read
    // slice, registered from the vi pins on the same edge as vr (= vr[5:4]); the part-0 write enable is a kept
    // one-hot copy per {lane, 16-b column} (as dsdv_idx_tx_n32 hsw).  No select drives more than 32 pins.
    reg[255:0]vilow[0:3];reg[19:0]cursor[0:3];reg[3:0]vhave;
    wire cv=vr[0]&&vr[3:1]==4;wire[1:0]vl=vr[5:4];
    wire[255:0]vlo;wire[19:0]vcur;
    for(genvar c=0;c<8;c=c+1)begin:g_vs
        dsdv_i13_lsel #(.W(32),.ID(c))u(.ck(ck),.s_n(vi[5:4]),
            .d({vilow[3][32*c+:32],vilow[2][32*c+:32],vilow[1][32*c+:32],vilow[0][32*c+:32]}),.q(vlo[32*c+:32]));
    end
    dsdv_i13_lsel #(.W(20),.ID(8))u_cs(.ck(ck),.s_n(vi[5:4]),.d({cursor[3],cursor[2],cursor[1],cursor[0]}),.q(vcur));
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
    (* keep *)reg[12:0]pmk,pmk2,pmk3;   // pin-registered copies of the prefix mask (= vr[244:232]): max-id bits [6:0]+count, [13:7], [19:14]
    always @(posedge ck)begin pmk<=vi[244:232];pmk2<=vi[244:232];pmk3<=vi[244:232];end
    reg pok;reg[19:0]pmax;reg[3:0]pn;
    always @*begin
        pok=pmask!=0&&((pmask&(pmask+13'd1))==0);pmax=vw[16+:20];pn=0;
        for(integer e=0;e<13;e=e+1)begin
            if(pmk[e])begin pmax[6:0]=vw[36*e+16+:7];pn=4'(e+1);end
            if(pmk2[e])pmax[13:7]=vw[36*e+23+:7];
            if(pmk3[e])pmax[19:14]=vw[36*e+30+:6];
        end
        for(integer e=1;e<13;e=e+1)if(pmask[e]&&!(vw[36*e+16+:20]>vw[36*(e-1)+16+:20]))pok=0;
    end
    reg w0v,w0ok,w0qv;reg[7:0]w0tag;reg[1:0]w0q;
    reg[19:0]w0first,w0max;reg[3:0]w0n;reg[480:0]w0d;
    (* keep *)reg wbd,wbb,wbb2;   // bank copies: busy compare + row address / link write address (two bank halves)
    always @(posedge ck or negedge rl[0])if(!rl[0])w0v<=0;else w0v<=packet;
    // S81-I13 census pass 5: the W0 stage captures every edge (no load enable): every use of a W0 field is qualified
    // by w0v (wacc / f_wr) on the edge after the capture, so the 530-bit packet load enable is gone.
    always @(posedge ck)begin
        w0ok<=pok;w0qv<=lqv[vl];w0q<=lqf[2*vl+:2];wbd<=vw[500];wbb<=vw[500];wbb2<=vw[500];
        w0tag<=vw[507:500];w0first<=vw[16+:20];w0max<=pmax;w0n<=pn;w0d<=vw[480:0];
    end
    // bank state: tag, row count, entry count; per {bank,qslot}: head/tail/last id; per row: next (flat arrays)
    reg[15:0]ctag;reg[1:0]ctagv;reg[2*(RB+1)-1:0]nrow;reg[2*(CW+1)-1:0]nent;
    reg[8*RB-1:0]headf,tailf;reg[8*20-1:0]lastf;reg[7:0]hv,lastv;
    reg wk_on;  // the armed job's merge walk started
    wire wb=w0tag[0];wire[2:0]wqi={wb,w0q};
    // W0-word reads of the qslot / bank state: rsel slices (keep_hierarchy), each with its own select register captured
    // on the W0 edge (= {wb,w0q} / wb), <= 6 bits per slice, so no select bit drives more than one small slice
    wire[2:0]wq_n={vw[500],lqf[2*vl+:2]};wire wb_n=vw[500];
    wire[19:0]lastf_w;wire[RB-1:0]tailf_w,tailf_w2;wire lastv_w,hv_w;wire[8:0]ctg_w;wire[RB:0]nrow_w;wire[CW:0]nent_w;
    wire[15:0]hlv_d;wire[17:0]ctg_d={ctag[15:8],ctagv[1],ctag[7:0],ctagv[0]};
    for(genvar e=0;e<8;e=e+1)begin:g_hlv assign hlv_d[2*e+:2]={lastv[e],hv[e]};end
    for(genvar k=0;k<5;k=k+1)begin:g_rlf
        dsdv_i13_rsel #(.N(8),.FW(20),.LO(4*k),.W(4))u(.ck(ck),.s_n(wq_n),.d(lastf),.q(lastf_w[4*k+:4]));
    end
    dsdv_i13_rsel #(.N(8),.FW(RB),.LO(0),.W(4),.ID(0))u_rtf0(.ck(ck),.s_n(wq_n),.d(tailf),.q(tailf_w[3:0]));
    dsdv_i13_rsel #(.N(8),.FW(RB),.LO(4),.W(RB-4),.ID(0))u_rtf1(.ck(ck),.s_n(wq_n),.d(tailf),.q(tailf_w[RB-1:4]));
    dsdv_i13_rsel #(.N(8),.FW(RB),.LO(0),.W(4),.ID(1))u_rtf2(.ck(ck),.s_n(wq_n),.d(tailf),.q(tailf_w2[3:0]));
    dsdv_i13_rsel #(.N(8),.FW(RB),.LO(4),.W(RB-4),.ID(1))u_rtf3(.ck(ck),.s_n(wq_n),.d(tailf),.q(tailf_w2[RB-1:4]));
    dsdv_i13_rsel #(.N(8),.FW(2),.LO(0),.W(2))u_rhl(.ck(ck),.s_n(wq_n),.d(hlv_d),.q({lastv_w,hv_w}));
    dsdv_i13_rsel #(.N(2),.FW(9),.LO(0),.W(5))u_rct0(.ck(ck),.s_n(wb_n),.d(ctg_d),.q(ctg_w[4:0]));
    dsdv_i13_rsel #(.N(2),.FW(9),.LO(5),.W(4))u_rct1(.ck(ck),.s_n(wb_n),.d(ctg_d),.q(ctg_w[8:5]));
    dsdv_i13_rsel #(.N(2),.FW(RB+1),.LO(0),.W(RB+1))u_rnr(.ck(ck),.s_n(wb_n),.d(nrow),.q(nrow_w));
    dsdv_i13_rsel #(.N(2),.FW(CW+1),.LO(0),.W(6))u_rne0(.ck(ck),.s_n(wb_n),.d(nent),.q(nent_w[5:0]));
    dsdv_i13_rsel #(.N(2),.FW(CW+1),.LO(6),.W(CW-5))u_rne1(.ck(ck),.s_n(wb_n),.d(nent),.q(nent_w[CW:6]));
    wire wnew=!ctg_w[0]||ctg_w[8:1]!=w0tag;
    wire[RB:0]wrow=wnew?{(RB+1){1'b0}}:nrow_w;
    wire[CW:0]went=(wnew?{(CW+1){1'b0}}:nent_w)+(CW+1)'(w0n);
    wire wlast=!wnew&&lastv_w;
    wire wbad=!w0ok||!w0qv||(MUT!=3&&wlast&&w0first<=lastf_w)||wrow>=RW||went>C;
    wire wbusy=armed&&!done&&j_cam&&jbw==wbd;
    wire wconf=wbusy&&((w0tag!=j_ot)||wk_on);
    // accept = w0v && ok, formed in 4 holders (each <= 16 enable holders); per-entry / per-bank write enables in holders
    wire wok=!wbad&&!wconf;wire[3:0]wac;
    for(genvar k=0;k<4;k=k+1)begin:g_wac dsdv_i13_and #(.N(2),.ID(k))u(.a({w0v,wok}),.y(wac[k]));end
    wire wacc=wac[3];
    wire[7:0]wdec,ehd,etl,elf0,elf1;wire hnew=wnew||!hv_w;
    for(genvar e=0;e<8;e=e+1)begin:g_wen
        assign wdec[e]=wqi==3'(e);
        dsdv_i13_and #(.N(3),.ID(10+e))u_hd(.a({wac[e/4],wdec[e],hnew}),.y(ehd[e]));
        dsdv_i13_and #(.N(2),.ID(20+e))u_tl(.a({wac[e/4],wdec[e]}),.y(etl[e]));
        dsdv_i13_and #(.N(2),.ID(30+e))u_l0(.a({wac[2],wdec[e]}),.y(elf0[e]));
        dsdv_i13_and #(.N(2),.ID(40+e))u_l1(.a({wac[2],wdec[e]}),.y(elf1[e]));
    end
    wire[1:0]ect,enr,ene;
    for(genvar b=0;b<2;b=b+1)begin:g_ben
        dsdv_i13_and #(.N(3),.ID(50+b))u_ct(.a({wac[3],wnew,wb==1'(b)}),.y(ect[b]));
        dsdv_i13_and #(.N(2),.ID(52+b))u_nr(.a({wac[3],wb==1'(b)}),.y(enr[b]));
        dsdv_i13_and #(.N(2),.ID(54+b))u_ne(.a({wac[3],wb==1'(b)}),.y(ene[b]));
    end
    reg cwe;reg[RB:0]cwa;reg[RDW-1:0]cwd;
    always @(posedge ck)begin cwa<={wbd,wrow[RB-1:0]};cwd<={w0max,w0d};end
    // per-row next pointer: banked link table, write landed one edge later, registered per-bank read address copies
    // (replaces one 2*RW x RB flop array read through one wk_row register)
    wire[RB-1:0]lnk_rd,wk_row_n,wk_row_n2,wk_hsel;wire wk_ld,wk_av;
    // next walk row, formed twice (keep_hierarchy) so each copy drives <= 29 read-address registers
    dsdv_i13_nx #(.W(RB),.ID(0))u_nx0(.hd(wk_ld),.av(wk_av),.h(wk_hsel),.l(lnk_rd),.c(wk_row),.q(wk_row_n));
    dsdv_i13_nx #(.W(RB),.ID(1))u_nx1(.hd(wk_ld),.av(wk_av),.h(wk_hsel),.l(lnk_rd),.c(wk_row),.q(wk_row_n2));
    dsdv_i13_lnk #(.N(2*RW),.W(RB))u_lnk(.ck(ck),.we(wacc&&!wnew&&hv_w),.wa({wbb,tailf_w}),.wa2({wbb2,tailf_w2}),
        .wd(wrow[RB-1:0]),.ra_n({jbh,wk_row_n}),.ra_n2({jbh,wk_row_n2}),.rd(lnk_rd));
    reg f_wr;
    // bank tag / row / entry counts and per-qslot head/tail/last are qualified by ctagv / hv / lastv: no reset
    always @(posedge ck)begin
        for(integer b=0;b<2;b=b+1)begin
            if(ect[b])ctag[8*b+:8]<=w0tag;
            if(enr[b])nrow[(RB+1)*b+:(RB+1)]<=wrow+1'b1;
            if(ene[b])nent[(CW+1)*b+:(CW+1)]<=went;
        end
        for(integer e=0;e<8;e=e+1)begin
            if(ehd[e])headf[RB*e+:RB]<=wrow[RB-1:0];
            if(etl[e])tailf[RB*e+:RB]<=wrow[RB-1:0];
            if(elf0[e])lastf[20*e+:10]<=w0max[9:0];
            if(elf1[e])lastf[20*e+10+:10]<=w0max[19:10];
        end
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
    (* keep *)reg[21:0]olw;   // olow[12 c +: 12] load (= oe && !orr[6], registered from the vo pins)
    always @(posedge ck)olw<={22{vo[0]&&vo[3:1]==5&&!vo[6]}};
    always @(posedge ck)for(integer b=0;b<256;b=b+1)if(olw[b/12])olow[b]<=orr[20+b];
    reg[1:0]pqc;reg pqi;reg[15:0]pm0,pm1;wire[319:0]pqd;wire[335:0]pq0={pm0,pqd};
    wire ire=ir!=iw&&(pqc+pqi)<2;
    wire[335:0]ird;
    dsdv_i13_ram #(.DEPTH(IF),.W(336),.SRAM_MACRO(SRAM_MACRO))u_ids(.ck(ck),.re(ire),.ra(ir[IW-1:0]),.rd(ird),
        .we(pushidx&&(iw-ir)<IF),.wa(iw[IW-1:0]),.wd({ow[335:320],ow[319:0]}));
    // head word serializer -> X (one lookup key register)
    wire[15:0]im=pm0;
    integer ii;reg ifound;always @*begin ii=0;ifound=0;for(integer q=0;q<16;q=q+1)if(im[q]&&!ifound)begin ii=q;ifound=1;end end
    wire hasid=pqc!=0&&ifound;
    reg xv,xrok;wire[19:0]xid,xid1,xid2;wire[1:0]xr,xr1,xr2;
    // lookup key {xr,xid}: three copies in keep_hierarchy holders (11 b each half): R0 compare, R1 compare, issue + order
    wire xload=hasid&&(!xv||req);
    wire[15:0]im_next=xload?(im&~(16'd1<<ii)):im;
    wire pqpop=pqc!=0&&im_next==0;
    // id words: 2-entry show-ahead ring in 11 slices (<= 30 b) with own one-hot head/tail pointers; masks above
    for(genvar k=0;k<11;k=k+1)begin:g_pq
        localparam integer PLO=30*k,PWD=(320-PLO<30)?320-PLO:30;
        dsdv_i13_ring #(.W(PWD),.NE(2),.R1(0),.ID(k))u(.ck(ck),.job(jobs[1]),.pu_n(ire),.pa(pqc!=0),.pb(im_next==0),
            .d(ird[PLO+:PWD]),.r0(pqd[PLO+:PWD]),.r1());
    end
    wire[19:0]sid=pq0[20*ii+:20];wire[19:0]srk0=sid>>jsx0,srk1=sid>>jsx1,srkk=sid>>jsk;
    wire[21:0]xkd={srk1[1],srk0[0],sid};
    wire[65:0]xk;
    for(genvar c=0;c<3;c=c+1)begin:g_xk
        dsdv_i13_kreg #(.W(11),.ID(10+2*c))u_lo(.ck(ck),.en(xload),.d(xkd[10:0]),.q(xk[22*c+:11]));
        dsdv_i13_kreg #(.W(11),.ID(11+2*c))u_hi(.ck(ck),.en(xload),.d(xkd[21:11]),.q(xk[22*c+11+:11]));
    end
    assign {xr1,xid1}=xk[21:0];assign {xr2,xid2}=xk[43:22];assign {xr,xid}=xk[65:44];
    always @(posedge ck)begin
        if(xload)xrok<=srkk[19:2]==0;
        if(pqpop)pm0<=pm1;else pm0<=im_next;
        if(pqi)begin if((pqc-pqpop)==0)pm0<=ird[335:320];else pm1<=ird[335:320];end
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
    (* keep *)reg[1:0]wk_qh,wk_qa,wk_qb;   // valid / head / tail select copies
    reg[2:0]rqc;reg rqi;reg[1:0]rqiq;
    wire[RDW-1:0]rq0,rq1;wire[1:0]rk0,rk1;
    wire[2:0]wqj={jbh,wk_qh},wqa={jbh,wk_qa},wqb={jbt,wk_qb};
    assign rre=wk_on&&!wk_done&&bank_ok&&wk_cur&&(rqc+rqi)<4;
    assign rra={jb,wk_row};
    wire wk_hd=wk_on&&!wk_done&&bank_ok&&!wk_cur&&hv[wqj];
    assign wk_hsel=headf[RB*wqa+:RB];
    assign wk_ld=!job&&wk_on&&!wk_done&&bank_ok&&!wk_cur&&hv[wqj];
    assign wk_av=!job&&wk_on&&!wk_done&&bank_ok&&wk_cur&&rre&&wk_row!=wk_tail;
    always @*begin
        wk_q_n=wk_q;
        if(job)wk_q_n=0;
        else if(wk_on&&!wk_done&&bank_ok)begin
            if(!wk_cur)begin
                if(!hv[wqj]&&wk_q!=3)wk_q_n=wk_q+1'b1;
            end else if(rre)begin
                if(wk_row==wk_tail&&wk_q!=3)wk_q_n=wk_q+1'b1;
            end
        end
    end
    always @(posedge ck)begin wk_row<=wk_row_n;if(wk_hd)wk_tail<=tailf[RB*wqb+:RB];end
    always @(posedge ck or negedge rl[3])if(!rl[3])begin wk_on<=0;wk_done<=0;wk_cur<=0;wk_q<=0;wk_qh<=0;wk_qa<=0;wk_qb<=0;end
    else begin
        wk_q<=wk_q_n;wk_qh<=wk_q_n;wk_qa<=wk_q_n;wk_qb<=wk_q_n;
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
            eq0[e]=r0v&&rq0[468+e]&&rk0==xr1&&rq0[36*e+16+:20]==xid1;
            eq1[e]=r1v&&rq1[468+e]&&rk1==xr2&&rq1[36*e+16+:20]==xid2;
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
    // candidate-row window: 4-entry ring in 17 slices (<= 30 b of {rk, row}) with own one-hot tail / head / head+1
    // pointers re-formed from shared terms (push = rqi, pop = rqp_a & rqp_b), R0 / R1 = AND-OR reads
    wire rqp_a=xv&&xrok&&gt0,rqp_b=armed&&!done&&j_cam;
    wire[RDW+1:0]rqw={rqiq,rrd},rr0,rr1;
    for(genvar k=0;k<17;k=k+1)begin:g_rq
        localparam integer QLO=30*k,QWD=(RDW+2-QLO<30)?RDW+2-QLO:30;
        dsdv_i13_ring #(.W(QWD),.NE(4),.R1(1),.ID(k))u(.ck(ck),.job(jobs[0]),.pu_n(rre),.pa(rqp_a),.pb(rqp_b),
            .d(rqw[QLO+:QWD]),.r0(rr0[QLO+:QWD]),.r1(rr1[QLO+:QWD]));
    end
    assign {rk0,rq0}=rr0;assign {rk1,rq1}=rr1;
    always @(posedge ck)rqiq<=wk_q;
    always @(posedge ck or negedge rl[3])if(!rl[3])begin rqc<=0;rqi<=0;end
    else if(job)begin rqc<=0;rqi<=0;end
    else begin rqi<=rre;rqc<=rqc-rqpop+rqi;end
    // ---------------------------------------------------------------- lookup issue and LP-edge result pipe
    wire[GW:0]group_fill;reg[LP-1:0]lpv;
    assign req=armed&&!done&&xv&&group_fill<GF-4&&(!j_cam2||jtake);
    assign req_id=xid;
    reg[20*LP-1:0]ipp;reg[17*LP-1:0]csp;wire[15:0]ds2;
    wire[19:0]ip1=ipp[20*(LP-2)+:20],ip2=ipp[20*(LP-1)+:20];
    wire[15:0]cs2=csp[17*(LP-1)+:16];wire ch2=csp[17*(LP-1)+16];
    // dense score pick: 4 slices of 4 b, each with a kept copy of ip1[3:0] (registered from the stage before ip1)
    wire[19:0]ip0=(LP>2)?ipp[20*(LP-3)+:20]:req_id;
    for(genvar c=0;c<4;c=c+1)begin:g_ds
        dsdv_i13_dsel #(.ID(c),.OFF(4*c))u(.ck(ck),.s_n(ip0[3:0]),.d(dense_rd),.q(ds2[4*c+:4]));
    end
    always @(posedge ck)begin
        ipp<={ipp[20*(LP-1)-1:0],req_id};
        csp<={csp[17*(LP-1)-1:0],jhit,jhit?jsc:16'd0};
    end
    always @(posedge ck or negedge rl[3])if(!rl[3])lpv<=0;else begin lpv<={lpv[LP-2:0],req};if(job)lpv<=0;end
    always @(posedge ck or negedge rl[1])if(!rl[1])f_lookup<=0;else begin
        if(lpv[LP-1]&&j_cam&&!ch2)f_lookup<=1;
    end
    // Rank-preserving groups: flush/LAST at rank boundary, emit a new HDR before
    // the next rank's type8 word. Quarter order is global index order.
    reg[GW:0]gw,gr;wire[467:0]pack;reg[3:0]np;reg[1:0]pq;
    reg pack_done;reg[9:0]nlook;reg[19:0]previous;reg previous_v;
    wire[19:0]rz0=ip2>>jsz0,rz1=ip2>>jsz1;wire[1:0]rankq={rz1[1],rz0[0]};wire[15:0]score=j_cam2?cs2:ds2;
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
        end
    end
    // group FIFO: GF x 484 b in 17 slices (<= 30 b), each with its own one-hot write/read pointers and its own copy of
    // the output-control state (haveq/outq/phase), re-formed from shared terms, so no pointer or select drives > 32 pins
    // group being packed: 13 entries x 36 b in 26 half-entry slices, each forming its own load from lpv / np / ranks
    wire[35:0]pkd={ip2,score};
    wire lv_n=lpv[LP-2]&&!job;   // = next lpv[LP-1] (slice copies register it)
    for(genvar e=0;e<13;e=e+1)begin:g_pk
        for(genvar h=0;h<2;h=h+1)begin:g_h
            dsdv_i13_pks #(.E(e),.ID(2*e+h))u(.ck(ck),.lv_n(lv_n),.np(np),.rq(rankq),.pq(pq),.d(pkd[18*h+:18]),
                .q(pack[36*e+18*h+:18]));
        end
    end
    wire gwe_a=(e_lk&&e_fw)||(e_fin&&np!=0),gwe_b=!gfull;wire[1:0]gwe;   // group write, two holder copies (9 / 8 slices)
    for(genvar k=0;k<2;k=k+1)begin:g_gwe dsdv_i13_and #(.N(2),.ID(60+k))u(.a({gwe_a,gwe_b}),.y(gwe[k]));end
    wire[483:0]gwd={e_lk?(rankq!=pq):1'b1,pq,13'((14'd1<<np)-1),pack};
    wire[483:0]front;wire grid,gne;
    assign gne=gr!=gw;
    for(genvar k=0;k<17;k=k+1)begin:g_gf
        localparam integer GLO=30*k,GWD=(484-GLO<30)?484-GLO:30;
        dsdv_i13_gfs #(.W(GWD),.GF(GF),.ID(k))u(.ck(ck),.job(jobs[2]),.grid(grid),.ne(gne),
            .fq(front[482:481]),.we(gwe[k/9]),.wd(gwd[GLO+:GWD]),.q(front[GLO+:GWD]));
    end
    wire[1:0]fq=front[482:481];
    wire[511:0]i13w={4'd8,j_pt,18'd0,front[483],front[480:468],front[467:0]};
    wire[511:0]hdrw={4'd1,j_pt,468'd0,fq,j_k,j_hb};
    reg phase,haveq;reg[1:0]outq;reg[2:0]rphase;
    assign grid=armed&&tick>=j_dly+2&&rphase==0;
    always @(posedge ck or negedge rl[4])if(!rl[4])rphase<=0;else if(job)rphase<=0;
    else if(armed&&tick>=j_dly+2)rphase<=(rphase==j_r-1)?3'd0:rphase+1'b1;
    // the three candidate beats (wiring + header constants); the select happens in the emit slices
    reg[V-1:0]eh,el,ehi;
    always @*begin
        eh=1|276'(4<<1)|(276'(j_l)<<4)|276'(1<<7)|(276'(hdrw[511:500])<<8)|(276'(hdrw[255:0])<<20);
        el=1|276'(4<<1)|(276'(j_l)<<4)|(276'(i13w[511:500])<<8)|(276'(i13w[255:0])<<20);
        ehi=1|276'(4<<1)|(276'(j_l)<<4)|276'(1<<6)|(276'(i13w[511:256])<<20);
        if(MUT==1)eh[51:50]=2'd2;
        if(MUT==2&&j_cam)begin eh[20]=~eh[20];el[20]=~el[20];ehi[20]=~ehi[20];end
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
    // lo[V-1:1]: 10 emit slices (<= 28 b), each with its own output-control state copy
    wire[V-1:1]lo_s;
    for(genvar k=0;k<10;k=k+1)begin:g_em
        localparam integer ELO=1+28*k,EWD=(V-ELO<28)?V-ELO:28;
        dsdv_i13_emit #(.W(EWD),.ID(k))u(.ck(ck),.job_a(job_a),.job_b(job_b),.grid(grid),.ne(gne),.fq(fq),
            .eh(eh[ELO+:EWD]),.el(el[ELO+:EWD]),.ehi(ehi[ELO+:EWD]),.q(lo_s[ELO+:EWD]));
    end
    always @*lo[V-1:1]=lo_s;
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
// one-hot select bit drives W <= 32 AND-OR pins.
(* keep_hierarchy="yes" *)
module dsdv_i13_lsel #(parameter integer W=32,ID=0)(input wire ck,input wire[1:0]s_n,input wire[4*W-1:0]d,output reg[W-1:0]q);
    (* keep *)reg[3:0]s;   // one-hot lane select (= vr[5:4] decoded); each bit drives W AND-OR pins
    always @(posedge ck)for(integer l=0;l<4;l=l+1)s[l]<=s_n==2'(l);
    always @*begin q=0;for(integer l=0;l<4;l=l+1)q=q|(d[W*l+:W]&{W{s[l]}});end
endmodule

// S81-I13 census 2026-10-25: per-row next-pointer table (N x W), banked.  Writes land one edge after we/wa/wd in
// 32-entry write banks (each with its own kept write staging: valid, address, data -> <=32 entry loads); reads are
// combinational from registered per-bank read-address copies (ra = ra_n of the previous edge): 32-entry read slices
// of one bit each (ra_n / ra_n2 = two copies of the next address, each feeding half the slices), then a one-hot group
// select (kept, decoded from ra_n's group bits).
module dsdv_i13_lnk #(parameter integer N=256,W=7)(input wire ck,we,input wire[$clog2(N)-1:0]wa,wa2,input wire[W-1:0]wd,
    input wire[$clog2(N)-1:0]ra_n,ra_n2,output reg[W-1:0]rd);
    localparam integer AB=$clog2(N),NH=N/32;
    initial if(N%64!=0||N<128)$fatal(1,"dsdv_i13_lnk: N must be a multiple of 64, >= 128");
    wire[N*W-1:0]q;
    for(genvar h=0;h<NH;h=h+1)begin:g_w
        dsdv_i13_lnk_w #(.W(W),.H(h),.AB(AB))u(.ck(ck),.we(we),.wa((h<NH/2)?wa:wa2),.wd(wd),.q(q[32*W*h+:32*W]));
    end
    wire[NH*W-1:0]gq;
    for(genvar g=0;g<NH;g=g+1)begin:g_g
        for(genvar b=0;b<W;b=b+1)begin:g_b
            wire[31:0]col;
            for(genvar e=0;e<32;e=e+1)begin:g_e assign col[e]=q[W*(32*g+e)+b];end
            dsdv_i13_lnk_r #(.ID(W*g+b))u(.ck(ck),.ra_n((g<NH/2)?ra_n[4:0]:ra_n2[4:0]),.d(col),.q(gq[W*g+b]));
        end
    end
    (* keep *)reg[NH-1:0]gh;   // one-hot bank select
    always @(posedge ck)for(integer g=0;g<NH;g=g+1)gh[g]<=ra_n[AB-1:5]==(AB-5)'(g);
    always @*begin rd=0;for(integer g=0;g<NH;g=g+1)rd=rd|(gq[W*g+:W]&{W{gh[g]}});end
endmodule
(* keep_hierarchy="yes" *)
module dsdv_i13_nx #(parameter integer W=7,ID=0)(input wire hd,av,input wire[W-1:0]h,l,c,output wire[W-1:0]q);
    assign q=hd?h:(av?l:c);
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
module dsdv_i13_lnk_r #(parameter integer ID=0)(input wire ck,input wire[4:0]ra_n,input wire[31:0]d,output wire q);
    (* keep *)reg[4:0]a;
    always @(posedge ck)a<=ra_n;
    assign q=d[a];
endmodule

// S81-I13 census 2026-10-25: output-control state (haveq / outq / phase), replicated per slice; same update as the
// top copy: job clears haveq/phase; on a grid slot with a group queued: new rank -> header beat (haveq, outq <= fq),
// else low half (phase 1), else high half (phase 0, pop).
module dsdv_i13_octl(input wire ck,job,grid,ne,input wire[1:0]fq,output reg haveq,phase,output reg[1:0]outq,
    output wire hsel,pop);
    assign hsel=!haveq||outq!=fq;
    assign pop=grid&&ne&&!hsel&&phase;
    always @(posedge ck)if(job)begin haveq<=0;phase<=0;end
    else if(grid&&ne)begin
        if(hsel)begin haveq<=1;outq<=fq;end else phase<=!phase;
    end
endmodule
(* keep_hierarchy="yes" *)
module dsdv_i13_gfs #(parameter integer W=30,GF=8,ID=0)(input wire ck,job,grid,ne,input wire[1:0]fq,
    input wire we,input wire[W-1:0]wd,output reg[W-1:0]q);
    localparam integer NC=(W+14)/15;
    wire haveq,phase,hsel,pop;wire[1:0]outq;
    dsdv_i13_octl u_c(.ck(ck),.job(job),.grid(grid),.ne(ne),.fq(fq),.haveq(haveq),.phase(phase),.outq(outq),.hsel(hsel),.pop(pop));
    (* keep *)reg[GF-1:0]wp,rp,rp2;   // rp2 = read-pointer copy for the upper half of the word
    reg[W-1:0]m[0:GF-1];
    wire[GF*NC-1:0]en;   // per-entry write enable, one holder per <= 15 bits
    for(genvar e=0;e<GF;e=e+1)begin:g_e for(genvar c=0;c<NC;c=c+1)begin:g_c
        dsdv_i13_and #(.N(2),.ID(NC*e+c))u(.a({we,wp[e]}),.y(en[NC*e+c]));
    end end
    always @(posedge ck)begin
        if(job)begin wp<=1;rp<=1;rp2<=1;end
        else begin
            if(we)wp<={wp[GF-2:0],wp[GF-1]};
            if(pop)begin rp<={rp[GF-2:0],rp[GF-1]};rp2<={rp2[GF-2:0],rp2[GF-1]};end
        end
        for(integer e=0;e<GF;e=e+1)for(integer b=0;b<W;b=b+1)if(en[NC*e+b/15])m[e][b]<=wd[b];
    end
    always @*begin q=0;for(integer e=0;e<GF;e=e+1)for(integer b=0;b<W;b=b+1)q[b]=q[b]|(m[e][b]&(b<W/2?rp[e]:rp2[e]));end
endmodule
(* keep_hierarchy="yes" *)
module dsdv_i13_emit #(parameter integer W=28,ID=0)(input wire ck,job_a,job_b,grid,ne,input wire[1:0]fq,
    input wire[W-1:0]eh,el,ehi,output reg[W-1:0]q);
    wire job=job_a&&job_b;
    wire haveq,phase,hsel,pop;wire[1:0]outq;
    dsdv_i13_octl u_c(.ck(ck),.job(job),.grid(grid),.ne(ne),.fq(fq),.haveq(haveq),.phase(phase),.outq(outq),.hsel(hsel),.pop(pop));
    always @(posedge ck)if(grid&&ne)q<=hsel?eh:(phase?ehi:el);
endmodule
(* keep_hierarchy="yes" *)
module dsdv_i13_dsel #(parameter integer ID=0,OFF=0)(input wire ck,input wire[3:0]s_n,input wire[255:0]d,output reg[3:0]q);
    (* keep *)reg[3:0]s;   // = ip1[3:0]
    always @(posedge ck)begin s<=s_n;q<=d[16*s+OFF+:4];end
endmodule

// S81-I13 census 2026-10-25: NE-entry ring slice (show-ahead queue column).  Own one-hot tail (wp), head (hp) and,
// with R1, head+1 (hq) pointers, all kept; push / pop / job are re-formed locally from shared terms, so no pointer or
// enable drives more than W <= 30 pins.  Same order as the shift queue it replaces (push at head + count, pop = head).
(* keep_hierarchy="yes" *)
module dsdv_i13_ring #(parameter integer W=30,NE=4,R1=1,ID=0)(input wire ck,job,pu_n,pa,pb,input wire[W-1:0]d,
    output reg[W-1:0]r0,r1);
    localparam integer NC=(W+14)/15;
    (* keep *)reg pu;   // slice copy of the push valid (rqi / pqi): registered from its pre-register term (rre / ire)
    always @(posedge ck)pu<=pu_n&&!job;
    wire push=pu&&!job,pop=pa&&pb&&!job;
    (* keep *)reg[NE-1:0]wp,hp,hq,hp2,hq2;   // hp2 / hq2 = head copies for the upper half of the word
    reg[W-1:0]m[0:NE-1];
    wire[NE*NC-1:0]en;   // per-entry write enable, one holder per <= 15 bits
    for(genvar e=0;e<NE;e=e+1)begin:g_e for(genvar c=0;c<NC;c=c+1)begin:g_c
        dsdv_i13_and #(.N(2),.ID(NC*e+c))u(.a({push,wp[e]}),.y(en[NC*e+c]));
    end end
    always @(posedge ck)begin
        if(job)begin wp<=1;hp<=1;hq<=2;hp2<=1;hq2<=2;end
        else begin
            if(push)wp<={wp[NE-2:0],wp[NE-1]};
            if(pop)begin
                hp<={hp[NE-2:0],hp[NE-1]};hq<={hq[NE-2:0],hq[NE-1]};
                hp2<={hp2[NE-2:0],hp2[NE-1]};hq2<={hq2[NE-2:0],hq2[NE-1]};
            end
        end
        for(integer e=0;e<NE;e=e+1)for(integer b=0;b<W;b=b+1)if(en[NC*e+b/15])m[e][b]<=d[b];
    end
    always @*begin
        r0=0;r1=0;
        for(integer e=0;e<NE;e=e+1)for(integer b=0;b<W;b=b+1)begin
            r0[b]=r0[b]|(m[e][b]&(b<W/2?hp[e]:hp2[e]));
            if(R1)r1[b]=r1[b]|(m[e][b]&(b<W/2?hq[e]:hq2[e]));
        end
    end
endmodule

// S81-I13 census 2026-10-25: half of one pack entry. On a returned lookup: a new group (np == 0 or group flush) loads
// entry 0 and clears the rest; otherwise entry np takes the result.
(* keep_hierarchy="yes" *)
module dsdv_i13_pks #(parameter integer E=0,ID=0)(input wire ck,lv_n,input wire[3:0]np,input wire[1:0]rq,pq,
    input wire[17:0]d,output reg[17:0]q);
    (* keep *)reg lv;   // slice copy of lpv[LP-1]
    always @(posedge ck)lv<=lv_n;
    wire ng=np==0||np==13||rq!=pq;
    wire ld=(E==0)?ng:(ng||np==4'(E));
    wire[1:0]en;   // load enable, one holder per 9 bits
    dsdv_i13_and #(.N(2),.ID(0))u_e0(.a({lv,ld}),.y(en[0]));
    dsdv_i13_and #(.N(2),.ID(1))u_e1(.a({lv,ld}),.y(en[1]));
    wire[17:0]dv=(E==0||!ng)?d:18'd0;
    always @(posedge ck)for(integer b=0;b<18;b=b+1)if(en[b/9])q[b]<=dv[b];
endmodule

// S81-I13 census pass 5 holders (keep_hierarchy, so synthesis cannot fold a shared term back into every bit):
// an AND gate, a loaded register, a registered-select read slice, a job decoder.
(* keep_hierarchy="yes" *)
module dsdv_i13_and #(parameter integer N=2,ID=0)(input wire[N-1:0]a,output wire y);
    assign y=&a;
endmodule
(* keep_hierarchy="yes" *)
module dsdv_i13_kreg #(parameter integer W=11,ID=0)(input wire ck,en,input wire[W-1:0]d,output reg[W-1:0]q);
    always @(posedge ck)if(en)q<=d;
endmodule
(* keep_hierarchy="yes" *)
module dsdv_i13_rsel #(parameter integer N=8,FW=20,LO=0,W=4,ID=0)(input wire ck,input wire[$clog2(N)-1:0]s_n,
    input wire[N*FW-1:0]d,output wire[W-1:0]q);
    (* keep *)reg[$clog2(N)-1:0]s;
    always @(posedge ck)s<=s_n;
    assign q=d[FW*s+LO+:W];
endmodule
(* keep_hierarchy="yes" *)
module dsdv_i13_jdec #(parameter integer ID=0)(input wire[3:0]h,input wire[10:0]c,output wire job);
    assign job=h[0]&&h[3:1]==0&&c[7:0]==8'h5c&&c[10:8]==2;
endmodule
