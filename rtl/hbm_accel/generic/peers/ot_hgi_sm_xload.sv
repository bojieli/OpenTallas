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
// BLOCK-DOT x (fmt 1 FP8 / fmt 2 FP4 weights; hgi-1010/d, the DS activation path): x is quantised HERE, exactly as the
//   golden's linear_q (hdc_golden_v41.quant_fp8: per 32-block amax, E4M3 codes + block exponent) by the qualified r25
//   activation quantiser ot_hdc_actquant (one block an edge), and laid out as the smh block-dot fragment
//   (tools/dshbm_matched_sm_seq.gen_op): lane j (< LA = 4 FP8 / 8 FP4) of column p at bit p XC + 266 j holds block
//   b = (g LA + j) 8 + t: 32 codes (8 b each) then the exponent (10 b); lanes past K / 32 blocks are 0.  Per fragment
//   address (g, t): the P x LA blocks are read (4 sectors each, two assembling at a time on the packet clients),
//   quantised into a P x 2,128-b register file (cleared per address), then the address's beats leave on the xw pins.
// Refusals (x_fault): A not VM (STREAM x enters from the SU stream, not here), A.base / A.stride not 8-word aligned,
//   block-dot K not a multiple of 32 (or 0), a non-finite element in a block-dot block (the quantiser's fault).
// STORAGE (FILL-9 2026-10-10): 32 ot_sram_1r1w_128x256_m1 macros m[t][q] (t < 8 fragment row, q < 4 lane quarter):
// word p (slot) of m[t][q] holds lanes 16q .. 16q + 15 of slot p, t-value t, as 16 x BF16.  A landing sector (p, j) is
// ONE masked word write in each of the 8 macros m[t][j >> 4] (16-b mask at slice j & 15); a beat reads the 4 macros
// m[t][*] at word p (1,024 b).
// PIPELINE (fe-push-hgi-1010, 2026-10-10; root cause of the fc210e160 routes: TT -545 post-CTS a / -109 routed b):
//   (1) macro out -> 8:1 t-select (s2_t binary select fanning out to 1,024 mux bits, 24 levels) -> rw in ONE cycle
//       across the macro field.  Now: a gated capture flop at each macro (cap = rd AND its own registered read
//       enable, zero otherwise), a registered OR-4 per (macro half, quarter) and a registered OR-2 into rw: no select
//       net, every stage local to its macros (no single-cycle wire > 504 um).
//   (2) held response -> priority select -> 4:1 x 274 mux -> 8 x RNE adders + a 21-b range compare -> write pins in
//       ONE cycle (hv -> wq_d 24 levels).  Now: L1 registers the selected sector, L2 converts (the range compare is
//       against a per-group running remainder, not g x 512 + ...), W1 per-quarter copy, W2 per-macro pin flops.
//   (3) read command: central decision -> per-quarter copy -> per-macro pin flops (enable / address replicated per
//       macro, kept), so no register drives the 32 macros' pins across the field.
//   (4) beat assembly registered (xb), xw_* are pure pin flops.
// The x-store write SEQUENCE is unchanged (tb_hgi_xload_lock vs the flop x-load ot_hgi_sm_xload_old); latency +6
// edges a beat (pipelined) and +3 edges a landing (once a group: emission waits for the write pipe to drain).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sm_xload #(
    parameter integer NXC = 4,            // VM packet clients (reads in flight)
    parameter integer PMAX = 8,
    parameter integer MUT_M = 0,          // mutant (FILL-9): a landing sector's write mask on lane slice (j ^ 1) of its quarter
    parameter integer MUT_T = 0,          // mutant: lane j takes t from the wrong half (k = (g 64 + j) 8 + (7 - t))
    parameter integer MUT_BD = 0          // mutant: a block-dot block lands in the neighbouring lane (j ^ 1)
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
    output wire [NXC*338-1:0] vmq,   // {v, payload 337}: v from a reset flop, payload from a data flop
    input  wire [NXC*274-1:0] vmr
);
    localparam integer XC = 3152, XOFF = 2128;
    localparam integer RD = 8;             // read pipe: r0 decision, r1 quarter copy, r2 pins, r3 macro out, r4 cap, r5 or4, r6 rw, r7 xb
    reg busy; reg [3:0] pp; reg [17:0] base; reg [17:0] st;
    reg [7:0] gn, g; reg [3:0] p_rd; reg [6:0] j_rd; reg [3:0] t; reg [6:0] b; reg [6:0] nb;
    reg signed [22:0] krem;                // K - g x 512 (elements of this group still inside K)
    // ---- reset: the port drives only the relay (design standard); control flops reset from rst_c, data flops never
    wire rst_c;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rst_c));
    // ---- read pipeline valids (reset) and metadata (data)
    reg [RD-1:0] rv;
    reg [6:0] rm_addr [0:RD-1]; reg [6:0] rm_b [0:RD-1]; reg rm_ok [0:RD-1];
    reg [2:0] r0_t; reg [3:0] r0_sp;
    reg [2047:0] xb;                       // r7: the assembled beat
    // ---- write pipeline: L1 (selected sector), L2 (converted), W1 (per-quarter copy), W2 (per-macro pins)
    reg l1_v, l2_v; reg [3:0] w1_v;
    reg [273:0] l1_d; reg [127:0] l2_d; reg [1:0] l2_q; reg [3:0] l2_a; reg [3:0] l2_l;
    reg [127:0] w1_d [0:3]; reg [3:0] w1_a [0:3]; reg [3:0] w1_l [0:3];
    // ---- read command per-quarter copy (r1): t one-hot + slot address
    reg [7:0] r1_oh [0:3]; reg [3:0] r1_sp [0:3];
    // ---- macro field
    wire [255:0] cap [0:31];               // gated capture of m[t][q] at index t * 4 + q (zero unless read)
    reg  [255:0] or4 [0:7];                // index h * 4 + q: OR of cap[t][q] over t in half h (t >> 2 == h)
    genvar gt, gq, gs;
    generate for (gt = 0; gt < 8; gt = gt + 1) begin : g_t
        for (gq = 0; gq < 4; gq = gq + 1) begin : g_q
            // per-macro pin flops (kept: one copy a macro, so no register drives pins across the field)
            (* keep = 1 *) reg       rp_ce;  (* keep = 1 *) reg [3:0] rp_a;   (* keep = 1 *) reg rp_sel;
            (* keep = 1 *) reg       wp_ce;  (* keep = 1 *) reg [3:0] wp_a;   reg [15:0] wp_d;  reg [15:0] wp_m;
            reg [255:0] cq;
            wire [255:0] rd;
            wire [3:0] lsl = w1_l[gq] ^ ((MUT_M != 0) ? 4'd1 : 4'd0);
            always @(posedge clk or negedge rst_c) begin
                if (!rst_c) begin rp_ce <= 1'b0; rp_sel <= 1'b0; wp_ce <= 1'b0; end
                else begin rp_ce <= rv[1] && r1_oh[gq][gt]; rp_sel <= rp_ce; wp_ce <= w1_v[gq]; end
            end
            always @(posedge clk) begin
                rp_a <= r1_sp[gq];
                wp_a <= w1_a[gq]; wp_d <= w1_d[gq][16 * gt +: 16]; wp_m <= 16'd1 << lsl;
                cq <= rd & {256{rp_sel}};                                      // capture: zero unless this macro was read
            end
            wire [255:0] wmask;
            for (gs = 0; gs < 16; gs = gs + 1) begin : g_m
                assign wmask[16 * gs +: 16] = {16{wp_m[gs]}};
            end
            ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk),
                .r_ce_in(rp_ce), .r_addr_in({3'd0, rp_a}), .rd_out(rd),
                .w_ce_in(wp_ce), .w_addr_in({3'd0, wp_a}), .wd_in({16{wp_d}}),
                .w_mask_in(wmask), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
            assign cap[gt * 4 + gq] = cq;
        end
    end endgenerate
    always @(posedge clk) for (integer h = 0; h < 2; h = h + 1) for (integer q = 0; q < 4; q = q + 1)
        or4[h * 4 + q] <= cap[(4 * h + 0) * 4 + q] | cap[(4 * h + 1) * 4 + q] | cap[(4 * h + 2) * 4 + q] |
                          cap[(4 * h + 3) * 4 + q];
    reg [1023:0] rw;                       // the beat's slot word (OR-2 of the halves)
    always @(posedge clk) for (integer q = 0; q < 4; q = q + 1) rw[256 * q +: 256] <= or4[q] | or4[4 + q];
    // ---- VM responses
    reg [NXC-1:0] hv;                      // a client's response held, not yet landed
    reg [273:0] hdat [0:NXC-1];
    reg [10:0] got;                        // sectors landed for this group
    integer cl; reg lsel_v; integer lsel;
    always @* begin
        lsel_v = 1'b0; lsel = 0;
        for (cl = NXC - 1; cl >= 0; cl = cl - 1) if (hv[cl]) begin lsel_v = 1'b1; lsel = cl; end
    end
    reg [1:0] ph;                          // 0 read, 1 emit, 2 done
    reg [273:0] vr [0:NXC-1];
    always @(posedge clk) for (integer cv = 0; cv < NXC; cv = cv + 1) vr[cv] <= vmr[cv*274 +: 274];
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
    function automatic [3:0] slot_of(input [6:0] bb);
        integer x; slot_of = 4'd0;
        for (x = 0; x < NBMAX; x = x + 1) if (bb == x && bslot(x) >= 0) slot_of = bslot(x);
    endfunction
    function automatic in_slot(input [6:0] bb, input [3:0] np);
        integer x; in_slot = 1'b0;
        for (x = 0; x < NBMAX; x = x + 1) if (bb == x && bslot(x) >= 0 && bslot(x) < np) in_slot = 1'b1;
    endfunction
    // ---- command pin flop (the x_* decode does not run from the pins): +1 edge a command
    reg cmd_v; reg [39:0] c_base; reg [20:0] c_n; reg [3:0] c_p; reg [31:0] c_stride; reg [1:0] c_space, c_fmt;
    assign x_rdy = !busy && !cmd_v;
    always @(posedge clk) if (x_v && x_rdy) begin
        c_base <= x_base; c_n <= x_n; c_p <= x_p; c_stride <= x_stride; c_space <= x_space; c_fmt <= x_fmt;
    end
    wire c_bdf = (c_fmt == 2'd1 || c_fmt == 2'd2);
    wire c_bad = c_space != 2'd1 || |c_base[2:0] || |c_stride[2:0] || c_p > PMAX || c_p == 4'd0 ||
                 (c_bdf && (|c_n[4:0] || c_n == 21'd0));
    // ---- block-dot state
    reg bd; reg [3:0] la; reg [15:0] nbk;  // fmt 1 / 2; lanes a fragment column; K / 32 blocks
    reg [1:0] bph;                         // 1 read + quantise address (g, t), 2 emit its beats
    reg [3:0] bp; reg [3:0] bj; reg [1:0] bs; reg asl;   // issue cursor: column, lane, sector, assembly slot
    reg [15:0] bq_exp, bq_got; reg bq_iss_done; reg bflt;
    reg [1023:0] ab [0:1]; reg [2:0] acnt [0:1]; reg [3:0] ap [0:1]; reg [3:0] aj [0:1]; reg [1:0] aact;
    reg [2127:0] qb [0:PMAX-1];
    wire aq_vo, aq_f; wire [255:0] aq_q; wire signed [9:0] aq_e; wire [511:0] aq_y;
    reg aq_v; reg [1023:0] aq_x; reg [7:0] aq_tg; reg [7:0] tgf [0:15]; reg [3:0] tgh, tgt;
    ot_hdc_actquant u_aq (.clk(clk), .rst_n(rst_c), .v(aq_v), .fp4(1'b0), .x(aq_x), .vo(aq_vo), .q(aq_q), .e(aq_e),
                          .y(aq_y), .fault(aq_f));
    localparam integer NBQ = (PMAX * XC + 2047) / 2048;
    wire [PMAX*XC-1:0] fq;
    for (genvar gf = 0; gf < PMAX; gf = gf + 1) begin : g_fq
        assign fq[gf*XC +: XC] = {{(XC-2128){1'b0}}, qb[gf]};
    end
    wire [NBQ*2048-1:0] fqx = {{(NBQ*2048 - PMAX*XC){1'b0}}, fq};
    reg be_v; reg [6:0] be_a, be_g; reg [2047:0] be_d;   // a block-dot beat on its way to the xw pins
    wire [15:0] blk = ({8'd0, g} * {12'd0, la} + {12'd0, bj}) * 16'd8 + {12'd0, t};
    wire blk_ok = blk < nbk;
    wire [31:0] wdb = {14'd0, base} + bp * {14'd0, st} + {blk, 5'd0} + {bs, 3'd0};
    wire bd_rd = busy && ph == 2'd3 && bph == 2'd1;
    wire bd_issue = bd_rd && !bq_iss_done && bp < pp && blk_ok && found && !aact[asl];
    reg bq_v; reg bq_s;                    // a complete block -> the quantiser (older slot first)
    always @* begin
        bq_v = 1'b0; bq_s = 1'b0;
        if (aact[!asl] && acnt[!asl] == 3'd4) begin bq_v = 1'b1; bq_s = !asl; end
        else if (aact[asl] && acnt[asl] == 3'd4) begin bq_v = 1'b1; bq_s = asl; end
    end
    wire bd_done_rd = bd_rd && bq_iss_done && bq_got == bq_exp && !aact[0] && !aact[1] && !aq_v;
    wire be_last = bph == 2'd2 && b == nb - 7'd1;
    wire start = cmd_v && !c_bad;
    // ---- VM packet requests: valid (reset) + payload (data)
    reg [NXC-1:0] vq_v; reg [336:0] vq_d [0:NXC-1];
    genvar gc;
    generate for (gc = 0; gc < NXC; gc = gc + 1) begin : g_vq
        assign vmq[gc*338 +: 338] = {vq_v[gc], vq_d[gc]};
    end endgenerate
    // ---- shared decisions
    reg found; integer cf; reg [31:0] wd;
    always @* begin
        found = 1'b0; cf = 0;
        for (integer cc = NXC - 1; cc >= 0; cc = cc - 1) if (!cbusy[cc]) begin found = 1'b1; cf = cc; end
        wd = {14'd0, base} + p_rd * {14'd0, st} + {g, 9'd0} + {j_rd, 3'd0};
    end
    wire rd_ph = busy && ph == 2'd0, em_ph = busy && ph == 2'd1;
    wire issue = rd_ph && found && p_rd < pp;
    reg [NXC-1:0] take;
    always @* for (integer ct = 0; ct < NXC; ct = ct + 1) take[ct] = (rd_ph || bd_rd) && cbusy[ct] && !hv[ct] && vr[ct][273] && !vr[ct][256];
    // a landing waits until no read is still on its way to the macro pins (write-after-read order of the field)
    wire rd_pins_busy = |rv[2:0];
    wire land = rd_ph && lsel_v && !rd_pins_busy;
    wire wr_busy = l1_v || l2_v || |w1_v;
    wire to_emit = rd_ph && got == {pp, 6'd0} && !wr_busy;   // every landed sector written (W2 is the macro write edge)
    wire last_b = b == nb - 7'd1, last_bt = last_b && t == 4'd7, last_g = g == gn - 8'd1;
    wire fin = busy && ph == 2'd2 && !(|rv) && !be_v;         // last beat out
    // ---- control (reset)
    always @(posedge clk or negedge rst_c) begin
        if (!rst_c) begin cmd_v <= 1'b0; busy <= 1'b0; x_done <= 1'b0; x_fault <= 1'b0; xw_en <= 1'b0; vq_v <= 0;
                          cbusy <= 0; ph <= 0; hv <= 0; rv <= 0; l1_v <= 1'b0; l2_v <= 1'b0; w1_v <= 4'd0;
                          bd <= 1'b0; bph <= 2'd0; aact <= 2'b00; aq_v <= 1'b0; tgh <= 4'd0; tgt <= 4'd0; be_v <= 1'b0;
                          bflt <= 1'b0; end
        else begin
            x_done <= fin && !(bd && bflt);
            if (fin && bd && bflt) x_fault <= 1'b1;
            rv <= {rv[RD-2:0], em_ph}; xw_en <= rv[RD-1] || be_v;
            l1_v <= land; l2_v <= l1_v;
            for (integer wq = 0; wq < 4; wq = wq + 1) w1_v[wq] <= l2_v && l2_q == wq;
            cmd_v <= (x_v && x_rdy) ? 1'b1 : 1'b0;
            if (cmd_v && c_bad) x_fault <= 1'b1;
            if (start) begin busy <= 1'b1; ph <= c_bdf ? 2'd3 : 2'd0; bd <= c_bdf; bph <= 2'd1; aact <= 2'b00; bflt <= 1'b0; end
            vq_v <= {NXC{1'b0}};
            if (issue || bd_issue) begin vq_v[cf] <= 1'b1; cbusy[cf] <= 1'b1; end
            for (integer ch = 0; ch < NXC; ch = ch + 1) if (take[ch]) hv[ch] <= 1'b1;
            if (land) begin hv[lsel] <= 1'b0; cbusy[lsel] <= 1'b0; end
            // block-dot: land one held sector an edge into its assembly slot; complete blocks -> the quantiser
            aq_v <= 1'b0; be_v <= 1'b0;
            if (bd_rd && lsel_v) begin hv[lsel] <= 1'b0; cbusy[lsel] <= 1'b0; end
            if (bd_issue && bs == 2'd3) aact[asl] <= 1'b1;
            if (bd_rd && bq_v) begin aq_v <= 1'b1; aact[bq_s] <= 1'b0; end
            if (aq_v) tgt <= tgt + 4'd1;
            if (ph == 2'd3 && aq_vo) begin tgh <= tgh + 4'd1; if (aq_f) bflt <= 1'b1; end
            if (bd_done_rd) bph <= 2'd2;
            if (busy && ph == 2'd3 && bph == 2'd2) begin
                be_v <= 1'b1;
                if (be_last) begin
                    if (t == 4'd7 && g == gn - 8'd1) ph <= 2'd2; else bph <= 2'd1;
                end
            end
            if (to_emit) ph <= 2'd1;
            if (em_ph && last_bt) ph <= last_g ? 2'd2 : 2'd0;
            if (fin) begin busy <= 1'b0; ph <= 2'd0; end
        end
    end
    // ---- data (no reset)
    always @(posedge clk) begin
        if (start) begin
            base <= c_base[17:0]; pp <= c_p; st <= c_stride[17:0]; krem <= {2'b00, c_n};
            gn <= ((c_n - 21'd1) >> 9) + 8'd1; g <= 8'd0; p_rd <= 4'd0; j_rd <= 7'd0; got <= 11'd0;
            nb <= ({12'd0, c_p} * 16'd3152 + 16'd2047) >> 11;    // 16 b: P x XC reaches 25,216
            la <= (c_fmt == 2'd2) ? 4'd8 : 4'd4; nbk <= c_n[20:5];
            if (c_bdf) begin
                // Gn = ceil(ceil(nb / 8) / LA) groups: FP8 ceil(K / 1,024), FP4 ceil(K / 2,048)
                gn <= (c_fmt == 2'd2) ? ((c_n - 21'd1) >> 11) + 8'd1 : ((c_n - 21'd1) >> 10) + 8'd1;
                t <= 4'd0; b <= 7'd0; bp <= 4'd0; bj <= 4'd0; bs <= 2'd0; asl <= 1'b0;
                bq_exp <= 16'd0; bq_got <= 16'd0; bq_iss_done <= 1'b0; acnt[0] <= 3'd0; acnt[1] <= 3'd0;
                for (integer w = 0; w < PMAX; w = w + 1) qb[w] <= 2128'd0;
            end
        end
        // ---- block-dot data path
        if (bd_rd && !bq_iss_done) begin
            if (bp >= pp) bq_iss_done <= 1'b1;
            else if (!blk_ok) begin                     // a block past K / 32: skipped (its lanes stay 0)
                if (bj == la - 4'd1) begin bj <= 4'd0; bp <= bp + 4'd1; end else bj <= bj + 4'd1;
            end else if (bd_issue) begin
                vq_d[cf] <= {1'b0, wdb[29:3], 5'd0, 256'd0, 32'd0, {5'd0, asl, bs, bp, bj}};
                if (bs == 2'd3) begin
                    bs <= 2'd0; ap[asl] <= bp; aj[asl] <= bj; asl <= !asl; bq_exp <= bq_exp + 16'd1;
                    if (bj == la - 4'd1) begin bj <= 4'd0; bp <= bp + 4'd1; end else bj <= bj + 4'd1;
                end else bs <= bs + 2'd1;
            end
        end
        if (bd_rd && lsel_v) begin : bland                   // tag {slot, sector, p, j}
            reg sl_; reg [1:0] ss_; sl_ = hdat[lsel][267]; ss_ = hdat[lsel][266:265];
            ab[sl_][256*ss_ +: 256] <= hdat[lsel][255:0];
            acnt[sl_] <= ((bq_v && bq_s == sl_) ? 3'd0 : acnt[sl_]) + 3'd1;
        end
        if (bd_rd && bq_v) begin
            aq_x <= ab[bq_s]; aq_tg <= {ap[bq_s], aj[bq_s]};
            if (!(lsel_v && hdat[lsel][267] == bq_s)) acnt[bq_s] <= 3'd0;
        end
        if (aq_v) tgf[tgt] <= aq_tg;                         // the quantiser is in order: tags ride
        if (ph == 2'd3 && aq_vo) begin
            qb[tgf[tgh][7:4]][266*(tgf[tgh][3:0] ^ MUT_BD[3:0]) +: 266] <= {aq_e, aq_q}; bq_got <= bq_got + 16'd1;
        end
        if (busy && ph == 2'd3 && bph == 2'd2) begin
            be_a <= {g[3:0], t[2:0]}; be_g <= b; be_d <= fqx[b*2048 +: 2048];
            if (be_last) begin
                b <= 7'd0;
                for (integer w = 0; w < PMAX; w = w + 1) qb[w] <= 2128'd0;
                bp <= 4'd0; bj <= 4'd0; bs <= 2'd0; bq_exp <= 16'd0; bq_got <= 16'd0; bq_iss_done <= 1'b0;
                if (t == 4'd7) begin t <= 4'd0; if (g != gn - 8'd1) g <= g + 8'd1; end else t <= t + 4'd1;
            end else b <= b + 7'd1;
        end
        if (issue) begin
            vq_d[cf] <= {1'b0, wd[29:3], 5'd0, 256'd0, 32'd0, {5'd0, p_rd, j_rd}};
            if (j_rd == 7'd63) begin j_rd <= 7'd0; p_rd <= p_rd + 4'd1; end else j_rd <= j_rd + 7'd1;
        end
        for (integer cd = 0; cd < NXC; cd = cd + 1) if (take[cd]) hdat[cd] <= vr[cd];
        // landing: L1 = the selected held sector, L2 = BF16 + range, W1 = per-quarter copy (W2 = per-macro pins)
        if (land) l1_d <= hdat[lsel];
        begin : l2c
            reg [3:0] lp; reg [6:0] lj; reg [15:0] v [0:7];
            lp = l1_d[267:264]; lj = l1_d[263:257];                 // tag [272:257] = {p 4, j 7} low bits
            for (integer wv = 0; wv < 8; wv = wv + 1)
                v[wv] = ($signed({13'd0, lj, 3'd0}) + wv < krem) ? bf16(l1_d[32*wv +: 32]) : 16'd0;
            if (l1_v) begin
                l2_q <= lj[5:4]; l2_a <= lp; l2_l <= lj[3:0];
                l2_d <= {v[7], v[6], v[5], v[4], v[3], v[2], v[1], v[0]};
            end
        end
        for (integer wc = 0; wc < 4; wc = wc + 1) if (l2_v && l2_q == wc) begin
            w1_d[wc] <= l2_d; w1_a[wc] <= l2_a; w1_l[wc] <= l2_l;
        end
        if (rd_ph) got <= got + {10'd0, land};
        if (to_emit) begin t <= 4'd0; b <= 7'd0; end
        // read pipeline: r0 decision -> r1 per-quarter copy -> r2 macro pins -> r3 macro out -> r4 cap -> r5 or4
        //                -> r6 rw -> r7 xb (beat) -> xw pins
        if (em_ph) begin
            r0_t <= tt[2:0]; r0_sp <= slot_of(b);
            rm_addr[0] <= {g[3:0], t[2:0]}; rm_b[0] <= b; rm_ok[0] <= in_slot(b, pp);
            if (last_b) begin
                b <= 7'd0;
                if (t == 4'd7 && !last_g) begin
                    g <= g + 8'd1; p_rd <= 4'd0; j_rd <= 7'd0; got <= 11'd0; krem <= krem - 23'sd512;
                end
                t <= t + 4'd1;
            end else b <= b + 7'd1;
        end
        for (integer q = 0; q < 4; q = q + 1) begin r1_oh[q] <= 8'd1 << r0_t; r1_sp[q] <= r0_sp; end
        for (integer s = 1; s < RD; s = s + 1) begin
            rm_addr[s] <= rm_addr[s - 1]; rm_b[s] <= rm_b[s - 1]; rm_ok[s] <= rm_ok[s - 1];
        end
        // r7 (xb): the beat assembled from rw (r6) under its stage-6 beat index; xw_* = pin flops of xb
        if (rv[RD-2]) xb <= rm_ok[RD-2] ? beats[rm_b[RD-2]] : 2048'd0;
        if (rv[RD-1]) begin xw_addr <= rm_addr[RD-1]; xw_grp <= rm_b[RD-1]; xw_data <= xb; end
        if (be_v) begin xw_addr <= be_a; xw_grp <= be_g; xw_data <= be_d; end
    end
endmodule
`default_nettype wire
