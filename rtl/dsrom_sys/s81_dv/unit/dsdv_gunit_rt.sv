`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-1 (2026-10-17): dsdv_gunit_rt -- the router leaf group of the S81-DV G-unit (leaves L1 select, L3 normalise).
//
// Per layer-token (tools/hdc_golden_v41.Model.moe, every rounding the golden's):
//     ids = sorted(topk_lowest_index(add(scores, bias), K))       ot_dsrom_su_bias_select (bias add + ot_hdc_select_tree)
//     w_j = mul(div(scores[ids[j]], add(seqsum(scores[ids]), 1e-20)), route_scale)        ot_s81_su_rw (unchanged)
// and the result goes back to every slice as three CTL row writes (ot_s81sl_xr target 5) that the G-unit injects on
// the V rung both ways (each slice's xr re-injects a V CTL on its tier line, so one injection per tier reaches 8 slices).
// The ids row leaves FIRST, straight after the select (the expert launch is on the token's critical path); the routing
// weights are needed only at the expert combine and follow when the normaliser finishes.
//
// Inputs
//   SC beats (kind 5) tapped + sunk by the unit's ot_dsdv_vstop, on sa (northbound, from s_3S) / sb (southbound, from
//   s_3N).  An SC V beat is a slice send beat cut to the 276-b rung (ot_s81sl_xr): score row r = [49:40] (r < 64),
//   scores j = 0..6 = [52 + 32 j +: 32], score index 7 r + j (indices >= ne ignored).  The compiler places each score
//   once; ceil(ne / 7) beats per token in any order and either direction (two in one cycle are fine).
//   cw (configuration / job port, registered; p4i routes it from seq_host):
//     cw_a[9] = 0  table write, set s = cw_a[8]: rows 0..55 = bias words 8 r .. 8 r + 7 (the layer's ffn.gate.bias),
//                  row 62 word 6 = route_scale (rows 56..61 and the rest of 62 belong to the HC leaf group)
//     cw_a[9:8] = 2'b10, cw_a[0] = 0  ROUTER JOB for the next SC window: cw_d {set [40], ne [39:31], row [30:21],
//                  lmask [20:16], smask [15:0]}
// Output
//   ct_v / ct_b, CTL target 5 row writes (header [0] 1, [3:1] 0, [8:4] 0 = line default, [12:9] sid; payload
//   [21 +: 186] = {body 160, lmask 5, target 5, smask 16}, body = {.., data 128 [135:8], mask 4 [7:4]... see ctl()}):
//     E1 row `row`     mask 0011  {ids 3..5, ids 0..2} (9 b each, 3 per word from bit 0)      at a fixed edge after
//                                                                                           the last SC beat
//     E2 row `row + 1` mask 1111  {w3, w2, w1, w0}                                           later (normaliser)
//     E3 row `row + 2` mask 0011  {w5, w4}                                                   the edge after E2
// fault (sticky): duplicate SC row, row >= 64, an SC beat with no armed job or while the token is being finished, a
// job write while one is armed, a select result with fewer than K experts, an adder / divider / multiplier fault.
// Every input lands in a flop; every output leaves a flop.  MUT (bench only): 1 = bias not added; 4 = ot_s81_su_rw
// MUT 4 (route_scale skipped).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_rt #(
    parameter integer V    = 276,
    parameter integer K    = 6,
    parameter integer LA   = 4,
    parameter integer NSET = 2,
    parameter integer MUT  = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [3:0]    sid,
    input  wire          sa_v, input wire [V-1:0] sa_b,
    input  wire          sb_v, input wire [V-1:0] sb_b,
    input  wire          cw_v, input wire [9:0] cw_a, input wire [255:0] cw_d,
    output reg           ct_v,
    output reg  [V-1:0]  ct_b,
    output reg           fault
);
    localparam integer NE = 448, W = 64, NB = 8, IW = 9, SB = (NSET > 1) ? $clog2(NSET) : 1;
    integer i, j;
    // ---------------------------------------------------------------- input flops
    reg av, bv, wv; reg [V-1:0] ab, bb; reg [9:0] wa; reg [255:0] wd; reg [3:0] sid_c;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin av <= 1'b0; bv <= 1'b0; wv <= 1'b0; end
        else begin av <= sa_v; bv <= sb_v; wv <= cw_v; end
    always @(posedge clk) begin ab <= sa_b; bb <= sb_b; wa <= cw_a; wd <= cw_d; sid_c <= sid; end
    wire [SB-1:0] wset = (NSET > 1) ? wa[8 +: SB] : {SB{1'b0}};
    // ---------------------------------------------------------------- tables: bias (NSET x 448), route_scale
    reg [31:0] bias [0:NSET*NE-1];
    reg [31:0] rscale [0:NSET-1];
    always @(posedge clk) if (wv && !wa[9]) begin
        if (wa[5:0] < 6'd56) for (j = 0; j < 8; j = j + 1) bias[NE * wset + 8 * wa[5:0] + j] <= wd[32 * j +: 32];
        if (wa[5:0] == 6'd62) rscale[wset] <= wd[32 * 6 +: 32];
    end
    // ---------------------------------------------------------------- router job (armed -> taken by the SC window)
    reg jv; reg [SB-1:0] jset; reg [8:0] jne; reg [9:0] jrow; reg [4:0] jlm; reg [15:0] jsm;
    reg [SB-1:0] cset; reg [8:0] ne; reg [9:0] row; reg [4:0] lmask; reg [15:0] smask; reg [6:0] nsc; reg [31:0] scale;
    wire job_w = wv && wa[9:8] == 2'b10 && !wa[0];
    wire take;                                        // the first SC beat of a window takes the armed job
    // ---------------------------------------------------------------- score store
    reg [31:0] sc [0:NE-1];
    reg [63:0] seen; reg [6:0] nseen;
    wire [5:0] ra = ab[45:40], rb = bb[45:40];
    always @(posedge clk) begin
        if (av) for (j = 0; j < 7; j = j + 1) sc[7 * ra + j] <= ab[52 + 32 * j +: 32];
        if (bv) for (j = 0; j < 7; j = j + 1) sc[7 * rb + j] <= bb[52 + 32 * j +: 32];
    end
    // ---------------------------------------------------------------- sequencer (fixed cycle counts, no handshakes)
    localparam [2:0] S_IN = 3'd0, S_SEL = 3'd1, S_WSEL = 3'd2, S_RW = 3'd3, S_WRW = 3'd4, S_CT = 3'd5;
    reg [2:0] st; reg [5:0] n; reg [3:0] nbs; reg [4:0] nrw;
    reg s_v, s_l; reg [W-1:0] s_lv; reg [W*32-1:0] s_val, s_bias; reg [W*IW-1:0] s_idx;
    wire o_sv; wire [K-1:0] o_sel; wire [K*IW-1:0] o_idx; wire [K-1:0] o_ninf; wire o_sf;
    reg [IW-1:0] ids [0:K-1];
    reg r_st, r_v, r_l; reg [511:0] r_x;
    wire rw_v; wire [511:0] rw_d; wire [15:0] rw_m; wire rw_f;
    reg [511:0] wq;
    assign take = st == S_IN && (av || bv) && nseen == 7'd0;
    reg e1, e2, e3;                                   // CTL emits (registered selects for the output flop below)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            st <= S_IN; seen <= 64'd0; nseen <= 7'd0; fault <= 1'b0; s_v <= 1'b0; r_st <= 1'b0; r_v <= 1'b0;
            jv <= 1'b0; e1 <= 1'b0; e2 <= 1'b0; e3 <= 1'b0;
        end else begin
            s_v <= 1'b0; r_st <= 1'b0; r_v <= 1'b0; e1 <= 1'b0; e2 <= 1'b0; e3 <= e2;
            if (o_sf || rw_f) fault <= 1'b1;
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
                        nsc <= (jne + 9'd6) / 9'd7; scale <= rscale[jset];
                    end
                    seen <= seen | (av ? 64'd1 << ra : 64'd0) | (bv ? 64'd1 << rb : 64'd0);
                    nseen <= nseen + av + bv;
                    if (nseen != 7'd0 && nseen + av + bv == nsc && (av || bv)) begin
                        st <= S_SEL; n <= 6'd0; nbs <= (ne + 9'd63) >> 6; nrw <= (ne + 9'd15) >> 4;
                    end
                end
                S_SEL: begin                                  // ceil(ne / 64) beats into the bias + select tree
                    s_v <= 1'b1; s_l <= n + 6'd1 == {2'd0, nbs};
                    n <= n + 6'd1;
                    if (n + 6'd1 == {2'd0, nbs}) st <= S_WSEL;
                end
                S_WSEL: if (o_sv) begin
                    for (i = 0; i < K; i = i + 1) ids[i] <= o_idx[IW * i +: IW];
                    if (o_sel != {K{1'b1}}) fault <= 1'b1;
                    st <= S_RW; n <= 6'd0; r_st <= 1'b1; e1 <= 1'b1;
                end
                S_RW: begin                                   // ids row, then ceil(ne / 16) score rows, one a cycle
                    r_v <= 1'b1; r_l <= n == {1'b0, nrw};
                    n <= n + 6'd1;
                    if (n == {1'b0, nrw}) st <= S_WRW;
                end
                S_WRW: if (rw_v) begin wq <= rw_d; st <= S_CT; e2 <= 1'b1; end
                S_CT: begin st <= S_IN; seen <= 64'd0; nseen <= 7'd0; end
                default: st <= S_IN;
            endcase
        end
    // select operands (beat n of 64 lanes; the job's bias set) and su_rw operand rows (row n), registered
    always @(posedge clk) begin
        for (j = 0; j < W; j = j + 1) begin
            s_lv[j] <= (W * n + j) < ne;
            s_val[32 * j +: 32] <= (W * n + j < NE) ? sc[W * n + j] : 32'd0;
            s_bias[32 * j +: 32] <= (MUT == 1 || W * n + j >= NE) ? 32'd0 : bias[NE * cset + W * n + j];
            s_idx[IW * j +: IW] <= W * n + j;
        end
        if (n == 6'd0) begin r_x <= 512'd0; for (i = 0; i < K; i = i + 1) r_x[32 * i +: IW] <= ids[i]; end
        else for (j = 0; j < 16; j = j + 1) r_x[32 * j +: 32] <= (16 * (n - 1) + j < NE) ? sc[16 * (n - 1) + j] : 32'd0;
    end
    ot_dsrom_su_bias_select #(.K(K), .VW(32), .IW(IW), .W(W), .NB(NB), .ORDER(1), .LA(LA)) u_sel (
        .clk(clk), .rst_n(rst_n), .in_valid(s_v), .in_last(s_l), .in_lv(s_lv), .in_val(s_val), .in_bias(s_bias),
        .in_idx(s_idx), .out_valid(o_sv), .out_v(o_sel), .out_idx(o_idx), .out_ninf(o_ninf), .out_fault(o_sf));
    ot_s81_su_rw #(.MUT(MUT == 4 ? 4 : 0), .KMAX(8)) u_rw (.clk(clk), .rst_n(rst_n), .start(r_st), .k_i(K[3:0]),
        .scale_i(scale), .off_i(4'd0), .i_v(r_v), .i_x(r_x), .i_last(r_l), .o_v(rw_v), .o_d(rw_d), .o_m(rw_m), .fault(rw_f));
    // ---------------------------------------------------------------- CTL row writes (target 5), output flops
    function automatic [V-1:0] ctl(input [9:0] a, input [3:0] m, input [127:0] d, input [15:0] sm, input [4:0] lm,
                                   input [3:0] s);
        reg [185:0] p;
        begin
            p = 186'd0; p[15:0] = sm; p[20:16] = 5'd5; p[25:21] = lm;
            p[26 +: 10] = a; p[36 +: 4] = m; p[40 +: 128] = d;
            ctl = {V{1'b0}}; ctl[0] = 1'b1; ctl[12:9] = s; ctl[21 +: 186] = p;
        end
    endfunction
    wire [31:0] pk0 = {5'd0, ids[2], ids[1], ids[0]}, pk1 = {5'd0, ids[5 < K ? 5 : 0], ids[4 < K ? 4 : 0], ids[3 < K ? 3 : 0]};
    always @(posedge clk or negedge rst_n) if (!rst_n) ct_v <= 1'b0; else ct_v <= e1 || e2 || e3;
    always @(posedge clk)
        ct_b <= e1 ? ctl(row, 4'h3, {64'd0, pk1, pk0}, smask, lmask, sid_c)
              : e2 ? ctl(row + 10'd1, 4'hf, wq[127:0], smask, lmask, sid_c)
                   : ctl(row + 10'd2, 4'h3, {64'd0, wq[191:128]}, smask, lmask, sid_c);
endmodule
