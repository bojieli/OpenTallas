// Four actual local return engines, each with a distinct clock entry and registered payload pins.
// Return data/valid gain exactly one fixed cycle. Bank requests retain the original epoch.
// BF16 y dependencies remain real and cross columns; this is not claimed as a free transpose.
// All four clock roots require the same phase; COLUMN0 owns the merged-valid register. Canonical compiler/slot adoption is separate.

module ot_s81_hc_ctra_column #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, CHAIN_STEP = AL, READ_STAGE = 0, COLUMN = 0
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
    wire [S_RT+3:0] rv_base;
    wire [3:0] fault_flags = {peer_fault,flag_fault};
    wire [3:0] hnz_flags = {peer_hnz,flag_hnz};
    generate if(COLUMN==0) begin : g_merge
        reg rr_merge;
        reg [S_RT+3:0] rv_delay;
        always @(posedge clk) rr_merge<=rst_in;
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
    always @(posedge clk) rr <= rst_in;
    always @(posedge clk or negedge rr)
        if(!rr) begin flag_fault<=0;flag_hnz<=0;end
        else begin
            flag_fault <= (|nflt_n) | (|nflt_s) | pflt_n | pflt_s;
            flag_hnz <= hnz_n | hnz_s;
        end
    always @(posedge clk) header_delay <= rd_full[P_D-1:0];
    ot_s81_hc_ctra #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),.ML(ML),.AL(AL),.CHAIN_STEP(CHAIN_STEP),.READ_STAGE(READ_STAGE)) u (
        .clk(clk),
        .rst_in(rst_in),
        .tid(tid),
        .last(last),
        .fv(fv),
        .fdx(fdx),
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
        .yb_n(yb_n),
        .yb_s(yb_s),
        .cs(cs),
        .nflt_n('0),
        .nflt_s('0),
        .hov_d(hov_d),
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
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, CHAIN_STEP = AL, READ_STAGE = 0
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
    input  wire [3:0]             hnz_n, hnz_s, pflt_n, pflt_s   // ctpl half 0 (N) / half 1 (S), group g
);
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FXW = O_D + S_RD * 512;
    localparam integer SH = S_RT / 2, P_D = S_RT + 8 * S_RT + 16 * S_RT + 8, RDW = P_D + 512 * S_RT, WA = P_D + 512 * SH;

    genvar c, sl, chunk;
    generate for(c=0;c<4;c=c+1) begin : g_column
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
        ot_s81_hc_ctra_column #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),.ML(ML),.AL(AL),.CHAIN_STEP(CHAIN_STEP),.READ_STAGE(READ_STAGE),.COLUMN(c)) u (
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
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, CHAIN_STEP = AL, READ_STAGE = 0, COLUMN = 0
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
    input  wire [8*16-1:0]        yb_n, yb_s
);
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FXW = O_D + S_RD * 512;
    localparam integer SH = S_RT / 2, P_D = S_RT + 8 * S_RT + 16 * S_RT + 8, RDW = P_D + 512 * S_RT;
    localparam integer WB = 512 * SH + 128;

    initial if(S_RT!=4 || COLUMN<0 || COLUMN>3) $fatal(1,"return column requires S_RT4 and column0..3");
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
        .rst_in(rst_in),
        .tid(tid),
        .last(last),
        .fv(fv),
        .fdx(fdx),
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
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, CHAIN_STEP = AL, READ_STAGE = 0
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
        ot_s81_hc_ctrb_column #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),.ML(ML),.AL(AL),.CHAIN_STEP(CHAIN_STEP),.READ_STAGE(READ_STAGE),.COLUMN(c)) u (
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
