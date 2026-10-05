`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Qwen3-8B O4 ROM die tile element (W12; docs/MICROARCH_MODEL.md, Qwen section).
//
// ot_qwen_rom_tile_logic_context_candidate_r3_retained is everything of one tile that is not a memory macro;
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
module ot_qwen_rom_tile_logic_context_candidate_r3_retained #(
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
    parameter integer ROM_REPLICA_CELL_RETENTION = 0, // explicit85FF, defaultoff; map awaits Ampere context
    parameter integer ROM_CONTROL_DISTRIBUTION = 0, // cdcbe60a exact76BUF
    parameter integer ROM_BANK5_CONTROL = 0, // Maxwell cdcbe60a; same-edge, defaultoff
    parameter integer ROM_HOLD_DIRECT_CAPTURE = 0, // Maxwell645ae1dd7; opt-in, no added edges
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
    output wire [119:0]      rom_distributed_addr,
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
    reg              go_q;
    reg  [IBW-1:0]   ib_q;
    reg  [TG*32-1:0] xl_q;
    wire             go_i  = IREG ? go_q : ib_go;
    wire [IBW-1:0]   ib_i  = IREG ? ib_q : ib;
    wire [TG*32-1:0] xl_r  = IREG ? xl_q : xl;
    wire [TG*32-1:0] xl_i;
    ot_hdc_delay #(.W(TG*32), .D(MEM_EXTRA)) u_xm (.clk(clk), .rst_n(rst_n), .d(xl_r), .q(xl_i));
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
    wire [TG*W*8-1:0] wrom_q;
    wire              me_kv_re;
    wire [TG*AW-1:0]  me_kv_addr;
    wire [TG*W*32-1:0] me_kv_q;
    wire              me_fault;
    ot_qwen_w12_matvec_part #(.W(W), .G(TG), .IL(IL), .AW(AW), .NW(NW), .INT8_WEIGHT(1), .INT8_SCALE_WCS_BASE(1),
        .PART(1), .GT(GT), .GBASE_PORT(1), .SMIN(SMIN), .NX(0), .MEM_EXTRA(MEM_EXTRA),
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

    generate if (ROM_REPLICA_CELL_RETENTION != 0 &&
        (ROM_CONTROL_DISTRIBUTION == 0 || ROM_BANK5_CONTROL == 0 ||
         ROM_HOLD_DIRECT_CAPTURE == 0 || CODE_BANKS != 5 || TG != 4 || W != 16 || MEM_EXTRA != 1)) begin : g_unpriced_retention
        initial $error("explicit retention requires selected bank5 complete context; mapping awaits finite G0");
    end endgenerate
    // -- code ROM: bank select -----------------------------------------------------
    wire [CODE_BANKS-1:0] code_rd_bank; // Explicit before primitive-port expression.
    reg  [CODE_BANKS-1:0] code_sel_q;
    genvar b, p;
    generate
        for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_ce
            assign rom_ce[b] = wrom_re && (wrom_addr[AW-1:12] == b);
        end
    endgenerate
    assign rom_addr = wrom_addr[11:0];
    wire [84:0] distributed_strobe_n;
    wire [79:0] distributed_hold_term;
    wire [89:0] distributed_metadata_reset_n;
    wire [4:0] bank_hold_term;
    generate if (ROM_CONTROL_DISTRIBUTION != 0) begin : g_distribution
        genvar db;
        for (db=0; db<5; db=db+1) begin : g_term
            assign bank_hold_term[db] = code_sel_q[db] & ~distributed_strobe_n[17*db];
        end
        ot_qwen_rom_bank5_control_distribution u_tree (
            .bank_read_n(~code_rd_bank), .bank_hold_term(bank_hold_term),
            .low_address(rom_addr), .reset_n(rst_n),
            .strobe_sink_n(distributed_strobe_n), .hold_term_sink(distributed_hold_term),
            .macro_address(rom_distributed_addr), .metadata_reset_n(distributed_metadata_reset_n));
        for (db=0;db<5;db=db+1) begin : g_early_select
            always @(posedge clk or negedge distributed_metadata_reset_n[db])
                if (!distributed_metadata_reset_n[db]) code_sel_q[db] <= 1'b0;
                else if (wrom_re) code_sel_q[db] <= rom_ce[db];
        end
    end else begin : g_undistributed
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) code_sel_q <= {CODE_BANKS{1'b0}};
            else if (wrom_re) code_sel_q <= rom_ce;
        end
        assign rom_distributed_addr = {10{rom_addr}};
        assign distributed_strobe_n = 85'b0;
        assign distributed_hold_term = 80'b0;
        assign distributed_metadata_reset_n = {90{rst_n}};
        assign bank_hold_term = 5'b0;
    end endgenerate
    //: MEM_EXTRA: the read strobe and bank select one more cycle, for the captured banks' OR
    wire code_rd_q;
    reg [CODE_BANKS-1:0] code_sel_q2;
    generate if (ROM_CONTROL_DISTRIBUTION != 0 &&
        (ROM_BANK5_CONTROL == 0 || ROM_HOLD_DIRECT_CAPTURE == 0 || W != 16 || TG != 4 || CODE_BANKS != 5 || MEM_EXTRA != 1)) begin : g_unpriced_distribution
        initial $error("ROM_CONTROL_DISTRIBUTION requires priced bank5/direct W16/TG4/CB5/MEM_EXTRA1");
    end endgenerate
    generate if (ROM_BANK5_CONTROL != 0) begin : g_bank_control
        genvar rb;
        for (rb = 0; rb < CODE_BANKS; rb = rb + 1) begin : g_bank
            wire read_q;
            wire bank_reset_n = (ROM_CONTROL_DISTRIBUTION != 0) ? distributed_metadata_reset_n[5+rb] : rst_n;
            if (ROM_REPLICA_CELL_RETENTION != 0) begin : g_retained
                wire read_q_n;
                // Actual RVT Liberty: QN next_state=!D, RESETN presets QN=1.
                (* keep = 1, dont_touch = 1 *) DFFASRHQNx1_ASAP7_75t_R u_read_ff
                    (.CLK(clk), .D(wrom_re), .RESETN(bank_reset_n), .SETN(1'b1), .QN(read_q_n));
                assign read_q = ~read_q_n;
            end else begin : g_inferred
                reg read_state_q;
                always @(posedge clk or negedge bank_reset_n)
                    if (!bank_reset_n) read_state_q <= 1'b0;
                    else read_state_q <= wrom_re;
                assign read_q = read_state_q;
            end
            assign code_rd_bank[rb] = read_q;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) code_sel_q2[rb] <= 1'b0;
                else if (read_q) code_sel_q2[rb] <= code_sel_q[rb];
        end
        assign code_rd_q = code_rd_bank[0];
    end else begin : g_shared_control
        reg read_q;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin read_q <= 1'b0; code_sel_q2 <= {CODE_BANKS{1'b0}}; end
            else begin
                read_q <= wrom_re;
                if (read_q) code_sel_q2 <= code_sel_q;
            end
        end
        assign code_rd_q = read_q;
        assign code_rd_bank = {CODE_BANKS{read_q}};
    end endgenerate
    generate if (ROM_BANK5_CONTROL != 0 &&
        (ROM_HOLD_DIRECT_CAPTURE == 0 || W != 16 || TG != 4 || CODE_BANKS != 5 || MEM_EXTRA != 1)) begin : g_unpriced_bank5
        initial $error("ROM_BANK5_CONTROL requires priced directcapture W16/TG4/CB5/MEM_EXTRA1");
    end endgenerate
    generate if (ROM_HOLD_DIRECT_CAPTURE != 0 &&
        (W != 16 || TG != 4 || CODE_BANKS != 5 || MEM_EXTRA != 1)) begin : g_unpriced_shape
        initial $error("ROM_HOLD_DIRECT_CAPTURE requires Maxwell-priced W16/TG4/CB5/MEM_EXTRA1");
    end endgenerate
    localparam integer PWB = 2 * W * 8;      // a group pair's slice of the code word (256 of the macro's 266 bits)
    generate
        for (p = 0; p < TG / 2; p = p + 1) begin : g_pair
            wire [PWB-1:0] or_q [0:CODE_BANKS];
            assign or_q[0] = {PWB{1'b0}};
            for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_bank
                wire [PWB-1:0] rd = rom_rd[(p*CODE_BANKS + b)*266 +: PWB];
                if (MEM_EXTRA != 0) begin : g_cap
                    if (ROM_HOLD_DIRECT_CAPTURE != 0) begin : g_direct
                        // CE-idle holds rd in the source ROM. Observability is
                        // still qualified by identical delayed bank metadata.
                        reg [PWB-1:0] cap;
                        always @(posedge clk) cap <= rd;
                        genvar chunk;
                        for (chunk = 0; chunk < PWB / 32; chunk = chunk + 1) begin : g_mask
                            // Eight32-bit chunks per column,16 per bank:
                            // exactly80 reset/hold selectorFFs. Keep replicas
                            // for physical locality; mapped preservation gates.
                            wire local_sel;
                            wire mask_reset_n = (ROM_CONTROL_DISTRIBUTION != 0) ?
                                distributed_metadata_reset_n[10+16*b+8*p+chunk] : rst_n;
                            if (ROM_REPLICA_CELL_RETENTION != 0) begin : g_retained
                                wire local_sel_n;
                                reg local_next;
                                always @* begin
                                    local_next = local_sel;
                                    if (ROM_CONTROL_DISTRIBUTION != 0) begin
                                        if (!distributed_strobe_n[17*b+1+8*p+chunk])
                                            local_next = distributed_hold_term[16*b+8*p+chunk];
                                    end else if (code_rd_bank[b]) local_next = code_sel_q[b];
                                end
                                (* keep = 1, dont_touch = 1 *) DFFASRHQNx1_ASAP7_75t_R u_mask_ff
                                    (.CLK(clk), .D(local_next), .RESETN(mask_reset_n), .SETN(1'b1), .QN(local_sel_n));
                                assign local_sel = ~local_sel_n;
                            end else begin : g_inferred
                                reg local_state_q;
                                always @(posedge clk or negedge mask_reset_n) begin
                                    if (!mask_reset_n) local_state_q <= 1'b0;
                                    else if (ROM_CONTROL_DISTRIBUTION != 0) begin
                                        if (!distributed_strobe_n[17*b+1+8*p+chunk])
                                            local_state_q <= distributed_hold_term[16*b+8*p+chunk];
                                    end else if (code_rd_bank[b]) local_state_q <= code_sel_q[b];
                                end
                                assign local_sel = local_state_q;
                            end
                            assign or_q[b+1][32*chunk +: 32] = or_q[b][32*chunk +: 32] |
                                (cap[32*chunk +: 32] & {32{local_sel}});
                        end
                    end else begin : g_original
                        // Original source behavior, defaultoff.
                        reg [PWB-1:0] cap;
                        always @(posedge clk) if (code_sel_q[b] && code_rd_q) cap <= rd;
                        assign or_q[b+1] = or_q[b] | (cap & {PWB{code_sel_q2[b]}});
                    end
                end else begin : g_nocap
                    assign or_q[b+1] = or_q[b] | (rd & {PWB{code_sel_q[b]}});
                end
            end
            assign wrom_q[PWB*p +: PWB] = or_q[CODE_BANKS];
        end
    endgenerate

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
        if (MEM_EXTRA != 0) begin : g_kvcap
            reg kv_rd_q;
            reg [TG*W*8-1:0] cap;
            always @(posedge clk or negedge rst_n) if (!rst_n) kv_rd_q <= 1'b0; else kv_rd_q <= me_kv_re;
            always @(posedge clk) if (kv_rd_q) cap <= kvs_rd;
            assign kvs_rd_m = cap;
        end else begin : g_kvnocap
            assign kvs_rd_m = kvs_rd;
        end
        assign kvs_r_ce = me_kv_re;
        assign kvs_r_addr = is_v ? lv : lk;
        genvar e;
        for (e = 0; e < TG * W; e = e + 1) begin : g_x
            assign me_kv_q[32*e +: 32] = e4m3_f32(kvs_rd_m[8*e +: 8]);
        end
        assign kv_re = 1'b0;
        assign kv_addr = {TG*AW{1'b0}};
    end else begin : g_kv_global
        assign kvs_r_ce = 1'b0;
        assign kvs_r_addr = {KV_AW{1'b0}};
        assign kv_re = me_kv_re;
        assign kv_addr = me_kv_addr;
        //: host-served global KV (simulation): the same capture stage as the slice
        if (MEM_EXTRA != 0) begin : g_kvgcap
            reg kv_rd_q;
            reg [TG*W*32-1:0] cap;
            always @(posedge clk or negedge rst_n) if (!rst_n) kv_rd_q <= 1'b0; else kv_rd_q <= me_kv_re;
            always @(posedge clk) if (kv_rd_q) cap <= kv_q;
            assign me_kv_q = cap;
        end else begin : g_kvgnocap
            assign me_kv_q = kv_q;
        end
    end endgenerate
endmodule

// The hardened element: the logic bound to its 2 x CODE_BANKS code ROM macros
// and its KV slice (2 x ot_sram_1r1w_128x256_m1_r2c2, written through a
// registered masked port from the die's KV fill network).
module ot_qwen_rom_tile_context_candidate_r3_retained #(
    parameter integer NW = 18,
    parameter integer GT = 6144,
    parameter integer SMIN = 6,
    parameter integer CODE_BANKS = 10,
    parameter integer KV_VB = 262144,
    parameter integer KV_NH = 4,
    parameter integer MEM_EXTRA = 0,
    parameter integer ROM_REPLICA_CELL_RETENTION = 0,
    parameter integer ROM_CONTROL_DISTRIBUTION = 0, // cdcbe60a exact76BUF
    parameter integer ROM_BANK5_CONTROL = 0, // Maxwell cdcbe60a; same-edge, defaultoff
    parameter integer ROM_HOLD_DIRECT_CAPTURE = 0, // Maxwell645ae1dd7; opt-in, no added edges
    parameter integer ACC_LAT = 5,        // lane accumulator FP32 add latency (ot_qwen_w12_matvec_part ACC_LAT)
    parameter integer FAST_ISSUE = 0,     // 1.2 GHz issue loop (ot_qwen_w12_matvec_part FAST_ISSUE)
    parameter integer KV_PREP = 0,        // KV-op offset pipeline cycles (ot_qwen_w12_matvec_part KV_PREP)
    parameter integer MUL_LAT = 5,        // lane BF16 product latency (ot_qwen_w12_matvec_part MUL_LAT)
    parameter integer TREE_LAT = 3        // split-tree pair adder latency (ot_qwen_w12_matvec_part TREE_LAT)
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
    wire [11:0]           rom_addr;
    wire [119:0]          rom_distributed_addr;
    wire [2*CODE_BANKS*266-1:0] rom_rd;
    wire                  kvs_r_ce;
    wire [6:0]            kvs_r_addr;
    wire [511:0]          kvs_rd;
    ot_qwen_rom_tile_logic_context_candidate_r3_retained #(.NW(NW), .GT(GT), .SMIN(SMIN), .CODE_BANKS(CODE_BANKS), .KV_LOCAL(1),
        .KV_VB(KV_VB), .KV_NH(KV_NH), .MEM_EXTRA(MEM_EXTRA), .ROM_REPLICA_CELL_RETENTION(ROM_REPLICA_CELL_RETENTION), .ROM_HOLD_DIRECT_CAPTURE(ROM_HOLD_DIRECT_CAPTURE), .ROM_BANK5_CONTROL(ROM_BANK5_CONTROL), .ROM_CONTROL_DISTRIBUTION(ROM_CONTROL_DISTRIBUTION), .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT)) u_logic (
        .clk(clk), .rst_n(rst_n), .tile_id(tile_id), .ib_go(ib_go), .ib(ib), .xl(xl),
        .t_out(t_out), .t_vout(t_vout), .n_a(n_a), .n_b(n_b), .n_va(n_va), .n_y(n_y), .n_vy(n_vy), .fault(fault),
        .rom_ce(rom_ce), .rom_addr(rom_addr), .rom_distributed_addr(rom_distributed_addr), .rom_rd(rom_rd),
        .kvs_r_ce(kvs_r_ce), .kvs_r_addr(kvs_r_addr), .kvs_rd(kvs_rd),
        .kv_re(), .kv_addr(), .kv_q({4*16*32{1'b0}}));
    genvar p, b;
    generate
        for (p = 0; p < 2; p = p + 1) begin : g_col
            for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_bank
                ot_rom_4096x266_m8 u_rom (.clk(clk), .ce_in(rom_ce[b]), .addr_in(ROM_CONTROL_DISTRIBUTION != 0 ? rom_distributed_addr[12*(p*5+b) +: 12] : rom_addr),
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
    generate
        for (p = 0; p < 2; p = p + 1) begin : g_kv
            ot_sram_1r1w_128x256_m1_r2c2 u_kv (
                .clk(clk), .r_ce_in(kvs_r_ce), .r_addr_in(kvs_r_addr), .rd_out(kvs_rd[256*p +: 256]),
                .w_ce_in(kvw_ce_q), .w_addr_in(kvw_addr_q), .wd_in(kvw_data_q[256*p +: 256]),
                .w_mask_in(kvw_mask_q[256*p +: 256]),
                .rr_en(2'b0), .rr_addr(14'd0), .cr_en(2'b0), .cr_sel(16'd0));
        end
    endgenerate
endmodule
