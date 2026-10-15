`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_qwen_me_array_dvm_w12: the Qwen TP8 matrix-engine array of ot_qwen_me_array_w12 with the DISTRIBUTED x slices
// (ot_qfd_xslice.sv) in place of the central x network.  Same tiles, tree nodes and spine top; what changes is how a
// tile's xl pins are driven:
//   x writes (SU / attention return) + the accepted go / ib -> ot_qfd_xs_tap (one pipeline) -> HB head-row stages ->
//                                         every column's ot_qfd_xhead (fill, then go) -> N / S corridor of NH ot_qfd_xcst stations
//                                         -> each station's tap -> NH - 1 - s equalising stages -> the tile (lockstep,
//                                         as the array model's uniform BD)
// Geometry: NCOL columns x 2*NH rows, tile id = col * 2*NH + row (rows 0 .. NH-1: N corridor, station = row; rows
// NH .. 2NH-1: S corridor, station = row - NH).  GT = NCOL * 2*NH * TG.
// BD of this array (go accepted -> the tiles' ib_go, + IREG) = 3 + HB + DX + NH + 3 (r3: go / ib enter the x tap and
// share the fill's pipeline, 3 tap stages); the plain-head equivalent (chead instead of xhead, no x) is HB + NH + 3, so
// the x path costs 3 + DX edges on the instruction broadcast and the central read's XVM is gone.
// Tile ids (r3): tile (column c, head row r) is tile t = tid(c, r) of the array's tree order (TIDM 1: the die's morton
// map, compute_spine.ref_tile_id; TIDM 0: c * 2NH + r); the head takes the column's ids as its tids strap.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_me_array_dvm_w12 #(
    parameter integer W  = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer XCW = 12,
    parameter integer INT8_SCALE_WCS_BASE = 1,
    parameter integer NCOL = 2,
    parameter integer NH = 8,
    parameter integer TG = 4,
    parameter integer GT = NCOL * 2 * NH * TG,
    parameter integer SMIN = 3,
    parameter integer SMAX = 5,
    parameter integer TCUT = 3,
    parameter integer HB = 2,
    parameter integer LEAF_FILL_PIPE = 0,
    parameter integer LEAF_BANK_PIPE = 0,
    parameter integer REQ_PIPE = 0,
    parameter integer DX = 10 + LEAF_BANK_PIPE + REQ_PIPE + (NH/2-1)*LEAF_FILL_PIPE,
    parameter integer FILL_LEAD = 2 + (NH/2-1)*LEAF_FILL_PIPE,
    parameter integer TIDM = 1,
    parameter integer XOFF = 3,
    parameter integer NWS = 0,
    parameter integer TWS = 0,
    parameter integer ORD = 0,
    parameter integer CODE_BANKS = 2,
    parameter integer BAW = 12,
    parameter integer ACC_LAT = 5,
    parameter integer FAST_ISSUE = 0,
    parameter integer MUL_LAT = 5,
    parameter integer TREE_LAT = 3,
    parameter integer NATIVE_AFFINE=0,
    parameter integer STATIC_SCHEDULE=0,
    parameter integer TAP_MUT = 0,
    parameter integer LEAF_MUT = 0,
    parameter integer HEAD_MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output wire              idle,
    input  wire [NW-1:0]     i_nout, i_tiles, i_k,
    input  wire              i_wsrc,
    input  wire [AW-1:0]     i_wbase, i_ts, i_ks, i_js,
    input  wire [AW-1:0]     i_xbase, i_xks, i_xjs, i_xcs,
    input  wire [2:0]        i_jsh,
    input  wire [3:0]        i_split,
    input  wire [AW-1:0]     i_wcs,
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase, i_ots, i_ojs,
    input  wire              i_mmode, i_oen, i_amax, i_rmax,
    input  wire [AW-1:0]     i_mbase,
    output wire              scale_re,
    output wire [GT-1:0]     scale_gre,
    output wire [GT*AW-1:0]  scale_addr,
    input  wire [GT*W*16-1:0] scale_q,
    // x fill (VM write face)
    input  wire              xpf_v,
    input  wire [AW-1:0]     xpf_xbase,
    input  wire [XCW-1:0]    xpf_xcs,
    input  wire [XCW-1:0]    xpf_xks,
    input  wire [3:0]        xpf_split,
    input  wire [NW-1:0]     xpf_k,
    input  wire              xpf_round,
    input  wire              sw_v,
    input  wire [AW-1:0]     sw_a,
    input  wire [63:0]       sw_m,
    input  wire [64*32-1:0]  sw_d,
    input  wire              aw_v,
    input  wire [AW-1:0]     aw_a,
    input  wire [15:0]       aw_m,
    input  wire [16*32-1:0]  aw_d,
    output wire [GT/TG*CODE_BANKS-1:0]     t_rom_ce,
    output wire [GT/TG*12-1:0]             t_rom_addr,
    input  wire [GT/TG*2*CODE_BANKS*266-1:0] t_rom_rd,
    output wire              ov,
    output wire [GT-1:0]     o_we,
    output wire [GT*AW-1:0]  o_addr,
    output wire [GT*W-1:0]   o_mask,
    output wire [GT*W*32-1:0] o_data,
    output wire [NW-1:0]     am_idx,
    output wire [31:0]       am_val,
    output wire              am_any,
    output wire              mx_we,
    output wire [AW-1:0]     mx_addr,
    output wire [W-1:0]      mx_mask,
    output wire [W*32-1:0]   mx_data,
    output wire [15:0]       progress,
    output wire              fault,
    output wire              x_fault,
    // observability for the bench: the xl word each tile receives
    output wire [GT/TG*TG*32-1:0] tile_xl
);
    localparam integer NT  = GT / TG;
    localparam integer LT  = $clog2(TG);
    localparam integer NPT = GT >> TCUT;
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    localparam integer DESC = 2 + AW + 2 * XCW + 4 + NW + 1;
    localparam integer FW  = DESC + 2 + (AW - 6) + 6 + 64 + 1024;
    localparam integer HW  = 1 + IBW + FW;
    localparam integer CW  = 1 + IBW + 128 + 8;
    localparam integer BD  = 3 + HB + DX + NH + 3;      // tap (3) + head row + head + corridor + tile
    localparam integer IREG = 1;
    localparam integer NREG = (NWS > 0) ? 1 : 0;
    localparam integer NPG = GT >> SMIN;
    generate if (NT != NCOL * 2 * NH) begin : g_bad
        initial $error("GT must be NCOL * 2 * NH * TG");
    end endgenerate

    // -- spine top (its x port is unused: the tiles take x from the slices) ----------------------------------------
    wire [NPT*W*32-1:0] t_lvl;
    wire                fab_fault;
    wire [NPG-1:0]      sp_scale_gre, sp_o_we;
    wire [NPG*AW-1:0]   sp_scale_addr, sp_o_addr;
    wire [NPG*W-1:0]    sp_o_mask;
    wire [NPG*W*32-1:0] sp_o_data;
    ot_qwen_me_spine_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .INT8_SCALE_WCS_BASE(INT8_SCALE_WCS_BASE), .GT(GT), .TG(TG),
        .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT), .BD(BD), .XVM(0), .NWS(NWS), .TWS(TWS), .TOREG(0), .ORD(ORD),
        .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .FAST_ISSUE(FAST_ISSUE), .MUL_LAT(MUL_LAT)) u_spine (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc),
        .i_wbase(i_wbase), .i_ts(i_ts), .i_ks(i_ks), .i_js(i_js),
        .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs),
        .i_jsh(i_jsh), .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round),
        .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs),
        .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax), .i_mbase(i_mbase),
        .scale_re(scale_re), .scale_gre(sp_scale_gre), .scale_addr(sp_scale_addr), .scale_q(scale_q[NPG*W*16-1:0]),
        .x_re(), .x_addr(), .x_q({(1<<SMAX)*32{1'b0}}),
        .wrom_re(), .wrom_addr(), .kv_re(),
        .tgo(), .tb(), .xl_d(), .t_lvl(t_lvl), .fab_fault(fab_fault),
        .ov(ov), .o_we(sp_o_we), .o_addr(sp_o_addr), .o_mask(sp_o_mask), .o_data(sp_o_data),
        .am_idx(am_idx), .am_val(am_val), .am_any(am_any),
        .mx_we(mx_we), .mx_addr(mx_addr), .mx_mask(mx_mask), .mx_data(mx_data),
        .progress(progress), .fault(fault));
    generate if (NPG < GT) begin : g_zx
        assign scale_gre = {{(GT - NPG){1'b0}}, sp_scale_gre};
        assign scale_addr = {{((GT - NPG) * AW){1'b0}}, sp_scale_addr};
        assign o_we = {{(GT - NPG){1'b0}}, sp_o_we};
        assign o_addr = {{((GT - NPG) * AW){1'b0}}, sp_o_addr};
        assign o_mask = {{((GT - NPG) * W){1'b0}}, sp_o_mask};
        assign o_data = {{((GT - NPG) * W * 32){1'b0}}, sp_o_data};
    end else begin : g_full
        assign scale_gre = sp_scale_gre; assign scale_addr = sp_scale_addr;
        assign o_we = sp_o_we; assign o_addr = sp_o_addr; assign o_mask = sp_o_mask; assign o_data = sp_o_data;
    end endgenerate

    wire [IBW-1:0] ib = {i_nout, i_tiles, i_k, i_wsrc, i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs,
                         i_jsh, i_split, i_wcs, i_round, i_obase, i_ots, i_ojs, i_mmode, i_oen, i_amax, i_rmax,
                         i_mbase};
    wire [NT-1:0]   tile_fault;
    wire [NT*TG*32-1:0] xl_t;
    wire [NT-1:0]   go_t;
    wire [NT*IBW-1:0] ib_t;
    ot_qfd_xdvm_fabric #(.AW(AW), .NW(NW), .XCW(XCW), .IL(IL), .NCOL(NCOL), .NH(NH), .TG(TG), .SMIN(SMIN), .SMAX(SMAX),
        .HB(HB), .LEAF_FILL_PIPE(LEAF_FILL_PIPE), .LEAF_BANK_PIPE(LEAF_BANK_PIPE), .REQ_PIPE(REQ_PIPE), .DX(DX), .FILL_LEAD(FILL_LEAD), .TIDM(TIDM), .XOFF(XOFF), .NATIVE_AFFINE(NATIVE_AFFINE),.STATIC_SCHEDULE(STATIC_SCHEDULE),.TAP_MUT(TAP_MUT), .LEAF_MUT(LEAF_MUT),
        .HEAD_MUT(HEAD_MUT)) u_fab (
        .clk(clk), .rst_n(rst_n), .go_acc(go && ready), .ib(ib),
        .xpf_v(xpf_v), .xpf_xbase(xpf_xbase), .xpf_xcs(xpf_xcs), .xpf_xks(xpf_xks), .xpf_split(xpf_split),
        .xpf_k(xpf_k), .xpf_round(xpf_round), .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d),
        .aw_v(aw_v), .aw_a(aw_a), .aw_m(aw_m), .aw_d(aw_d), .go_t(go_t), .ib_t(ib_t), .xl_t(xl_t), .x_fault(x_fault));
    assign tile_xl = xl_t;

    // -- tiles and the tree above them (as ot_qwen_me_array_w12) -----------------------------------------------------
    function automatic integer host_level(input integer tt);
        integer kk;
        begin
            host_level = 0;
            for (kk = 1; kk <= TCUT - LT; kk = kk + 1)
                if ((tt % (1 << kk)) == (1 << (kk - 1)) - 1 && (tt >> kk) < (GT >> (LT + kk)) && host_level == 0)
                    host_level = LT + kk;
        end
    endfunction
    wire [NT*W*32-1:0] lw [LT:TCUT];
    wire [NT-1:0]      lvv [LT:TCUT];
    genvar t, lv, p;
    generate
        for (lv = LT + 1; lv <= TCUT; lv = lv + 1) begin : g_lz
            for (p = (GT >> lv); p < NT; p = p + 1) begin : g_z
                assign lw[lv][p*W*32 +: W*32] = {W*32{1'b0}};
                assign lvv[lv][p] = 1'b0;
            end
        end
        for (t = 0; t < NT; t = t + 1) begin : g_tile
            localparam integer HL = host_level(t);
            localparam integer HK = HL - LT;
            localparam integer HP = (HL > 0) ? (t >> HK) : 0;
            wire [W*32-1:0] na, nb, ny;
            wire            nva, nvy;
            if (HL > 0) begin : g_host
                ot_hdc_delay #(.W(2*W*32), .D(NWS - NREG)) u_nw (.clk(clk), .rst_n(rst_n),
                    .d({lw[HL-1][(2*HP)*W*32 +: W*32], lw[HL-1][(2*HP+1)*W*32 +: W*32]}), .q({na, nb}));
                ot_hdc_delay #(.W(1), .D(NWS - NREG), .RESET(1)) u_nv (.clk(clk), .rst_n(rst_n),
                    .d(lvv[HL-1][2*HP]), .q(nva));
                assign lw[HL][HP*W*32 +: W*32] = ny;
                assign lvv[HL][HP] = nvy;
            end else begin : g_nohost
                assign na = {W*32{1'b0}}; assign nb = {W*32{1'b0}}; assign nva = 1'b0;
            end
            ot_qwen_rom_tile_logic_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .GT(GT), .TG(TG), .SMIN(SMIN),
                .CODE_BANKS(CODE_BANKS), .IREG(IREG), .NREG(NREG), .KV_LOCAL(0), .MEM_EXTRA(0), .BAW(BAW),
                .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .FAST_ISSUE(FAST_ISSUE), .MUL_LAT(MUL_LAT)) u_t (
                .clk(clk), .rst_n(rst_n), .tile_id(t[15:0]), .ib_go(go_t[t]), .ib(ib_t[t*IBW +: IBW]),
                .xl(xl_t[t*TG*32 +: TG*32]),
                .t_out(lw[LT][t*W*32 +: W*32]), .t_vout(lvv[LT][t]),
                .n_a(na), .n_b(nb), .n_va(nva), .n_y(ny), .n_vy(nvy), .fault(tile_fault[t]),
                .rom_ce(t_rom_ce[t*CODE_BANKS +: CODE_BANKS]), .rom_addr(t_rom_addr[t*12 +: 12]),
                .rom_rd(t_rom_rd[t*2*CODE_BANKS*266 +: 2*CODE_BANKS*266]),
                .kvs_r_ce(), .kvs_r_addr(), .kvs_rd({TG*W*8{1'b0}}),
                .kv_re(), .kv_addr(), .kv_q({TG*W*32{1'b0}}));
        end
    endgenerate
    assign t_lvl = lw[TCUT][NPT*W*32-1:0];
    assign fab_fault = |tile_fault;
endmodule

module ot_qfd_xdvm_fabric #(
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer XCW = 12,
    parameter integer IL = 8,
    parameter integer NCOL = 2,
    parameter integer NH = 8,
    parameter integer TG = 4,
    parameter integer SMIN = 3,
    parameter integer SMAX = 5,
    parameter integer HB = 2,
    parameter integer LEAF_FILL_PIPE = 0,
    parameter integer LEAF_BANK_PIPE = 0,
    parameter integer REQ_PIPE = 0,
    parameter integer DX = 10 + LEAF_BANK_PIPE + REQ_PIPE + (NH/2-1)*LEAF_FILL_PIPE,
    parameter integer FILL_LEAD = 2 + (NH/2-1)*LEAF_FILL_PIPE,
    parameter integer TIDM = 1,
    parameter integer XOFF = 3,
    parameter integer NATIVE_AFFINE=0,
    parameter integer STATIC_SCHEDULE=0,
    parameter integer TAP_MUT = 0,
    parameter integer LEAF_MUT = 0,
    parameter integer HEAD_MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go_acc,          // the accepted go (go && ready)
    input  wire [3*NW+13*AW+13-1:0] ib,
    input  wire              xpf_v,
    input  wire [AW-1:0]     xpf_xbase,
    input  wire [XCW-1:0]    xpf_xcs,
    input  wire [XCW-1:0]    xpf_xks,
    input  wire [3:0]        xpf_split,
    input  wire [NW-1:0]     xpf_k,
    input  wire              xpf_round,
    input  wire              sw_v,
    input  wire [AW-1:0]     sw_a,
    input  wire [63:0]       sw_m,
    input  wire [64*32-1:0]  sw_d,
    input  wire              aw_v,
    input  wire [AW-1:0]     aw_a,
    input  wire [15:0]       aw_m,
    input  wire [16*32-1:0]  aw_d,
    output wire [NCOL*2*NH-1:0] go_t,
    output wire [NCOL*2*NH*(3*NW+13*AW+13)-1:0] ib_t,
    output wire [NCOL*2*NH*TG*32-1:0] xl_t,
    output wire              x_fault
);
    localparam integer NT  = NCOL * 2 * NH;
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    localparam integer DESC = 2 + AW + 2 * XCW + 4 + NW + 1;
    localparam integer FW  = DESC + 2 + (AW - 6) + 6 + 64 + 1024;
    localparam integer HW  = 1 + IBW + FW;
    localparam integer CW  = 1 + IBW + 128 + 8;
    // -- the x tap: writes + the accepted go / ib -> the head-row word (one pipeline), HB head-row stages ------------
    wire [HW-1:0]  hw0, he0;
    wire           tap_fault;
    wire [NCOL:0]  fch;                         // fault chain, outermost column first (fch[NCOL] = 0: no outer column)
    ot_qfd_xs_tap #(.AW(AW), .NW(NW), .XCW(XCW),.NATIVE_AFFINE(NATIVE_AFFINE),.STATIC_SCHEDULE(STATIC_SCHEDULE), .MUT(TAP_MUT)) u_tap (.clk(clk), .rst_n(rst_n),
        .xpf_v(xpf_v), .xpf_xbase(xpf_xbase), .xpf_xcs(xpf_xcs), .xpf_xks(xpf_xks), .xpf_split(xpf_split),
        .xpf_k(xpf_k), .xpf_round(xpf_round), .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d),
        .aw_v(aw_v), .aw_a(aw_a), .aw_m(aw_m), .aw_d(aw_d), .gi({ib, go_acc}), .hw(hw0), .he(he0),
        .fw_i(fch[0]), .fe_i(1'b0), .fault(tap_fault));
    // head-row stages: valid bits (go, descriptor valid, data valid) reset, payload not
    localparam [HW-1:0] VM = ({{(HW-1){1'b0}}, 1'b1}) | ({{(HW-1){1'b0}}, 1'b1} << (1 + IBW)) |
                             ({{(HW-1){1'b0}}, 1'b1} << (1 + IBW + DESC));
    wire [HW-1:0]  hv, hp;
    ot_hdc_delay #(.W(HW), .D(HB), .RESET(1)) u_hv (.clk(clk), .rst_n(rst_n), .d(hw0 & VM), .q(hv));
    ot_hdc_delay #(.W(HW), .D(HB)) u_hp (.clk(clk), .rst_n(rst_n), .d(hw0), .q(hp));
    wire [HW-1:0]  hw = (hp & ~VM) | hv;
    assign fch[NCOL] = 1'b0;
    // tile id of (column, head row): rows 0 .. NH-1 = N stations outward (die row NH + s), NH .. 2NH-1 = S stations
    // outward (die row NH - 1 - s); TIDM 1: 16 x block + morton(c mod 4, die row mod 4) (compute_spine.ref_tile_id,
    // smaller blocks when NCOL or 2NH < 4)
    function automatic integer tid(input integer c, input integer r);
        integer dr, bc, br, lbc, lbr, blk, z, p, i;
        begin
            if (TIDM == 0) tid = c * 2 * NH + r;
            else begin
                dr = (r < NH) ? NH + r : NH - 1 - (r - NH);
                bc = (NCOL >= 4) ? 4 : NCOL; br = (2 * NH >= 4) ? 4 : 2 * NH;
                lbc = (bc >= 4) ? 2 : (bc >= 2) ? 1 : 0; lbr = (br >= 4) ? 2 : (br >= 2) ? 1 : 0;
                blk = (c / bc) * (2 * NH / br) + dr / br;
                z = 0; p = 0;
                for (i = 0; i < 2; i = i + 1) begin
                    if (i < lbc) begin z = z | (((c % bc) >> i) & 1) << p; p = p + 1; end
                    if (i < lbr) begin z = z | (((dr % br) >> i) & 1) << p; p = p + 1; end
                end
                tid = bc * br * blk + z;
            end
        end
    endfunction

    // -- columns ---------------------------------------------------------------------------------------------------
    genvar c, j, s, h;
    generate for (c = 0; c < NCOL; c = c + 1) begin : g_col
        wire [CW-1:0] cn, cs;
        wire [1:0]    lw_v, lc_v, lw_ep, lc_ep;
        wire [11:0]   lw_off;
        wire [127:0]  lw_m;
        wire [2047:0] lw_d;
        wire [NH*18-1:0] lw_ctl;
        wire [NH-1:0] lr_v, lr_t, lr_ep, lq_v, lq_bad;
        wire [NH*28-1:0] lr_p;
        wire [NH*64-1:0] lq;
        wire [16*2*NH-1:0] tids;
        for (j = 0; j < 2 * NH; j = j + 1) begin : g_tid
            localparam integer TJ = tid(c, j);
            assign tids[16*j +: 16] = TJ;
        end
        ot_qfd_xhead #(.AW(AW), .NW(NW), .XCW(XCW), .TG(TG), .IL(IL), .NH(NH), .SMIN(SMIN), .SMAX(SMAX), .LEAF_BANK_PIPE(LEAF_BANK_PIPE), .REQ_PIPE(REQ_PIPE), .DX(DX),
            .FILL_LEAD(FILL_LEAD),.NATIVE_AFFINE(NATIVE_AFFINE), .MUT(HEAD_MUT)) u_head (.ck(clk), .rst_n(rst_n), .tids(tids), .fault_i(fch[c+1]),
            .a_d(hw), .a_r(), .b_d(), .b_r(1'b1),
            .n_d(cn), .n_r(1'b1), .s_d(cs), .s_r(1'b1),
            .lw_v(lw_v), .lw_ep(lw_ep), .lw_off(lw_off), .lw_m(lw_m), .lw_d(lw_d), .lw_ctl(lw_ctl),
            .lc_v(lc_v), .lc_ep(lc_ep), .lr_v(lr_v), .lr_t(lr_t), .lr_ep(lr_ep), .lr_p(lr_p),
            .lq(lq), .lq_v(lq_v), .lq_bad(lq_bad), .fault(fch[c]));
        // two write chains (N: leaves 0 .. NH/2-1, S: NH/2 .. NH-1), each leaf one pin-register stage of the chain
        localparam integer NCH = NH / 2;
        for (h = 0; h < 2; h = h + 1) begin : g_ch
            wire          cv [0:NCH];
            wire          cep [0:NCH];
            wire          wv [0:NCH];
            wire          wep [0:NCH];
            wire [5:0]    woff [0:NCH];
            wire [63:0]   wm [0:NCH];
            wire [1023:0] wd [0:NCH];
            wire [NCH*18-1:0] wc [0:NCH];
            assign cv[0] = lc_v[h]; assign cep[0] = lc_ep[h]; assign wv[0] = lw_v[h]; assign wep[0] = lw_ep[h];
            assign woff[0] = lw_off[6*h +: 6]; assign wm[0] = lw_m[64*h +: 64]; assign wd[0] = lw_d[1024*h +: 1024]; assign wc[0] = lw_ctl[h*NCH*18 +: NCH*18];
            for (j = 0; j < NCH; j = j + 1) begin : g_leaf
                localparam integer LF = h * NCH + j;
                if(LEAF_BANK_PIPE!=0 && LEAF_FILL_PIPE!=0 && NH==8 && LEAF_MUT==0)begin : g_fixed_leaf
                    qfd_xs_leaf_banked u_leaf (.clk(clk), .rst_n(rst_n),
                    .w_v(wv[j]), .w_ep(wep[j]), .w_off(woff[j]), .w_m(wm[j]), .w_d(wd[j]), .w_ctl(wc[j]),
                    .c_v(cv[j]), .c_ep(cep[j]),
                    .wo_v(wv[j+1]), .wo_ep(wep[j+1]), .wo_off(woff[j+1]), .wo_m(wm[j+1]), .wo_d(wd[j+1]), .wo_ctl(wc[j+1]),
                    .co_v(cv[j+1]), .co_ep(cep[j+1]),
                    .r_v(lr_v[LF]), .r_t(lr_t[LF]), .r_ep(lr_ep[LF]), .r_p(lr_p[28*LF +: 28]),
                    .q_v(lq_v[LF]), .q(lq[64*LF +: 64]), .q_bad(lq_bad[LF]));
                end else begin : g_parameter_leaf
                ot_qfd_xs_leaf #(.FILL_PIPE(LEAF_FILL_PIPE), .BANK_PIPE(LEAF_BANK_PIPE), .NCH(NCH), .MUT(LEAF_MUT)) u_leaf (.clk(clk), .rst_n(rst_n),
                    .w_v(wv[j]), .w_ep(wep[j]), .w_off(woff[j]), .w_m(wm[j]), .w_d(wd[j]), .w_ctl(wc[j]),
                    .c_v(cv[j]), .c_ep(cep[j]),
                    .wo_v(wv[j+1]), .wo_ep(wep[j+1]), .wo_off(woff[j+1]), .wo_m(wm[j+1]), .wo_d(wd[j+1]), .wo_ctl(wc[j+1]),
                    .co_v(cv[j+1]), .co_ep(cep[j+1]),
                    .r_v(lr_v[LF]), .r_t(lr_t[LF]), .r_ep(lr_ep[LF]), .r_p(lr_p[28*LF +: 28]),
                    .q_v(lq_v[LF]), .q(lq[64*LF +: 64]), .q_bad(lq_bad[LF]));
                end
            end
        end
        for (h = 0; h < 2; h = h + 1) begin : g_cor
            wire [CW-1:0] chain [0:NH];
            assign chain[0] = (h == 0) ? cn : cs;
            for (s = 0; s < NH; s = s + 1) begin : g_st
                localparam integer T = tid(c, h * NH + s);
                wire [IBW+128:0] tap;
                ot_qfd_xcst #(.AW(AW), .NW(NW), .IL(IL), .XOFF(XOFF)) u_st (.ck(clk), .rst_n(rst_n), .sidx(s[2:0]),
                    .a_d(chain[s]), .a_r(), .b_d(chain[s+1]), .b_r(1'b1), .tap_d(tap));
                // equalise to the corridor's depth (the die's tiles run in lockstep)
                wire [IBW+128:0] tq;
                wire             tgq;
                ot_hdc_delay #(.W(IBW + 128), .D(NH - 1 - s)) u_eq (.clk(clk), .rst_n(rst_n), .d(tap[IBW+128:1]), .q(tq[IBW+128:1]));
                ot_hdc_delay #(.W(1), .D(NH - 1 - s), .RESET(1)) u_eqg (.clk(clk), .rst_n(rst_n), .d(tap[0]), .q(tgq));
                assign go_t[T] = tgq;
                assign ib_t[T*IBW +: IBW] = tq[IBW:1];
                assign xl_t[T*TG*32 +: TG*32] = tq[IBW+128 -: 128];
            end
        end
    end endgenerate
    assign x_fault = tap_fault;                 // the columns' faults reach the tap along the head row's fault chain

endmodule
