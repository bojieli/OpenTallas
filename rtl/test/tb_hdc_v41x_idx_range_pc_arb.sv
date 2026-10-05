`timescale 1ns/1ps
// One HBM stack, four quarter ranges sharing its 32 physical PCs. Raw
// prefix keys are dropped here; the separate quarter collector owns that
// operation in the integrated four-stack path.
module tb_hdc_v41x_idx_range_pc_arb #(
    parameter integer NKEYS=1040, WB=32, GA=24, QUANTUM=1,
    parameter integer QD=64, RW=16
);
    localparam integer NPC=32,AW=28,HW=20,NW=30,TAGW=16,LENW=4,BEATW=4,DW=256;
    reg clk=0,rst_n=0,cmd_v=0;
    always #5 clk=~clk;
    wire [16*NW-1:0] first_local,count;
    wire [16*HW-1:0] base_block;
    wire [159:0] skip;
    ot_hdc_v41x_idx_quarter_ranges #(.NW(NW),.HW(HW)) geom (
        .i_nkeys(NW'(NKEYS)),.i_base_block(HW'(0)),
        .o_first_local(first_local),.o_count(count),
        .o_base_block(base_block),.o_skip(skip));
    wire [4*NPC-1:0] vreq,rreq,vrsp,rrsp;
    wire [4*NPC*AW-1:0] areq;
    wire [4*NPC*LENW-1:0] lreq;
    wire [4*NPC*TAGW-1:0] treq,trsp;
    wire [4*NPC*BEATW-1:0] brsp;
    wire [4*NPC*DW-1:0] drsp;
    wire [3:0] busy,ovalid;
    wire [4*16-1:0] okv;
    wire [4*16*544-1:0] okey;
    wire [4*48-1:0] keys,beats;
    for(genvar q=0;q<4;q=q+1) begin:g_range
        ot_hdc_v41x_idx_kstream_range #(.NPC(NPC),.WB(WB),.GA(GA),
            .AW(AW),.HW(HW),.TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.DW(DW)) ks (
            .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v && count[q*NW +: NW]!=0),
            .cmd_base(base_block[q*HW +: HW]),.cmd_skip(skip[q*10 +: 10]),
            .cmd_nkeys((HW+10)'(count[q*NW +: NW])),.busy(busy[q]),
            .req_v(vreq[q*NPC +: NPC]),.req_rdy(rreq[q*NPC +: NPC]),
            .req_addr(areq[q*NPC*AW +: NPC*AW]),
            .req_len(lreq[q*NPC*LENW +: NPC*LENW]),
            .req_tag(treq[q*NPC*TAGW +: NPC*TAGW]),
            .rsp_v(vrsp[q*NPC +: NPC]),.rsp_rdy(rrsp[q*NPC +: NPC]),
            .rsp_tag(trsp[q*NPC*TAGW +: NPC*TAGW]),
            .rsp_beat(brsp[q*NPC*BEATW +: NPC*BEATW]),
            .rsp_data(drsp[q*NPC*DW +: NPC*DW]),
            .o_valid(ovalid[q]),.o_ready(1'b1),
            .o_kv(okv[q*16 +: 16]),.o_key(okey[q*16*544 +: 16*544]),
            .cnt_keys_streamed(keys[q*48 +: 48]),
            .cnt_hbm_beats(beats[q*48 +: 48]));
    end
    wire [NPC-1:0] hvreq,hrreq,hvrsp,hrrsp;
    wire [NPC*AW-1:0] hareq;
    wire [NPC*LENW-1:0] hlreq;
    wire [NPC*TAGW-1:0] htreq,htrsp;
    wire [NPC*BEATW-1:0] hbrsp;
    wire [NPC*DW-1:0] hdrsp;
    wire [31:0] grants;
    ot_hdc_v41x_idx_range_pc_arb #(.NPC(NPC),.AW(AW),.LENW(LENW),
        .TAGW(TAGW),.BEATW(BEATW),.DW(DW),.QUANTUM(QUANTUM)) arb (
        .clk(clk),.rst_n(rst_n),.i_req_v(vreq),.i_req_rdy(rreq),
        .i_req_addr(areq),.i_req_len(lreq),.i_req_tag(treq),
        .h_req_v(hvreq),.h_req_rdy(hrreq),.h_req_addr(hareq),
        .h_req_len(hlreq),.h_req_tag(htreq),
        .h_rsp_v(hvrsp),.h_rsp_rdy(hrrsp),.h_rsp_tag(htrsp),
        .h_rsp_beat(hbrsp),.h_rsp_data(hdrsp),
        .o_rsp_v(vrsp),.o_rsp_rdy(rrsp),.o_rsp_tag(trsp),
        .o_rsp_beat(brsp),.o_rsp_data(drsp),.dbg_grants(grants));
    ot_hdc_v41x_idx_hbm #(.NPC(NPC),.AW(AW),.DW(DW),.MEM_WORDS(1),
        .TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.QD(QD),.RQD(32),.RW(RW),
        .REFPB(3),.MEM_MODE(1)) hm (
        .clk(clk),.rst_n(rst_n),.req_v(hvreq),.req_rdy(hrreq),
        .req_addr(hareq),.req_len(hlreq),.req_tag(htreq),
        .req_we({NPC{1'b0}}),.req_wdata({NPC*DW{1'b0}}),
        .req_wstrb({NPC*32{1'b0}}),.wr_done(),
        .rsp_v(hvrsp),.rsp_rdy(hrrsp),.rsp_tag(htrsp),
        .rsp_beat(hbrsp),.rsp_data(hdrsp));
    function automatic [255:0] pat(input [AW-1:0] sec);
        for(integer w=0;w<8;w=w+1)
            pat[32*w +:32]=(sec*32'd8+w)*32'h9E3779B1 ^ 32'h5bd1e995;
    endfunction
    function automatic [543:0] expkey(input integer key);
        integer sb,pos;
        reg [AW-1:0] sc,cs;
        reg [255:0] sw;
        begin
            sb=key/1024;pos=key%1024;
            sc=AW'(2176*sb+pos/8);
            cs=AW'(2176*sb+128+2*pos);
            sw=pat(sc);
            expkey={sw[32*(pos%8) +:32],pat(cs+1),pat(cs)};
        end
    endfunction
    integer seen[0:3],checked[0:3];
    integer cycle=0,q,l,key,hits,total_checked,total_beats,total_expected;
    longint hbm_act,hbm_hit,hbm_conf,hbm_ref;
    integer idle_pc_slots=0,blocked_req_slots=0,blocked_rsp_slots=0;
    integer context_switches=0;
    integer no_req_c,blocked_req_c,blocked_rsp_c,switch_c;
    reg [1:0] last_ctx[0:NPC-1];
    reg last_ctx_valid[0:NPC-1];
    initial for(integer j=0;j<4;j=j+1) begin seen[j]=0;checked[j]=0;end
    initial for(integer j=0;j<NPC;j=j+1) begin last_ctx[j]=0;last_ctx_valid[j]=0;end
    always @(posedge clk) begin
        cycle<=cycle+1;
        if(cycle>200000) $fatal(1,"range arb timeout n=%0d wb=%0d ga=%0d",NKEYS,WB,GA);
        if(rst_n) begin
            no_req_c=0;blocked_req_c=0;blocked_rsp_c=0;switch_c=0;
            for(integer p=0;p<NPC;p=p+1) begin
                if(!hvreq[p]) no_req_c=no_req_c+1;
                if(hvreq[p] && !hrreq[p]) blocked_req_c=blocked_req_c+1;
                if(hvrsp[p] && !hrrsp[p]) blocked_rsp_c=blocked_rsp_c+1;
                if(hvreq[p] && hrreq[p]) begin
                    if(last_ctx_valid[p] && last_ctx[p]!=htreq[p*TAGW+TAGW-4 +:2])
                        switch_c=switch_c+1;
                    last_ctx[p]<=htreq[p*TAGW+TAGW-4 +:2];
                    last_ctx_valid[p]<=1;
                end
            end
            idle_pc_slots<=idle_pc_slots+no_req_c;
            blocked_req_slots<=blocked_req_slots+blocked_req_c;
            blocked_rsp_slots<=blocked_rsp_slots+blocked_rsp_c;
            context_switches<=context_switches+switch_c;
        end
        if(rst_n) for(q=0;q<4;q=q+1) if(ovalid[q]) begin
            hits=0;
            for(l=0;l<16;l=l+1) if(okv[q*16+l]) begin
                key=((int'(first_local[q*NW +: NW])>>10)<<10)+seen[q]+l;
                if(key>=int'(first_local[q*NW +: NW]) &&
                   key<int'(first_local[q*NW +: NW]+count[q*NW +: NW])) begin
                    if(okey[(q*16+l)*544 +:544] !== expkey(key))
                        $fatal(1,"range arb mismatch q=%0d key=%0d",q,key);
                    hits=hits+1;
                end
            end
            checked[q]<=checked[q]+hits;
            seen[q]<=seen[q]+16;
        end
    end
    initial begin
        repeat(4) @(negedge clk);rst_n=1;
        @(negedge clk);cmd_v=1;
        @(negedge clk);cmd_v=0;
        wait(busy==0);
        repeat(3) @(posedge clk);
        total_checked=0;total_beats=0;total_expected=0;
        hbm_act=0;hbm_hit=0;hbm_conf=0;hbm_ref=0;
        for(integer p=0;p<NPC;p=p+1) begin
            hbm_act=hbm_act+hm.st_act[p];
            hbm_hit=hbm_hit+hm.st_hit[p];
            hbm_conf=hbm_conf+hm.st_conf[p];
            hbm_ref=hbm_ref+hm.st_ref[p];
        end
        for(integer j=0;j<4;j=j+1) begin
            total_checked=total_checked+checked[j];
            total_beats=total_beats+int'(beats[j*48 +:48]);
            total_expected=total_expected+2*int'(count[j*NW +:NW])+
                ((int'(skip[j*10 +:10])+int'(count[j*NW +:NW])+7)/8)-
                (int'(skip[j*10 +:10])/8);
            if(checked[j]!=int'(count[j*NW +:NW]))
                $fatal(1,"range arb q=%0d checked=%0d expected=%0d",j,checked[j],count[j*NW +:NW]);
        end
        if(total_beats!=total_expected)
            $fatal(1,"range arb sectors=%0d expected=%0d",total_beats,total_expected);
        $display("V41X_RANGE_ARB_PASS n=%0d wb=%0d ga=%0d quantum=%0d qd=%0d rw=%0d checked=%0d sectors=%0d cycles=%0d grants=%0d",
                 NKEYS,WB,GA,QUANTUM,QD,RW,total_checked,total_beats,cycle,grants);
        $display("V41X_RANGE_ARB_DIAG idle_pc_slots=%0d blocked_req_slots=%0d blocked_rsp_slots=%0d context_switches=%0d",
                 idle_pc_slots,blocked_req_slots,blocked_rsp_slots,context_switches);
        $display("V41X_RANGE_ARB_HBM act=%0d hit=%0d conf=%0d ref=%0d bp=%0d rd_lat_sum_ps=%0d rd_lat_max_ps=%0d",
                 hbm_act,hbm_hit,hbm_conf,hbm_ref,hm.st_bp_cycles,hm.st_rd_lat_sum,hm.st_rd_lat_max);
        $finish;
    end
endmodule
