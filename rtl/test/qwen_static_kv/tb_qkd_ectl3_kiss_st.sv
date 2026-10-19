`timescale 1ns/1ps
`ifndef KVD_ECSTMUT
`define KVD_ECSTMUT 0
`endif
// RTL-BUILD-KV/ASTK 2026-10-18: exact lockstep of the static ECTL frame on the credit-free ASTK ABI (qkd_ectl3_kiss_st:
// C = qkd_ectl_c_st without nb_cr / so[423:412]) against the current frame qkd_ectl3_kiss_s, on the static K stimulus of
// tb_qkd_static_k_issuer (T 8192 and 3 more contexts, 36 layers each stack/engine pair below, K responses from the bench's
// fixed-latency row model) with random q words, exp_done, e words and head score returns.  Every edge compares e0..e3,
// t0 / t1, the K request bundle, the issuer fault and so (B 413 b vs A {so[424], so[411:0]}); A's dropped outputs must be
// constant: nb_valid / nb_beat / nb_g / nb_gam (so[421:412]) = 0 and v_done (so[423]) = 0, and the head decision field
// (t[1039:1028]) = 0.  k_done (so[422]) toggles but has no reader (qkd_astk_ep_cal / ep_s do not take it).
// Mutants: +define+KVD_ECSTMUT=1 (so fault <- k_done), 2 (q word one si bit low): must FAIL.
module tb_qkd_ectl3_kiss_st;
    // KV-ECTL4 2026-10-18: RL / QK = the frame's RESPONSE_LAT / QK_ISSUE_AGE (die: 80 / 91; default the unit 2 / 34)
    parameter integer RL=2, QK=34;
    reg ck=0,rst_n=0;
    always #0.5 ck=~ck;
    reg [632:0] si=0;
    integer ctx=8192,stack=1,engine=3;
    wire [4:0] cfg=5'(engine*4+stack);
    reg [5:0] layer_cur=0;
    reg rsp_valid=0;reg [1023:0] rsp_data=0;reg [13:0] rsp_t=0;
    reg rsp_v=0;reg [15:0] rsp_epoch=0;reg [5:0] rsp_layer=0;
    reg [33:0] s0=0,s1=0,s2=0,s3=0;
    wire [424:0] so_a;wire [412:0] so_b;
    wire [1558:0] t0_a,t1_a,t0_b,t1_b;
    wire [15:0] e_a[0:3],e_b[0:3];
    wire rqv_a,rqv_b,rqvv_a,rqvv_b,f_a,f_b;wire [13:0] rqt_a,rqt_b;wire [15:0] rqe_a,rqe_b;wire [5:0] rql_a,rql_b;
    qkd_ectl3_kiss_s #(.RESPONSE_LAT(RL),.QK_ISSUE_AGE(QK)) ua (
        .ck({3{ck}}),.rst_n(rst_n),.cfg(cfg),.e0(e_a[0]),.e1(e_a[1]),.e2(e_a[2]),.e3(e_a[3]),
        .s0(s0),.s1(s1),.s2(s2),.s3(s3),.t0(t0_a),.t1(t1_a),.kgo(si[0]),.epoch(16'h1234),.layer(layer_cur),
        .req_valid(rqv_a),.req_t(rqt_a),.req_v(rqvv_a),.req_epoch(rqe_a),.req_layer(rql_a),
        .rsp_valid(rsp_valid),.rsp_data(rsp_data),.rsp_t(rsp_t),.rsp_v(rsp_v),.rsp_epoch(rsp_epoch),.rsp_layer(rsp_layer),
        .fault(f_a),.si({1'b0,si}),.so(so_a));
    qkd_ectl3_kiss_st #(.RESPONSE_LAT(RL),.QK_ISSUE_AGE(QK)) ub (
        .ck({3{ck}}),.rst_n(rst_n),.cfg(cfg),.e0(e_b[0]),.e1(e_b[1]),.e2(e_b[2]),.e3(e_b[3]),
        .s0(s0),.s1(s1),.s2(s2),.s3(s3),.t0(t0_b),.t1(t1_b),.kgo(si[0]),.epoch(16'h1234),.layer(layer_cur),
        .req_valid(rqv_b),.req_t(rqt_b),.req_v(rqvv_b),.req_epoch(rqe_b),.req_layer(rql_b),
        .rsp_valid(rsp_valid),.rsp_data(rsp_data),.rsp_t(rsp_t),.rsp_v(rsp_v),.rsp_epoch(rsp_epoch),.rsp_layer(rsp_layer),
        .fault(f_b),.si(si),.so(so_b));
    function automatic [1023:0] rowf(input integer n);
        for(integer j=0;j<32;j=j+1) rowf[j*32+:32]=32'h42000000 ^ (n*32'h10203) ^ j;
    endfunction
    reg [1023:0] response[0:1023];
    reg rv[0:1023];
    reg [13:0] tags[0:1023];
    integer cyc,nbridge,mism=0,edges=0,kdone=0,kreq=0,qwords=0,seed=5,ci;
    always @(negedge ck) if(rst_n) begin
        edges=edges+1;
        if(so_b!=={so_a[424],so_a[411:0]} || so_a[421:412]!==0 || so_a[423]!==0 || t0_b!==t0_a || t1_b!==t1_a ||
           t0_a[1039:1028]!==0 || t1_a[1039:1028]!==0 || e_b[0]!==e_a[0] || e_b[1]!==e_a[1] || e_b[2]!==e_a[2] || e_b[3]!==e_a[3] ||
           rqv_b!==rqv_a || rqt_b!==rqt_a || rqvv_b!==rqvv_a || rqe_b!==rqe_a || rql_b!==rql_a || f_b!==f_a) begin
            mism=mism+1;
            if(mism<6)$display("MISMATCH edge=%0d so=%b nb0=%b vd0=%b t0=%b t1=%b lt0=%b e=%b req=%b f=%b",edges,so_b==={so_a[424],so_a[411:0]},
                so_a[421:412]===0,so_a[423]===0,t0_b===t0_a,t1_b===t1_a,t0_a[1039:1028]===0,
                {e_b[0],e_b[1],e_b[2],e_b[3]}==={e_a[0],e_a[1],e_a[2],e_a[3]},{rqv_b,rqt_b,rqvv_b,rqe_b,rql_b}==={rqv_a,rqt_a,rqvv_a,rqe_a,rql_a},f_b===f_a);
        end
        if(so_a[422])kdone=kdone+1;
        if(t0_a[1040])qwords=qwords+1;
    end
    initial begin
        repeat(6) @(negedge ck);rst_n=1;
        repeat(80) @(negedge ck);
        for(ci=0;ci<4;ci=ci+1)begin
        ctx=(ci==0)?8192:((ci==1)?1000:((ci==2)?300:5000));
        for(integer layer_idx=0;layer_idx<((ci==0)?8:3);layer_idx=layer_idx+1)begin
        layer_cur=6'(layer_idx+ci);nbridge=0;
        for(integer j=0;j<1024;j=j+1)begin rv[j]=0;response[j]=0;tags[j]=0;end
        for(cyc=0;cyc<500;cyc=cyc+1) begin
            si=0;si[14:1]=14'(ctx);si[17:15]=cyc%8;
            if(cyc==0)si[0]=1;
            if(cyc>=1&&cyc<=32)begin si[18]=1;si[24:19]=cyc-1;end
            for(integer w=0;w<16;w=w+1)si[25+32*w+:32]=$random(seed);
            si[537+:32]=$random(seed);si[569+:32]=$random(seed);si[601+:32]=$random(seed);
            s0={$random(seed)}%(1<<30);s1=$random(seed);s2=$random(seed);s3={2'b00,32'($random(seed))};
            rsp_valid=rv[cyc];rsp_data=response[cyc];rsp_t=tags[cyc];
            rsp_epoch=16'h1234;rsp_layer=layer_cur;rsp_v=0;
            @(posedge ck);
            if(rqv_a)begin
                rv[cyc+RL]=1;response[cyc+RL]=rowf(nbridge)^{32{32'($random(seed))}};tags[cyc+RL]=rqt_a;nbridge=nbridge+1;kreq=kreq+1;
            end
            @(negedge ck);
        end
        end
        end
        if(mism==0 && kreq>0 && kdone>0 && qwords>0)
            $display("PASS qkd_ectl3_kiss_st lockstep vs qkd_ectl3_kiss_s: RL %0d QK %0d, %0d edges, K requests %0d, k_done edges %0d, q words %0d, mut %0d",RL,QK,edges,kreq,kdone,qwords,`KVD_ECSTMUT);
        else $display("FAIL qkd_ectl3_kiss_st mismatches=%0d kreq=%0d kdone=%0d q=%0d mut %0d",mism,kreq,kdone,qwords,`KVD_ECSTMUT);
        $finish;
    end
endmodule
