// HC half-octet with the four-column return and per-column return slices (HC-COLUMN 10-16, coordinator option A).
//
// ot_s81_hc_ctrn_col  : one of four identical return slices replacing the 576.72-um ctrn strip.  It registers, for its
//                       column c, everything the next row's column-c return leaves read: valid (8), header (108), the
//                       own ctra / ctrb payload chunks (256 + 256) and the partner column (c+2)%4's chunks (256 + 256),
//                       which the far-half 128-bit shift of ot_s81_hc_ctrs pulls in.  1,140 b, one register stage = the
//                       old ctrn (RLY 2), so the chain keeps its cycle count; payload is replicated x2, header / valid x4.
// ot_s81_hc_retrow    : the return row: ctra_column x4 + ctrb_column x4 (YB_STAGE 1) + ctrn_col x4, chained through
//                       per-column bundles (rb_in / rb_out, 4 x RBW).
// ot_s81_hc_rb_flat2cols / ot_s81_hc_rb_cols2flat : pure wiring between the flat (rv, rd) chain and the bundles, used at
//                       the two ends of a cth_ntc chain so the HC slab ports stay unchanged.
// ot_s81_hc_cth_ntc   : ot_s81_hc_cth_nt with the CTFN local banks (ot_s81_hc_ctfn_banks_candidate, 5 clock entries) and
//                       the return row; chain ports carry the bundles.
// Cycle cost (static calendar, S-FUNC): the columns run PAYLOAD_STAGE 0 (cycle-identical to monolithic ctra / ctrb) and
// the ctrn_col slices replace ctrn's one register, so the only change is the y-beat stage: every row's engine runs one
// cycle later (fv-domain pin registers), i.e. bank requests +1 and the HC return +1, once per chain (not per row).

module ot_s81_hc_ctrn_col #(
    parameter integer S_RT = 4
) (
    input  wire               clk,
    input  wire               rst_in,
    input  wire [S_RT+3:0]    rv_c,
    input  wire [107:0]       hdr_c,
    input  wire [255:0]       a_own, b_own, a_par, b_par,
    output reg  [S_RT+3:0]    rv_out,
    output reg  [107:0]       hdr_out,
    output reg  [255:0]       a_own_out, b_own_out, a_par_out, b_par_out
);
    reg rr;                                              // regional reset relay, as ot_s81_hc_ctrn
    always @(posedge clk) rr <= rst_in;
    always @(posedge clk or negedge rr) if (!rr) rv_out <= 0; else rv_out <= rv_c;
    always @(posedge clk) begin
        hdr_out <= hdr_c; a_own_out <= a_own; b_own_out <= b_own; a_par_out <= a_par; b_par_out <= b_par;
    end
endmodule

// bundle layout per column (RBW = 1140): {b_par, a_par, b_own, a_own, hdr, rv}; a_* = ctra slots 0..1, b_* = slots 2..3,
// each [128 * slot + 64 * k] = chunk (column + 4 k) of that slot (the column leaves' payload_delay order)
module ot_s81_hc_rb_flat2cols #(
    parameter integer S_RT = 4
) (
    input  wire [S_RT+3:0]    rv,
    input  wire [RDW-1:0]     rd,
    output wire [4*RBW-1:0]   rb
);
    localparam integer P_D = S_RT + 8 * S_RT + 16 * S_RT + 8, RDW = P_D + 512 * S_RT, RVW = S_RT + 4, RBW = RVW + 108 + 1024;
    genvar c, sl, k;
    generate for (c = 0; c < 4; c = c + 1) begin : g_c
        localparam integer PC = (c + 2) % 4, B = RBW * c;
        assign rb[B +: RVW] = rv;
        assign rb[B + RVW +: 108] = rd[P_D - 1:0];
        for (sl = 0; sl < 2; sl = sl + 1) begin : g_s
            for (k = 0; k < 2; k = k + 1) begin : g_k
                assign rb[B + RVW + 108 +       128 * sl + 64 * k +: 64] = rd[P_D + 512 * sl       + 64 * (c  + 4 * k) +: 64];
                assign rb[B + RVW + 108 + 256 + 128 * sl + 64 * k +: 64] = rd[P_D + 512 * (sl + 2) + 64 * (c  + 4 * k) +: 64];
                assign rb[B + RVW + 108 + 512 + 128 * sl + 64 * k +: 64] = rd[P_D + 512 * sl       + 64 * (PC + 4 * k) +: 64];
                assign rb[B + RVW + 108 + 768 + 128 * sl + 64 * k +: 64] = rd[P_D + 512 * (sl + 2) + 64 * (PC + 4 * k) +: 64];
            end
        end
    end endgenerate
endmodule

module ot_s81_hc_rb_cols2flat #(
    parameter integer S_RT = 4
) (
    input  wire [4*RBW-1:0]   rb,
    output wire [S_RT+3:0]    rv,
    output wire [RDW-1:0]     rd
);
    localparam integer P_D = S_RT + 8 * S_RT + 16 * S_RT + 8, RDW = P_D + 512 * S_RT, RVW = S_RT + 4, RBW = RVW + 108 + 1024;
    assign rv = rb[0 +: RVW];
    assign rd[P_D - 1:0] = rb[RVW +: 108];
    genvar c, sl, k;
    generate for (c = 0; c < 4; c = c + 1) begin : g_c
        for (sl = 0; sl < 2; sl = sl + 1) begin : g_s
            for (k = 0; k < 2; k = k + 1) begin : g_k
                assign rd[P_D + 512 * sl       + 64 * (c + 4 * k) +: 64] = rb[RBW * c + RVW + 108 +       128 * sl + 64 * k +: 64];
                assign rd[P_D + 512 * (sl + 2) + 64 * (c + 4 * k) +: 64] = rb[RBW * c + RVW + 108 + 256 + 128 * sl + 64 * k +: 64];
            end
        end
    end endgenerate
endmodule

module ot_s81_hc_retrow #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, CHAIN_STEP = AL, READ_STAGE = 1
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire [7:0]             tid,
    input  wire                   last,
    input  wire [S_RD+4:0]        fv,
    input  wire [O_D-1:0]         fdx,
    input  wire [4*RBW-1:0]       rb_in,
    output wire [4*RBW-1:0]       rb_out,
    output wire [16*S_RT-1:0]     rq_q0, rq_q1, rq_q2, rq_q3,
    output wire [3:0]             hs_run_c,
    output wire [15:0]            hs_c0, hs_c1, hs_c2, hs_c3,
    input  wire [16*64*S_RT-1:0]  hrq,                // lane tile n = 4 bank + group
    input  wire [16*16-1:0]       yb,
    input  wire [4*32-1:0]        cs,
    input  wire [15:0]            nflt,
    input  wire                   hov_d,
    input  wire [7:0]             hnz_d, pflt_d
);
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1;
    localparam integer RVW = S_RT + 4, RBW = RVW + 108 + 1024;
    // the cs / hov relay nets (COLUMN 3 / COLUMN 0 relay one register; every other column reads the net)
    wire [127:0] cs_net;
    wire         hov_net;
    genvar c;
    generate for (c = 0; c < 4; c = c + 1) begin : g_col
        localparam integer B = RBW * c, PC = (c + 2) % 4;
        wire [RVW-1:0] rvm;
        wire [107:0]   hdr;
        wire [255:0]   a_rdm, b_rdm;
        wire [63:0]    yb_fwd;
        wire [127:0]   csf;
        wire           hovf, flag_fault, flag_hnz;
        wire [16*S_RT-1:0] rq;
        wire           hsr;
        wire [15:0]    hsc;
        wire [191:0]   yb_peer;
        wire [2:0]     peer_fault, peer_hnz;
        for (genvar pc = 0; pc < 4; pc = pc + 1) begin : g_peer
            if (pc != c) begin : g_p
                localparam integer PI = (pc < c) ? pc : pc - 1;
                assign yb_peer[64 * PI +: 64] = g_col[pc].yb_fwd;
                assign peer_fault[PI] = g_col[pc].flag_fault;
                assign peer_hnz[PI]   = g_col[pc].flag_hnz;
            end
        end
        wire [4*64*S_RT-1:0] hrq_col;
        for (genvar j = 0; j < 4; j = j + 1) begin : g_h
            assign hrq_col[64 * S_RT * j +: 64 * S_RT] = hrq[64 * S_RT * (c + 4 * j) +: 64 * S_RT];
        end
        ot_s81_hc_ret_column #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),.ML(ML),.AL(AL),.CHAIN_STEP(CHAIN_STEP),.READ_STAGE(READ_STAGE),.COLUMN(c)) u_c (
            .clk(clk), .rst_in(rst_in), .tid(tid), .last(last), .fv(fv), .fdx(fdx),
            .rv_in(rb_in[B +: RVW]), .hdr_in(rb_in[B + RVW +: 108]),
            .ao_in(rb_in[B + RVW + 108 +: 256]), .bo_in(rb_in[B + RVW + 364 +: 256]),
            .ap_in(rb_in[B + RVW + 620 +: 256]), .bp_in(rb_in[B + RVW + 876 +: 256]),
            .rvm(rvm), .hdr(hdr), .a_rdm(a_rdm), .b_rdm(b_rdm), .rq_q(rq), .hs_run(hsr), .hs_c(hsc),
            .hrq_col(hrq_col),
            .yb_loc({yb[16 * (c + 12) +: 16], yb[16 * (c + 8) +: 16], yb[16 * (c + 4) +: 16], yb[16 * c +: 16]}),
            .yb_fwd(yb_fwd), .yb_peer(yb_peer),
            .cs_in(c == 3 ? cs : cs_net), .cs_rel(cs_net), .cs_fwd(csf),
            .hov_in(c == 0 ? hov_d : hov_net), .hov_rel(hov_net), .hov_fwd(hovf),
            .nflt_col({nflt[c + 12], nflt[c + 8], nflt[c + 4], nflt[c]}),
            .hnz_n(hnz_d[2 * c]), .hnz_s(hnz_d[2 * c + 1]), .pflt_n(pflt_d[2 * c]), .pflt_s(pflt_d[2 * c + 1]),
            .flag_fault(flag_fault), .flag_hnz(flag_hnz), .peer_fault(peer_fault), .peer_hnz(peer_hnz));
        ot_s81_hc_ctrn_col #(.S_RT(S_RT)) u_n (
            .clk(clk), .rst_in(rst_in), .rv_c(rvm), .hdr_c(hdr), .a_own(a_rdm), .b_own(b_rdm),
            .a_par(g_col[PC].a_rdm), .b_par(g_col[PC].b_rdm),
            .rv_out(rb_out[B +: RVW]), .hdr_out(rb_out[B + RVW +: 108]),
            .a_own_out(rb_out[B + RVW + 108 +: 256]), .b_own_out(rb_out[B + RVW + 364 +: 256]),
            .a_par_out(rb_out[B + RVW + 620 +: 256]), .b_par_out(rb_out[B + RVW + 876 +: 256]));
    end endgenerate
    assign cs_net = g_col[3].csf;
    assign hov_net = g_col[0].hovf;
    assign rq_q0 = g_col[0].rq; assign rq_q1 = g_col[1].rq; assign rq_q2 = g_col[2].rq; assign rq_q3 = g_col[3].rq;
    assign hs_run_c = {g_col[3].hsr, g_col[2].hsr, g_col[1].hsr, g_col[0].hsr};
    assign hs_c0 = g_col[0].hsc; assign hs_c1 = g_col[1].hsc; assign hs_c2 = g_col[2].hsc; assign hs_c3 = g_col[3].hsc;
endmodule

module ot_s81_hc_cth_ntc #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, WIN = 2, WOUT = 2, ML = 5, AL = 4,
    parameter integer RLY = 2, CNL_PIN = 0, CHAIN_STEP = AL, LANE_SPECIALIZE = 0, LOCAL_SPLIT = 1
) (
    input  wire                       clk,
    input  wire                       rst_in,
    output wire                       rst_out,
    input  wire [7:0]                 tid,
    input  wire                       last,
    input  wire [S_RD+4:0]            fv_in,
    input  wire [FDW-1:0]             fd_in,
    output wire [S_RD+4:0]            fv_out,
    output wire [FDW-1:0]             fd_out,
    input  wire [4*RBW-1:0]           rb_in,      // per-column return bundles from the previous row's ctrn_col slices
    output wire [4*RBW-1:0]           rb_out,
    output wire [127:0]               cy_out,
    input  wire [127:0]               cy_in,
    // NORM tree lanes (ot_s81_hc_ctfx_nt): partial-sum lane south (dl), scale lane north (ul)
    input  wire [DLW-1:0]             dl_in,
    output wire [DLW-1:0]             dl_out,
    input  wire [32:0]                ul_in,
    output wire [32:0]                ul_out
);
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, YW = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FDW = O_D + FDD, FXW = O_D + S_RD * 512;
    localparam integer RDW = S_RT + 8 * S_RT + 16 * S_RT + 8 + 512 * S_RT;
    localparam integer DLW = 2 * 137 + 1;
    localparam integer RBW = S_RT + 4 + 108 + 1024;
`ifndef SYNTHESIS
    initial if (RLY != 2) $fatal(1, "ot_s81_hc_cth_ntc: the ctrn_col slices are one register stage (= ctrn at RLY 2)");
`endif
`ifndef SYNTHESIS
    initial if (LANE_SPECIALIZE && !CNL_PIN) $fatal(1,"cth LANE_SPECIALIZE requires CNL_PIN");
    initial if (RLY < 2 || GS != 8) $fatal(1, "ot_s81_hc_cth: RLY >= 2 (the return merge takes a relay stage), GS 8");
`endif

    // Constant bit maps: HLOAD64-bit lane words, GAIN32-bit lane words, shared pre128.
    function automatic integer lane_payload_width(input integer ln);
        begin case(ln) 0:lane_payload_width=256; 1:lane_payload_width=288;
              2:lane_payload_width=352; default:lane_payload_width=288; endcase end
    endfunction
    function automatic integer lane_payload_needed(input integer ln,input integer bitno);
        integer g;
        begin
            lane_payload_needed=(bitno<128) ||
                (bitno>=64*ln && bitno<64*ln+64) ||
                (bitno>=64*(ln+4) && bitno<64*(ln+4)+64);
            for(g=0;g<4;g=g+1)
                if(bitno>=32*(ln+4*g) && bitno<32*(ln+4*g)+32)
                    lane_payload_needed=1;
        end
    endfunction
    function automatic integer lane_payload_rank(input integer ln,input integer bitno);
        integer b;
        begin lane_payload_rank=0;
            for(b=0;b<bitno;b=b+1) lane_payload_rank=lane_payload_rank+lane_payload_needed(ln,b);
        end
    endfunction
    function automatic integer lane_payload_index(input integer ln,input integer packedbit);
        integer b,c;
        begin lane_payload_index=0;c=0;
            for(b=0;b<512;b=b+1) if(lane_payload_needed(ln,b)) begin
                if(c==packedbit) lane_payload_index=b;
                c=c+1;
            end
        end
    endfunction
    wire [S_RD+4:0] fv;
    wire [FXW-1:0]  fdx;
    wire [S_RD+4:0] fv_local;
    wire [FXW-1:0] fdx_local;
    wire [S_RD+4:0] fvm;
    wire [4*32-1:0] cs;
    wire [16*32-1:0] acc;
    wire [FDW-1:0]  fdm;
    wire            rst_c;                     // ctfn's first reset stage -> one relay flop in every tile
    // CTFN as four local-clock data banks + reset leaf (5 clock entries; same 2 data stages, +1 INIT reset edge)
    ot_s81_hc_ctfn_banks_candidate u_fn (
        .ck({5{clk}}), .rst_in(rst_in), .rst_c(rst_c), .fv_in(fv_in), .fd_in(fd_in), .fvm(fvm), .fdm(fdm));
    wire [DLW-1:0] dl_m;
    wire [32:0]    ul_m;
    generate if (LOCAL_SPLIT && CNL_PIN) begin : g_fxs
        ot_s81_hc_ctfxs_nt #(.NG(NG), .D(D), .S_RD(S_RD), .ML(ML), .AL(AL), .CHAIN_STEP(CHAIN_STEP)) u_fx (
            .clk(clk), .clk_l(clk), .rst_in(rst_c), .fv_in(fv_in), .fd_in(fd_in[FXW-1:0]), .fv(fv), .fdx(fdx),
            .tid(tid), .cs_n(cs[63:0]), .cs_s(cs[127:64]), .dl_in(dl_in), .dl_out(dl_m), .ul_in(ul_m), .ul_out(ul_out));
        ot_s81_hc_ctfl_nt #(.S_RD(S_RD)) u_fl (
            .clk(clk), .rst_in(rst_c), .fv(fv), .fdx(fdx), .fv_local(fv_local), .fdx_local(fdx_local));
    end else begin : g_fx
        ot_s81_hc_ctfx_nt #(.NG(NG), .D(D), .S_RD(S_RD), .ML(ML), .AL(AL), .CHAIN_STEP(CHAIN_STEP), .LOCAL_EPOCH(CNL_PIN)) u_fx (
            .clk(clk), .rst_in(rst_c), .fv_in(fv_in), .fd_in(fd_in[FXW-1:0]), .fv(fv), .fdx(fdx), .fv_local(fv_local), .fdx_local(fdx_local),
            .tid(tid), .cs_n(cs[63:0]), .cs_s(cs[127:64]), .dl_in(dl_in), .dl_out(dl_m), .ul_in(ul_m), .ul_out(ul_out));
    end endgenerate
    ot_s81_hc_ctfs_nt #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .RLY(RLY)) u_fs (
        .clk(clk), .rst_in(rst_c), .rst_out(rst_out), .fvm(fvm), .fdm(fdm), .fv_out(fv_out), .fd_out(fd_out),
        .dl_in(dl_m), .dl_out(dl_out), .ul_in(ul_in), .ul_out(ul_m));
    // One physical source per horizontal CTNL column, same registered epoch.
    wire [16*S_RT-1:0] rq_col [0:3];
    wire [3:0] hs_run_col;
    wire [15:0] hs_c_col [0:3];
    wire [16*64-1:0]    hpr;                       // lane tile n = 4 bank + group
    wire [16*64*S_RT-1:0] hrq;
    wire [16*16-1:0]    yb;
    wire [16*32-1:0]    sq, cyo;
    wire [15:0]         nflt;
    wire [7:0]          hov, pwb, phs, hnz_d, pflt_d, hov_d;
    wire [8*16-1:0]     pob;
    wire [8*32-1:0]     hpo;                       // lane-pair tile m = 2 group + half
    genvar j, l, m;
    generate for (j = 0; j < 4; j = j + 1) begin : g_b
        for (l = 0; l < 4; l = l + 1) begin : g_l
            localparam integer n = 4 * j + l;
            if (!LANE_SPECIALIZE) begin : g_dynamic_lane
            ot_s81_hc_ctnl #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY), .PIN_STAGE(CNL_PIN), .CHAIN_STEP(CHAIN_STEP)) u_n (
                .clk(clk), .clk_io(clk), .rst_in(rst_c), .tid(tid), .bank(j[1:0]), .lane(l[1:0]), .last(last), .fv(fv), .fdx(fdx),
                .wb_v(hov[2 * l]), .wb_en(pwb[2 * l]), .wb_hs(phs[2 * l]), .wb_ob(pob[16 * (2 * l) +: 16]),
                .wb_d(hpo[64 * l +: 64]), .rq_q(rq_col[l]), .hs_run(hs_run_col[l]), .hs_c(hs_c_col[l]),
                .hpr(hpr[64 * n +: 64]), .hrq(hrq[64 * S_RT * n +: 64 * S_RT]),
                .cy_in(cy_in[32 * j +: 32]), .acc_in(l == 0 ? 32'd0 : acc[32 * (n > 0 ? n - 1 : 0) +: 32]),
                .sqn_in(l == 3 ? 32'd0 : sq[32 * (n < 15 ? n + 1 : 15) +: 32]),
                .sq_out(sq[32 * n +: 32]), .acc_out(acc[32 * n +: 32]), .cy_out(cyo[32 * n +: 32]),
                .yb(yb[16 * n +: 16]), .flt(nflt[n]));
            end else begin : g_fixed_lane
                localparam integer P_BITS=lane_payload_width(l);
                wire [O_D+S_RD*P_BITS-1:0] fd_lane;
                assign fd_lane[O_D-1:0]=fdx[O_D-1:0];
                for(genvar rp=0;rp<S_RD;rp=rp+1) begin : g_read_port
                    for(genvar pb=0;pb<P_BITS;pb=pb+1) begin : g_payload
                        localparam integer RAW_BIT=lane_payload_index(l,pb);
                        assign fd_lane[O_D+rp*P_BITS+pb]=fdx[O_D+rp*512+RAW_BIT];
                    end
                end
                if (l==0) begin : g_l0
            ot_s81_hc_ctnl_l0 #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY), .PIN_STAGE(CNL_PIN), .CHAIN_STEP(CHAIN_STEP)) u_n (
                .clk(clk), .rst_in(rst_c), .tid(tid), .bank(j[1:0]), .lane(l[1:0]), .last(last), .fv(fv), .fdx(fd_lane),
                .wb_v(hov[2 * l]), .wb_en(pwb[2 * l]), .wb_hs(phs[2 * l]), .wb_ob(pob[16 * (2 * l) +: 16]),
                .wb_d(hpo[64 * l +: 64]), .rq_q(rq_col[l]), .hs_run(hs_run_col[l]), .hs_c(hs_c_col[l]),
                .hpr(hpr[64 * n +: 64]), .hrq(hrq[64 * S_RT * n +: 64 * S_RT]),
                .cy_in(cy_in[32 * j +: 32]), .acc_in(l == 0 ? 32'd0 : acc[32 * (n > 0 ? n - 1 : 0) +: 32]),
                .sqn_in(l == 3 ? 32'd0 : sq[32 * (n < 15 ? n + 1 : 15) +: 32]),
                .sq_out(sq[32 * n +: 32]), .acc_out(acc[32 * n +: 32]), .cy_out(cyo[32 * n +: 32]),
                .yb(yb[16 * n +: 16]), .flt(nflt[n]));
                end
                else if (l==1) begin : g_l1
            ot_s81_hc_ctnl_l1 #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY), .PIN_STAGE(CNL_PIN), .CHAIN_STEP(CHAIN_STEP)) u_n (
                .clk(clk), .rst_in(rst_c), .tid(tid), .bank(j[1:0]), .lane(l[1:0]), .last(last), .fv(fv), .fdx(fd_lane),
                .wb_v(hov[2 * l]), .wb_en(pwb[2 * l]), .wb_hs(phs[2 * l]), .wb_ob(pob[16 * (2 * l) +: 16]),
                .wb_d(hpo[64 * l +: 64]), .rq_q(rq_col[l]), .hs_run(hs_run_col[l]), .hs_c(hs_c_col[l]),
                .hpr(hpr[64 * n +: 64]), .hrq(hrq[64 * S_RT * n +: 64 * S_RT]),
                .cy_in(cy_in[32 * j +: 32]), .acc_in(l == 0 ? 32'd0 : acc[32 * (n > 0 ? n - 1 : 0) +: 32]),
                .sqn_in(l == 3 ? 32'd0 : sq[32 * (n < 15 ? n + 1 : 15) +: 32]),
                .sq_out(sq[32 * n +: 32]), .acc_out(acc[32 * n +: 32]), .cy_out(cyo[32 * n +: 32]),
                .yb(yb[16 * n +: 16]), .flt(nflt[n]));
                end
                else if (l==2) begin : g_l2
            ot_s81_hc_ctnl_l2io #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY), .PIN_STAGE(CNL_PIN), .CHAIN_STEP(CHAIN_STEP)) u_n (
                .clk(clk), .clk_io(clk), .rst_in(rst_c), .tid(tid), .bank(j[1:0]), .lane(l[1:0]), .last(last), .fv(fv), .fdx(fd_lane),
                .wb_v(hov[2 * l]), .wb_en(pwb[2 * l]), .wb_hs(phs[2 * l]), .wb_ob(pob[16 * (2 * l) +: 16]),
                .wb_d(hpo[64 * l +: 64]), .rq_q(rq_col[l]), .hs_run(hs_run_col[l]), .hs_c(hs_c_col[l]),
                .hpr(hpr[64 * n +: 64]), .hrq(hrq[64 * S_RT * n +: 64 * S_RT]),
                .cy_in(cy_in[32 * j +: 32]), .acc_in(l == 0 ? 32'd0 : acc[32 * (n > 0 ? n - 1 : 0) +: 32]),
                .sqn_in(l == 3 ? 32'd0 : sq[32 * (n < 15 ? n + 1 : 15) +: 32]),
                .sq_out(sq[32 * n +: 32]), .acc_out(acc[32 * n +: 32]), .cy_out(cyo[32 * n +: 32]),
                .yb(yb[16 * n +: 16]), .flt(nflt[n]));
                end
                else if (l==3) begin : g_l3
            ot_s81_hc_ctnl_l3 #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY), .PIN_STAGE(CNL_PIN), .CHAIN_STEP(CHAIN_STEP)) u_n (
                .clk(clk), .rst_in(rst_c), .tid(tid), .bank(j[1:0]), .lane(l[1:0]), .last(last), .fv(fv), .fdx(fd_lane),
                .wb_v(hov[2 * l]), .wb_en(pwb[2 * l]), .wb_hs(phs[2 * l]), .wb_ob(pob[16 * (2 * l) +: 16]),
                .wb_d(hpo[64 * l +: 64]), .rq_q(rq_col[l]), .hs_run(hs_run_col[l]), .hs_c(hs_c_col[l]),
                .hpr(hpr[64 * n +: 64]), .hrq(hrq[64 * S_RT * n +: 64 * S_RT]),
                .cy_in(cy_in[32 * j +: 32]), .acc_in(l == 0 ? 32'd0 : acc[32 * (n > 0 ? n - 1 : 0) +: 32]),
                .sqn_in(l == 3 ? 32'd0 : sq[32 * (n < 15 ? n + 1 : 15) +: 32]),
                .sq_out(sq[32 * n +: 32]), .acc_out(acc[32 * n +: 32]), .cy_out(cyo[32 * n +: 32]),
                .yb(yb[16 * n +: 16]), .flt(nflt[n]));
                end
            end
        end
        assign cy_out[32 * j +: 32] = cyo[32 * (4 * j + 2) +: 32];
    end endgenerate
    generate for (m = 0; m < 8; m = m + 1) begin : g_p
        ot_s81_hc_ctpl #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .WIN(WIN), .WOUT(WOUT), .ML(ML), .AL(AL), .PIN_STAGE(1)) u_p (
            .clk(clk), .rst_in(rst_c), .grp(m[2:1]), .half(m[0]), .fv(fv_local), .fdx(fdx_local),
            .hpr({hpr[64 * (12 + m / 2) +: 64], hpr[64 * (8 + m / 2) +: 64], hpr[64 * (4 + m / 2) +: 64], hpr[64 * (m / 2) +: 64]}),
            .hov(hov[m]), .pwb(pwb[m]), .phs(phs[m]), .pob(pob[16 * m +: 16]), .hpo(hpo[32 * m +: 32]),
            .hov_d(hov_d[m]), .hnz_d(hnz_d[m]), .pflt_d(pflt_d[m]));
    end endgenerate
    assign cs = {acc[32 * 15 +: 32], acc[32 * 11 +: 32], acc[32 * 7 +: 32], acc[32 * 3 +: 32]};
    ot_s81_hc_retrow #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .CHAIN_STEP(CHAIN_STEP), .READ_STAGE(CNL_PIN)) u_ret (
        .clk(clk), .rst_in(rst_c), .tid(tid), .last(last), .fv(fv_local), .fdx(fdx_local[O_D-1:0]), .rb_in(rb_in), .rb_out(rb_out),
        .rq_q0(rq_col[0]), .rq_q1(rq_col[1]), .rq_q2(rq_col[2]), .rq_q3(rq_col[3]), .hs_run_c(hs_run_col),
        .hs_c0(hs_c_col[0]), .hs_c1(hs_c_col[1]), .hs_c2(hs_c_col[2]), .hs_c3(hs_c_col[3]),
        .hrq(hrq), .yb(yb), .cs(cs), .nflt(nflt), .hov_d(hov_d[0]), .hnz_d(hnz_d), .pflt_d(pflt_d));
endmodule

// ot_s81_hc_ret_column (HC-COLUMN 10-16): ONE hardened leaf per return column = ctra_column + ctrb_column of COLUMN c
// (YB_STAGE 1, PAYLOAD_STAGE 0), merged so the ctrb y beat (ctra relays) stays inside the leaf.  The previous row's
// ctrn_col slice c feeds it directly (own + partner chunks, header, valid).  cs_in / hov_in are the raw sources at
// COLUMN 3 / COLUMN 0 and the relayed nets (cs_rel / hov_rel) elsewhere: the parent wires both pins of a non-relaying
// column to the relay net, so no column carries an unused long join.
module ot_s81_hc_ret_column #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, CHAIN_STEP = AL, READ_STAGE = 1,
    parameter integer COLUMN = 0
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire [7:0]             tid,
    input  wire                   last,
    input  wire [S_RD+4:0]        fv,
    input  wire [O_D-1:0]         fdx,
    input  wire [S_RT+3:0]        rv_in,            // from the previous row's ctrn_col slice COLUMN
    input  wire [107:0]           hdr_in,
    input  wire [255:0]           ao_in, bo_in, ap_in, bp_in,
    output wire [S_RT+3:0]        rvm,              // to this row's ctrn_col slice COLUMN
    output wire [107:0]           hdr,
    output wire [255:0]           a_rdm, b_rdm,     // to slice COLUMN (own) and slice (COLUMN+2)%4 (partner)
    output wire [16*S_RT-1:0]     rq_q,             // to this x-column's four ctnl tiles
    output wire                   hs_run,
    output wire [15:0]            hs_c,
    input  wire [4*64*S_RT-1:0]   hrq_col,          // ctnl[j][COLUMN].hrq, j = 0..3 (lane COLUMN + 4 j), 4 slots each
    input  wire [63:0]            yb_loc,           // ctnl[j][COLUMN].yb, j = 0..3
    output wire [63:0]            yb_fwd,
    input  wire [191:0]           yb_peer,          // the other three columns' yb_fwd, ascending column
    input  wire [127:0]           cs_in,            // COLUMN 3: the ctnl column-3 accumulators; else the cs relay net
    input  wire [127:0]           cs_rel,
    output wire [127:0]           cs_fwd,
    input  wire                   hov_in,           // COLUMN 0: ctpl m0 hov_d; else the hov relay net
    input  wire                   hov_rel,
    output wire                   hov_fwd,
    input  wire [3:0]             nflt_col,         // ctnl[j][COLUMN].flt, j = 0..3
    input  wire                   hnz_n, hnz_s, pflt_n, pflt_s,   // ctpl group COLUMN half 0 / 1
    output wire                   flag_fault, flag_hnz,
    input  wire [2:0]             peer_fault, peer_hnz
);
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, SH = S_RT / 2;
    localparam integer PC = (COLUMN + 2) % 4;
    initial if (COLUMN < 0 || COLUMN > 3 || S_RT != 4) $fatal(1, "ot_s81_hc_ret_column: COLUMN 0..3, S_RT 4");
    genvar rs, rc, bank, q;
    wire [511:0] a_rdp, b_rdp;
    generate for (rs = 0; rs < 2; rs = rs + 1) begin : g_rs
        for (rc = 0; rc < 2; rc = rc + 1) begin : g_rc
            localparam integer Q = 8 * rs + COLUMN + 4 * rc, QS = Q - 2, A = 14 + Q;
            assign a_rdp[64 * (2 * rs + rc) +: 64] = ao_in[128 * rs + 64 * rc +: 64];
            if (QS >= 0) begin : g_sh
                assign a_rdp[256 + 64 * (2 * rs + rc) +: 64] = ap_in[128 * (QS / 8) + 64 * ((QS % 8) / 4) +: 64];
            end else begin : g_z
                assign a_rdp[256 + 64 * (2 * rs + rc) +: 64] = 64'd0;
            end
            assign b_rdp[64 * (2 * rs + rc) +: 64] = bo_in[128 * rs + 64 * rc +: 64];
            if (A / 8 == 1) begin : g_bsa
                assign b_rdp[256 + 64 * (2 * rs + rc) +: 64] = ap_in[128 + 64 * ((A % 8) / 4) +: 64];
            end else begin : g_bsb
                assign b_rdp[256 + 64 * (2 * rs + rc) +: 64] = bp_in[128 * (A / 8 - 2) + 64 * ((A % 8) / 4) +: 64];
            end
        end
    end endgenerate
    wire [2*64*SH-1:0] hr_n, hr_s, hrb_n, hrb_s;       // [bank][slot]: N = j 0/1, S = j 2/3
    generate for (bank = 0; bank < 2; bank = bank + 1) begin : g_h
        for (q = 0; q < SH; q = q + 1) begin : g_q
            assign hr_n [64 * (SH * bank + q) +: 64] = hrq_col[64 * S_RT * bank       + 64 * q +: 64];
            assign hr_s [64 * (SH * bank + q) +: 64] = hrq_col[64 * S_RT * (bank + 2) + 64 * q +: 64];
            assign hrb_n[64 * (SH * bank + q) +: 64] = hrq_col[64 * S_RT * bank       + 64 * (q + SH) +: 64];
            assign hrb_s[64 * (SH * bank + q) +: 64] = hrq_col[64 * S_RT * (bank + 2) + 64 * (q + SH) +: 64];
        end
    end endgenerate
    wire [255:0] yb_rel;                              // the relayed y beat for ctrb: own yb_fwd + the peers'
    generate for (q = 0; q < 16; q = q + 1) begin : g_yr
        localparam integer CC = q % 4, K = q / 4, P = (CC < COLUMN) ? CC : CC - 1;
        if (CC == COLUMN) begin : g_own
            assign yb_rel[16 * q +: 16] = yb_fwd[16 * K +: 16];
        end else begin : g_peer
            assign yb_rel[16 * q +: 16] = yb_peer[64 * P + 16 * K +: 16];
        end
    end endgenerate
    ot_s81_hc_ctra_column #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),.ML(ML),.AL(AL),.CHAIN_STEP(CHAIN_STEP),.READ_STAGE(READ_STAGE),.COLUMN(COLUMN),.YB_STAGE(1),.PAYLOAD_STAGE(0)) u_a (
        .clk(clk), .rst_in(rst_in), .tid(tid), .last(last), .fv(fv), .fdx(fdx), .rv_in(rv_in), .rdh_in(hdr_in), .rdp_in(a_rdp),
        .rvm(rvm), .peer_fault(peer_fault), .peer_hnz(peer_hnz), .yb_loc(yb_loc), .yb_fwd(yb_fwd), .yb_peer(yb_peer),
        .cs_fwd(cs_fwd), .cs_rel(cs_rel), .hov_fwd(hov_fwd), .hov_rel(hov_rel),
        .rdm(a_rdm), .rq_q(rq_q), .hs_run(hs_run), .hs_c(hs_c),
        .rq_q_c1(), .rq_q_c2(), .rq_q_c3(), .hs_run_c1(), .hs_run_c2(), .hs_run_c3(), .hs_c_c1(), .hs_c_c2(), .hs_c_c3(),
        .hrq_n(hr_n), .hrq_s(hr_s), .yb_n(128'd0), .yb_s(128'd0), .cs(cs_in),
        .nflt_n(nflt_col[1:0]), .nflt_s(nflt_col[3:2]), .hov_d(hov_in),
        .hnz_n(hnz_n), .hnz_s(hnz_s), .pflt_n(pflt_n), .pflt_s(pflt_s),
        .flag_fault(flag_fault), .flag_hnz(flag_hnz), .header_delay(hdr));
    ot_s81_hc_ctrb_column #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),.ML(ML),.AL(AL),.CHAIN_STEP(CHAIN_STEP),.READ_STAGE(READ_STAGE),.COLUMN(COLUMN),.YB_STAGE(1),.PAYLOAD_STAGE(0)) u_b (
        .clk(clk), .rst_in(rst_in), .tid(tid), .last(last), .fv(fv), .fdx(fdx), .rv_in(rv_in), .rdh_in(hdr_in), .rdp_in(b_rdp),
        .rdm(b_rdm), .hrq_n(hrb_n), .hrq_s(hrb_s), .yb_n(yb_rel[127:0]), .yb_s(yb_rel[255:128]));
endmodule
