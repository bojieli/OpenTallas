module ot_qwen_rom_tile_logic_nl_ctlpart_v1 #(
    parameter integer W  = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
`ifndef SYNTHESIS
    parameter integer ROM_TILE = -1, // constant die tile identity for released simulation masks
`endif
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
    // ROM_CAPX = 2 (el1011-q-tile 2026-10-11; needs ROM_CAP2 = 1): the INT8 -> BF16 expansion in TWO register rungs
    // (fba TT -51: cap -> cap2x was 20 levels: negate + leading-one + shift + mask in one stage).  Rung A (cx1, beside
    // cap): sign, magnitude, leading-one position, masked nonzero; rung B (cap2x): normalising shift + exponent.
    // +1 memory cycle per matvec fill (RX + 1; KV and x follow RX).
    // BAW: bank address width (12: ot_rom_4096x266_m8 banks; 11: ot_rom_2048x266_m8 half-depth banks, SS clk->q
    // 604 ps, twice CODE_BANKS for the same words -- the single-cycle capture then closes with a balanced clock)
    parameter integer BAW = 12,
    // LRST = 1: lane / tree-level reset copies inside the engine (ot_qwen_w12_matvec_part LRST)
    parameter integer LRST = 0,
    // ARPB = 1 (qwen-1010/c 2026-10-10; needs ROM_PIPE; 0 = unchanged): the LAST request-relay stage keeps ONE address
    // register per bank (a kept leaf beside the bank's two macros, rom_addr_b) instead of one per bank group: the group
    // copy rq_ad_s drove 6 macro address pins across the macro cluster (rp1pcl-hm0 TT -84: 9 levels of buffers).  Same
    // edge, same value: 0 cycles.  rom_addr / rom_addr_n then come from banks 0 / SB.
    parameter integer ARPB = 0,
    // TMUT (bench mutants, 0 = none): 1 = bank 0's address copy one edge stale; 2 = one tree adder's reset copy never
    // released (LRST 3)
    // ANR = 1 (hardcore-1010 D, 2026-10-10; 0 = unchanged): every lane / tree / node FP32 adder as ot_hdc_fp32_add_lat_nr
    // (cut bundles reset only their valid bit; HSPLIT kept copy for the B2a pass-through).  Bit-identical, 0 cycles.
    parameter integer ANR = 0,
    // MPR = 1 (el1011-q-tile 2026-10-11; needs ROM_PIPE and ARPB; 0 = unchanged): the last request-relay stage as ONE kept
    // {ce, address} register PER MACRO (rom_req_m, 2 columns x CODE_BANKS), placed at that macro's pins (rom_cap_at_pins.tcl
    // OT_PREQ=1).  The per-bank copy drove its bank's macro in BOTH columns across the frame (fba TT -59: rom_ce -> ce_in
    // 10 levels).  rom_ce / rom_addr_b keep the same stream (bench ROM model); same edge, same value: 0 cycles.
    parameter integer MPR = 0,
    // HIER = NPL > 0 (el1011-q-tile): the engine's lanes + tree as hardened lane-slice leaves (ot_qwen_w12_matvec_part HIER)
    parameter integer HIER = 0,
    parameter integer HIER_HARD = 0,      // the slices as the hardened leaf ot_qwen_tile_lsl (round 2)
    // el1011-q-tile h3 (2026-10-11; the glue stays tile-level logic, GLUE PLACEMENT): TOREG = tile output pin registers
    // on t_out / t_vout (+1 cycle a tile->node hop), TIDR = registered tile_id strap, LRR = one reset relay flop per
    // hardened leaf
    parameter integer TOREG = 0,
    parameter integer TIDR = 0,
    parameter integer LRR = 0,
    parameter integer RPH = 0,            // q13 r5 leaf 1: 1 = ROM pair pipeline as ot_qwen_rpair_logic per bank (soft), 2 = hardened leaf ot_qwen_tile_rpair (owns its 2 macros)
    parameter integer RQR = 0,            // q14 r5-fp1: ROM return relay: 1 = one register per bank group (south / north) on the rows' relay words before the group OR (+1 cycle on the ROM data), and per-group copies of the rpair address / any seam (needs RPH)
    parameter integer XTX = 0,             // el1011-q-tile r3: registered transmit rungs per hardened leaf (matvec HIER_HARD; +XTX cycles)
    // TMUT 3 = column 1 / bank 0's MPR copy one edge stale
    parameter integer TMUT = 0,
    // q13 spec r5 leaf 2 (2026-10-13), pure re-hierarchy (same registers, same edges):
    //   NDH 1 = the upper tree node as the hardened leaf ot_qwen_tile_node (W 16, NREG 1, TREE_LAT 7, ANR 1); its fault
    //           pin is registered in the leaf (+1 cycle on the node fault flag only; data/valid unchanged).
    //   BMUT  = bench boundary mutants: 2 = the node leaf's a input with lanes 0 / 1 swapped; 3 = the leaf's t_d
    //           (t_out feed-through) input with lanes 0 / 1 swapped.
    //   q14: with NDH 1 the TOREG t_out / t_vout pin registers are the leaf's feed-through registers (needs TOREG 1).
    parameter integer NDH = 0,
    // q14 r9 (2026-10-14): NODE 0 = node-less tile (the block-last tile of a 16-leaf tree has no node role): no node
    //   logic at all, n_a / n_b / n_va unread, n_y / n_vy / node fault constant 0; t_out via the TOREG pin registers.
    parameter integer NODE = 1,
    parameter integer BMUT = 0,
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
    parameter integer TREE_LAT = 3,       // split-tree pair adder latency (ot_qwen_w12_matvec_part TREE_LAT)
    parameter integer TX_MUT = 0,
    parameter integer CHILD_CLOCKS = 0
) (
    input wire [58*514-1:0] bank_q,
    output wire [58*514-1:0] bank_d,
    input wire [13:0] rst_child_n,
    input wire [CODE_BANKS-1:0] ck_rpair,
    input wire [7:0] ck_lsl,
    input wire ck_node,
    input wire clk_ctl,
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
    output wire [CODE_BANKS*12-1:0] rom_addr_b,   // per-bank address (ARPB; else each bank's group address)
    output wire [2*CODE_BANKS*13-1:0] rom_req_m,  // MPR: per-macro {ce, addr[11:0]}, macro (column p, bank b) at p*CODE_BANKS+b
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
    wire [58*514-1:0] bank_d_me;
    wire [513:0] bank_d_tor;
`ifndef SYNTHESIS
    initial if(NODE!=0 || TOREG!=1) $fatal(1,"nl_banked logic: NODE 0 / TOREG 1 only");
`endif
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    localparam integer RX = (ROM_PIPE != 0) ? (ROM_ARELAY + 2 + ROM_CAP2 + ((ROM_CAPX == 2) ? 1 : 0) + ((RQR != 0) ? 1 : 0)) : 0;   // extra memory cycles of the ROM pipeline
    localparam integer ME_EXTRA = MEM_EXTRA + RX + 1; // actual balanced return capture (+1)
    localparam integer SB = (CODE_BANKS + 1) / 2;                      // south group: banks [0, SB)
    generate if (ROM_PIPE != 0 && (MEM_EXTRA != 1 || ROM_ARELAY < 1)) begin : g_rp_bad
        initial $error("ROM_PIPE needs MEM_EXTRA = 1 and ROM_ARELAY >= 1");
    end endgenerate
    wire [TG*32-1:0] xl_q;
    wire go_i;
    wire [IBW-1:0] ib_i;
    wire [TG*32-1:0] xl_r  = IREG ? xl_q : xl;
    wire [TG*32-1:0] xl_i;
assign xl_q=bank_q[6810 +: 128];
assign bank_d[6682 +: 256] = {xl,xl_r};
assign bank_d[6938 +: 258] = 0;
assign bank_d[8224 +: 256] = {128'b0,bank_q[6682 +: 128]};
assign bank_d[8480 +: 258] = 0;
assign bank_d[7196 +: 256] = {128'b0,bank_q[8224 +: 128]};
assign bank_d[7452 +: 258] = 0;
assign bank_d[7710 +: 256] = {128'b0,bank_q[7196 +: 128]};
assign bank_d[7966 +: 258] = 0;
assign bank_d[28784 +: 256] = {128'b0,bank_q[7710 +: 128]};
assign bank_d[29040 +: 258] = 0;
assign bank_d[8738 +: 256] = {128'b0,bank_q[28784 +: 128]};
assign bank_d[8994 +: 258] = 0;
assign bank_d[9252 +: 256] = {128'b0,bank_q[8738 +: 128]};
assign bank_d[9508 +: 258] = 0;
assign bank_d[9766 +: 256] = {bank_q[10280 +: 128],bank_q[9252 +: 128]};
assign bank_d[10022 +: 258] = 0;
assign bank_d[10280 +: 256] = {128'b0,bank_q[9766 +: 128]};
assign bank_d[10536 +: 258] = 0;
assign xl_i=bank_q[10280 +: 128];



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
    //: TIDR: the static tile_id strap through a register (the strap pins sat 69 levels from kdif; a strap is constant from
    //: before reset release, so the registered copy is the same value at every use)
    wire [15:0]       tile_id_i;
    wire [W*32-1:0]   t_out_i;
    wire              t_vout_i;

    //: TOREG: the tile's tree output as pin registers (the leaves' tree registers sat 216-457 um from the t_out pins);
    //: data and valid together, +1 cycle on the tile -> node hop
    //: with the hardened node leaf (NDH = 1) these registers live INSIDE the leaf (its t_d -> t_out feed-through: the
    //: t_out pins lie in the leaf's W pin band), same edge and value
    wire [W*32-1:0]   t_out_nd;
    wire              t_vout_nd;
    generate if (NDH != 0 && NODE != 0) begin : g_tond
        assign t_out = t_out_nd;
        assign t_vout = t_vout_nd;
    end else if (TOREG != 0) begin : g_toreg
        // NL: TOREG capture = actual CLOSED bank 'to_reg' (slot 37); same edge and value
        assign bank_d_tor = {1'b0, t_vout_i, t_out_i};
        assign t_out = bank_q[19018 +: 512];
        assign t_vout = bank_q[19530];
    end else begin : g_tonr
        assign t_out = t_out_i;
        assign t_vout = t_vout_i;
    end endgenerate
initial if(IREG!=1 || TIDR!=1 || FAST_ISSUE!=1 || ISSUE_LEAF!=1) $fatal(1,"control partition requires registered descriptor/strap and FAST_ISSUE leaf");
wire [1+1+((AW-1)-(0)+1)+1+((NW-1)-(0)+1)+((NW-1)-(0)+1)+((NW-1)-(0)+1)+1+1+1+1+1+1+((AW-1)-(0)+1)+((AW-1)-(0)+1)+((3)-(0)+1)+((AW-1)-(0)+1)+((NW-1)-(0)+1)+((AW-1)-(0)+1)+((AW-1)-(0)+1)+((AW-1)-(0)+1)+((NW-1)-(0)+1)+((NW-1)-(0)+1)+(($clog2(IL)-1)-(0)+1)+((AW-1)-(0)+1)+((AW-1)-(0)+1)+((NW)-(0)+1)+((NW)-(0)+1)+((AW-1)-(0)+1)+1+1+1+1-1:0] ctl_bus;
ot_qwen_nknl_control_capture_v1 #(.W(W),.G(TG),.IL(IL),.AW(AW),.NW(NW),.GT(GT),.SMIN(SMIN),.KV_PREP(KV_PREP),.INT8_WEIGHT(1),.INT8_SCALE_WCS_BASE(1),.TMUT(TMUT),.IREG(IREG),.TIDR(TIDR)) u_control(
.clk(clk_ctl),.rst_n(rst_n),.ib_go(ib_go),.ib(ib),.tile_id(tile_id),.go_i(go_i),.ib_i(ib_i),.tile_id_i(tile_id_i),.ctl_bus(ctl_bus));
    ot_qwen_w12_matvec_ctlpart_v1 #(.TX_MUT(TX_MUT),.W(W), .G(TG), .IL(IL), .AW(AW), .NW(NW), .INT8_WEIGHT(1), .INT8_SCALE_WCS_BASE(1),
        .CHILD_CLOCKS(CHILD_CLOCKS), .PART(1), .GT(GT), .GBASE_PORT(1), .SMIN(SMIN), .NX(0), .MEM_EXTRA(ME_EXTRA), .WCONV(ROM_PIPE), .LRST(LRST), .TMUT(TMUT), .ANR(ANR), .HIER(HIER), .HIER_HARD(HIER_HARD), .LRR(LRR), .XTX(XTX),
        .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT)) u_me (
        .ctl_bus(ctl_bus),.bank_q(bank_q),.bank_d(bank_d_me),.rst_child_n(rst_child_n),
        .ck_lsl(ck_lsl),
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
        .i_gbase({16'd0, tile_id_i} * TG), .t_in({W*32{1'b0}}), .t_fault_in(1'b0),
        .t_out(t_out_i), .t_vout(t_vout_i), .t_fault(), .active_o());

    // -- upper tree node ---------------------------------------------------------
    wire node_fault;
    generate if (NODE == 0) begin : g_nonode
        assign t_out_nd = {W*32{1'b0}};
        assign t_vout_nd = 1'b0;
        assign n_y = {W*32{1'b0}};
        assign n_vy = 1'b0;
        assign node_fault = 1'b0;
    end else if (NDH != 0) begin : g_ndh
        if (W != 16 || NREG != 1 || TREE_LAT != 7 || ANR != 1 || TOREG == 0) begin : g_bad
            initial $error("NDH needs W 16, NREG 1, TREE_LAT 7, ANR 1, TOREG 1 (the fixed hardened leaf ot_qwen_tile_node)");
        end
        wire [W*32-1:0] td_x;
        if (BMUT == 3) begin : g_bt
            assign td_x = {t_out_i[W*32-1:64], t_out_i[31:0], t_out_i[63:32]};
        end else begin : g_tk
            assign td_x = t_out_i;
        end
        wire [W*32-1:0] na_x;
        if (BMUT == 2) begin : g_bm
            assign na_x = {n_a[W*32-1:64], n_a[31:0], n_a[63:32]};
        end else begin : g_ok
            assign na_x = n_a;
        end
        ot_qwen_tile_node u_node (.clk(CHILD_CLOCKS ? ck_node : clk), .rst_n(rst_child_n[13]), .a(na_x), .b(n_b), .va(n_va),
                                  .y(n_y), .vy(n_vy), .fault(node_fault),
                                  .t_d(td_x), .t_vd(t_vout_i), .t_out(t_out_nd), .t_vout(t_vout_nd));
    end else begin : g_nd
        assign t_out_nd = {W*32{1'b0}};
        assign t_vout_nd = 1'b0;
        ot_qwen_me_node_w12 #(.W(W), .WS(NREG), .TREE_LAT(TREE_LAT), .ANR(ANR)) u_node (.clk(clk), .rst_n(rst_n), .a(n_a), .b(n_b), .va(n_va),
                                               .y(n_y), .vy(n_vy), .fault(node_fault));
    end endgenerate
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
    function automatic [2:0] lead1(input [7:0] m);           // leading-one position (0 when m == 0)
        integer i;
        begin lead1 = 0; for (i = 0; i < 8; i = i + 1) if (m[i]) lead1 = i[2:0]; end
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
        assign rom_addr_b = {CODE_BANKS{rom_addr}};
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
            if (ARPB == 0 || a < ROM_ARELAY) begin : g_ad
                always @(posedge clk) begin
                    rq_ad_s[a] <= (a == 1) ? {{(12-BAW){1'b0}}, wrom_addr[BAW-1:0]} : rq_ad_s[a-1];
                    rq_ad_n[a] <= (a == 1) ? {{(12-BAW){1'b0}}, wrom_addr[BAW-1:0]} : rq_ad_n[a-1];
                end
            end
        end
        for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_ce
            assign rom_ce[b] = (b < SB) ? rq_ce_s[ROM_ARELAY][b] : rq_ce_n[ROM_ARELAY][b];
        end
        if (ARPB != 0) begin : g_arpb
            //: ARPB: the last relay stage as one kept address register per bank (rom_addr_b)
            wire [11:0] ad_pre;
            if (ROM_ARELAY == 1) begin : g_ap1
                assign ad_pre = {{(12-BAW){1'b0}}, wrom_addr[BAW-1:0]};
            end else begin : g_apn
                assign ad_pre = rq_ad_s[ROM_ARELAY-1];
            end
            for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_ab
                if (TMUT == 1 && b == 0) begin : g_mut
                    wire [11:0] stale;
                    ot_qwen_arpb_reg u_s (.clk(clk), .d(ad_pre), .q(stale));
                    ot_qwen_arpb_reg u_a (.clk(clk), .d(stale), .q(rom_addr_b[12*b +: 12]));
                end else begin : g_ok
                    ot_qwen_arpb_reg u_a (.clk(clk), .d(ad_pre), .q(rom_addr_b[12*b +: 12]));
                end
            end
            assign rom_addr = rom_addr_b[11:0];
            assign rom_addr_n = rom_addr_b[12*((SB < CODE_BANKS) ? SB : 0) +: 12];
`ifndef SYNTHESIS
            //: every bank's copy must equal the group address it replaces, every edge
            reg [11:0] ad_ref;
            integer ck;
            always @(posedge clk) ad_ref <= ad_pre;
            always @(negedge clk) for (ck = 0; ck < CODE_BANKS; ck = ck + 1)
                if (rom_addr_b[12*ck +: 12] !== ad_ref) begin
                    $display("FAIL arpb bank %0d address copy %h != %h", ck, rom_addr_b[12*ck +: 12], ad_ref);
                    $finish;
                end
`endif
        end else begin : g_agrp
            //: two address ports to the wrapper's macros: rom_addr (south banks) and rom_addr_n (north banks)
            assign rom_addr = rq_ad_s[ROM_ARELAY];
            assign rom_addr_n = rq_ad_n[ROM_ARELAY];
            for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_abg
                assign rom_addr_b[12*b +: 12] = (b < SB) ? rq_ad_s[ROM_ARELAY] : rq_ad_n[ROM_ARELAY];
            end
        end
        if (MPR != 0 && RPH == 0) begin : g_mpr
            //: MPR: one kept {ce, address} register per macro, the pre-stage of the last relay as its D
            wire [CODE_BANKS-1:0] ce_pre;
            wire [11:0] adm_pre;
            if (ROM_ARELAY == 1) begin : g_mp1
                assign ce_pre = ce0;
                assign adm_pre = {{(12-BAW){1'b0}}, wrom_addr[BAW-1:0]};
            end else begin : g_mpn
                for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_cp
                    assign ce_pre[b] = (b < SB) ? rq_ce_s[ROM_ARELAY-1][b] : rq_ce_n[ROM_ARELAY-1][b];
                end
                assign adm_pre = rq_ad_s[ROM_ARELAY-1];
            end
            genvar mc;
            for (mc = 0; mc < 2; mc = mc + 1) begin : g_mc
                for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_mb
                    if (TMUT == 3 && mc == 1 && b == 0) begin : g_mut
                        wire [12:0] stale;
                        ot_qwen_mpr_reg u_s (.clk(clk), .rst_n(rst_n), .d({ce_pre[b], adm_pre}), .q(stale));
                        ot_qwen_mpr_reg u_r (.clk(clk), .rst_n(rst_n), .d(stale), .q(rom_req_m[13*(mc*CODE_BANKS+b) +: 13]));
                    end else begin : g_ok
                        ot_qwen_mpr_reg u_r (.clk(clk), .rst_n(rst_n), .d({ce_pre[b], adm_pre}), .q(rom_req_m[13*(mc*CODE_BANKS+b) +: 13]));
                    end
                end
            end
`ifndef SYNTHESIS
            //: every macro's copy must equal its bank's request stream (ce; address when enabled), every edge
            integer mk;
            always @(negedge clk) if (rst_n) for (mk = 0; mk < 2*CODE_BANKS; mk = mk + 1)
                if (rom_req_m[13*mk+12] !== rom_ce[mk % CODE_BANKS] ||
                    (rom_ce[mk % CODE_BANKS] && rom_req_m[13*mk +: 12] !== rom_addr_b[12*(mk % CODE_BANKS) +: 12])) begin
                    $display("FAIL mpr macro %0d request copy %h != ce %b addr %h", mk, rom_req_m[13*mk +: 13],
                             rom_ce[mk % CODE_BANKS], rom_addr_b[12*(mk % CODE_BANKS) +: 12]);
                    $finish;
                end
`endif
        end else if (RPH == 0) begin : g_nmpr
            assign rom_req_m = {2*CODE_BANKS*13{1'b0}};
        end
        if (RPH != 0) begin : g_rph
            //: q13 r5 leaf 1: one ot_qwen_rpair_logic per bank row (its 2 macro request registers, capture / expansion
            //: rungs, select, group + relay registers); the seam is flop -> flop: in = the relay pre-stage {ce, any, address},
            //: out = the bank's registered relay word.  rs | rn of the flat pipeline == OR over the banks' relay words
            //: (the group OR commutes with the two register stages): same values, same edges.
            if (MPR == 0 || ROM_ARELAY < 2 || TG != 4) begin : g_bad
                initial begin $display("FAIL RPH needs MPR = 1, ROM_ARELAY >= 2, TG = 4"); $finish; end
            end
            wire [CODE_BANKS-1:0] ce_pre;
            wire [11:0] adm_pre = rq_ad_s[ROM_ARELAY-1];
            //: q14 r5-fp1 (RQR): the bank rows stand in two groups (south banks [0, SB), north banks [SB, CODE_BANKS)) on
            //: either side of the lane block, > 1 mm end to end.  Each group gets its own copy of the seam address / any
            //: (the relay's kept south / north copies: same value, same edge) and ONE register on its OR of the rows'
            //: relay words; the group words are ORed after it (+1 cycle on the ROM data, in RX).
            wire [11:0] adm_pre_n = (RQR != 0) ? rq_ad_n[ROM_ARELAY-1] : rq_ad_s[ROM_ARELAY-1];
            wire        any_s = (RQR != 0) ? (|rq_ce_s[ROM_ARELAY-1]) : (|ce_pre);
            wire        any_n = (RQR != 0) ? (|rq_ce_n[ROM_ARELAY-1]) : (|ce_pre);
            wire [2*2*PWB-1:0] rw [0:CODE_BANKS];
            wire [2*2*PWB-1:0] rwn [0:CODE_BANKS];
            assign rw[0] = {2*2*PWB{1'b0}};
            assign rwn[0] = {2*2*PWB{1'b0}};
            for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_rb
                assign ce_pre[b] = (b < SB) ? rq_ce_s[ROM_ARELAY-1][b] : rq_ce_n[ROM_ARELAY-1][b];
                wire [2*2*PWB-1:0] r_q;
                if (RPH == 2) begin : g_hd
                    if (PWB != 256 || ROM_CAP2 != 1 || ROM_CAPX != 2 || BAW != 12 || ROM_MUT != 0 || TMUT != 0) begin : g_hbad
                        initial begin $display("FAIL RPH = 2: parameters differ from the hardened leaf ot_qwen_tile_rpair"); $finish; end
                    end
                    ot_qwen_tile_rpair
`ifndef SYNTHESIS
                        #(.ROM_TILE(ROM_TILE), .ROM_BANK(b))
`endif
                        u_rp (.clk(CHILD_CLOCKS ? ck_rpair[b] : clk), .rst_n(rst_child_n[b]), .ce_d(ce_pre[b]), .any_d((b < SB) ? any_s : any_n), .ad_d((b < SB) ? adm_pre : adm_pre_n), .r_q(r_q));
                    assign rom_req_m[13*b +: 13] = 13'd0;
                    assign rom_req_m[13*(CODE_BANKS+b) +: 13] = 13'd0;
                end else begin : g_sf
                    wire [25:0] rq;
                    ot_qwen_rpair_logic #(.PWB(PWB), .ROM_CAP2(ROM_CAP2), .ROM_CAPX(ROM_CAPX), .ROM_MUT(ROM_MUT),
                        .MUT3((TMUT == 3 && b == 0) ? 1 : 0), .MUT5((TMUT == 5 && b == 0) ? 1 : 0)) u_rp (
                        .clk(clk), .rst_n(rst_child_n[b]), .ce_d(ce_pre[b]), .any_d((b < SB) ? any_s : any_n), .ad_d((b < SB) ? adm_pre : adm_pre_n), .req_m(rq),
                        .rd({rom_rd[(CODE_BANKS + b)*266 +: PWB], rom_rd[b*266 +: PWB]}), .r_q(r_q));
                    assign rom_req_m[13*b +: 13] = rq[12:0];
                    assign rom_req_m[13*(CODE_BANKS+b) +: 13] = rq[25:13];
                end
                assign rw[b+1]  = (RQR != 0 && b >= SB) ? rw[b] : (rw[b] | r_q);     // RQR: the south group only
                assign rwn[b+1] = (RQR != 0 && b >= SB) ? (rwn[b] | r_q) : rwn[b];   // RQR: the north group
            end
            if (RQR != 0) begin : g_rqr
wire [1023:0] gs_q,gn_q,gs_r,gn_r;
assign bank_d[514 +: 256] = rw[CODE_BANKS][0 +:256];
assign bank_d[770 +: 258] = 0;
assign gs_q[0 +:256]=bank_q[514 +: 256];
assign bank_d[24672 +: 256] = gs_q[0 +:256];
assign bank_d[24928 +: 258] = 0;
assign gs_r[0 +:256]=bank_q[24672 +: 256];
assign bank_d[1028 +: 256] = rw[CODE_BANKS][256 +:256];
assign bank_d[1284 +: 258] = 0;
assign gs_q[256 +:256]=bank_q[1028 +: 256];
assign bank_d[25186 +: 256] = gs_q[256 +:256];
assign bank_d[25442 +: 258] = 0;
assign gs_r[256 +:256]=bank_q[25186 +: 256];
assign bank_d[1542 +: 256] = rw[CODE_BANKS][512 +:256];
assign bank_d[1798 +: 258] = 0;
assign gs_q[512 +:256]=bank_q[1542 +: 256];
assign bank_d[25700 +: 256] = gs_q[512 +:256];
assign bank_d[25956 +: 258] = 0;
assign gs_r[512 +:256]=bank_q[25700 +: 256];
assign bank_d[2056 +: 256] = rw[CODE_BANKS][768 +:256];
assign bank_d[2312 +: 258] = 0;
assign gs_q[768 +:256]=bank_q[2056 +: 256];
assign bank_d[26214 +: 256] = gs_q[768 +:256];
assign bank_d[26470 +: 258] = 0;
assign gs_r[768 +:256]=bank_q[26214 +: 256];
assign bank_d[2570 +: 256] = rwn[CODE_BANKS][0 +:256];
assign bank_d[2826 +: 258] = 0;
assign gn_q[0 +:256]=bank_q[2570 +: 256];
assign bank_d[26728 +: 256] = gn_q[0 +:256];
assign bank_d[26984 +: 258] = 0;
assign gn_r[0 +:256]=bank_q[26728 +: 256];
assign bank_d[3084 +: 256] = rwn[CODE_BANKS][256 +:256];
assign bank_d[3340 +: 258] = 0;
assign gn_q[256 +:256]=bank_q[3084 +: 256];
assign bank_d[27242 +: 256] = gn_q[256 +:256];
assign bank_d[27498 +: 258] = 0;
assign gn_r[256 +:256]=bank_q[27242 +: 256];
assign bank_d[3598 +: 256] = rwn[CODE_BANKS][512 +:256];
assign bank_d[3854 +: 258] = 0;
assign gn_q[512 +:256]=bank_q[3598 +: 256];
assign bank_d[27756 +: 256] = gn_q[512 +:256];
assign bank_d[28012 +: 258] = 0;
assign gn_r[512 +:256]=bank_q[27756 +: 256];
assign bank_d[4112 +: 256] = rwn[CODE_BANKS][768 +:256];
assign bank_d[4368 +: 258] = 0;
assign gn_q[768 +:256]=bank_q[4112 +: 256];
assign bank_d[28270 +: 256] = gn_q[768 +:256];
assign bank_d[28526 +: 258] = 0;
assign gn_r[768 +:256]=bank_q[28270 +: 256];
assign wrom_q=gs_r|gn_r;
            end else begin : g_rq0
                assign wrom_q = rw[CODE_BANKS];
            end
`ifndef SYNTHESIS
            integer mk;
            always @(negedge clk) if (rst_n && RPH == 1) for (mk = 0; mk < 2*CODE_BANKS; mk = mk + 1)
                if (rom_req_m[13*mk+12] !== rom_ce[mk % CODE_BANKS] ||
                    (rom_ce[mk % CODE_BANKS] && rom_req_m[13*mk +: 12] !== rom_addr_b[12*(mk % CODE_BANKS) +: 12])) begin
                    $display("FAIL rph macro %0d request copy %h != ce %b addr %h", mk, rom_req_m[13*mk +: 13],
                             rom_ce[mk % CODE_BANKS], rom_addr_b[12*(mk % CODE_BANKS) +: 12]);
                    $finish;
                end
`endif
        end
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
        for (p = 0; p < ((RPH == 0) ? TG / 2 : 0); p = p + 1) begin : g_pair
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
                if (ROM_CAP2 != 0 && ROM_CAPX == 2) begin : g_capx2
                    //: rung A (beside cap): sign, magnitude, leading-one position, masked nonzero, per byte
                    (* keep *) reg [PWB/8-1:0] xa_s, xa_nz;
                    (* keep *) reg [PWB-1:0]   xa_m;
                    (* keep *) reg [3*PWB/8-1:0] xa_p;
                    (* keep *) reg [2*PWB-1:0] cap2x;
                    (* keep *) reg [PWB/32-1:0] sel_r;          // the select, one kept copy per 4 bytes
                    genvar ex, er;
                    for (er = 0; er < PWB / 32; er = er + 1) begin : g_selr
                        always @(posedge clk) sel_r[er] <= (ROM_MUT != 0) ? sel_1[b] : sel_c[b];
                    end
                    for (ex = 0; ex < PWB / 8; ex = ex + 1) begin : g_cvx
                        wire [7:0] cb = cap[8*ex +: 8];
                        wire [7:0] mg = cb[7] ? (~cb + 8'd1) : cb;
                        always @(posedge clk) begin
                            xa_s[ex] <= cb[7];
                            xa_m[8*ex +: 8] <= mg;
                            xa_p[3*ex +: 3] <= lead1(mg);
                            xa_nz[ex] <= (mg != 8'd0);
                        end
                        //: rung B: normalising shift + exponent, masked by the select of the edge rung A holds
                        wire [7:0] nm = xa_m[8*ex +: 8] << (3'd7 - xa_p[3*ex +: 3]);
                        always @(posedge clk)
                            cap2x[16*ex +: 16] <= (xa_nz[ex] && sel_r[ex / 4]) ?
                                {xa_s[ex], 8'd127 + {5'd0, xa_p[3*ex +: 3]}, nm[6:0]} : 16'd0;
                    end
                    assign cx = {PWB{1'b0}}; assign sx = 1'b0; assign sx_early = 1'b0; assign cxw = cap2x;
                end else if (ROM_CAP2 != 0 && ROM_CAPX != 0) begin : g_capx
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
assign bank_d[0 +: 514]=0;
assign bank_d[4626 +: 514]=bank_d_me[4626 +:514];
assign bank_d[5140 +: 514]=bank_d_me[5140 +:514];
assign bank_d[5654 +: 514]=bank_d_me[5654 +:514];
assign bank_d[6168 +: 514]=bank_d_me[6168 +:514];
assign bank_d[10794 +: 514]=bank_d_me[10794 +:514];
assign bank_d[11308 +: 514]=bank_d_me[11308 +:514];
assign bank_d[11822 +: 514]=bank_d_me[11822 +:514];
assign bank_d[12336 +: 514]=bank_d_me[12336 +:514];
assign bank_d[12850 +: 514]=bank_d_me[12850 +:514];
assign bank_d[13364 +: 514]=bank_d_me[13364 +:514];
assign bank_d[13878 +: 514]=bank_d_me[13878 +:514];
assign bank_d[14392 +: 514]=bank_d_me[14392 +:514];
assign bank_d[14906 +: 514]=bank_d_me[14906 +:514];
assign bank_d[15420 +: 514]=bank_d_me[15420 +:514];
assign bank_d[15934 +: 514]=bank_d_me[15934 +:514];
assign bank_d[16448 +: 514]=bank_d_me[16448 +:514];
assign bank_d[16962 +: 514]=bank_d_me[16962 +:514];
assign bank_d[17476 +: 514]=bank_d_me[17476 +:514];
assign bank_d[17990 +: 514]=bank_d_me[17990 +:514];
assign bank_d[18504 +: 514]=bank_d_me[18504 +:514];
assign bank_d[19018 +: 514]=bank_d_tor;
assign bank_d[19532 +: 514]=0;
assign bank_d[20046 +: 514]=0;
assign bank_d[20560 +: 514]=0;
assign bank_d[21074 +: 514]=0;
assign bank_d[21588 +: 514]=bank_d_me[21588 +:514];
assign bank_d[22102 +: 514]=bank_d_me[22102 +:514];
assign bank_d[22616 +: 514]=0;
assign bank_d[23130 +: 514]=0;
assign bank_d[23644 +: 514]=0;
assign bank_d[24158 +: 514]=0;
assign bank_d[29298 +: 514]=bank_d_me[29298 +:514];
endmodule
