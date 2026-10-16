// YB_STAGE 1 (HC-COLUMN 10-16, coordinator-approved): the y beat (16 b per ctnl lane tile) is relayed one cycle inside
// ctra column c (its own x-column's four ctnl tiles, yb_loc -> yb_fwd) so no y join leaves its 144 um column + one
// neighbour hop; every fv-domain input (rst_in, tid, last, fv, fdx, cs, flags) gets a matching pin register, so the whole
// engine runs exactly one cycle later. rd_in / rv_in / hrq stay unregistered: in the chain they already arrive one cycle
// later (far-tile origination and the bank round trip shift with the engine), so the return gains +1 fixed cycle once
// per HC chain, bank requests +1. Default 0 = the 82424ff85 successor unchanged.
// Four actual local return engines, each with a distinct clock entry and registered payload pins.
// Return data/valid gain exactly one fixed cycle. Bank requests retain the original epoch.
// BF16 y dependencies remain real and cross columns; this is not claimed as a free transpose.
// All four clock roots require the same phase; COLUMN0 owns the merged-valid register. Canonical compiler/slot adoption is separate.

module ot_s81_hc_ctra_column #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, CHAIN_STEP = AL, READ_STAGE = 0, COLUMN = 0, YB_STAGE = 0
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire [7:0]             tid,
    input  wire                   last,
    input  wire [S_RD+4:0]        fv,
    input  wire [O_D-1:0]         fdx,
    input  wire [S_RT+3:0]        rv_in,
    input  wire [P_D-1:0]         rdh_in,
    input  wire [256*SH-1:0]      rdp_in,
    output wire [S_RT+3:0]        rvm,
    input  wire [2:0]             peer_fault, peer_hnz,
    input  wire [63:0]            yb_loc,           // YB_STAGE: own x-column lanes {n=COLUMN+12,+8,+4,COLUMN} 16 b each
    output wire [63:0]            yb_fwd,           // YB_STAGE: the relayed yb_loc (one cycle) for the peers / ctrb
    input  wire [191:0]           yb_peer,          // YB_STAGE: the other three columns' yb_fwd, ascending column

    output wire [128*SH-1:0]      rdm,
    output wire [16*S_RT-1:0]     rq_q,
    output wire                   hs_run,
    output wire [15:0]            hs_c,
    output wire [16*S_RT-1:0]     rq_q_c1, rq_q_c2, rq_q_c3,
    output wire                  hs_run_c1, hs_run_c2, hs_run_c3,
    output wire [15:0]           hs_c_c1, hs_c_c2, hs_c_c3,
    input  wire [2*64*SH-1:0]     hrq_n, hrq_s,     // [lane n (or n - 8)][slot s] 64 b
    input  wire [8*16-1:0]        yb_n, yb_s,
    input  wire [4*32-1:0]        cs,
    input  wire [1:0]             nflt_n, nflt_s,
    input  wire                   hov_d,
    output reg                    flag_fault, flag_hnz,
    output reg [P_D-1:0]           header_delay,
    input  wire                   hnz_n, hnz_s, pflt_n, pflt_s   // ctpl half 0 (N) / half 1 (S), group g
);
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FXW = O_D + S_RD * 512;
    localparam integer SH = S_RT / 2, P_D = S_RT + 8 * S_RT + 16 * S_RT + 8, RDW = P_D + 512 * S_RT, WA = P_D + 512 * SH;

    initial if(S_RT!=4 || COLUMN<0 || COLUMN>3) $fatal(1,"return column requires S_RT4 and column0..3");
    // fv-domain view of the inputs: pin registers under YB_STAGE, the raw pins otherwise
    wire              e_rst;
    wire [7:0]        e_tid;
    wire              e_last, e_hov;
    wire [S_RD+4:0]   e_fv;
    wire [O_D-1:0]    e_fdx;
    wire [4*32-1:0]   e_cs;
    wire [1:0]        e_nflt_n, e_nflt_s;
    wire              e_hnz_n, e_hnz_s, e_pflt_n, e_pflt_s;
    wire [8*16-1:0]   e_yb_n, e_yb_s;
    generate if(YB_STAGE) begin : g_ybstage
        reg rst_q, last_q, hov_q, hnz_nq, hnz_sq, pflt_nq, pflt_sq;
        reg [7:0] tid_q; reg [S_RD+4:0] fv_q; reg [O_D-1:0] fdx_q; reg [4*32-1:0] cs_q; reg [1:0] nflt_nq, nflt_sq;
        reg [63:0] yb_r;
        always @(posedge clk) begin
            rst_q<=rst_in; tid_q<=tid; last_q<=last; fv_q<=fv; fdx_q<=fdx; cs_q<=cs; hov_q<=hov_d;
            nflt_nq<=nflt_n; nflt_sq<=nflt_s; hnz_nq<=hnz_n; hnz_sq<=hnz_s; pflt_nq<=pflt_n; pflt_sq<=pflt_s;
            yb_r<=yb_loc;
        end
        assign yb_fwd=yb_r;
        wire [255:0] yb_all;
        for(genvar n=0;n<16;n=n+1) begin : g_yb
            localparam integer CC=n%4, K=n/4, P=(CC<COLUMN)?CC:CC-1;
            if(CC==COLUMN) begin : g_own
                assign yb_all[16*n +:16]=yb_r[16*K +:16];
            end else begin : g_peer
                assign yb_all[16*n +:16]=yb_peer[64*P+16*K +:16];
            end
        end
        assign {e_yb_s,e_yb_n}=yb_all;
        assign e_rst=rst_q; assign e_tid=tid_q; assign e_last=last_q; assign e_fv=fv_q; assign e_fdx=fdx_q; assign e_cs=cs_q;
        assign e_hov=hov_q; assign e_nflt_n=nflt_nq; assign e_nflt_s=nflt_sq; assign e_hnz_n=hnz_nq; assign e_hnz_s=hnz_sq;
        assign e_pflt_n=pflt_nq; assign e_pflt_s=pflt_sq;
    end else begin : g_direct
        assign yb_fwd='0;
        assign e_rst=rst_in; assign e_tid=tid; assign e_last=last; assign e_fv=fv; assign e_fdx=fdx; assign e_cs=cs;
        assign e_hov=hov_d; assign e_nflt_n=nflt_n; assign e_nflt_s=nflt_s; assign e_hnz_n=hnz_n; assign e_hnz_s=hnz_s;
        assign e_pflt_n=pflt_n; assign e_pflt_s=pflt_s; assign e_yb_n=yb_n; assign e_yb_s=yb_s;
    end endgenerate
    wire [S_RT+3:0] rv_base;
    wire [3:0] fault_flags = {peer_fault,flag_fault};
    wire [3:0] hnz_flags = {peer_hnz,flag_hnz};
    generate if(COLUMN==0) begin : g_merge
        reg rr_merge;
        reg [S_RT+3:0] rv_delay;
        always @(posedge clk) rr_merge<=e_rst;
        always @(posedge clk or negedge rr_merge)
            if(!rr_merge) rv_delay<='0;
            else begin
                rv_delay<=rv_base;
                rv_delay[S_RT+2]<=rv_base[S_RT+2] | (|fault_flags);
                rv_delay[S_RT+3]<=rv_base[S_RT+3] | (|hnz_flags);
            end
        assign rvm=rv_delay;
    end else begin : g_unmerged
        assign rvm=rv_base;
    end endgenerate
    wire [WA-1:0] rd_full;
    wire [8*64*SH-1:0] hr_n, hr_s;
    wire [WA-1:0] rd_same, rd_shift, rd_bound;
    genvar q;
    assign rd_same[P_D-1:0]=rdh_in;
    assign rd_shift[P_D-1:0]='0;
    generate for(q=0;q<16;q=q+1) begin : g_bind
        if(q>=0 && q%4==COLUMN) begin : g_same
            assign rd_same[P_D+64*q +:64]=rdp_in[64*(((q-0)/8)*2+(q%8)/4) +:64];
        end else assign rd_same[P_D+64*q +:64]=64'd0;
        if((q+2)>=0 && (q+2)<16 && (q+2)%4==COLUMN) begin : g_shift
            assign rd_shift[P_D+64*q +:64]=rdp_in[128*SH+64*(((q+2-0)/8)*2+((q+2)%8)/4) +:64];
        end else assign rd_shift[P_D+64*q +:64]=64'd0;
    end endgenerate
    assign rd_bound=rd_same|rd_shift;
    genvar lane, sl, chunk;
    generate for(lane=0;lane<8;lane=lane+1) begin : g_lane
        assign hr_n[64*SH*lane +:64*SH] = (lane%4==COLUMN) ? hrq_n[64*SH*(lane/4) +:64*SH] : '0;
        assign hr_s[64*SH*lane +:64*SH] = (lane%4==COLUMN) ? hrq_s[64*SH*(lane/4) +:64*SH] : '0;
    end endgenerate
    reg rr;
    always @(posedge clk) rr <= e_rst;
    always @(posedge clk or negedge rr)
        if(!rr) begin flag_fault<=0;flag_hnz<=0;end
        else begin
            flag_fault <= (|e_nflt_n) | (|e_nflt_s) | e_pflt_n | e_pflt_s;
            flag_hnz <= e_hnz_n | e_hnz_s;
        end
    always @(posedge clk) header_delay <= rd_full[P_D-1:0];
    ot_s81_hc_ctra #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),.ML(ML),.AL(AL),.CHAIN_STEP(CHAIN_STEP),.READ_STAGE(READ_STAGE)) u (
        .clk(clk),
        .rst_in(e_rst),
        .tid(e_tid),
        .last(e_last),
        .fv(e_fv),
        .fdx(e_fdx),
        .rv_in(rv_in),
        .rd_in(rd_bound),
        .rvm(rv_base),
        .rdm(rd_full),
        .rq_q(rq_q),
        .hs_run(hs_run),
        .hs_c(hs_c),
        .rq_q_c1(rq_q_c1),
        .rq_q_c2(rq_q_c2),
        .rq_q_c3(rq_q_c3),
        .hs_run_c1(hs_run_c1),
        .hs_run_c2(hs_run_c2),
        .hs_run_c3(hs_run_c3),
        .hs_c_c1(hs_c_c1),
        .hs_c_c2(hs_c_c2),
        .hs_c_c3(hs_c_c3),
        .hrq_n(hr_n),
        .hrq_s(hr_s),
        .yb_n(e_yb_n),
        .yb_s(e_yb_s),
        .cs(e_cs),
        .nflt_n('0),
        .nflt_s('0),
        .hov_d(e_hov),
        .hnz_n('0),
        .hnz_s('0),
        .pflt_n('0),
        .pflt_s('0));
    reg [128*SH-1:0] payload_delay;
    generate for(sl=0;sl<SH;sl=sl+1) begin : g_slot
        for(chunk=0;chunk<2;chunk=chunk+1) begin : g_chunk
            always @(posedge clk) payload_delay[128*sl+64*chunk +:64] <= rd_full[P_D+512*sl+64*(COLUMN+4*chunk) +:64];
        end
    end endgenerate
    assign rdm=payload_delay;
endmodule

module ot_s81_hc_ctra_columns #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, CHAIN_STEP = AL, READ_STAGE = 0, YB_STAGE = 0
) (
    input  wire [3:0]             clk_col,
    input  wire                   rst_in,
    input  wire [7:0]             tid,
    input  wire                   last,
    input  wire [S_RD+4:0]        fv,
    input  wire [O_D-1:0]         fdx,
    input  wire [S_RT+3:0]        rv_in,
    input  wire [WA-1:0]          rd_in,
    output wire [S_RT+3:0]        rvm,
    output wire [WA-1:0]          rdm,
    output wire [16*S_RT-1:0]     rq_q,
    output wire                   hs_run,
    output wire [15:0]            hs_c,
    output wire [16*S_RT-1:0]     rq_q_c1, rq_q_c2, rq_q_c3,
    output wire                  hs_run_c1, hs_run_c2, hs_run_c3,
    output wire [15:0]           hs_c_c1, hs_c_c2, hs_c_c3,
    input  wire [8*64*SH-1:0]     hrq_n, hrq_s,     // [lane n (or n - 8)][slot s] 64 b
    input  wire [8*16-1:0]        yb_n, yb_s,
    input  wire [4*32-1:0]        cs,
    input  wire [7:0]             nflt_n, nflt_s,
    input  wire                   hov_d,
    input  wire [3:0]             hnz_n, hnz_s, pflt_n, pflt_s,  // ctpl half 0 (N) / half 1 (S), group g
    output wire [255:0]           yb_rel            // YB_STAGE: {yb_s,yb_n} one cycle late, from the four columns' relays (feeds ctrb)
);
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FXW = O_D + S_RD * 512;
    localparam integer SH = S_RT / 2, P_D = S_RT + 8 * S_RT + 16 * S_RT + 8, RDW = P_D + 512 * S_RT, WA = P_D + 512 * SH;

    genvar c, sl, chunk;
    wire [255:0] yb_raw = {yb_s, yb_n};
    generate for(c=0;c<4;c=c+1) begin : g_column
        wire [63:0] yb_fwd;
        wire [63:0] yb_loc = {yb_raw[16*(c+12) +:16], yb_raw[16*(c+8) +:16], yb_raw[16*(c+4) +:16], yb_raw[16*c +:16]};
        wire [191:0] yb_peer;
        for(genvar pc=0;pc<4;pc=pc+1) begin : g_peer
            if(pc<c) begin : g_lo assign yb_peer[64*pc +:64]=g_column[pc].yb_fwd; end
            else if(pc>c) begin : g_hi assign yb_peer[64*(pc-1) +:64]=g_column[pc].yb_fwd; end
        end
        for(genvar k=0;k<4;k=k+1) begin : g_rel
            assign yb_rel[16*(c+4*k) +:16]=yb_fwd[16*k +:16];
        end
        wire [128*SH-1:0] col_data;
        wire [256*SH-1:0] local_rdp;
        for(genvar rs=0;rs<SH;rs=rs+1) begin : g_rdslot
            for(genvar rc=0;rc<2;rc=rc+1) begin : g_rdchunk
                assign local_rdp[64*(2*rs+rc) +:64]=rd_in[P_D+64*(8*rs+c+4*rc) +:64];
                if((8*rs+c+4*rc)>=2) assign local_rdp[128*SH+64*(2*rs+rc) +:64]=rd_in[P_D+64*((8*rs+c+4*rc)-2) +:64];
                else assign local_rdp[128*SH+64*(2*rs+rc) +:64]='0;
            end
        end
        wire [2*64*SH-1:0] local_hr_n, local_hr_s;
        for(genvar bank=0;bank<2;bank=bank+1) begin : g_hrq
            assign local_hr_n[64*SH*bank +:64*SH] = hrq_n[64*SH*(c+4*bank) +:64*SH];
            assign local_hr_s[64*SH*bank +:64*SH] = hrq_s[64*SH*(c+4*bank) +:64*SH];
        end
        wire [S_RT+3:0] rv_base;
        wire flag_fault,flag_hnz;
        wire [P_D-1:0] header_delay;
        wire [16*S_RT-1:0] local_rq_q;
        wire [1-1:0] local_hs_run;
        wire [16-1:0] local_hs_c;
        wire [16*S_RT-1:0] local_rq_q_c1;
        wire [16*S_RT-1:0] local_rq_q_c2;
        wire [16*S_RT-1:0] local_rq_q_c3;
        wire [1-1:0] local_hs_run_c1;
        wire [1-1:0] local_hs_run_c2;
        wire [1-1:0] local_hs_run_c3;
        wire [16-1:0] local_hs_c_c1;
        wire [16-1:0] local_hs_c_c2;
        wire [16-1:0] local_hs_c_c3;
        // Every column already owns the identical real scheduler state. Route
        // its registered request to its own banks, avoiding A0 broadcasts.
        if(c==0) begin : g_requests0
            assign rq_q=local_rq_q;
            assign hs_run=local_hs_run;
            assign hs_c=local_hs_c;
        end else if(c==1) begin : g_requests1
            assign rq_q_c1=local_rq_q;
            assign hs_run_c1=local_hs_run;
            assign hs_c_c1=local_hs_c;
        end else if(c==2) begin : g_requests2
            assign rq_q_c2=local_rq_q;
            assign hs_run_c2=local_hs_run;
            assign hs_c_c2=local_hs_c;
        end else begin : g_requests3
            assign rq_q_c3=local_rq_q;
            assign hs_run_c3=local_hs_run;
            assign hs_c_c3=local_hs_c;
        end
        ot_s81_hc_ctra_column #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),.ML(ML),.AL(AL),.CHAIN_STEP(CHAIN_STEP),.READ_STAGE(READ_STAGE),.COLUMN(c),.YB_STAGE(YB_STAGE)) u (
            .clk(clk_col[c]),
            .rst_in(rst_in),
            .tid(tid),
            .last(last),
            .fv(fv),
            .fdx(fdx),
            .rv_in(rv_in),
            .rdh_in(rd_in[P_D-1:0]),
            .rdp_in(local_rdp),
            .rvm(rv_base),
            .peer_fault(c==0 ? {g_column[3].flag_fault,g_column[2].flag_fault,g_column[1].flag_fault} : 3'b0),
            .peer_hnz(c==0 ? {g_column[3].flag_hnz,g_column[2].flag_hnz,g_column[1].flag_hnz} : 3'b0),
            .yb_loc(yb_loc),
            .yb_fwd(yb_fwd),
            .yb_peer(yb_peer),
            .rdm(col_data),
            .rq_q(local_rq_q),
            .hs_run(local_hs_run),
            .hs_c(local_hs_c),
            .rq_q_c1(local_rq_q_c1),
            .rq_q_c2(local_rq_q_c2),
            .rq_q_c3(local_rq_q_c3),
            .hs_run_c1(local_hs_run_c1),
            .hs_run_c2(local_hs_run_c2),
            .hs_run_c3(local_hs_run_c3),
            .hs_c_c1(local_hs_c_c1),
            .hs_c_c2(local_hs_c_c2),
            .hs_c_c3(local_hs_c_c3),
            .hrq_n(local_hr_n),
            .hrq_s(local_hr_s),
            .yb_n(yb_n),
            .yb_s(yb_s),
            .cs(cs),
            .nflt_n({nflt_n[c+4],nflt_n[c]}),
            .nflt_s({nflt_s[c+4],nflt_s[c]}),
            .hov_d(hov_d),
            .hnz_n(hnz_n[c]),
            .hnz_s(hnz_s[c]),
            .pflt_n(pflt_n[c]),
            .pflt_s(pflt_s[c]),
            .flag_fault(flag_fault),
            .flag_hnz(flag_hnz),
            .header_delay(header_delay));
        for(sl=0;sl<SH;sl=sl+1) begin : g_slot
            for(chunk=0;chunk<2;chunk=chunk+1) begin : g_chunk
                assign rdm[P_D+512*sl+64*(c+4*chunk) +:64] = col_data[128*sl+64*chunk +:64];
            end
        end
    end endgenerate
    assign rdm[P_D-1:0]=g_column[0].header_delay;
    assign rvm=g_column[0].rv_base;
endmodule

module ot_s81_hc_ctrb_column #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, CHAIN_STEP = AL, READ_STAGE = 0, COLUMN = 0, YB_STAGE = 0
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire [7:0]             tid,
    input  wire                   last,
    input  wire [S_RD+4:0]        fv,
    input  wire [O_D-1:0]         fdx,
    input  wire [S_RT+3:0]        rv_in,
    input  wire [P_D-1:0]         rdh_in,           // rd_in header
    input  wire [256*SH-1:0]      rdp_in,           // rd_in data bits [512 SH - 128, 512 S_RT)
    output wire [128*SH-1:0]      rdm,              // rdm data slots SH .. S_RT-1
    input  wire [2*64*SH-1:0]     hrq_n, hrq_s,     // [lane][slot s - SH] 64 b
    input  wire [8*16-1:0]        yb_n, yb_s        // YB_STAGE: the relayed y beat (ctra columns' yb_fwd), already one cycle late
);
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FXW = O_D + S_RD * 512;
    localparam integer SH = S_RT / 2, P_D = S_RT + 8 * S_RT + 16 * S_RT + 8, RDW = P_D + 512 * S_RT;
    localparam integer WB = 512 * SH + 128;

    initial if(S_RT!=4 || COLUMN<0 || COLUMN>3) $fatal(1,"return column requires S_RT4 and column0..3");
    wire e_rst, e_last; wire [7:0] e_tid; wire [S_RD+4:0] e_fv; wire [O_D-1:0] e_fdx;
    generate if(YB_STAGE) begin : g_ybstage
        reg rst_q, last_q; reg [7:0] tid_q; reg [S_RD+4:0] fv_q; reg [O_D-1:0] fdx_q;
        always @(posedge clk) begin rst_q<=rst_in; tid_q<=tid; last_q<=last; fv_q<=fv; fdx_q<=fdx; end
        assign e_rst=rst_q; assign e_tid=tid_q; assign e_last=last_q; assign e_fv=fv_q; assign e_fdx=fdx_q;
    end else begin : g_direct
        assign e_rst=rst_in; assign e_tid=tid; assign e_last=last; assign e_fv=fv; assign e_fdx=fdx;
    end endgenerate
    wire [512*SH-1:0] rd_full;
    wire [8*64*SH-1:0] hr_n, hr_s;
    wire [WB-1:0] rd_same, rd_shift, rd_bound;
    genvar q;
    generate for(q=0;q<18;q=q+1) begin : g_bind
        if((q+14)>=16 && (q+14)%4==COLUMN) begin : g_same
            assign rd_same[0+64*q +:64]=rdp_in[64*((((q+14)-16)/8)*2+((q+14)%8)/4) +:64];
        end else assign rd_same[0+64*q +:64]=64'd0;
        if(((q+14)+2)>=16 && ((q+14)+2)<32 && ((q+14)+2)%4==COLUMN) begin : g_shift
            assign rd_shift[0+64*q +:64]=rdp_in[128*SH+64*((((q+14)+2-16)/8)*2+(((q+14)+2)%8)/4) +:64];
        end else assign rd_shift[0+64*q +:64]=64'd0;
    end endgenerate
    assign rd_bound=rd_same|rd_shift;
    genvar lane, sl, chunk;
    generate for(lane=0;lane<8;lane=lane+1) begin : g_lane
        assign hr_n[64*SH*lane +:64*SH] = (lane%4==COLUMN) ? hrq_n[64*SH*(lane/4) +:64*SH] : '0;
        assign hr_s[64*SH*lane +:64*SH] = (lane%4==COLUMN) ? hrq_s[64*SH*(lane/4) +:64*SH] : '0;
    end endgenerate
    ot_s81_hc_ctrb #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),.ML(ML),.AL(AL),.CHAIN_STEP(CHAIN_STEP),.READ_STAGE(READ_STAGE)) u (
        .clk(clk),
        .rst_in(e_rst),
        .tid(e_tid),
        .last(e_last),
        .fv(e_fv),
        .fdx(e_fdx),
        .rv_in(rv_in),
        .rdh_in(rdh_in),
        .rdd_in(rd_bound),
        .rdm(rd_full),
        .hrq_n(hr_n),
        .hrq_s(hr_s),
        .yb_n(yb_n),
        .yb_s(yb_s));
    reg [128*SH-1:0] payload_delay;
    generate for(sl=0;sl<SH;sl=sl+1) begin : g_slot
        for(chunk=0;chunk<2;chunk=chunk+1) begin : g_chunk
            always @(posedge clk) payload_delay[128*sl+64*chunk +:64] <= rd_full[0+512*sl+64*(COLUMN+4*chunk) +:64];
        end
    end endgenerate
    assign rdm=payload_delay;
endmodule

module ot_s81_hc_ctrb_columns #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, CHAIN_STEP = AL, READ_STAGE = 0, YB_STAGE = 0
) (
    input  wire [3:0]             clk_col,
    input  wire                   rst_in,
    input  wire [7:0]             tid,
    input  wire                   last,
    input  wire [S_RD+4:0]        fv,
    input  wire [O_D-1:0]         fdx,
    input  wire [S_RT+3:0]        rv_in,
    input  wire [P_D-1:0]         rdh_in,           // rd_in header
    input  wire [WB-1:0]          rdd_in,           // rd_in data bits [512 SH - 128, 512 S_RT)
    output wire [512*SH-1:0]      rdm,              // rdm data slots SH .. S_RT-1
    input  wire [8*64*SH-1:0]     hrq_n, hrq_s,     // [lane][slot s - SH] 64 b
    input  wire [8*16-1:0]        yb_n, yb_s
);
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FXW = O_D + S_RD * 512;
    localparam integer SH = S_RT / 2, P_D = S_RT + 8 * S_RT + 16 * S_RT + 8, RDW = P_D + 512 * S_RT;
    localparam integer WB = 512 * SH + 128;

    genvar c, sl, chunk;
    generate for(c=0;c<4;c=c+1) begin : g_column
        wire [128*SH-1:0] col_data;
        wire [256*SH-1:0] local_rdp;
        for(genvar rs=0;rs<SH;rs=rs+1) begin : g_rdslot
            for(genvar rc=0;rc<2;rc=rc+1) begin : g_rdchunk
                assign local_rdp[64*(2*rs+rc) +:64]=rdd_in[64*((8*rs+c+4*rc)+2) +:64];
                assign local_rdp[128*SH+64*(2*rs+rc) +:64]=rdd_in[64*(8*rs+c+4*rc) +:64];
            end
        end
        wire [2*64*SH-1:0] local_hr_n, local_hr_s;
        for(genvar bank=0;bank<2;bank=bank+1) begin : g_hrq
            assign local_hr_n[64*SH*bank +:64*SH] = hrq_n[64*SH*(c+4*bank) +:64*SH];
            assign local_hr_s[64*SH*bank +:64*SH] = hrq_s[64*SH*(c+4*bank) +:64*SH];
        end
        ot_s81_hc_ctrb_column #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),.ML(ML),.AL(AL),.CHAIN_STEP(CHAIN_STEP),.READ_STAGE(READ_STAGE),.COLUMN(c),.YB_STAGE(YB_STAGE)) u (
            .clk(clk_col[c]),
            .rst_in(rst_in),
            .tid(tid),
            .last(last),
            .fv(fv),
            .fdx(fdx),
            .rv_in(rv_in),
            .rdh_in(rdh_in),
            .rdp_in(local_rdp),
            .rdm(col_data),
            .hrq_n(local_hr_n),
            .hrq_s(local_hr_s),
            .yb_n(yb_n),
            .yb_s(yb_s));
        for(sl=0;sl<SH;sl=sl+1) begin : g_slot
            for(chunk=0;chunk<2;chunk=chunk+1) begin : g_chunk
                assign rdm[0+512*sl+64*(c+4*chunk) +:64] = col_data[128*sl+64*chunk +:64];
            end
        end
    end endgenerate
endmodule
