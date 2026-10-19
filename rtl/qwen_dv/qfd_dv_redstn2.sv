`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_redstn2 -- the slice2 (dv2r8f2 port cut) reduction station: as qfd_dv_redstn (levels 7 / 8 / 9 with the
// qfd_slab_pair_add adder, ot_hdc_fp32_mul_lat BF16 row scale, same rounding points), but the quad's two level-7 pairs
// arrive IN PARALLEL on their own ports:
//   rs_s = {far rs_o 514, near rs 514} of the band-1 cluster: the lower pair (b0 far over b1's feedthrough, b1 near)
//   rs_n = {far rs_o 514, near rs 514} of the band-2 cluster: the upper pair (b3 far, b2 near)
// The far word of a pair arrives SKEW (14) edges after its near word: both near words pass a SKEW-edge line.
//   lo = b0 + b1, hi = b3 + b2 (IEEE add commutes; zero results canonical): the golden (b0 + b1), (b2 + b3).
//   MODE 0 (L7, gate / up): lo words are results j = 0..7 at once; hi words wait in an 8-word buffer and follow
//          (the single 16-lane scale: + 8 edges, priced).  MODE 1 (L8): lo + hi on the same edge.
//   MODE 2 / 3: level 9 as qfd_dv_redstn (receiver: own L8 + l9_i; sender: own L8 on l9_o).
// MUT 3 (bench negative control): the scale word of result j is read at sbase + j + 1 (must FAIL).
// LAST-K SELECTION (QW-DIEFIX 10-19, QW-XHEAD XT1 finding): the tiles stream their running accumulator once per k step,
//   so a cluster pair delivers JB (8) words per (round, k): rounds x kc x 8 words, and only the k = kc - 1 block is the
//   level-6 result (XT1 measured qkv 64 / o 48 / gu 256 / down 144 rs words for 8 / 24 / 8 / 24 results).  cfg_kcm1 =
//   kc - 1 (STN cmd [58:51]; 0 = every word is a result, the pre-fix behaviour for kc = 1).  Each pair stream (lo = rs_s,
//   hi = rs_n) counts its words in blocks of JB and passes only the last block of every kc to level 7; the dropped words
//   are still checked (valid pairing, fault bits).  Pure counters on the input valids: no data-path flop, no new edge.
//   MUT 14 (negative control): kcm1 ignored (every word passes: wrong sums + too many result words -> must FAIL).
// =====================================================================================================================
module qfd_dv_redstn2 #(
    parameter integer ADD_LAT   = 7,
    parameter integer SKEW      = 14,
    parameter integer SCALE_LAT = 6,
    parameter integer MUT       = 0,
    parameter integer JB        = 8                // words per (round, k) block of one pair
) (
    input  wire          ck,
    input  wire          rst_n,
    // op configuration (held from the STN command until the next one)
    input  wire          cfg_v,
    input  wire [1:0]    cfg_mode,
    input  wire          cfg_wsrc,
    input  wire [7:0]    cfg_nwords,
    input  wire [8:0]    cfg_sbase,
    input  wire [7:0]    cfg_kcm1,                 // kc - 1: only every kc-th JB-word block is a result
    // words (pin-registered by the slice top)
    input  wire [1027:0] rs_s,
    input  wire [1027:0] rs_n,
    input  wire [513:0]  nb_i,
    output reg  [513:0]  nb_o,
    // BF16 table read (word address; answer 2 edges later)
    output reg           bt_re,
    output reg  [8:0]    bt_word,
    input  wire [255:0]  bt_q,
    // scaled result word
    output reg           r_v,
    output reg  [7:0]    r_idx,
    output reg           r_last,
    output reg  [511:0]  r_d,
    output reg           fault
);
    // ---------------------------------------------------------------- configuration
    reg [1:0] mode; reg wsrc; reg [7:0] nwords; reg [8:0] sbase; reg [7:0] kcm1;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin mode <= 2'd0; wsrc <= 1'b0; nwords <= 8'd0; sbase <= 9'd0; kcm1 <= 8'd0; end
        else if (cfg_v) begin mode <= cfg_mode; wsrc <= cfg_wsrc; nwords <= cfg_nwords; sbase <= cfg_sbase;
                              kcm1 <= (MUT == 14) ? 8'd0 : cfg_kcm1; end
    // ---------------------------------------------------------------- level 7: two pairs in parallel
    wire [513:0] ns, nn;                           // the near words, SKEW edges later
    ot_hdc_delay #(.W(514), .D(SKEW), .RESET(1)) u_sks (.clk(ck), .rst_n(rst_n), .d(rs_s[513:0]), .q(ns));
    ot_hdc_delay #(.W(514), .D(SKEW), .RESET(1)) u_skn (.clk(ck), .rst_n(rst_n), .d(rs_n[513:0]), .q(nn));
    wire [513:0] fs = rs_s[1027:514], fn = rs_n[1027:514];
    wire plo = fs[512] & ns[512], phi = fn[512] & nn[512];        // a pair word (every k step)
    // last-k selection: per pair stream, word index in the JB block and k index; klast_* = this block is k = kc - 1
    localparam integer JBW = (JB > 1) ? $clog2(JB) : 1;
    reg [JBW-1:0] wlo, whi;
    reg [7:0]     klo, khi;
    reg           klast_lo, klast_hi;
    wire          eblo = plo && wlo == JB - 1, ebhi = phi && whi == JB - 1;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin
            wlo <= 0; whi <= 0; klo <= 8'd0; khi <= 8'd0; klast_lo <= 1'b1; klast_hi <= 1'b1;
        end else if (cfg_v) begin
            wlo <= 0; whi <= 0; klo <= 8'd0; khi <= 8'd0;
            klast_lo <= (MUT == 14) || cfg_kcm1 == 8'd0; klast_hi <= (MUT == 14) || cfg_kcm1 == 8'd0;
        end else begin
            if (plo) wlo <= eblo ? {JBW{1'b0}} : wlo + 1'b1;
            if (phi) whi <= ebhi ? {JBW{1'b0}} : whi + 1'b1;
            if (eblo) begin
                klo <= klast_lo ? 8'd0 : klo + 8'd1;
                klast_lo <= klast_lo ? kcm1 == 8'd0 : klo + 8'd1 == kcm1;
            end
            if (ebhi) begin
                khi <= klast_hi ? 8'd0 : khi + 8'd1;
                klast_hi <= klast_hi ? kcm1 == 8'd0 : khi + 8'd1 == kcm1;
            end
        end
    wire vlo_in = plo & klast_lo, vhi_in = phi & klast_hi;
    wire [511:0] ylo, yhi;
    wire [15:0] vlol, vhil;
    wire [31:0] elo, ehi;
    genvar l;
    generate for (l = 0; l < 16; l = l + 1) begin : g_l7
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT), .DRST(0)) u_lo (.clk(ck), .rst_n(rst_n), .valid_in(vlo_in),
            .a(fs[32*l +: 32]), .b(ns[32*l +: 32]), .y(ylo[32*l +: 32]), .err(elo[2*l +: 2]), .valid_out(vlol[l]));
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT), .DRST(0)) u_hi (.clk(ck), .rst_n(rst_n), .valid_in(vhi_in),
            .a(fn[32*l +: 32]), .b(nn[32*l +: 32]), .y(yhi[32*l +: 32]), .err(ehi[2*l +: 2]), .valid_out(vhil[l]));
    end endgenerate
    wire vlo = vlol[0], vhi = vhil[0];
    // MODE 0: the hi (up) block waits in an 8-word buffer and leaves on edges with no lo word
    reg [511:0] hb [0:7];
    reg [2:0]   hw, hr;
    reg [3:0]   hn;
    wire        hpop = mode == 2'd0 && !vlo && hn != 4'd0;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin hw <= 3'd0; hr <= 3'd0; hn <= 4'd0; end
        else if (cfg_v) begin hw <= 3'd0; hr <= 3'd0; hn <= 4'd0; end
        else begin
            if (vhi && mode == 2'd0) hw <= hw + 3'd1;
            if (hpop) hr <= hr + 3'd1;
            hn <= hn + ((vhi && mode == 2'd0) ? 4'd1 : 4'd0) - (hpop ? 4'd1 : 4'd0);
        end
    always @(posedge ck) if (vhi && mode == 2'd0) hb[hw] <= yhi;
    wire        v7 = (mode == 2'd0) && (vlo || hpop);
    wire [511:0] y7 = vlo ? ylo : hb[hr];
    // ---------------------------------------------------------------- level 8: lo + hi on the same edge
    wire v8_in = vlo && vhi && mode != 2'd0;
    wire [511:0] y8;
    wire [15:0] v8l;
    wire [31:0] e8;
    generate for (l = 0; l < 16; l = l + 1) begin : g_l8
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT), .DRST(0)) u_add (.clk(ck), .rst_n(rst_n), .valid_in(v8_in),
            .a(ylo[32*l +: 32]), .b(yhi[32*l +: 32]), .y(y8[32*l +: 32]), .err(e8[2*l +: 2]), .valid_out(v8l[l]));
    end endgenerate
    wire v8 = v8l[0];
    // ---------------------------------------------------------------- level 9 (receiver): own level-8 word k + nb word k
    reg [2:0] c8, c9;
    reg [3:0] lead;                                 // own level-8 words held but not yet met (0 .. 8)
    reg [511:0] h9 [0:7];
    wire nbv = nb_i[512];
    wire own9 = v8 && mode == 2'd2;
    wire v9_in = nbv && mode == 2'd2;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin c8 <= 3'd0; c9 <= 3'd0; lead <= 4'd0; end
        else if (cfg_v) begin c8 <= 3'd0; c9 <= 3'd0; lead <= 4'd0; end
        else begin
            if (own9) c8 <= c8 + 3'd1;
            if (v9_in) c9 <= c9 + 3'd1;
            lead <= lead + (own9 ? 4'd1 : 4'd0) - (v9_in ? 4'd1 : 4'd0);
        end
    always @(posedge ck) if (own9) h9[c8] <= y8;
    wire [511:0] y9;
    wire [15:0] v9l;
    wire [31:0] e9;
    generate for (l = 0; l < 16; l = l + 1) begin : g_l9
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT), .DRST(0)) u_add (.clk(ck), .rst_n(rst_n), .valid_in(v9_in),
            .a(h9[c9][32*l +: 32]), .b(nb_i[32*l +: 32]), .y(y9[32*l +: 32]), .err(e9[2*l +: 2]), .valid_out(v9l[l]));
    end endgenerate
    wire v9 = v9l[0];
    // ---------------------------------------------------------------- level-9 sender: own level-8 words leave on nb_o
    always @(posedge ck or negedge rst_n)
        if (!rst_n) nb_o <= 514'd0;
        // LB2-QWEN-C 10-18: the idle word is all zero ("a zero word is no word" on every slice port): the level-8
        // adder data (DRST 0, unreset by design) leaves only with its valid, so the 514-b die lane carries no
        // initial-state garbage (c_colW5 smoke RESET_DET: o_n_dv_l9_W4 toggled every idle edge) and idles quiet.
        // OT_QFD_L9_IDLE_MUT = the as-built ungated word (smoke mutant: reset determinism must FAIL).
`ifdef OT_QFD_L9_IDLE_MUT
        else nb_o <= {1'b0, v8 && mode == 2'd3, y8};
`else
        else nb_o <= (v8 && mode == 2'd3) ? {2'b01, y8} : 514'd0;
`endif
    // ---------------------------------------------------------------- the finished word of the op's mode
    wire        fv = (mode == 2'd0) ? v7 : (mode == 2'd1) ? v8 : (mode == 2'd2) ? v9 : 1'b0;
    wire [511:0] fd = (mode == 2'd0) ? y7 : (mode == 2'd1) ? y8 : y9;
    reg  [7:0]  j;                                  // result index within the op
    always @(posedge ck or negedge rst_n)
        if (!rst_n) j <= 8'd0;
        else if (cfg_v) j <= 8'd0;
        else if (fv) j <= j + 8'd1;
    // scale read: request on the finished word's edge, the word waits 2 edges for the BF16 table answer
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin bt_re <= 1'b0; bt_word <= 9'd0; end
        else begin bt_re <= fv && !wsrc; bt_word <= sbase + {1'b0, j} + ((MUT == 3) ? 9'd1 : 9'd0); end
    reg [511:0] fd1, fd2, fd3;
    reg         fv1, fv2, fv3, ws1, ws2, ws3, ls1, ls2, ls3;
    reg [7:0]   j1, j2, j3;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin fv1 <= 1'b0; fv2 <= 1'b0; fv3 <= 1'b0; end
        else begin fv1 <= fv; fv2 <= fv1; fv3 <= fv2; end
    always @(posedge ck) begin
        fd1 <= fd; fd2 <= fd1; fd3 <= fd2; ws1 <= wsrc; ws2 <= ws1; ws3 <= ws2; j1 <= j; j2 <= j1; j3 <= j2;
        ls1 <= (j + 8'd1 == nwords); ls2 <= ls1; ls3 <= ls2;
    end
    // fd3 / bt_q are aligned: bt_re is registered on the edge after fv (E1), the macro reads at E2, the capture flop at
    // E3: bt_q and fd3 are both valid in the cycle after E3
    wire [511:0] y;
    wire [15:0]  vs;
    wire [31:0]  es;
    generate for (l = 0; l < 16; l = l + 1) begin : g_sc
        ot_hdc_fp32_mul_lat #(.LAT(SCALE_LAT)) u_mul (.clk(ck), .rst_n(rst_n), .valid_in(fv3),
            .a(fd3[32*l +: 32]), .b({ws3 ? 16'h3F80 : bt_q[16*l +: 16], 16'd0}),
            .y(y[32*l +: 32]), .err(es[2*l +: 2]), .valid_out(vs[l]));
    end endgenerate
    wire [7:0] jo; wire lo;
    ot_hdc_delay #(.W(9), .D(SCALE_LAT)) u_jd (.clk(ck), .rst_n(rst_n), .d({ls3, j3}), .q({lo, jo}));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) r_v <= 1'b0;
        else r_v <= vs[0];
    always @(posedge ck) begin r_d <= y; r_idx <= jo; r_last <= lo; end
    // ---------------------------------------------------------------- faults (sticky): valid mismatch, a cluster /
    // neighbour fault bit, an FP error, a neighbour word with no held own word, more result words than configured
    wire in_bad = (fs[512] ^ ns[512]) | (fn[512] ^ nn[512]) | fs[513] | ns[513] | fn[513] | nn[513] | nb_i[513] |
                  (nbv && mode != 2'd2) | (mode != 2'd0 && (vlo ^ vhi)) | (vhi && mode == 2'd0 && hn == 4'd8 && !hpop) |
                  (v9_in && lead == 4'd0) | (fv && j >= nwords);
    wire fp_bad = (vlo && |elo) | (vhi && |ehi) | (v8 && |e8) | (v9 && |e9) | (vs[0] && |es);
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else fault <= fault | in_bad | fp_bad;
endmodule
