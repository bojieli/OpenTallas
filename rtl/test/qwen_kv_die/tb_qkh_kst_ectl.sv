`timescale 1ns/1ps
// KV-KT-E0 2026-11-18 (FABLE-FIX-KV-HG fix #2): the consumer of the head score under the kt input stations.
// Five control tiles (qkd_ectl3_epoch_direct_s, STATIC_QK, the tb_qkd_ectl3_h13 K pass: 256 K rows through the mapped
// SRAM), each with ONE native head attached directly (head id +HID=0..3, on the tile's t0 / e word of that id; its score
// {g_f, sc_f, sc_d} drives the tile's four score inputs, so the bench builds 5 heads, not 20; score tag depth HXK = 8 +
// the head's extra edges):
//   sys 0   ot_qkh_head_native_r4_s_lk                    HXK 8    today
//   sys 1   ot_qkh_head_native_r4_s_lk_kst KT_ST 0        HXK 8    must equal sys 0 on every edge, every so / t / e / rq bit
//   sys 2   ot_qkh_head_native_r4_s_lk_kst KT_ST 2        HXK 10   must equal sys 0 two edges earlier on the score fields of
//           so (sc_valid, sc_addr, sc_data under sc_valid, lmax, lmax_any, fault): 256 tags, the same score words under
//           the same tag; k_done is the tile's last K ISSUE (not a score event) and stays on its edge;
//           what the tile sends the heads and the store (t0, t1, e, rq) stays on the same edge
//   sys 3   KT_ST 2, HXK 8 (stations WITHOUT the HXK move)          negative control: tags meet the wrong scores
//   sys 4   KT_ST 2 on lanes 2..15 only (KT_MUT 1), HXK 10          negative control: the 14-lane parent-only form
// so the law the die applies is HXK += KT_ST (and, downstream of so, the attention calendar D_QK += KT_ST: the QK half
// of the calendar LMAX .. HUB_PUB moves with the score; tools/qwen_kv_die/kv_head_kst.py).
// Every other so field is classified (static, same edge, or moved with the score) and printed; none may be neither.
module tb_qkh_kst_ectl;
    localparam integer KT=2,NS=5;
    reg ck=0,rst_n=0;
    always #0.5 ck=~ck;
    reg [633:0] si=0;
    reg [1024:0] rs=0;
    wire [424:0] so [0:NS-1];
    wire [16:0] rq [0:NS-1];
    wire [1558:0] t0 [0:NS-1];wire [1558:0] t1 [0:NS-1];
    wire [63:0] e [0:NS-1];
    reg [1:0] hid=2'd0;
    genvar s;
    generate for(s=0;s<NS;s=s+1)begin:g_sys
        wire [33:0] sc1;
        wire [135:0] sc={4{sc1}};
        qkd_ectl3_epoch_direct_s #(.STATIC_QK(1),.QK_ISSUE_AGE(34),.ROW_RETURN_LAT(21),.HXK((s==2 || s==4) ? 8+KT : 8)) u_ectl (
            .ck({3{ck}}),.rst_n(rst_n),.cfg(5'b01101),.e0(e[s][0+:16]),.e1(e[s][16+:16]),.e2(e[s][32+:16]),.e3(e[s][48+:16]),
            .s0(sc[0+:34]),.s1(sc[34+:34]),.s2(sc[68+:34]),.s3(sc[102+:34]),.t0(t0[s]),.t1(t1[s]),.rq(rq[s]),.rs(rs),.si(si),.so(so[s]));
        wire [1558:0] t=hid[1]?t1[s]:t0[s];
        wire [15:0] eh=e[s][16*hid+:16];
`define KSE_P .ck_front({4{ck}}),.ck_score(ck),.ck_kt(ck),.ck_stin({16{ck}}),.ck_stk({16{ck}}),.ck_lane({16{ck}}),.rst_n(rst_n), \
            .c_in(t[3:0]),.row_in(t[1027:4]),.e_in(eh),.lt_in(t[1039:1028]),.hid(hid),.q_valid_in(t[1040]), \
            .q_beat_in(t[1046:1041]),.q_data_in(t[1558:1047]),.sc_d(sc1[31:0]),.sc_f(sc1[32]),.g_f(sc1[33])
        if(s==0)begin:g ot_qkh_head_native_r4_s_lk #(.Q_FP32(1)) u_head(`KSE_P); end
        else if(s==1)begin:g ot_qkh_head_native_r4_s_lk_kst #(.Q_FP32(1),.KT_ST(0)) u_head(`KSE_P); end
        else begin:g ot_qkh_head_native_r4_s_lk_kst #(.Q_FP32(1),.KT_ST(KT),.KT_MUT(s==4 ? 1 : 0)) u_head(`KSE_P); end
    end endgenerate
    // K row = 128 E4M3 codes; exponent bit 6 kept 0 so no code is the NaN S.1111.111 the lane products refuse (a clean
    // pass has no fault anywhere; the fault path is exercised by tb_qkh_head_kst)
    function automatic [1023:0] rowf(input integer n);
        reg [31:0] x;
        for(integer j=0;j<128;j=j+1)begin
            x=(n*32'h9E3779B1)^(j*32'h85EBCA6B);x=x^(x>>15);x=x*32'h2C1B3C6D;x=x^(x>>12);
            rowf[j*8+:8]=x[7:0]&8'hBF;
        end
    endfunction
    reg [1023:0] response[0:1023];
    reg rv[0:1023];
    // so fields: name, hi, lo
    localparam integer NF=12;
    integer fhi [0:NF-1];integer flo [0:NF-1];string fnm [0:NF-1];
    integer m0 [0:NF-1];integer m2 [0:NF-1];integer act [0:NF-1];
    reg [424:0] hist [0:7];
    wire [424:0] so_exp=hist[KT-1];
    integer cyc,nreq=0,nsc [0:NS-1],i,f,seed=7,seed0=7,w,m1=0,mx=0,nzdata=0,ok,neg3=0,neg4=0,hidv=0;
    integer hgf=0,hsf=0,ffirst=-1,edge_n=0;
    reg [31:0] qmask=32'h807fffff;
    reg [424:0] dmask;
    localparam [424:0] SCM=((425'd1<<399)-425'd1)<<13;    // so[411:13] = sc_valid, sc_addr, sc_data, lmax, lmax_any
    always @(negedge ck) if(rst_n)begin
        if(so[1]!==so[0] || t0[1]!==t0[0] || t1[1]!==t1[0] || e[1]!==e[0] || rq[1]!==rq[0])begin m1=m1+1;if(m1<4)$display("MISMATCH sys1 (KT_ST 0) vs sys0 at %0t",$time);end
        if(t0[2]!==t0[0] || t1[2]!==t1[0] || e[2]!==e[0] || rq[2]!==rq[0])begin mx=mx+1;if(mx<4)$display("MISMATCH sys2 t/e/rq moved at %0t",$time);end
        for(f=0;f<NF;f=f+1)begin
            dmask=((425'd1<<(fhi[f]-flo[f]+1))-425'd1)<<flo[f];
            // sc_data is a score only under sc_valid (the tile's own tag time): untagged words are not compared
            if(f==4 && !so[2][13] && !so[0][13])begin end
            else if((so[2]&dmask)!==(so[0]&dmask))m0[f]=m0[f]+1;
            if(f==4 && !so[2][13] && !so_exp[13])begin end
            else if((so[2]&dmask)!==(so_exp&dmask))begin m2[f]=m2[f]+1;if(f>=2 && f<=6 && m2[f]<3)$display("MISMATCH sys2 %s vs sys0 -%0d at %0t: %h vs %h",fnm[f],KT,$time,(so[2]&dmask)>>flo[f],(so_exp&dmask)>>flo[f]);end
            if((so[0]&dmask)!=0)act[f]=act[f]+1;
        end
        // negative controls: neither the same-edge nor the moved score fields
        if(so[3][13] && (so[3]&SCM)!==(so[0]&SCM) && (so[3]&SCM)!==(so_exp&SCM))neg3=neg3+1;
        if((so[4][13] || so_exp[13]) && (so[4]&SCM)!==(so_exp&SCM))neg4=neg4+1;
        for(i=0;i<NS;i=i+1)if(so[i][13])nsc[i]=nsc[i]+1;
        if(so[0][13] && so[0][153:26]!=0)nzdata=nzdata+1;
        edge_n=edge_n+1;
        if(g_sys[0].sc1[33])hgf=hgf+1;
        if(g_sys[0].sc1[32])hsf=hsf+1;
        if(so[0][424] && ffirst<0)begin ffirst=edge_n;$display("INFO first tile fault at edge %0d: head g_f edges %0d sc_f edges %0d",edge_n,hgf,hsf);end
        for(i=7;i>0;i=i-1)hist[i]=hist[i-1];
        hist[0]=so[0];
    end
    initial begin
        if($value$plusargs("SEED=%d",seed))begin end
        if($value$plusargs("HID=%d",hidv))begin end
        if($value$plusargs("QMASK=%h",qmask))begin end
        seed0=seed;
        hid=2'(hidv);
        fnm[0]="er_valid";fhi[0]=0;flo[0]=0;      fnm[1]="er_addr";fhi[1]=12;flo[1]=1;
        fnm[2]="sc_valid";fhi[2]=13;flo[2]=13;    fnm[3]="sc_addr";fhi[3]=25;flo[3]=14;
        fnm[4]="sc_data";fhi[4]=153;flo[4]=26;    fnm[5]="lmax";fhi[5]=409;flo[5]=154;
        fnm[6]="lmax_any";fhi[6]=411;flo[6]=410;  fnm[7]="nb_valid";fhi[7]=412;flo[7]=412;
        fnm[8]="nb_beat_g_gam";fhi[8]=421;flo[8]=413; fnm[9]="k_done";fhi[9]=422;flo[9]=422;
        fnm[10]="v_done";fhi[10]=423;flo[10]=423; fnm[11]="fault";fhi[11]=424;flo[11]=424;
        for(i=0;i<NF;i=i+1)begin m0[i]=0;m2[i]=0;act[i]=0;end
        for(i=0;i<NS;i=i+1)nsc[i]=0;
        for(i=0;i<8;i=i+1)hist[i]=0;
        for(integer j=0;j<1024;j=j+1) begin rv[j]=0;response[j]=0;end
        repeat(6) @(negedge ck);rst_n=1;
        repeat(80) @(negedge ck);
        for(cyc=0;cyc<560;cyc=cyc+1) begin
            si=0;si[14:1]=8192;si[17:15]=cyc%8;
            if(cyc==0)si[0]=1;
            if(cyc>=1&&cyc<=32)begin si[18]=1;si[24:19]=cyc-1;for(w=0;w<16;w=w+1)si[25+32*w+:32]=32'h3c000000^($random(seed)&qmask);end
            rs={response[cyc],rv[cyc]};
            @(posedge ck);
            if(rq[0][0])begin rv[cyc+16]=1;response[cyc+16]=rowf(nreq+seed0);nreq=nreq+1;end
            @(negedge ck);
        end
        ok=1;
        for(f=0;f<NF;f=f+1)begin
            $display("FIELD %-14s active %0d  mismatch same-edge %0d  mismatch -%0d edges %0d  -> %s",fnm[f],act[f],m0[f],KT,m2[f],
                     (m0[f]==0 && m2[f]==0)?"static":(m0[f]==0)?"same edge":(m2[f]==0)?"moved with the score":"NEITHER");
            if(m0[f]!=0 && m2[f]!=0)ok=0;
        end
        for(f=2;f<=6;f=f+1)if(m2[f]!=0)ok=0;                      // the score fields follow the law
        for(f=2;f<=5;f=f+1)if(m0[f]==0)ok=0;                      // ... and really moved (not static)
        if(m0[9]!=0 || act[9]==0)ok=0;                            // k_done: issue side, same edge
        if(m1!=0 || mx!=0)ok=0;
        if(nreq!=256 || nsc[0]!=256 || nsc[1]!=256 || nsc[2]!=256 || nzdata<200)ok=0;
        if(so[0][424] || so[1][424] || so[2][424] || !so[0][422] || !so[2][422])ok=0;
        if(neg3==0 || neg4==0)ok=0;
        $display("INFO head g_f edges %0d sc_f edges %0d first tile fault edge %0d qmask %h",hgf,hsf,ffirst,qmask);
        $display("INFO req %0d scores %0d/%0d/%0d/%0d/%0d nonzero score words %0d  negative controls off the law: no-HXK-move %0d edges, 14-lane %0d edges  faults %b%b%b%b%b",
                 nreq,nsc[0],nsc[1],nsc[2],nsc[3],nsc[4],nzdata,neg3,neg4,so[0][424],so[1][424],so[2][424],so[3][424],so[4][424]);
        if(ok)$display("PASS qkh_kst_ectl KT_ST 2 HXK 8+2: 256 tags, score words equal the source head 2 edges earlier (sc / lmax), t / e / rq same edge, KT_ST 0 identical, 2/2 negative controls off the law; head id %0d seed %0d",hidv,seed0);
        else $display("FAIL qkh_kst_ectl head id %0d seed %0d: sys1 %0d t/e/rq %0d req %0d scores %0d/%0d/%0d nz %0d neg %0d/%0d",hidv,seed0,m1,mx,nreq,nsc[0],nsc[1],nsc[2],nzdata,neg3,neg4);
        $finish;
    end
endmodule
