// ot_hgi_seq_au.sv -- AU child of the R25GQ sequencer split (el1013-hbm-seq-split, 2026-10-13).
// Holds the DYN table builder (ps .. dsq, tbc, trow), the record row register hrow_q and the address pipeline A0 .. A5
// with the A6 range flags: every table -> row -> A1 and A4 -> A5 path of the flat ot_hgi_seq stays inside this child.
// The arithmetic is MOVED from ot_hgi_seq.sv unchanged; the seam contract is ot_hgi_seq_seam.svh (rules R1-R4, X1).
// Seams: S1 (FE item) and S4 (BE re-injection) are registered at the pin, then selected into A0; S3 (result) leaves from
// TX flops.
`default_nettype none
module ot_hgi_seq_au #(
    parameter integer RW   = 4096,
    parameter integer NOS  = 160,
    parameter integer USE_MACRO = 0,
    parameter integer DS_TPL = 2,
    parameter integer DS_WIN = 128,
    parameter integer DS_SCAN = 16384,
    parameter integer DS_TOPK = 512,
    parameter integer DS_HDL = 9,
    parameter integer QD = 4,
    parameter integer FD = 12,
    parameter integer IKS_I = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    rank,
    // S5a / S5b  BE -> AU
    input  wire          be_jl_v,
    input  wire [19:0]   be_jl_pos,
    input  wire [17:0]   be_jl_token,
    input  wire          be_js,
    // AU -> FE
    output reg           au_tbl_ok,
    // S1  FE -> AU (lands in A0)
    input  wire          fe_s1_v,
    input  wire [39:0]   fe_s1_base,
    input  wire [31:0]   fe_s1_lstr,
    input  wire [31:0]   fe_s1_l1str,
    input  wire [31:0]   fe_s1_str,
    input  wire [26:0]   fe_s1_dmul,
    input  wire [5:0]    fe_s1_dsel,
    input  wire [5:0]    fe_s1_nsel,
    input  wire [19:0]   fe_s1_n,
    input  wire          fe_s1_idx,
    input  wire [1:0]    fe_s1_sp,
    input  wire [15:0]   fe_s1_L,
    input  wire [15:0]   fe_s1_L1,
    input  wire [2:0]    fe_s1_slot,
    input  wire [2:0]    fe_s1_j,
    input  wire [((QD <= 2) ? 1 : $clog2(QD))-1:0] fe_s1_tag,
    input  wire          fe_s1_last,
    input  wire          fe_s1_isI,
    input  wire          fe_s1_hi,
    input  wire          fe_s1_et,
    input  wire [2:0]    fe_hslot,
    // S4  BE -> AU (lands in A0)
    input  wire          be_s4_v,
    input  wire [23:0]   be_s4_ph,
    input  wire [39:0]   be_s4_base,
    input  wire [26:0]   be_s4_dmul,
    input  wire [1:0]    be_s4_sp,
    input  wire [31:0]   be_s4_x,
    input  wire [2:0]    be_s4_j,
    input  wire [((QD <= 2) ? 1 : $clog2(QD))-1:0] be_s4_tag,
    // S3  AU -> BE
    output reg           au_s3_v,
    output reg           au_s3_be,
    output reg  [((QD <= 2) ? 1 : $clog2(QD))-1:0] au_s3_tag,
    output reg  [2:0]    au_s3_j,
    output reg           au_s3_last,
    output reg           au_s3_isI,
    output reg  [63:0]   au_s3_acc,
    output reg  [20:0]   au_s3_n,
    output reg           au_s3_px,
    output reg           au_s3_pn,
    output reg           au_s3_flt,
    output reg           au_s3_badd,
    output reg  [17:0]   au_s3_iax,
    output reg           au_s3_ixb,
    output reg  [17:0]   au_s3_ian,
    output reg           au_s3_inb,
    output reg           au_s3_ihbm
);
`include "ot_hgi_seq_seam.svh"
    // ---- pin: rank (hold-delay stage + pin flop, as the flat design)
    wire [8-1:0] rank_h; ot_hgi_seq_hd #(.W(8), .N(2)) u_hdly_rank (.a(rank), .y(rank_h));
    reg [7:0] rank_r;
    always @(posedge clk) rank_r <= rank_h;
    // ---- reset: this child's OWN release synchroniser (R3 / R4)
    (* keep = 1 *) reg [1:0] rs_a;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs_a <= 2'b00; else rs_a <= {rs_a[0], 1'b1};
    wire rn_a = rs_a[1];
    localparam integer QB = (QD <= 2) ? 1 : $clog2(QD);
    // ------------------------------------------------------------------ field positions (spec.json, v1.0)
    localparam integer H_UNIT = 124, H_OP = 118, H_WAIT = 102, H_PRED = 100, H_OPND = 93, H_TMPL = 92, H_SLOT = 89,
                       H_PARAM = 64;
    localparam integer M_SPACE = 0, M_IBC = 5, M_IDX = 6, M_BASE = 8, M_N = 48, M_M = 68, M_STRIDE = 88,
                       M_LSTR = 136, M_DSEL = 168, M_DMUL = 174, M_NSEL = 201, M_L1STR = 207;
    function automatic [63:0] sx32(input [31:0] v); sx32 = {{32{v[31]}}, v}; endfunction
    function automatic [63:0] s3(input [63:0] a, input [63:0] b, input [63:0] c); s3 = a ^ b ^ c; endfunction
    function automatic [63:0] c3(input [63:0] a, input [63:0] b, input [63:0] c);
        c3 = {((a[62:0] & b[62:0]) | (a[62:0] & c[62:0]) | (b[62:0] & c[62:0])), 1'b0};
    endfunction
    // range check of an effective base by space (HBM 2^40 bytes, VM 2^18 words; STREAM / NONE unchecked).  ap = 1
    // (descriptor operands): VM words [2^18, 2^18 + 2^16) are the HC weight aperture.  The CP's own VM reads stay below 2^18.
    function automatic base_bad(input [1:0] sp, input [63:0] a, input ap);
        base_bad = (sp == 2'd0) ? (a[63:40] != 24'd0) :
                   (sp == 2'd1) ? ((a[63:19] != 45'd0) || (a[18] && (!ap || a[17:16] != 2'd0))) : 1'b0;
    endfunction
    function automatic dyn_rsv(input [5:0] c);           // codes with no value on r25
        dyn_rsv = (c >= 6'd9 && c <= 6'd14) || (c >= 6'd41);
    endfunction
    // ---- seam RX (R1): job load, job start, the record's slot
    reg be_jl_v_r, be_js_r; reg [19:0] be_jl_pos_r; reg [17:0] be_jl_token_r; reg [2:0] hslot_r;
    always @(posedge clk) begin be_jl_pos_r <= be_jl_pos; be_jl_token_r <= be_jl_token; hslot_r <= fe_hslot; end
    // AU copies of the job's pos / pos + 1 / token (loaded on the job-load RX; tbc restarts in the same edge, so the
    // table build sees pos exactly as the flat design does)
    reg [17:0] token; reg [19:0] pos; reg [20:0] pos1_q;
    always @(posedge clk) if (be_jl_v_r) begin pos <= be_jl_pos_r; pos1_q <= {1'b0, be_jl_pos_r} + 21'd1; token <= be_jl_token_r; end
    reg        s1_v_r; (* keep = 1 *) reg [1:0] s4_v_r;   // S1 / S4 RX valids (declared here: used by av below)
    reg [5:0] av;                        // stage valids A0 .. A5
    reg [6:0] tbc;                       // table build counter (restarts on the job-load RX)
`ifdef OT_HGI_SEQ_MUT_SEAM_RST
    // NEGATIVE CONTROL (stale reset copy): av / tbc on the raw rst_n, no av flush on be_js, no tbc restart on the job load
    always @(posedge clk or negedge rn_a)
        if (!rn_a) begin be_jl_v_r <= 1'b0; be_js_r <= 1'b0; au_s3_v <= 1'b0; au_tbl_ok <= 1'b0; end
        else begin be_jl_v_r <= be_jl_v; be_js_r <= be_js; au_s3_v <= av[5]; au_tbl_ok <= tbc[6]; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin av <= 6'd0; tbc <= 7'd0; end
        else begin av <= {av[4:0], s4_v_r[0] | s1_v_r}; if (!tbc[6]) tbc <= tbc + 7'd1; end
`else
    always @(posedge clk or negedge rn_a)
        if (!rn_a) begin be_jl_v_r <= 1'b0; be_js_r <= 1'b0; av <= 6'd0; tbc <= 7'd0; au_s3_v <= 1'b0; au_tbl_ok <= 1'b0; end
        else begin
            be_jl_v_r <= be_jl_v; be_js_r <= be_js;
            av <= be_js_r ? 6'd0 : {av[4:0], s4_v_r[0] | s1_v_r};     // a job start flushes the pipe
            if (be_jl_v_r) tbc <= 7'd0; else if (!tbc[6]) tbc <= tbc + 7'd1;
            au_s3_v <= av[5]; au_tbl_ok <= tbc[6];
        end
`endif
`ifndef SYNTHESIS
    reg seam_err; initial seam_err = 1'b0;
    reg rst_seen; initial rst_seen = 1'b0;          // the probe is armed by the first reset (2-state simulators start
    always @(negedge rst_n) rst_seen <= 1'b1;       // flops at arbitrary values: nothing before a reset is a seam event)
    always @(posedge clk) if (rst_seen && rn_a && s4_v_r[0] && s1_v_r) begin
        seam_err <= 1'b1; $error("ot_hgi_seq_au: S1 and S4 valid in one cycle (injector hold violated)");
    end
`endif
    // ------------------------------------------------------------------ DYN: per-slot table, built at job start
    // The DS full-shape selectors depend on (pos, slot, rank) only: pos and rank are fixed for a job, so the 7-stage
    // registered bank (v1's, unchanged arithmetic) is run once per slot at the job start (8 cycles a slot, 64 in all,
    // hidden under the first record fetch) and captured into trow[slot] = {DS 40 .. 16, p1, ps} (27 x 32 b).
    function automatic [20:0] mn(input [20:0] a, input [20:0] b); mn = (a < b) ? a : b; endfunction
    function automatic [20:0] cdv(input [20:0] a, input integer sh);       // ceil(a / 2^sh)
        cdv = (a + ((21'd1 << sh) - 21'd1)) >> sh;
    endfunction
    // (tbc declared above)             // table build counter: slot tbc[5:3], capture at tbc[2:0] == 7; done at 64
    wire [2:0] h_slot = tbc[5:3];
    reg [20:0] ps, p1, q_p1, q_n2, q_ns1, q_ns2, q_win, q_sc1, q_sc2, q_scr, q_ps;
    wire [19:0] pos_d; ot_hgi_seq_hd #(.W(20), .N(2)) u_hdly_pos (.a(pos), .y(pos_d));   // v2.3: FF hold -8.6 ps pos -> p1
    reg [20:0] q_sc1b, q_psb;
    reg [31:0] dsq [16:40];
    wire [28:0] rp0 = rank_r[0] ? {8'd0, q_sc1}       : 29'd0, rp1 = rank_r[1] ? {7'd0, q_sc1, 1'b0} : 29'd0,
                rp2 = rank_r[2] ? {6'd0, q_sc1, 2'b0} : 29'd0, rp3 = rank_r[3] ? {5'd0, q_sc1, 3'b0} : 29'd0,
                rp4 = rank_r[4] ? {4'd0, q_sc1, 4'b0} : 29'd0, rp5 = rank_r[5] ? {3'd0, q_sc1, 5'b0} : 29'd0,
                rp6 = rank_r[6] ? {2'd0, q_sc1, 6'b0} : 29'd0, rp7 = rank_r[7] ? {1'd0, q_sc1, 7'b0} : 29'd0;
    function automatic [57:0] fa3(input [28:0] a, input [28:0] b, input [28:0] c);   // {carry << 1, sum}
        fa3 = {((a & b) | (a & c) | (b & c)) << 1, a ^ b ^ c};
    endfunction
    wire [57:0] ra = fa3(rp0, rp1, rp2), rb = fa3(rp3, rp4, rp5);
    wire [57:0] rc = fa3(ra[28:0], ra[57:29], rb[28:0]), rd = fa3(rb[57:29], rp6, rp7);
    wire [57:0] re = fa3(rc[28:0], rc[57:29], rd[28:0]);
    wire [57:0] rf = fa3(re[28:0], re[57:29], rd[57:29]);
    reg [28:0] rs_s, rs_c; reg [15:0] rs_l; reg [13:0] rs_hs, rs_hc; reg [28:0] q_rsc_r;
    reg [20:0] q_psc, q_psd, q_sc1c, q_sc1d, q_sc1e; reg [20:0] r_diff; reg r_ge;
    always @(posedge clk) begin
        ps <= {1'b0, pos} + {18'd0, h_slot};                                   // stage 1
        p1 <= {1'b0, pos_d} + {18'd0, h_slot} + 21'd1;
        q_ps <= ps; q_p1 <= p1; q_n2 <= {1'b0, p1[20:1]};                       // stage 2
        q_ns1 <= mn(p1, DS_TOPK); q_ns2 <= mn({1'b0, p1[20:1]}, DS_TOPK); q_win <= mn(p1, DS_WIN);
        q_sc1 <= cdv(p1, DS_TPL); q_sc2 <= cdv({1'b0, p1[20:1]}, DS_TPL); q_scr <= cdv(mn(p1, DS_SCAN), DS_TPL);
        rs_s <= rf[28:0]; rs_c <= rf[57:29];                                     // stage 3 (carry-save rank x sc1)
        q_sc1b <= q_sc1; q_psb <= q_ps;
        dsq[16] <= q_win;            dsq[17] <= q_p1;             dsq[18] <= q_n2;             dsq[19] <= q_ns1;
        dsq[20] <= q_ns2;            dsq[21] <= q_win;            dsq[22] <= q_win + q_ns1;    dsq[23] <= q_win + q_ns2;
        dsq[24] <= q_sc1;            dsq[25] <= q_sc2;            dsq[26] <= q_scr;            dsq[27] <= mn(q_sc1, DS_TOPK);
        dsq[28] <= mn(q_sc2, DS_TOPK); dsq[29] <= mn(q_scr, DS_TOPK);
        dsq[30] <= cdv(q_sc1, 4);    dsq[31] <= cdv(q_sc1, 3);    dsq[32] <= cdv(q_sc2, 4);    dsq[33] <= cdv(q_scr, 4);
        dsq[34] <= cdv(q_win, 5);    dsq[35] <= cdv(dsq[22], 5);  dsq[36] <= cdv(dsq[23], 5);
        dsq[37] <= q_win - 21'd1;    dsq[38] <= {11'd0, q_win} << DS_HDL; dsq[39] <= {11'd0, q_win - 21'd1} << DS_HDL;
        rs_l <= {1'b0, rs_s[14:0]} + {1'b0, rs_c[14:0]}; rs_hs <= rs_s[28:15]; rs_hc <= rs_c[28:15];
        q_psc <= q_psb; q_sc1c <= q_sc1b;
        q_rsc_r <= {rs_hs + rs_hc + {13'd0, rs_l[15]}, rs_l[14:0]};
        q_psd <= q_psc; q_sc1d <= q_sc1c;
        r_ge <= (q_rsc_r[28:21] == 8'd0) && (q_psd >= q_rsc_r[20:0]); r_diff <= q_psd - q_rsc_r[20:0];
        q_sc1e <= q_sc1d;
        dsq[40] <= (r_ge && (r_diff < q_sc1e)) ? {11'd0, r_diff >> 3} : {11'd0, cdv(q_sc1e, 3)};      // stage 7
    end
    localparam integer TRW = 27 * 32;
    reg [8*TRW-1:0] trow;                // slot t at [t*TRW +: TRW]: field 0 ps, 1 p1, 2 + (c - 16) DS code c
    integer ti;
    always @(posedge clk) if (!tbc[6] && tbc[2:0] == 3'd7)
        for (ti = 0; ti < 8; ti = ti + 1) if (h_slot == ti[2:0])
            trow[ti*TRW +: TRW] <= {dsq[40], dsq[39], dsq[38], dsq[37], dsq[36], dsq[35], dsq[34], dsq[33], dsq[32],
                                    dsq[31], dsq[30], dsq[29], dsq[28], dsq[27], dsq[26], dsq[25], dsq[24], dsq[23],
                                    dsq[22], dsq[21], dsq[20], dsq[19], dsq[18], dsq[17], dsq[16], {11'd0, p1}, {11'd0, ps}};
    // (every module value a function reads is an argument: simulators re-evaluate a continuous assign on its arguments)
    function automatic [TRW-1:0] trow_of(input [8*TRW-1:0] tv, input [2:0] s);
        integer q; begin trow_of = {TRW{1'b0}}; for (q = 0; q < 8; q = q + 1) if (s == q[2:0]) trow_of = tv[q*TRW +: TRW]; end
    endfunction
    // ================================================================== AU: one descriptor a cycle
    // sideband bundle {isI, last, j, tag, sp, pn, px, flt, n[21], be}
    localparam integer SBW = 32 + QB;
    localparam integer SB_N = 1, SB_FLT = 22, SB_PX = 23, SB_PN = 24, SB_SP = 25, SB_TAG = 27, SB_J = 27 + QB,
                       SB_LAST = 30 + QB, SB_ISI = 31 + QB;
    // A0: the item (FE pop or BE re-injection)
    reg        a0_be, a0_idx, a0_last, a0_isI, a0_hi, a0_et;
    reg [63:0] a0_b64; reg [31:0] a0_lstr, a0_l1str, a0_str, a0_x; reg [26:0] a0_dmul; reg [5:0] a0_dsel, a0_nsel;
    reg [19:0] a0_n; reg [1:0] a0_sp; reg [15:0] a0_L, a0_L1; reg [2:0] a0_slot, a0_j; reg [QB-1:0] a0_tag;
    // S1 / S4 RX flops (R1: every seam input is registered at the pin; the X1 exception of the first seam draft is
    // gone -- a port driving the A0 select had 374 loads).  The select has two kept copies (<= ~256 loads each).
    reg [39:0] s1_base_r; reg [31:0] s1_lstr_r, s1_l1str_r, s1_str_r; reg [26:0] s1_dmul_r; reg [5:0] s1_dsel_r, s1_nsel_r;
    reg [19:0] s1_n_r; reg s1_idx_r; reg [1:0] s1_sp_r; reg [15:0] s1_L_r, s1_L1_r; reg [2:0] s1_slot_r, s1_j_r; reg [QB-1:0] s1_tag_r;
    reg        s1_last_r, s1_isI_r, s1_hi_r, s1_et_r;
    reg [23:0] s4_ph_r; reg [39:0] s4_base_r; reg [26:0] s4_dmul_r; reg [1:0] s4_sp_r; reg [31:0] s4_x_r; reg [2:0] s4_j_r; reg [QB-1:0] s4_tag_r;
    always @(posedge clk or negedge rn_a)
        if (!rn_a) begin s1_v_r <= 1'b0; s4_v_r <= 2'b00; end
        else begin s1_v_r <= fe_s1_v; s4_v_r <= {2{be_s4_v}}; end
    always @(posedge clk) begin
        s1_base_r <= fe_s1_base; s1_lstr_r <= fe_s1_lstr; s1_l1str_r <= fe_s1_l1str; s1_str_r <= fe_s1_str; s1_dmul_r <= fe_s1_dmul;
        s1_dsel_r <= fe_s1_dsel; s1_nsel_r <= fe_s1_nsel; s1_n_r <= fe_s1_n; s1_idx_r <= fe_s1_idx; s1_sp_r <= fe_s1_sp;
        s1_L_r <= fe_s1_L; s1_L1_r <= fe_s1_L1; s1_slot_r <= fe_s1_slot; s1_j_r <= fe_s1_j; s1_tag_r <= fe_s1_tag;
        s1_last_r <= fe_s1_last; s1_isI_r <= fe_s1_isI; s1_hi_r <= fe_s1_hi; s1_et_r <= fe_s1_et;
        s4_ph_r <= be_s4_ph; s4_base_r <= be_s4_base; s4_dmul_r <= be_s4_dmul; s4_sp_r <= be_s4_sp; s4_x_r <= be_s4_x;
        s4_j_r <= be_s4_j; s4_tag_r <= be_s4_tag;
    end
    always @(posedge clk) begin                    // A0, select copy 0: base, x, narrow fields
        if (s4_v_r[0]) begin
            a0_be <= 1'b1; a0_b64 <= {s4_ph_r, s4_base_r}; a0_x <= s4_x_r; a0_dsel <= 6'd0; a0_nsel <= 6'd0; a0_n <= 20'd0;
            a0_idx <= 1'b0; a0_sp <= s4_sp_r; a0_slot <= 3'd0; a0_j <= s4_j_r;
            a0_tag <= s4_tag_r; a0_last <= 1'b0; a0_isI <= 1'b0; a0_hi <= 1'b0; a0_et <= 1'b0;
        end else begin
            a0_be <= 1'b0; a0_b64 <= {24'd0, s1_base_r}; a0_x <= 32'd0;
            a0_dsel <= s1_dsel_r; a0_nsel <= s1_nsel_r; a0_n <= s1_n_r; a0_idx <= s1_idx_r;
            a0_sp <= s1_sp_r; a0_slot <= s1_slot_r; a0_j <= s1_j_r; a0_tag <= s1_tag_r;
            a0_last <= s1_last_r; a0_isI <= s1_isI_r; a0_hi <= s1_hi_r;
            a0_et <= s1_et_r;
        end
    end
    always @(posedge clk) begin                    // A0, select copy 1: strides, multiplier, loop counters
        if (s4_v_r[1]) begin
            a0_lstr <= 32'd0; a0_l1str <= 32'd0; a0_str <= 32'd0; a0_dmul <= s4_dmul_r; a0_L <= 16'd0; a0_L1 <= 16'd0;
        end else begin
            a0_lstr <= s1_lstr_r; a0_l1str <= s1_l1str_r; a0_str <= s1_str_r; a0_dmul <= s1_dmul_r; a0_L <= s1_L_r; a0_L1 <= s1_L1_r;
        end
    end
    // A1: DYN lookups (table row of the record's slot), n, the per-descriptor checks
    function automatic [31:0] dynx(input [5:0] c, input [TRW-1:0] row, input [2:0] s, input [15:0] L, input [15:0] L1,
                                   input [19:0] pv, input [20:0] p1v, input [17:0] tv, input [7:0] rv);
        integer q; begin
            case (c)
                6'd0: dynx = 32'd0;
                6'd1: dynx = {12'd0, pv};
                6'd2: dynx = {11'd0, p1v};
                6'd3: dynx = {14'd0, tv};
                6'd4: dynx = {16'd0, L};
                6'd5: dynx = {24'd0, rv};
                6'd6: dynx = {29'd0, s};
                6'd7: dynx = row[0 +: 32];
                6'd8: dynx = {16'd0, L1};
                6'd15: dynx = row[32 +: 32];
                default: begin dynx = 32'd0; for (q = 16; q <= 40; q = q + 1) if (c == q[5:0]) dynx = row[(q - 14)*32 +: 32]; end
            endcase
        end
    endfunction
    // v2.3 (route 905100ec5: a0_slot -> 8:1 row mux -> 27:1 code mux -> a1_x): the record's table row is registered
    // from h (fixed for the record; an item reaches A1 >= 2 cycles after its header pop, h of the next record lands
    // >= 1 cycle after the last item's A1)
    reg [TRW-1:0] hrow_q;
    always @(posedge clk) hrow_q <= trow_of(trow, hslot_r);   // fe_hslot: h's slot, one seam hop
    wire [TRW-1:0] a0_row = hrow_q;
    wire [31:0] dyn_d = dynx(a0_dsel, a0_row, a0_slot, a0_L, a0_L1, pos, pos1_q, token, rank_r),
                dyn_n = dynx(a0_nsel, a0_row, a0_slot, a0_L, a0_L1, pos, pos1_q, token, rank_r);
    wire a0_flt = !a0_be && ((a0_isI && (a0_idx || a0_nsel == 6'd63 || (a0_sp != 2'd1 && !(IKS_I != 0 && a0_sp == 2'd0)))) ||
                             (!a0_isI && (a0_idx || a0_nsel == 6'd63) && !a0_hi) ||
                             (!a0_idx && dyn_rsv(a0_dsel)) ||
                             (a0_nsel != 6'd0 && a0_nsel != 6'd63 && dyn_rsv(a0_nsel)) ||
                             (a0_et && a0_j == 3'd0 && a0_sp != 2'd1));
    reg [63:0] a1_b64; reg [31:0] a1_lstr, a1_l1str, a1_x, a1_str; reg [26:0] a1_dmul; reg [15:0] a1_L, a1_L1;
    reg [SBW-1:0] a1_sb;
    always @(posedge clk) begin
        a1_b64 <= a0_b64; a1_lstr <= a0_lstr; a1_l1str <= a0_l1str; a1_dmul <= a0_dmul; a1_L <= a0_L; a1_L1 <= a0_L1; a1_str <= a0_str;
        a1_x <= a0_be ? a0_x : (a0_idx ? 32'd0 : dyn_d);
        a1_sb <= {a0_isI, a0_last, a0_j, a0_tag, a0_sp, !a0_be && !a0_isI && a0_nsel == 6'd63, !a0_be && !a0_isI && a0_idx,
                  a0_flt, (a0_nsel == 6'd0) ? {1'b0, a0_n} : dyn_n[20:0], a0_be};
    end
    // A2: 60 partial-product rows (base, L x lstride, L1 x l1stride, X x dyn_mul) -> CSA 60 -> 40 -> 27 -> 18 -> 12 -> 8
    reg [60*64-1:0] pr; reg [40*64-1:0] v1; reg [27*64-1:0] v2; reg [18*64-1:0] v3; reg [12*64-1:0] v4; reg [8*64-1:0] v5;
    integer q2;
    always @* begin
        pr[0 +: 64] = a1_b64;
        for (q2 = 0; q2 < 16; q2 = q2 + 1) begin
            pr[(1 + q2)*64 +: 64]  = a1_L[q2]  ? (sx32(a1_lstr) << q2)  : 64'd0;
            pr[(17 + q2)*64 +: 64] = a1_L1[q2] ? (sx32(a1_l1str) << q2) : 64'd0;
        end
        for (q2 = 0; q2 < 27; q2 = q2 + 1) pr[(33 + q2)*64 +: 64] = a1_dmul[q2] ? ({32'd0, a1_x} << q2) : 64'd0;
        for (q2 = 0; q2 < 20; q2 = q2 + 1) begin
            v1[(2*q2)*64 +: 64]     = s3(pr[(3*q2)*64 +: 64], pr[(3*q2+1)*64 +: 64], pr[(3*q2+2)*64 +: 64]);
            v1[(2*q2+1)*64 +: 64]   = c3(pr[(3*q2)*64 +: 64], pr[(3*q2+1)*64 +: 64], pr[(3*q2+2)*64 +: 64]);
        end
        for (q2 = 0; q2 < 13; q2 = q2 + 1) begin
            v2[(2*q2)*64 +: 64]     = s3(v1[(3*q2)*64 +: 64], v1[(3*q2+1)*64 +: 64], v1[(3*q2+2)*64 +: 64]);
            v2[(2*q2+1)*64 +: 64]   = c3(v1[(3*q2)*64 +: 64], v1[(3*q2+1)*64 +: 64], v1[(3*q2+2)*64 +: 64]);
        end
        v2[26*64 +: 64] = v1[39*64 +: 64];
        for (q2 = 0; q2 < 9; q2 = q2 + 1) begin
            v3[(2*q2)*64 +: 64]     = s3(v2[(3*q2)*64 +: 64], v2[(3*q2+1)*64 +: 64], v2[(3*q2+2)*64 +: 64]);
            v3[(2*q2+1)*64 +: 64]   = c3(v2[(3*q2)*64 +: 64], v2[(3*q2+1)*64 +: 64], v2[(3*q2+2)*64 +: 64]);
        end
        for (q2 = 0; q2 < 6; q2 = q2 + 1) begin
            v4[(2*q2)*64 +: 64]     = s3(v3[(3*q2)*64 +: 64], v3[(3*q2+1)*64 +: 64], v3[(3*q2+2)*64 +: 64]);
            v4[(2*q2+1)*64 +: 64]   = c3(v3[(3*q2)*64 +: 64], v3[(3*q2+1)*64 +: 64], v3[(3*q2+2)*64 +: 64]);
        end
        for (q2 = 0; q2 < 4; q2 = q2 + 1) begin
            v5[(2*q2)*64 +: 64]     = s3(v4[(3*q2)*64 +: 64], v4[(3*q2+1)*64 +: 64], v4[(3*q2+2)*64 +: 64]);
            v5[(2*q2+1)*64 +: 64]   = c3(v4[(3*q2)*64 +: 64], v4[(3*q2+1)*64 +: 64], v4[(3*q2+2)*64 +: 64]);
        end
    end
    reg [8*64-1:0] a2_r; reg [15:0] a2_L; reg [31:0] a2_str; reg [SBW-1:0] a2_sb;
    always @(posedge clk) begin a2_r <= v5; a2_L <= a1_L; a2_str <= a1_str; a2_sb <= a1_sb; end
    // A3: CSA 8 -> 6 -> 4 -> 3 -> 2, then (+ L) and (+ L + I.stride): the I-table read addresses I_eff + L, + stride
    reg [6*64-1:0] w1; reg [4*64-1:0] w2; reg [3*64-1:0] w3; reg [63:0] fs0, fc0, fs1, fc1, fs2, fc2;
    always @* begin
        w1[0 +: 64] = s3(a2_r[0 +: 64], a2_r[64 +: 64], a2_r[128 +: 64]);   w1[64 +: 64] = c3(a2_r[0 +: 64], a2_r[64 +: 64], a2_r[128 +: 64]);
        w1[128 +: 64] = s3(a2_r[192 +: 64], a2_r[256 +: 64], a2_r[320 +: 64]); w1[192 +: 64] = c3(a2_r[192 +: 64], a2_r[256 +: 64], a2_r[320 +: 64]);
        w1[256 +: 64] = a2_r[384 +: 64]; w1[320 +: 64] = a2_r[448 +: 64];
        w2[0 +: 64] = s3(w1[0 +: 64], w1[64 +: 64], w1[128 +: 64]);     w2[64 +: 64] = c3(w1[0 +: 64], w1[64 +: 64], w1[128 +: 64]);
        w2[128 +: 64] = s3(w1[192 +: 64], w1[256 +: 64], w1[320 +: 64]); w2[192 +: 64] = c3(w1[192 +: 64], w1[256 +: 64], w1[320 +: 64]);
        w3[0 +: 64] = s3(w2[0 +: 64], w2[64 +: 64], w2[128 +: 64]);     w3[64 +: 64] = c3(w2[0 +: 64], w2[64 +: 64], w2[128 +: 64]);
        w3[128 +: 64] = w2[192 +: 64];
        fs0 = s3(w3[0 +: 64], w3[64 +: 64], w3[128 +: 64]);             fc0 = c3(w3[0 +: 64], w3[64 +: 64], w3[128 +: 64]);
        fs1 = s3(fs0, fc0, {48'd0, a2_L});                               fc1 = c3(fs0, fc0, {48'd0, a2_L});
        fs2 = s3(fs1, fc1, sx32(a2_str));                                fc2 = c3(fs1, fc1, sx32(a2_str));
    end
    reg [63:0] a3_s0, a3_c0, a3_s1, a3_c1, a3_s2, a3_c2; reg [SBW-1:0] a3_sb;
    always @(posedge clk) begin a3_s0 <= fs0; a3_c0 <= fc0; a3_s1 <= fs1; a3_c1 <= fc1; a3_s2 <= fs2; a3_c2 <= fc2; a3_sb <= a2_sb; end
    // A4: 16-bit chunks, both carries (17-bit adds only)
    reg [3*4*17-1:0] a4_z0, a4_z1; reg [SBW-1:0] a4_sb;
    integer q4;
    always @(posedge clk) begin
        for (q4 = 0; q4 < 4; q4 = q4 + 1) begin
            a4_z0[(0*4 + q4)*17 +: 17] <= {1'b0, a3_s0[q4*16 +: 16]} + {1'b0, a3_c0[q4*16 +: 16]};
            a4_z1[(0*4 + q4)*17 +: 17] <= {1'b0, a3_s0[q4*16 +: 16]} + {1'b0, a3_c0[q4*16 +: 16]} + 17'd1;
            a4_z0[(1*4 + q4)*17 +: 17] <= {1'b0, a3_s1[q4*16 +: 16]} + {1'b0, a3_c1[q4*16 +: 16]};
            a4_z1[(1*4 + q4)*17 +: 17] <= {1'b0, a3_s1[q4*16 +: 16]} + {1'b0, a3_c1[q4*16 +: 16]} + 17'd1;
            a4_z0[(2*4 + q4)*17 +: 17] <= {1'b0, a3_s2[q4*16 +: 16]} + {1'b0, a3_c2[q4*16 +: 16]};
            a4_z1[(2*4 + q4)*17 +: 17] <= {1'b0, a3_s2[q4*16 +: 16]} + {1'b0, a3_c2[q4*16 +: 16]} + 17'd1;
        end
        a4_sb <= a3_sb;
    end
    // A5: carry select -> acc = the effective base, iax = acc + L, ian = acc + L + sx(I.stride)
    reg [3*64-1:0] csel; reg [16:0] cz; reg ccy; integer q5, p5;
    always @* begin
        for (p5 = 0; p5 < 3; p5 = p5 + 1) begin
            ccy = 1'b0;
            for (q5 = 0; q5 < 4; q5 = q5 + 1) begin
                cz = ccy ? a4_z1[(p5*4 + q5)*17 +: 17] : a4_z0[(p5*4 + q5)*17 +: 17];
                csel[p5*64 + q5*16 +: 16] = cz[15:0]; ccy = cz[16];
            end
        end
    end
    reg [63:0] a5_acc, a5_iax, a5_ian; reg [SBW-1:0] a5_sb;
    always @(posedge clk) begin a5_acc <= csel[0 +: 64]; a5_iax <= csel[64 +: 64]; a5_ian <= csel[128 +: 64]; a5_sb <= a4_sb; end
    // A6: range flags; the result is written into its queue entry (FE item) or returned to the BE (re-injection)
    wire        a5_be = a5_sb[0];
    wire [20:0] a5_n = a5_sb[SB_N +: 21];
    wire        a5_flt = a5_sb[SB_FLT], a5_px = a5_sb[SB_PX], a5_pn = a5_sb[SB_PN];
    wire [1:0]  a5_sp = a5_sb[SB_SP +: 2];
    wire [QB-1:0] a5_tag = a5_sb[SB_TAG +: QB];
    wire [2:0]  a5_j = a5_sb[SB_J +: 3];
    wire        a5_last = a5_sb[SB_LAST], a5_isI = a5_sb[SB_ISI];
    wire        a6_bad_d = base_bad(a5_sp, a5_acc, 1'b1), a6_bad_vm = base_bad(2'd1, a5_acc, 1'b0);
`ifdef OT_HGI_SEQ_MUT_IDXL
    wire [63:0] a6_iax = a5_acc;                          // NEGATIVE CONTROL: the indexed read ignores L
`else
    wire [63:0] a6_iax = a5_iax;
`endif
    wire        a6_ixb = (a6_iax[63:18] != 46'd0), a6_inb = (a5_ian[63:18] != 46'd0);
    wire        a6_ihbm = (IKS_I != 0) && a5_isI && a5_sp == 2'd0;      // IKS: an HBM-space I (range-checked as HBM)
    wire        a6_flt = a5_flt || (a5_isI ? (a6_ihbm ? a6_bad_d : a6_bad_vm) : (!(a5_px || a5_pn) && a6_bad_d));
    // ---- S3 TX (R1): the A6 view of the A5 flops, one dedicated flop a bit
    always @(posedge clk) begin
        au_s3_be <= a5_be; au_s3_tag <= a5_tag; au_s3_j <= a5_j; au_s3_last <= a5_last; au_s3_isI <= a5_isI;
        au_s3_acc <= a5_acc; au_s3_n <= a5_n; au_s3_px <= a5_px; au_s3_pn <= a5_pn; au_s3_flt <= a6_flt;
        au_s3_badd <= a6_bad_d; au_s3_iax <= a6_iax[17:0]; au_s3_ixb <= a6_ixb; au_s3_ian <= a5_ian[17:0];
        au_s3_inb <= a6_inb; au_s3_ihbm <= a6_ihbm;
    end
endmodule
`default_nettype wire
