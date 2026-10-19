`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT2 (2026-10-17): dsdv_gunit_l1 -- G-unit leaf L1 (5th of 6, below the stop L2): router score store, bias
// table, bias + top-6 select, the ids CTL row, the score-row stream to L3 (routing weights) and the merge of L3's
// weight rows into the router CTL toward L2.
//
// Per layer-token (tools/hdc_golden_v41.Model.moe, every rounding the golden's):
//     ids = sorted(topk_lowest_index(add(scores, bias), K))   ot_dsrom_su_bias_select (bias add + ot_hdc_select_tree)
// SC beats (kind 5) arrive from L2's vstop deliver flops (dl_*, unfiltered; kind decoded behind this leaf's input flop):
// score row r = [49:40] (r < 64), scores j = 0..6 = [52 + 32 j +: 32], index 7 r + j (indices >= ne ignored), each
// row once, ceil(ne / 7) beats in any order and either direction (two in one cycle are fine).
// cw (relayed by L2): cw_a[9] = 0 table write, set s = cw_a[8]: rows 0..55 = bias words 8 r .. 8 r + 7, row 62 word 6 =
// route_scale; cw_a[9:8] = 2'b10, cw_a[0] = 0 ROUTER JOB {set [40], ne [39:31], row [30:21], lmask [20:16],
// smask [15:0]}, armed before the window's first SC beat.
// Latency (router throughput qualification, GUNIT2): the select starts ON the edge after the last SC beat lands in
// this leaf's input flop (beat 0 of the select forwards that beat's scores; beats 1.. read the store), the ids CTL row
// is formed from the select tree's own output register (no ids register in between), and it leaves this leaf on the
// next edge.  Fixed: no handshakes, no ready / credit.
// Output ct (router CTL rows, target 5; zero when idle): ids row `row` (mask 0011), then later L3's two weight rows
// (relayed: input flop -> this output flop).  Both on one edge is a sticky fault (the compiler never schedules it).
// fault (sticky): duplicate SC row, row >= 64, an SC beat with no armed job or while the select runs, a job write
// while one is armed, fewer than K experts selected, an adder fault, L3's fault, an ids / weights CTL collision.
// Every input lands in a flop; every output leaves a flop.  MUT (bench only): 1 = bias not added.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_l1 #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // N face (L2)
    input  wire [275:0]  rn_i,  output wire [275:0] rn_o,
    input  wire          dl_av, input wire [275:0] dl_a, input wire dl_bv, input wire [275:0] dl_b,
    input  wire          cw_v, input wire [9:0] cw_a, input wire [255:0] cw_d, input wire [3:0] sid_i,
    output reg           ct_v, output reg [275:0] ct_b, output reg fault,
    // S face (L3)
    output wire [275:0]  rs_o,  input wire [275:0] rs_i,
    output reg           rw_st, output reg rw_v, output reg rw_l, output reg [511:0] rw_x,
    output reg  [31:0]   rw_scale, output reg [9:0] rw_row, output reg [4:0] rw_lm, output reg [15:0] rw_sm,
    output reg  [3:0]    sid_o,
    input  wire          w_v, input wire [275:0] w_b, input wire f3
);
    localparam integer V = 276, K = 6, LA = 4, NSET = 2, NE = 448, W = 64, NB = 8, IW = 9, SB = 1;
    integer i, j;
    // ---------------------------------------------------------------- rung feedthrough (L2 <-> L3)
    dsdv_gunit_pass #(.W(V)) u_dn (.clk(clk), .rst_n(rst_n), .d(rn_i), .q(rs_o));
    dsdv_gunit_pass #(.W(V)) u_up (.clk(clk), .rst_n(rst_n), .d(rs_i), .q(rn_o));
    // ---------------------------------------------------------------- input flops
    reg dav, dbv, wv, wv3, f3_q; reg [V-1:0] ab, bb, wb3; reg [9:0] wa; reg [255:0] wd; reg [3:0] sid_c;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin dav <= 1'b0; dbv <= 1'b0; wv <= 1'b0; wv3 <= 1'b0; f3_q <= 1'b0; end
        else begin dav <= dl_av; dbv <= dl_bv; wv <= cw_v; wv3 <= w_v; f3_q <= f3; end
    always @(posedge clk) begin ab <= dl_a; bb <= dl_b; wa <= cw_a; wd <= cw_d; sid_c <= sid_i; wb3 <= w_b; sid_o <= sid_c; end
    wire av = dav && ab[3:1] == 3'd5, bv = dbv && bb[3:1] == 3'd5;
    wire [SB-1:0] wset = wa[8 +: SB];
    // ---------------------------------------------------------------- tables: bias (NSET x 448), route_scale
    reg [31:0] bias [0:NSET*NE-1];
    reg [31:0] rscale [0:NSET-1];
    always @(posedge clk) if (wv && !wa[9]) begin
        if (wa[5:0] < 6'd56) for (j = 0; j < 8; j = j + 1) bias[NE * wset + 8 * wa[5:0] + j] <= wd[32 * j +: 32];
        if (wa[5:0] == 6'd62) rscale[wset] <= wd[32 * 6 +: 32];
    end
    // ---------------------------------------------------------------- router job (armed -> taken by the SC window)
    reg jv; reg [SB-1:0] jset; reg [8:0] jne; reg [9:0] jrow; reg [4:0] jlm; reg [15:0] jsm;
    reg [SB-1:0] cset; reg [8:0] ne; reg [9:0] row; reg [4:0] lmask; reg [15:0] smask; reg [6:0] nsc;
    wire job_w = wv && wa[9:8] == 2'b10 && !wa[0];
    // ---------------------------------------------------------------- score store
    reg [31:0] sc [0:NE-1];
    reg [63:0] seen; reg [6:0] nseen;
    wire [5:0] ra = ab[45:40], rb = bb[45:40];
    always @(posedge clk) begin
        if (av) for (j = 0; j < 7; j = j + 1) sc[7 * ra + j] <= ab[52 + 32 * j +: 32];
        if (bv) for (j = 0; j < 7; j = j + 1) sc[7 * rb + j] <= bb[52 + 32 * j +: 32];
    end
    // ---------------------------------------------------------------- sequencer (fixed cycle counts, no handshakes)
    localparam [1:0] S_IN = 2'd0, S_SEL = 2'd1, S_WSEL = 2'd2, S_RW = 2'd3;
    reg [1:0] st; reg [5:0] n; reg [3:0] nbs; reg [4:0] nrw;
    reg s_v, s_l; reg [W-1:0] s_lv; reg [W*32-1:0] s_val, s_bias; reg [W*IW-1:0] s_idx;
    wire o_sv; wire [K-1:0] o_sel; wire [K*IW-1:0] o_idx; wire [K-1:0] o_ninf; wire o_sf;
    reg [IW-1:0] ids [0:K-1];
    wire take = st == S_IN && (av || bv) && nseen == 7'd0;      // the first SC beat of a window takes the armed job
    wire last = st == S_IN && nseen != 7'd0 && (av || bv) && nseen + av + bv == nsc;
    wire [3:0] nbs_c = 4'((ne + 9'd63) >> 6);
    wire e1 = st == S_WSEL && o_sv;                               // the ids row leaves on this edge
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            st <= S_IN; seen <= 64'd0; nseen <= 7'd0; fault <= 1'b0; s_v <= 1'b0; rw_st <= 1'b0; rw_v <= 1'b0;
            jv <= 1'b0;
        end else begin
            s_v <= 1'b0; rw_st <= 1'b0; rw_v <= 1'b0;
            if (o_sf || f3_q || (e1 && wv3)) fault <= 1'b1;
            if (av && (ab[49:46] != 4'd0 || seen[ra])) fault <= 1'b1;
            if (bv && (bb[49:46] != 4'd0 || seen[rb] || (av && ra == rb))) fault <= 1'b1;
            if ((av || bv) && st != S_IN) fault <= 1'b1;
            if (job_w) begin
                if (jv && !take) fault <= 1'b1;
                jv <= 1'b1; jset <= wd[40 +: SB]; jsm <= wd[15:0]; jlm <= wd[20:16]; jrow <= wd[30:21]; jne <= wd[39:31];
            end
            case (st)
                S_IN: begin
                    if (take) begin
                        if (!jv) fault <= 1'b1;
                        jv <= job_w; cset <= jset; ne <= jne; row <= jrow; lmask <= jlm; smask <= jsm;
                        nsc <= 7'((jne + 9'd6) / 9'd7); rw_scale <= rscale[jset];
                    end
                    seen <= seen | (av ? 64'd1 << ra : 64'd0) | (bv ? 64'd1 << rb : 64'd0);
                    nseen <= nseen + av + bv;
                    if (last) begin                            // select beat 0 on this edge (forwarded below)
                        s_v <= 1'b1; s_l <= nbs_c == 4'd1; n <= 6'd1; nbs <= nbs_c; nrw <= 5'((ne + 9'd15) >> 4);
                        st <= (nbs_c == 4'd1) ? S_WSEL : S_SEL;
                    end
                end
                S_SEL: begin                                  // beats 1 .. ceil(ne / 64) - 1
                    s_v <= 1'b1; s_l <= n + 6'd1 == {2'd0, nbs};
                    n <= n + 6'd1;
                    if (n + 6'd1 == {2'd0, nbs}) st <= S_WSEL;
                end
                S_WSEL: if (o_sv) begin
                    for (i = 0; i < K; i = i + 1) ids[i] <= o_idx[IW * i +: IW];
                    if (o_sel != {K{1'b1}}) fault <= 1'b1;
                    st <= S_RW; n <= 6'd0; rw_st <= 1'b1;
                end
                S_RW: begin                                   // ids row, then ceil(ne / 16) score rows, one a cycle
                    rw_v <= 1'b1; rw_l <= n == {1'b0, nrw};
                    n <= n + 6'd1;
                    if (n == {1'b0, nrw}) begin st <= S_IN; seen <= 64'd0; nseen <= 7'd0; end
                end
                default: st <= S_IN;
            endcase
        end
    // select operands: beat bn of 64 lanes (beat 0 on the `last` edge forwards the arriving beat(s)' scores)
    wire fw = st == S_IN;
    wire [5:0] bn = fw ? 6'd0 : n;
    always @(posedge clk) begin
        for (j = 0; j < W; j = j + 1) begin
            s_lv[j] <= (W * bn + j) < ne;
            s_val[32 * j +: 32] <= (fw && av && ra == j / 7) ? ab[52 + 32 * (j % 7) +: 32]
                                 : (fw && bv && rb == j / 7) ? bb[52 + 32 * (j % 7) +: 32]
                                 : (W * bn + j < NE) ? sc[W * bn + j] : 32'd0;
            s_bias[32 * j +: 32] <= (MUT == 1 || W * bn + j >= NE) ? 32'd0 : bias[NE * cset + W * bn + j];
            s_idx[IW * j +: IW] <= W * bn + j;
        end
        if (n == 6'd0) begin rw_x <= 512'd0; for (i = 0; i < K; i = i + 1) rw_x[32 * i +: IW] <= ids[i]; end
        else for (j = 0; j < 16; j = j + 1) rw_x[32 * j +: 32] <= (16 * (n - 1) + j < NE) ? sc[16 * (n - 1) + j] : 32'd0;
        rw_row <= row; rw_lm <= lmask; rw_sm <= smask;
    end
    ot_dsrom_su_bias_select #(.K(K), .VW(32), .IW(IW), .W(W), .NB(NB), .ORDER(1), .LA(LA)) u_sel (
        .clk(clk), .rst_n(rst_n), .in_valid(s_v), .in_last(s_l), .in_lv(s_lv), .in_val(s_val), .in_bias(s_bias),
        .in_idx(s_idx), .out_valid(o_sv), .out_v(o_sel), .out_idx(o_idx), .out_ninf(o_ninf), .out_fault(o_sf));
    // ---------------------------------------------------------------- router CTL out (ids row here, weights from L3)
    function automatic [V-1:0] ctl(input [9:0] a, input [3:0] m, input [127:0] d, input [15:0] sm, input [4:0] lm,
                                   input [3:0] s);
        reg [185:0] p;
        begin
            p = 186'd0; p[15:0] = sm; p[20:16] = 5'd5; p[25:21] = lm;
            p[26 +: 10] = a; p[36 +: 4] = m; p[40 +: 128] = d;
            ctl = {V{1'b0}}; ctl[0] = 1'b1; ctl[12:9] = s; ctl[21 +: 186] = p;
        end
    endfunction
    wire [31:0] pk0 = {5'd0, o_idx[IW * 2 +: IW], o_idx[IW * 1 +: IW], o_idx[IW * 0 +: IW]};
    wire [31:0] pk1 = {5'd0, o_idx[IW * 5 +: IW], o_idx[IW * 4 +: IW], o_idx[IW * 3 +: IW]};
    always @(posedge clk or negedge rst_n) if (!rst_n) ct_v <= 1'b0; else ct_v <= e1 || wv3;
    always @(posedge clk)
        ct_b <= e1 ? ctl(row, 4'h3, {64'd0, pk1, pk0}, smask, lmask, sid_c) : wv3 ? wb3 : {V{1'b0}};
endmodule
