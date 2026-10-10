`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 SM x-load (hgi-adapters, 2026-10-09): the peer of ot_hgi_sm_record's x port.  Reads the activation rows of
// A (P slots, K elements each, VM FP32) through NXC hfd_hgi_vm packet clients and writes the SM x store over the
// EXISTING x-write port of every SM (xw_en / xw_addr / xw_grp / xw_data 2,048 b, broadcast to the 32 SMs), in the
// smh fragment layout (tools/dshbm_matched_sm_seq.gen_op, BF16 / INT8 front):
//   fragment address a = g x 8 + t (g < op_g = ceil(K / 512), t < 8); column p (slot) lane j (< 64) at bit
//   p x XC + LB x 266 + 16 j (XC = 3,152, LB x 266 = 2,128) holds to_bf16(x_p[k]), k = (g x 64 + j) x 8 + t (0 past K);
//   beat b (xw_grp) of address a carries fragment bits [b x 2,048 +: 2,048], b < ceil(P x XC / 2,048) (= op_xb).
// One VM sector = the 8 t values of one lane j, so a group g is 64 x P sector reads into a P x 64 x 8 BF16 tile, then
// 8 x op_xb beats.  to_bf16 = RNE (hdc_golden; the golden of SM.MATVEC fmt 0 / 3 rounds x to BF16).
// Refusals (x_fault): fmt 1 / 2 (the DS block-dot x is quant_fp8 codes + block exponents: the activation quantiser,
// not this loader), A not VM (STREAM x enters from the SU stream, not here), A.base / A.stride not 8-word aligned.
// STORAGE (FILL-9 2026-10-10, root cause of the 64-Kb flop tile: yosys OOM / 71,877 failing endpoints at TT -695 ps):
// 32 ot_sram_1r1w_128x256_m1 macros m[t][q] (t < 8 fragment row, q < 4 lane quarter): word p (slot) of m[t][q] holds
// lanes 16q .. 16q + 15 of slot p, t-value t, as 16 x BF16.  A landing sector (p, j) is ONE masked word write in each of
// the 8 macros m[t][j >> 4] (data replicated over the 16 lane slices, 16-b mask at slice j & 15); a beat reads the 4
// macros m[t][*] at word p (1,024 b).  Write and read requests are registered at the macro pins; the read pipeline is
// pins -> macro edge -> registered 8:1 t-select (rw) -> beat (xw_data): +2 edges a beat against the flop tile, same
// x-store write sequence (tb_hgi_xload_lock vs ot_hgi_sm_xload_old).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sm_xload #(
    parameter integer NXC = 4,            // VM packet clients (reads in flight)
    parameter integer PMAX = 8,
    parameter integer MUT_M = 0,          // mutant (FILL-9): a landing sector's write mask on lane slice (j ^ 1) of its quarter
    parameter integer MUT_T = 0           // mutant: lane j takes t from the wrong half (k = (g 64 + j) 8 + (7 - t))
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               x_v,
    output wire               x_rdy,
    input  wire [39:0]        x_base,
    input  wire [20:0]        x_n,
    input  wire [3:0]         x_p,
    input  wire [31:0]        x_stride,
    input  wire [1:0]         x_space,
    input  wire [1:0]         x_fmt,
    output reg                x_done,
    output reg                x_fault,
    output reg                xw_en,
    output reg  [6:0]         xw_addr,
    output reg  [6:0]         xw_grp,
    output reg  [2047:0]      xw_data,
    output reg  [NXC*338-1:0] vmq,
    input  wire [NXC*274-1:0] vmr
);
    localparam integer XC = 3152, XOFF = 2128;
    reg busy; reg [17:0] base; reg [20:0] kk; reg [3:0] pp; reg [17:0] st;
    reg [7:0] gn, g; reg [3:0] p_rd; reg [6:0] j_rd; reg [9:0] outst; reg [3:0] t; reg [6:0] b; reg [6:0] nb;
    // write request at the macro pins (registered; per-quarter data copies bound the fanout to 16 slices)
    reg wq_v; reg [1:0] wq_q; reg [3:0] wq_a; reg [3:0] wq_l; reg [127:0] wq_d [0:3];
    // read request at the macro pins (registered): s1 = address at the pins, s2 = macro output valid, s3 = rw valid
    reg s1_v, s2_v, s3_v; reg [2:0] s1_t, s2_t; reg [3:0] s1_sp; reg [6:0] s1_addr, s2_addr, s3_addr;
    reg [6:0] s1_b, s2_b, s3_b; reg s1_ok, s2_ok, s3_ok;
    wire [255:0] rd [0:31];                // m[t][q] at index t * 4 + q
    genvar gt, gq;
    generate for (gt = 0; gt < 8; gt = gt + 1) begin : g_t
        for (gq = 0; gq < 4; gq = gq + 1) begin : g_q
            wire [255:0] wmask = {240'd0, 16'hFFFF} << {wq_l ^ ((MUT_M != 0) ? 4'd1 : 4'd0), 4'd0};
            ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk),
                .r_ce_in(s1_v && s1_t == gt), .r_addr_in({3'd0, s1_sp}), .rd_out(rd[gt * 4 + gq]),
                .w_ce_in(wq_v && wq_q == gq), .w_addr_in({3'd0, wq_a}), .wd_in({16{wq_d[gq][16 * gt +: 16]}}),
                .w_mask_in(wmask), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        end
    end endgenerate
    reg [NXC-1:0] hv;                      // a client's response held, not yet landed
    reg [273:0] hdat [0:NXC-1];
    reg [10:0] got;                        // sectors landed for this group
    integer cl; reg [3:0] nland;
    reg lsel_v; integer lsel;
    always @* begin
        lsel_v = 1'b0; lsel = 0;
        for (cl = NXC - 1; cl >= 0; cl = cl - 1) if (hv[cl]) begin lsel_v = 1'b1; lsel = cl; end
        nland = {3'd0, lsel_v};
    end
    wire [10:0] got_n = got;
    reg [1:0] ph;                          // 0 read, 1 emit, 2 done
    assign x_rdy = !busy;
    reg [273:0] vr [0:NXC-1];
    integer c;
    always @(posedge clk) for (c = 0; c < NXC; c = c + 1) vr[c] <= vmr[c*274 +: 274];
    reg [NXC-1:0] cbusy;
    function automatic [15:0] bf16(input [31:0] x);
        reg [31:0] r;
        begin
            if (x[30:23] == 8'hFF && x[22:0] != 0) bf16 = x[31:16] | 16'h0040;
            else begin r = x + 32'h7FFF + {31'd0, x[16]}; bf16 = r[31:16]; end
        end
    endfunction
    // beat b of fragment (g, t): the fragment holds slot p's lanes at [p XC + XOFF, + 1,024); slot blocks are 3,152
    // apart with a 2,128-b gap > the 2,048-b beat, so a beat overlaps AT MOST ONE slot: a static (p, offset) per b
    localparam integer NBMAX = (PMAX * XC + 2047) / 2048;
    function automatic integer bslot(input integer bb);       // the slot a beat overlaps, -1 none
        integer pp2; bslot = -1;
        for (pp2 = 0; pp2 < PMAX; pp2 = pp2 + 1)
            if (pp2 * XC + XOFF < bb * 2048 + 2048 && pp2 * XC + XOFF + 1024 > bb * 2048) bslot = pp2;
    endfunction
    wire [3:0] tt = MUT_T ? (4'd7 - t) : t;
    reg [1023:0] rw;                       // registered t-select of the macro read (the beat's slot word)
    wire [2047:0] beat;
    wire [2047:0] beats [0:NBMAX-1];
    genvar gb;
    generate for (gb = 0; gb < NBMAX; gb = gb + 1) begin : g_beat
        localparam integer PS = bslot(gb);
        localparam integer OFF = (PS < 0) ? 0 : PS * XC + XOFF - gb * 2048;   // slot block start rel. to the beat
        if (PS < 0) begin : g_none
            assign beats[gb] = 2048'd0;
        end else if (OFF >= 0) begin : g_pos
            wire [4095:0] sh = {3072'd0, rw} << OFF;
            assign beats[gb] = sh[2047:0];
        end else begin : g_neg
            wire [1023:0] sh = rw >> (-OFF);
            assign beats[gb] = {1024'd0, sh};
        end
    end endgenerate
    assign beat = beats[s3_b];
    function automatic [3:0] slot_of(input [6:0] bb);
        integer x; slot_of = 4'd0;
        for (x = 0; x < NBMAX; x = x + 1) if (bb == x && bslot(x) >= 0) slot_of = bslot(x);
    endfunction
    function automatic in_slot(input [6:0] bb, input [3:0] np);
        integer x; in_slot = 1'b0;
        for (x = 0; x < NBMAX; x = x + 1) if (bb == x && bslot(x) >= 0 && bslot(x) < np) in_slot = 1'b1;
    endfunction
    integer w;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin busy <= 1'b0; x_done <= 1'b0; x_fault <= 1'b0; xw_en <= 1'b0; vmq <= 0; cbusy <= 0; ph <= 0;
                          hv <= 0; wq_v <= 1'b0; s1_v <= 1'b0; s2_v <= 1'b0; s3_v <= 1'b0; end
        else begin
            x_done <= 1'b0; xw_en <= 1'b0; wq_v <= 1'b0; s1_v <= 1'b0;
            // read pipeline: s1 (pins) -> s2 (macro edge) -> s3 (rw: t-select) -> the beat
            s2_v <= s1_v; s2_t <= s1_t; s2_addr <= s1_addr; s2_b <= s1_b; s2_ok <= s1_ok;
            s3_v <= s2_v; s3_addr <= s2_addr; s3_b <= s2_b; s3_ok <= s2_ok;
            if (s2_v) begin : tsel
                integer qq; for (qq = 0; qq < 4; qq = qq + 1) rw[256 * qq +: 256] <= rd[{s2_t, 2'(qq)}];
            end
            if (s3_v) begin xw_en <= 1'b1; xw_addr <= s3_addr; xw_grp <= s3_b; xw_data <= s3_ok ? beat : 2048'd0; end
            for (c = 0; c < NXC; c = c + 1) vmq[c*338 + 337] <= 1'b0;
            if (x_v && x_rdy) begin
                if (x_fmt == 2'd1 || x_fmt == 2'd2 || x_space != 2'd1 || |x_base[2:0] || |x_stride[2:0] || x_p > PMAX ||
                    x_p == 4'd0) x_fault <= 1'b1;
                else begin
                    busy <= 1'b1; base <= x_base[17:0]; kk <= x_n; pp <= x_p; st <= x_stride[17:0];
                    gn <= ((x_n - 21'd1) >> 9) + 8'd1; g <= 8'd0; p_rd <= 4'd0; j_rd <= 7'd0; got <= 11'd0; ph <= 2'd0;
                    nb <= ({12'd0, x_p} * 16'd3152 + 16'd2047) >> 11;    // 16 b: P x XC reaches 25,216
                end
            end
            if (busy && ph == 2'd0) begin
                // issue: one sector read a cycle on the lowest free client; lanes j, then columns p
                begin : iss
                    reg found; integer cf; reg [31:0] wd;
                    found = 1'b0; cf = 0;
                    for (c = NXC - 1; c >= 0; c = c - 1) if (!cbusy[c]) begin found = 1'b1; cf = c; end
                    wd = {14'd0, base} + p_rd * {14'd0, st} + {g, 9'd0} + {j_rd, 3'd0};
                    if (found && p_rd < pp) begin
                        vmq[cf*338 +: 338] <= {1'b1, 1'b0, wd[29:3], 5'd0, 256'd0, 32'd0, {5'd0, p_rd, j_rd}};
                        cbusy[cf] <= 1'b1;
                        if (j_rd == 7'd63) begin j_rd <= 7'd0; p_rd <= p_rd + 4'd1; end else j_rd <= j_rd + 7'd1;
                    end
                end
                for (c = 0; c < NXC; c = c + 1)                                  // hold every arriving response
                    if (cbusy[c] && !hv[c] && vr[c][273] && !vr[c][256]) begin hv[c] <= 1'b1; hdat[c] <= vr[c]; end
                if (lsel_v) begin : land                                        // land one held sector an edge
                    reg [3:0] lp; reg [6:0] lj; reg [15:0] v [0:7];
                    lp = hdat[lsel][267:264]; lj = hdat[lsel][263:257];      // tag [272:257] = {p 4, j 7} low bits
                    for (w = 0; w < 8; w = w + 1)
                        v[w] = (({13'd0, g, 9'd0} + {lj, 3'd0} + w) < kk) ? bf16(hdat[lsel][32*w +: 32]) : 16'd0;
                    wq_v <= 1'b1; wq_q <= lj[5:4]; wq_a <= lp; wq_l <= lj[3:0];
                    for (w = 0; w < 4; w = w + 1) wq_d[w] <= {v[7], v[6], v[5], v[4], v[3], v[2], v[1], v[0]};
                    hv[lsel] <= 1'b0; cbusy[lsel] <= 1'b0;
                end
                if (got_n == {pp, 6'd0}) begin ph <= 2'd1; t <= 4'd0; b <= 7'd0; end
            end
            if (busy && ph == 2'd0) got <= got + {7'd0, nland};
            if (busy && ph == 2'd1) begin                                     // emission stage 1: read bank t
                s1_v <= 1'b1; s1_t <= tt[2:0]; s1_sp <= slot_of(b);
                s1_addr <= {g[3:0], t[2:0]}; s1_b <= b; s1_ok <= in_slot(b, pp);
                if (b == nb - 7'd1) begin
                    b <= 7'd0;
                    if (t == 4'd7) begin
                        if (g == gn - 8'd1) begin ph <= 2'd2; end
                        else begin g <= g + 8'd1; p_rd <= 4'd0; j_rd <= 7'd0; got <= 11'd0; ph <= 2'd0; end
                    end
                    t <= t + 4'd1;
                end else b <= b + 7'd1;
            end
            if (busy && ph == 2'd2 && !s1_v && !s2_v && !s3_v) begin busy <= 1'b0; x_done <= 1'b1; ph <= 2'd0; end   // last beat out
        end
    end
endmodule
`default_nettype wire
