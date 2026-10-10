`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Qwen3-8B O4 ROM die tile element (W12; docs/MICROARCH_MODEL.md, Qwen section).
//
// ot_qwen_rom_tile_logic_w12 is everything of one tile that is not a memory macro;
// ot_qwen_rom_tile_w12 binds it to its macros and is the hardened, replicated
// element (1,536 per die at G = 6,144; 1,280 at 5,120).  The array (ot_qwen_me_array_w12) and the
// runtime composition use the logic module, so the verified logic is the
// hardened logic.
//
//   matrix lanes   TG = 4 groups x 16 lanes of ot_qwen_w12_matvec_part PART 1 (strap
//                  tile_id: global groups tile_id*4 ..+3), its issue loop run
//                  from the broadcast instruction, split-tree levels 1..2
//   upper node     one pair-adder word (ot_qwen_me_node_w12) of the split tree above
//                  the tiles; which (level, position) it serves is the die's
//                  wiring (31 nodes per 32-tile block of 128 groups)
//   code ROM       2 group-pair columns x CODE_BANKS depth-4,096 banks
//                  (ot_rom_4096x266_m8); bank b holds words 4096b..; the
//                  registered bank select ORs the enabled bank into the
//                  engine's MEM_PIPE capture in the same cycle (zero cycles,
//                  rtl/physical/ot_qwen_o4_g4_rommac.sv)
//   KV slice       (KV_LOCAL = 1) the current layer window's K and V words this
//                  tile's groups read, FP8 E4M3 codes, 2 x ot_sram_1r1w_128x256
//                  (groups 0-1, 2-3).  All four groups of a tile read the same
//                  local word in every cycle (tools/qwen_o4_kv_slice_map.py
//                  proves the map below one-to-one over the 8,192-position
//                  window and equal across a tile's groups):
//                    K word a (< VB):  t = (a mod 2^HB) >> 7,      local = (t div (GT >> SK)) * NH + (a >> HB)
//                    V word a (>= VB): p = ((a-VB) mod 2^HB) >> 3, local = KL + (p >> SV) * NH + ((a-VB) >> HB)
//                  and the codes expand exactly to the FP32 (BF16-exact) KV
//                  values the engine multiplies.  KV_LOCAL = 0 passes the
//                  global addresses and FP32 words through (simulation hosts).
//   input stages   IREG = 1 registers the instruction broadcast and x line at
//                  the tile boundary (one of the array's BD stages); NREG = 1
//                  registers the node inputs (one of NWS).
// ---------------------------------------------------------------------------
module ot_qwen_rom_tile_logic_w12 #(
    parameter integer W  = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 18,
    parameter integer GT = 6144,
    parameter integer TG = 4,
    parameter integer SMIN = 6,
    parameter integer CODE_BANKS = 10,
    parameter integer IREG = 1,
    // MEM_EXTRA = 1: every memory operand is captured at its source before use -- each ROM bank's
    // output at the macro pins (SS clk->q 739 ps leaves no room for the bank OR at 0.833 ns), the KV
    // slice word and the x line -- one cycle the engine's tags wait (ot_qwen_w12_matvec_part MEM_EXTRA)
    parameter integer MEM_EXTRA = 0,
    // ROM_PIPE = 1 (needs MEM_EXTRA = 1; default 0 = byte-identical original): the 1.2 GHz macro read pipeline
    // (qwen-blocks 2026-10-07).  ROM clk->q is 739-834 ps SS, so the single-cycle ROM->capture path closes only with
    // the ROM clock pin landed EARLY by CTS (useful skew from the CTS-only view ot_rom_4096x266_m8_skew250); that costs
    // the request path the same, so
    //   ROM_ARELAY register stages of the request (ce decode + address; one kept copy per bank group: banks
    //     [0, SB) south, [SB, CODE_BANKS) north) feed the macros from beside them,
    //   the capture register sits at the macro pins with no enable (the macro holds its output when not read),
    //   + 1 stage: INT8 -> BF16 expansion and the group OR (masked by the held bank select) at the group,
    //   + 1 stage: a relay register, then the two-group OR into the engine's mq capture.
    // The KV slice request and its write port take the same ROM_ARELAY stages (read/write order unchanged) and its
    // captured word 2 more; x waits the same.  The engine sees MEM_EXTRA + ROM_ARELAY + 2 memory cycles.
    parameter integer ROM_PIPE = 0,
    parameter integer ROM_ARELAY = 1,
    parameter integer ROM_MUT = 0,        // bench negative control: 1 = the capture register's bank select one edge early
    // ROM_CAP2 = 1 (safe-qwen S-A1, 2026-10-08; needs ROM_PIPE; 0 = unchanged): one more register stage between the pin
    // capture (cap, placed at the macro pins by rom_cap_at_pins.tcl) and the INT8 -> BF16 expansion / group OR (cap2,
    // with its bank select sel_c2), so the cap -> BF16 / group-OR -> gs stage (the predicted next limiter) is a
    // register-to-register hop.  +1 memory cycle per matvec fill (RX = ROM_ARELAY + 2 + ROM_CAP2; KV and x follow RX).
    parameter integer ROM_CAP2 = 0,
    // ROM_CAPX = 1 (redesign-qwen 2026-10-09; needs ROM_CAP2 = 1; 0 = unchanged): cap2 registers the bank-select-masked
    // INT8 -> BF16 expansion of cap instead of a copy of cap, so cap -> cap2 carries the expansion logic (no zero-logic
    // flop-to-flop hop beside the macro cluster: the rp1pc CTS hold stall sat on cap -> cap2) and cap2 -> gs is only the
    // 5:1 group OR.  Same edge, same word, same latency as ROM_CAP2 = 1 (cap2 is 2x wider: BF16).
    parameter integer ROM_CAPX = 0,
    // BAW: bank address width (12: ot_rom_4096x266_m8 banks; 11: ot_rom_2048x266_m8 half-depth banks, SS clk->q
    // 604 ps, twice CODE_BANKS for the same words -- the single-cycle capture then closes with a balanced clock)
    parameter integer BAW = 12,
    // LRST = 1: lane / tree-level reset copies inside the engine (ot_qwen_w12_matvec_part LRST)
    parameter integer LRST = 0,
    parameter integer NREG = 1,
    parameter integer KV_LOCAL = 1,
    parameter integer KV_AW = 7,          // local KV words: 2^KV_AW
    parameter integer KV_VB = 262144,     // first V word (4 heads x 65,536)
    parameter integer KV_HB = 16,         // words per head: 2^KV_HB
    parameter integer KV_NH = 4,          // KV heads per die
    parameter integer KV_SK = 7,          // scores split (log2)
    parameter integer KV_SV = 9,          // weighted-sum split (log2)
    parameter integer ACC_LAT = 5,        // lane accumulator FP32 add latency (ot_qwen_w12_matvec_part ACC_LAT)
    parameter integer FAST_ISSUE = 0,     // 1.2 GHz issue loop (ot_qwen_w12_matvec_part FAST_ISSUE)
    parameter integer KV_PREP = 0,        // KV-op offset pipeline cycles (ot_qwen_w12_matvec_part KV_PREP)
    parameter integer MUL_LAT = 5,        // lane BF16 product latency (ot_qwen_w12_matvec_part MUL_LAT)
    parameter integer TREE_LAT = 3        // split-tree pair adder latency (ot_qwen_w12_matvec_part TREE_LAT)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [15:0]       tile_id,
    // instruction broadcast (the i_* fields of ot_qwen_w12_matvec, packed as in ot_qwen_me_array_w12)
    input  wire              ib_go,
    input  wire [3*NW+13*AW+13-1:0] ib,
    // x line: this tile's TG chunk elements
    input  wire [TG*32-1:0]  xl,
    // split tree
    output wire [W*32-1:0]   t_out,
    output wire              t_vout,
    input  wire [W*32-1:0]   n_a,
    input  wire [W*32-1:0]   n_b,
    input  wire              n_va,
    output wire [W*32-1:0]   n_y,
    output wire              n_vy,
    output wire              fault,
    // code ROM macro pins
    output wire [CODE_BANKS-1:0] rom_ce,
    output wire [11:0]       rom_addr,
    output wire [11:0]       rom_addr_n,          // north banks' address (ROM_PIPE; else == rom_addr)
    input  wire [2*CODE_BANKS*266-1:0] rom_rd,
    // KV slice macro pins (KV_LOCAL = 1)
    output wire              kvs_r_ce,
    output wire [KV_AW-1:0]  kvs_r_addr,
    input  wire [TG*W*8-1:0] kvs_rd,
    // global KV port (KV_LOCAL = 0)
    output wire              kv_re,
    output wire [TG*AW-1:0]  kv_addr,
    input  wire [TG*W*32-1:0] kv_q
);
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    localparam integer RX = (ROM_PIPE != 0) ? (ROM_ARELAY + 2 + ROM_CAP2) : 0;   // extra memory cycles of the ROM pipeline
    localparam integer ME_EXTRA = MEM_EXTRA + RX;
    localparam integer SB = (CODE_BANKS + 1) / 2;                      // south group: banks [0, SB)
    generate if (ROM_PIPE != 0 && (MEM_EXTRA != 1 || ROM_ARELAY < 1)) begin : g_rp_bad
        initial $error("ROM_PIPE needs MEM_EXTRA = 1 and ROM_ARELAY >= 1");
    end endgenerate
    reg              go_q;
    reg  [IBW-1:0]   ib_q;
    reg  [TG*32-1:0] xl_q;
    wire             go_i  = IREG ? go_q : ib_go;
    wire [IBW-1:0]   ib_i  = IREG ? ib_q : ib;
    wire [TG*32-1:0] xl_r  = IREG ? xl_q : xl;
    wire [TG*32-1:0] xl_i;
    ot_hdc_delay #(.W(TG*32), .D(ME_EXTRA)) u_xm (.clk(clk), .rst_n(rst_n), .d(xl_r), .q(xl_i));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) go_q <= 1'b0;
        else go_q <= ib_go;
    end
    always @(posedge clk) begin ib_q <= ib; xl_q <= xl; end

    wire [NW-1:0] b_nout, b_tiles, b_k;
    wire          b_wsrc, b_round, b_mmode, b_oen, b_amax, b_rmax;
    wire [AW-1:0] b_wbase, b_ts, b_ks, b_js, b_xbase, b_xks, b_xjs, b_xcs, b_wcs, b_obase, b_ots, b_ojs, b_mbase;
    wire [2:0]    b_jsh;
    wire [3:0]    b_split;
    assign {b_nout, b_tiles, b_k, b_wsrc, b_wbase, b_ts, b_ks, b_js, b_xbase, b_xks, b_xjs, b_xcs,
            b_jsh, b_split, b_wcs, b_round, b_obase, b_ots, b_ojs, b_mmode, b_oen, b_amax, b_rmax, b_mbase} = ib_i;

    wire              wrom_re;
    wire [AW-1:0]     wrom_addr;
    wire [TG*W*((ROM_PIPE != 0) ? 16 : 8)-1:0] wrom_q;
    wire              me_kv_re;
    wire [TG*AW-1:0]  me_kv_addr;
    wire [TG*W*32-1:0] me_kv_q;
    wire              me_fault;
    ot_qwen_w12_matvec_part #(.W(W), .G(TG), .IL(IL), .AW(AW), .NW(NW), .INT8_WEIGHT(1), .INT8_SCALE_WCS_BASE(1),
        .PART(1), .GT(GT), .GBASE_PORT(1), .SMIN(SMIN), .NX(0), .MEM_EXTRA(ME_EXTRA), .WCONV(ROM_PIPE), .LRST(LRST),
        .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT)) u_me (
        .clk(clk), .rst_n(rst_n), .go(go_i), .ready(), .idle(),
        .i_nout(b_nout), .i_tiles(b_tiles), .i_k(b_k), .i_wsrc(b_wsrc),
        .i_wbase(b_wbase), .i_ts(b_ts), .i_ks(b_ks), .i_js(b_js),
        .i_xbase(b_xbase), .i_xks(b_xks), .i_xjs(b_xjs), .i_xcs(b_xcs),
        .i_jsh(b_jsh), .i_split(b_split), .i_wcs(b_wcs), .i_round(b_round),
        .i_obase(b_obase), .i_ots(b_ots), .i_ojs(b_ojs),
        .i_mmode(b_mmode), .i_oen(b_oen), .i_amax(b_amax), .i_rmax(b_rmax), .i_mbase(b_mbase),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .scale_re(), .scale_gre(), .scale_addr(), .scale_q({TG*W*16{1'b0}}),
        .kv_re(me_kv_re), .kv_addr(me_kv_addr), .kv_q(me_kv_q),
        .x_re(), .x_addr(), .x_q(xl_i),
        .ov(), .o_we(), .o_addr(), .o_mask(), .o_data(),
        .am_idx(), .am_val(), .am_any(), .mx_we(), .mx_addr(), .mx_mask(), .mx_data(),
        .progress(), .fault(me_fault),
        .i_gbase({16'd0, tile_id} * TG), .t_in({W*32{1'b0}}), .t_fault_in(1'b0),
        .t_out(t_out), .t_vout(t_vout), .t_fault(), .active_o());

    // -- upper tree node ---------------------------------------------------------
    wire node_fault;
    ot_qwen_me_node_w12 #(.W(W), .WS(NREG), .TREE_LAT(TREE_LAT)) u_node (.clk(clk), .rst_n(rst_n), .a(n_a), .b(n_b), .va(n_va),
                                               .y(n_y), .vy(n_vy), .fault(node_fault));
    assign fault = me_fault | node_fault;

    function automatic [15:0] int8_bf16(input [7:0] code);   // == ot_qwen_w12_matvec_part int8_bf16
        reg [7:0] mag, norm;
        reg [2:0] msb;
        integer bit_index;
        begin
            mag = code[7] ? (~code + 8'd1) : code;
            msb = 0;
            for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1)
                if (mag[bit_index]) msb = bit_index[2:0];
            norm = mag << (3'd7 - msb);
            int8_bf16 = (mag == 0) ? 16'd0 :
                        {code[7], (8'd127 + {5'd0, msb}), norm[6:0]};
        end
    endfunction
    // -- code ROM: bank select -----------------------------------------------------
    localparam integer PWB = 2 * W * 8;      // a group pair's slice of the code word (256 of the macro's 266 bits)
    genvar b, p;
    generate if (ROM_PIPE == 0) begin : g_rom_orig
    reg  [CODE_BANKS-1:0] code_sel_q;
        for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_ce
            assign rom_ce[b] = wrom_re && (wrom_addr[AW-1:BAW] == b);
        end
    assign rom_addr = {{(12-BAW){1'b0}}, wrom_addr[BAW-1:0]};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) code_sel_q <= {CODE_BANKS{1'b0}};
        else if (wrom_re) code_sel_q <= rom_ce;
    end
    //: MEM_EXTRA: the read strobe and bank select one more cycle, for the captured banks' OR
    reg code_rd_q;
    reg [CODE_BANKS-1:0] code_sel_q2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin code_rd_q <= 1'b0; code_sel_q2 <= {CODE_BANKS{1'b0}}; end
        else begin
            code_rd_q <= wrom_re;
            if (code_rd_q) code_sel_q2 <= code_sel_q;
        end
    end
        for (p = 0; p < TG / 2; p = p + 1) begin : g_pair
            wire [PWB-1:0] or_q [0:CODE_BANKS];
            assign or_q[0] = {PWB{1'b0}};
            for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_bank
                wire [PWB-1:0] rd = rom_rd[(p*CODE_BANKS + b)*266 +: PWB];
                if (MEM_EXTRA != 0) begin : g_cap
                    //: the bank's output register at its pins: captured only when the bank was read
                    reg [PWB-1:0] cap;
                    always @(posedge clk) if (code_sel_q[b] && code_rd_q) cap <= rd;
                    assign or_q[b+1] = or_q[b] | (cap & {PWB{code_sel_q2[b]}});
                end else begin : g_nocap
                    assign or_q[b+1] = or_q[b] | (rd & {PWB{code_sel_q[b]}});
                end
            end
            assign wrom_q[PWB*p +: PWB] = or_q[CODE_BANKS];
        end

        assign rom_addr_n = rom_addr;
    end else begin : g_rom_pipe
        //: request relay: ROM_ARELAY stages, one kept copy per bank group, decoded at the first stage
        wire [CODE_BANKS-1:0] ce0 = {CODE_BANKS{wrom_re}} & (({{(CODE_BANKS-1){1'b0}}, 1'b1}) << wrom_addr[AW-1:BAW]);
        (* keep *) reg [CODE_BANKS-1:0] rq_ce_s [1:ROM_ARELAY];
        (* keep *) reg [CODE_BANKS-1:0] rq_ce_n [1:ROM_ARELAY];
        (* keep *) reg [11:0]           rq_ad_s [1:ROM_ARELAY];
        (* keep *) reg [11:0]           rq_ad_n [1:ROM_ARELAY];
        genvar a;
        for (a = 1; a <= ROM_ARELAY; a = a + 1) begin : g_arl
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin rq_ce_s[a] <= {CODE_BANKS{1'b0}}; rq_ce_n[a] <= {CODE_BANKS{1'b0}}; end
                else begin
                    rq_ce_s[a] <= (a == 1) ? ce0 : rq_ce_s[a-1];
                    rq_ce_n[a] <= (a == 1) ? ce0 : rq_ce_n[a-1];
                end
            end
            always @(posedge clk) begin
                rq_ad_s[a] <= (a == 1) ? {{(12-BAW){1'b0}}, wrom_addr[BAW-1:0]} : rq_ad_s[a-1];
                rq_ad_n[a] <= (a == 1) ? {{(12-BAW){1'b0}}, wrom_addr[BAW-1:0]} : rq_ad_n[a-1];
            end
        end
        for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_ce
            assign rom_ce[b] = (b < SB) ? rq_ce_s[ROM_ARELAY][b] : rq_ce_n[ROM_ARELAY][b];
        end
        //: two address ports to the wrapper's macros: rom_addr (south banks) and rom_addr_n (north banks)
        assign rom_addr = rq_ad_s[ROM_ARELAY];
        assign rom_addr_n = rq_ad_n[ROM_ARELAY];
        //: bank select of the word in the capture registers (held when no read: the macros hold their output)
        reg [CODE_BANKS-1:0] sel_1, sel_c, sel_c2;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin sel_1 <= {CODE_BANKS{1'b0}}; sel_c <= {CODE_BANKS{1'b0}}; sel_c2 <= {CODE_BANKS{1'b0}}; end
            else begin
                if (|rom_ce) sel_1 <= rom_ce;          // the edge the macro samples
                sel_c <= sel_1;                        // the edge its word lands in the capture register
                sel_c2 <= sel_c;                       // ROM_CAP2: the edge it lands in cap2
            end
        end
        for (p = 0; p < TG / 2; p = p + 1) begin : g_pair
            wire [2*PWB-1:0] cv [0:CODE_BANKS-1];
            wire [2*PWB-1:0] os [0:CODE_BANKS];
            wire [2*PWB-1:0] on [0:CODE_BANKS];
            assign os[0] = {2*PWB{1'b0}};
            assign on[0] = {2*PWB{1'b0}};
            for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_bank
                //: the bank's output register at its pins, no enable
                (* keep *) reg [PWB-1:0] cap;
                always @(posedge clk) cap <= rom_rd[(p*CODE_BANKS + b)*266 +: PWB];
                wire [PWB-1:0] cx;                     // the word the expansion reads
                wire           sx, sx_early;           // its bank select (and the mutant's one-edge-early select)
                wire [2*PWB-1:0] cxw;                  // ROM_CAPX: the registered masked expansion
                if (ROM_CAP2 != 0 && ROM_CAPX != 0) begin : g_capx
                    //: cap2 = the masked BF16 expansion of cap (select of the edge cap holds the word: sel_c)
                    (* keep *) reg [2*PWB-1:0] cap2x;
                    genvar ex;
                    for (ex = 0; ex < PWB / 8; ex = ex + 1) begin : g_cvx
                        always @(posedge clk) cap2x[16*ex +: 16] <= int8_bf16(cap[8*ex +: 8]) & {16{(ROM_MUT != 0) ? sel_1[b] : sel_c[b]}};
                    end
                    assign cx = {PWB{1'b0}}; assign sx = 1'b0; assign sx_early = 1'b0; assign cxw = cap2x;
                end else if (ROM_CAP2 != 0) begin : g_cap2
                    (* keep *) reg [PWB-1:0] cap2;
                    always @(posedge clk) cap2 <= cap;
                    assign cx = cap2; assign sx = sel_c2[b]; assign sx_early = sel_c[b]; assign cxw = {2*PWB{1'b0}};
                end else begin : g_cap1
                    assign cx = cap; assign sx = sel_c[b]; assign sx_early = sel_1[b]; assign cxw = {2*PWB{1'b0}};
                end
                if (ROM_CAP2 != 0 && ROM_CAPX != 0) begin : g_cvr
                    assign cv[b] = cxw;
                end else begin : g_cvc
                    genvar e;
                    for (e = 0; e < PWB / 8; e = e + 1) begin : g_cv
                        assign cv[b][16*e +: 16] = int8_bf16(cx[8*e +: 8]) & {16{(ROM_MUT != 0) ? sx_early : sx}};
                    end
                end
                assign os[b+1] = (b < SB) ? (os[b] | cv[b]) : os[b];
                assign on[b+1] = (b < SB) ? on[b] : (on[b] | cv[b]);
            end
            //: group registers (south: banks [0, SB), north: the rest), then a relay register each
            reg [2*PWB-1:0] gs, gn, rs, rn;
            always @(posedge clk) begin gs <= os[CODE_BANKS]; gn <= on[CODE_BANKS]; rs <= gs; rn <= gn; end
            assign wrom_q[2*PWB*p +: 2*PWB] = rs | rn;
        end
    end endgenerate

    // -- KV slice --------------------------------------------------------------------
    function automatic [31:0] e4m3_f32(input [7:0] c);
        reg [3:0] e; reg [2:0] m; reg [7:0] fe; reg [22:0] fm;
        begin
            e = c[6:3]; m = c[2:0];
            if (e != 0) begin fe = {4'd0, e} + 8'd120; fm = {m, 20'd0}; end
            else if (m[2]) begin fe = 8'd120; fm = {m[1:0], 21'd0}; end      // 0.1xx * 2^-6 = 1.xx * 2^-7
            else if (m[1]) begin fe = 8'd119; fm = {m[0], 22'd0}; end       // 1.x * 2^-8
            else if (m[0]) begin fe = 8'd118; fm = 23'd0; end               // 2^-9
            else begin fe = 8'd0; fm = 23'd0; end
            e4m3_f32 = {c[7], fe, fm};
        end
    endfunction
    generate if (KV_LOCAL != 0) begin : g_kv_local
        localparam [KV_AW-1:0] PRK = GT >> KV_SK;
        //: K words a group holds: ceil(KV_PT position tiles / (GT >> SK)) rounds x NH heads (44 at G = 6,144, 8K)
        //: 2^(KV_HB-7) position tiles a head (512 at the 8K window); a literal 512 overlaps V onto K above 8K
        localparam integer KV_PT = 1 << (KV_HB - 7);
        localparam integer KV_KL = ((KV_PT + (GT >> KV_SK) - 1) / (GT >> KV_SK)) * KV_NH;
        wire [AW-1:0] a = me_kv_addr[AW-1:0];            // every group of the tile maps to the same word
        wire          is_v = (a >= KV_VB);
        wire [AW-1:0] w = a - KV_VB;
        wire [KV_HB-8:0] tk = a[KV_HB-1:7];
        wire [KV_HB-4:0] pv = w[KV_HB-1:3];
        wire [KV_AW-1:0] lk = (tk / PRK) * KV_NH + a[KV_HB+1:KV_HB];
        wire [KV_AW-1:0] lv = KV_KL + (pv >> KV_SV) * KV_NH + w[KV_HB+1:KV_HB];
        //: MEM_EXTRA: the slice word's capture register (held when not read)
        wire [TG*W*8-1:0] kvs_rd_m;
        wire          kv_ce_r;
        wire [KV_AW-1:0] kv_ad_r;
        if (ROM_PIPE != 0) begin : g_kvrl
            //: ROM_PIPE: the slice request takes the ROM request's relay stages (the write port the same, in the
            //: wrapper), its captured word 2 more stages
            ot_hdc_vline #(.D(ROM_ARELAY + 1)) u_kvce (.clk(clk), .rst_n(rst_n), .v(me_kv_re), .vd(kvce_l));
            wire [ROM_ARELAY+1:0] kvce_l;
            ot_hdc_delay #(.W(KV_AW), .D(ROM_ARELAY)) u_kvad (.clk(clk), .rst_n(rst_n), .d(is_v ? lv : lk), .q(kv_ad_r));
            assign kv_ce_r = kvce_l[ROM_ARELAY];
        end else begin : g_kvnorl
            assign kv_ce_r = me_kv_re;
            assign kv_ad_r = is_v ? lv : lk;
        end
        if (MEM_EXTRA != 0) begin : g_kvcap
            reg kv_rd_q;
            reg [TG*W*8-1:0] cap;
            always @(posedge clk or negedge rst_n) if (!rst_n) kv_rd_q <= 1'b0; else kv_rd_q <= kv_ce_r;
            always @(posedge clk) if (kv_rd_q) cap <= kvs_rd;
            ot_hdc_delay #(.W(TG*W*8), .D(RX - ((ROM_PIPE != 0) ? ROM_ARELAY : 0))) u_kvd (.clk(clk), .rst_n(rst_n),
                .d(cap), .q(kvs_rd_m));
        end else begin : g_kvnocap
            assign kvs_rd_m = kvs_rd;
        end
        assign kvs_r_ce = kv_ce_r;
        assign kvs_r_addr = kv_ad_r;
        genvar e;
        for (e = 0; e < TG * W; e = e + 1) begin : g_x
            assign me_kv_q[32*e +: 32] = e4m3_f32(kvs_rd_m[8*e +: 8]);
        end
        assign kv_re = 1'b0;
        assign kv_addr = {TG*AW{1'b0}};
    end else begin : g_kv_global
        assign kvs_r_ce = 1'b0;
        assign kvs_r_addr = {KV_AW{1'b0}};
        localparam integer KA = (ROM_PIPE != 0) ? ROM_ARELAY : 0;
        wire [KA+1:0] kvg_l;
        ot_hdc_vline #(.D(KA + 1)) u_kvgce (.clk(clk), .rst_n(rst_n), .v(me_kv_re), .vd(kvg_l));
        if (KA != 0) begin : g_kvgrl
            ot_hdc_delay #(.W(TG*AW), .D(KA)) u_kvgad (.clk(clk), .rst_n(rst_n), .d(me_kv_addr), .q(kv_addr));
            assign kv_re = kvg_l[KA];
        end else begin : g_kvgnorl
            assign kv_re = me_kv_re;
            assign kv_addr = me_kv_addr;
        end
        //: host-served global KV (simulation): the same capture stage as the slice
        if (MEM_EXTRA != 0) begin : g_kvgcap
            reg kv_rd_q;
            reg [TG*W*32-1:0] cap;
            always @(posedge clk or negedge rst_n) if (!rst_n) kv_rd_q <= 1'b0; else kv_rd_q <= kv_re;
            always @(posedge clk) if (kv_rd_q) cap <= kv_q;
            ot_hdc_delay #(.W(TG*W*32), .D(RX - KA)) u_kvgd (.clk(clk), .rst_n(rst_n), .d(cap), .q(me_kv_q));
        end else begin : g_kvgnocap
            assign me_kv_q = kv_q;
        end
    end endgenerate
endmodule

// The hardened element: the logic bound to its 2 x CODE_BANKS code ROM macros
// and its KV slice (2 x ot_sram_1r1w_128x256_m1_r2c2, written through a
// registered masked port from the die's KV fill network).
module ot_qwen_rom_tile_w12 #(
    parameter integer NW = 18,
    parameter integer GT = 6144,
    parameter integer SMIN = 6,
    parameter integer CODE_BANKS = 10,
    parameter integer KV_VB = 262144,
    parameter integer KV_NH = 4,
    parameter integer MEM_EXTRA = 0,
    parameter integer ACC_LAT = 5,        // lane accumulator FP32 add latency (ot_qwen_w12_matvec_part ACC_LAT)
    parameter integer FAST_ISSUE = 0,     // 1.2 GHz issue loop (ot_qwen_w12_matvec_part FAST_ISSUE)
    parameter integer KV_PREP = 0,        // KV-op offset pipeline cycles (ot_qwen_w12_matvec_part KV_PREP)
    parameter integer MUL_LAT = 5,        // lane BF16 product latency (ot_qwen_w12_matvec_part MUL_LAT)
    parameter integer TREE_LAT = 3,       // split-tree pair adder latency (ot_qwen_w12_matvec_part TREE_LAT)
    parameter integer ROM_PIPE = 0,       // ot_qwen_rom_tile_logic_w12 ROM_PIPE (the KV write port takes ROM_ARELAY more stages)
    parameter integer ROM_ARELAY = 1,
    parameter integer ROM_CAP2 = 0,       // ot_qwen_rom_tile_logic_w12 ROM_CAP2 (safe-qwen S-A1)
    parameter integer ROM_CAPX = 0,       // ot_qwen_rom_tile_logic_w12 ROM_CAPX (redesign-qwen)
    parameter integer LRST = 0,
    parameter integer BAW = 12            // 11: ot_rom_2048x266_m8 banks (set CODE_BANKS to twice the 4096-word count)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [15:0]       tile_id,
    input  wire              ib_go,
    input  wire [3*NW+13*24+13-1:0] ib,
    input  wire [4*32-1:0]   xl,
    output wire [16*32-1:0]  t_out,
    output wire              t_vout,
    input  wire [16*32-1:0]  n_a,
    input  wire [16*32-1:0]  n_b,
    input  wire              n_va,
    output wire [16*32-1:0]  n_y,
    output wire              n_vy,
    output wire              fault,
    // KV slice fill (local word, E4M3 codes, per-code mask)
    input  wire              kvw_ce,
    input  wire [6:0]        kvw_addr,
    input  wire [511:0]      kvw_data,
    input  wire [511:0]      kvw_mask
);
    wire [CODE_BANKS-1:0] rom_ce;
    wire [11:0]           rom_addr, rom_addr_n;
    wire [2*CODE_BANKS*266-1:0] rom_rd;
    wire                  kvs_r_ce;
    wire [6:0]            kvs_r_addr;
    wire [511:0]          kvs_rd;
    ot_qwen_rom_tile_logic_w12 #(.NW(NW), .GT(GT), .SMIN(SMIN), .CODE_BANKS(CODE_BANKS), .KV_LOCAL(1),
        .KV_VB(KV_VB), .KV_NH(KV_NH), .MEM_EXTRA(MEM_EXTRA), .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT), .ROM_PIPE(ROM_PIPE), .ROM_ARELAY(ROM_ARELAY), .ROM_CAP2(ROM_CAP2), .ROM_CAPX(ROM_CAPX), .LRST(LRST), .BAW(BAW)) u_logic (
        .clk(clk), .rst_n(rst_n), .tile_id(tile_id), .ib_go(ib_go), .ib(ib), .xl(xl),
        .t_out(t_out), .t_vout(t_vout), .n_a(n_a), .n_b(n_b), .n_va(n_va), .n_y(n_y), .n_vy(n_vy), .fault(fault),
        .rom_ce(rom_ce), .rom_addr(rom_addr), .rom_addr_n(rom_addr_n), .rom_rd(rom_rd),
        .kvs_r_ce(kvs_r_ce), .kvs_r_addr(kvs_r_addr), .kvs_rd(kvs_rd),
        .kv_re(), .kv_addr(), .kv_q({4*16*32{1'b0}}));
    genvar p, b;
    generate
        //: BAW 12 keeps the original macro path g_col[p].g_bank[b].u_rom (floorplan scripts, die views, runtime
        //: array binding); BAW 11 half-depth banks live under g_colh (zero-trip loops, no extra scope level)
        for (p = 0; p < ((BAW == 12) ? 2 : 0); p = p + 1) begin : g_col
            for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_bank
                ot_rom_4096x266_m8 u_rom (.clk(clk), .ce_in(rom_ce[b]),
                    .addr_in((ROM_PIPE != 0 && b >= (CODE_BANKS + 1) / 2) ? rom_addr_n : rom_addr),
                    .rd_out(rom_rd[(p*CODE_BANKS + b)*266 +: 266]));
            end
        end
        for (p = 0; p < ((BAW == 11) ? 2 : 0); p = p + 1) begin : g_colh
            for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_bank
                wire [11:0] ra = (ROM_PIPE != 0 && b >= (CODE_BANKS + 1) / 2) ? rom_addr_n : rom_addr;
                ot_rom_2048x266_m8 u_rom (.clk(clk), .ce_in(rom_ce[b]), .addr_in(ra[10:0]),
                    .rd_out(rom_rd[(p*CODE_BANKS + b)*266 +: 266]));
            end
        end
    endgenerate
    reg        kvw_ce_q;
    reg [6:0]  kvw_addr_q;
    reg [511:0] kvw_data_q, kvw_mask_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) kvw_ce_q <= 1'b0;
        else kvw_ce_q <= kvw_ce;
    end
    always @(posedge clk) begin kvw_addr_q <= kvw_addr; kvw_data_q <= kvw_data; kvw_mask_q <= kvw_mask; end
    //: ROM_PIPE: the write port takes the read request's ROM_ARELAY relay stages, so the slice sees reads and writes
    //: in the original order
    localparam integer KWD = (ROM_PIPE != 0) ? ROM_ARELAY : 0;
    wire        kvw_ce_r;
    generate if (KWD != 0) begin : g_kwv
        wire [KWD+1:0] kvw_l;
        ot_hdc_vline #(.D(KWD + 1)) u_kwv (.clk(clk), .rst_n(rst_n), .v(kvw_ce_q), .vd(kvw_l));
        assign kvw_ce_r = kvw_l[KWD];
    end else begin : g_kwn
        assign kvw_ce_r = kvw_ce_q;
    end endgenerate
    wire [6:0]  kvw_addr_r;
    wire [511:0] kvw_data_r, kvw_mask_r;
    ot_hdc_delay #(.W(7 + 1024), .D(KWD)) u_kwd (.clk(clk), .rst_n(rst_n), .d({kvw_addr_q, kvw_data_q, kvw_mask_q}),
        .q({kvw_addr_r, kvw_data_r, kvw_mask_r}));
    generate
        for (p = 0; p < 2; p = p + 1) begin : g_kv
            ot_sram_1r1w_128x256_m1_r2c2 u_kv (
                .clk(clk), .r_ce_in(kvs_r_ce), .r_addr_in(kvs_r_addr), .rd_out(kvs_rd[256*p +: 256]),
                .w_ce_in(kvw_ce_r), .w_addr_in(kvw_addr_r), .wd_in(kvw_data_r[256*p +: 256]),
                .w_mask_in(kvw_mask_r[256*p +: 256]),
                .rr_en(2'b0), .rr_addr(14'd0), .cr_en(2'b0), .cr_sel(16'd0));
        end
    endgenerate
endmodule
