`timescale 1ns/1ps
`default_nettype none
// ot_hgi_vm_tunit: the HGI VM block (ot_hgi_vm_unit NC 8 WP 32 WDIRECT 1, die instance hfd_hgi_vm4) rebuilt as a
// floorplanned, pipelined tile array (el1011-hbm-hcvm/vm, 2026-10-11).  Same ports as ot_hgi_vm_unit (drop-in master);
// the RP / W2 / AP features are not built (traps unless RP = W2 = AP = 0).
//
// Why (textbook audit of the flat unit, hgi_vm_{a,b}-cf6920af3 / hgi_vm-fb{a,b}-0dbd56701 PREROUTE_MARGIN at -2.1 ns,
// 23k endpoints < -750 ps): the flat unit decides every bank's grant in one cycle from 8 station heads spread over the
// top face and drives the granted 312-b encoded word to a bank up to ~1.5 mm away in the same cycle (28 repeaters on the
// worst path), muxes 32 banks' macro outputs into 8 clients across the die in one cycle, splits a bank's two macros up to
// 1.2 mm apart, puts the async reset of 11.5k flops (incl. 9k data pin flops) on one port net.
//
// Physical spec (floorplan hgi_vm_place_ta.tcl, slot 1399.656 x 1080 unchanged):
//   * 7 macro columns x 10 macro rows, channels >= 20 um; bank b = macros lo/hi stacked in ONE column (rows 2p, 2p+1).
//     Group L (cols 0-2) = banks 0-14, group M (col 3, rows 0-3) = banks 15-16, group R (cols 4-6) = banks 17-31: the
//     wide lanes 0-15 enter on the left face, 16-31 on the right face, so a lane only crosses its own half.
//   * hub (stations + arbiter + tag line + response merge) in column 3 above group M (~x 700, y 400-900): every bus
//     leaves the hub through >= 1 relay register per <= ~450 um.
//   * client requests: cq pin flop (q0, top face) -> relay (q1) -> hub stations.  Responses: hub (hr) -> relay (crr) ->
//     cr pin flop.  Status likewise.
//   * down tree: hub grant register s0 (8 client lanes {row, wdata, word mask} + per-bank {rv, rcid, wv, wcid}) ->
//     per-group relay r1 (one kept copy per group L / M / R) -> per-bank select + SECDED encode cs (column node) ->
//     per-bank macro input registers (m_*, next to the bank's macros).
//   * wide lanes: wq pin flop p0 (face) -> bank hit/dup bits relayed h1-h3 to the hub; the lane's data rides a 6-deep
//     relay line w1..w6 (encoded in w6) so it reaches its bank's m_* registers the cycle the hub's decision does.
//   * read return: macro output capture (raw, no logic before it) -> decode (d) -> per-bank relay (u) -> per-group
//     per-client OR merge (hm; a client has at most one read per slot) -> hub response register.
//   * reset: rst_n drives only ot_rst_relay (8 regional copies); data / pin / relay data flops carry no reset.
// Behaviour: the hub is a cycle-exact copy of ot_hgi_vm_unit's control (stations, grants, busy, mask / range / protocol
// faults) seeing cq 2 cycles and wq 3 cycles late; every bank access happens 3 cycles after the reference's.  Outputs:
// cr = the reference's 7 cycles later (payload zero when not valid), status 8 cycles later, wq_done 4 cycles later
// (tb/tb_hgi_vm_tunit_lock.sv locksteps against tb/ot_hgi_vm_unit_ref.sv with those shifts).  Reset release +3 cycles
// (ot_rst_relay).  Added cycles: request -> response +7, wq -> wq_done +7 (vs the reference's 3).
module ot_hgi_vm_tunit #(
    parameter integer NC = 8,
    parameter integer WP = 32,
    parameter integer WDIRECT = 1,
    parameter integer RP = 0,
    parameter integer W2 = 0,
    parameter integer LQ = 8,
    parameter integer QMACRO = 0,
    parameter integer AP = 0,
    parameter integer APD = 16,
    parameter integer APC = 1,
    parameter integer APS = 8,
    parameter integer MUT = 0     // 2 bank index from sector[5:1], 3 responses one slot early, 4 wide word mask ignored,
                                  // 1 no correction, 12 no address range check
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NC*338-1:0] cq,
    output reg  [NC*274-1:0] cr,
    output reg  [18:0]       status,
    input  wire [WP*(280+AP)-1:0] wq,
    output wire [WP-1:0]     wq_done,
    output wire [WP-1:0]     wq_rdy,
    output wire [8*278-1:0]  ap_q,
    input  wire [7:0]        ap_cr,
    input  wire [7:0]        ap_done,
    input  wire [(RP>0?RP:1)*16-1:0]  rq,
    output wire [(RP>0?RP:1)-1:0]     rq_cr,
    output wire [(RP>0?RP:1)*257-1:0] rr,
    input  wire [(W2>0?W2:1)*280-1:0] w2q,
    output wire [(W2>0?W2:1)-1:0]     w2q_cr,
    output wire [(W2>0?W2:1)-1:0]     w2q_done
);
    localparam integer NB = 32, OUT = 4, LW = 274;   // lane = {row 10, wdata 256, word mask 8}
    generate if (NC < 1 || NC > 8 || WP != 32 || WDIRECT != 1 || RP != 0 || W2 != 0 || AP != 0) begin : g_cfg_trap
        ot_hgi_vm_tunit_builds_only_NC_le8_WP32_WDIRECT1_RP0_W20_AP0 u_trap ();
    end endgenerate
    assign wq_rdy = {WP{1'b1}}; assign ap_q = '0; assign rq_cr = '0; assign rr = '0; assign w2q_cr = '0; assign w2q_done = '0;

    // bank -> group (0 L, 1 M, 2 R) and column (floorplan)
    function automatic integer grp(input integer b); grp = (b < 15) ? 0 : (b < 17) ? 1 : 2; endfunction

    // ---------------------------------------------------------------- (39,32) SECDED, identical to ot_hgi_vm_core
    function automatic [6:0] colv(input integer i);
        integer a, b, c, n; reg [6:0] v;
        begin
            n = 0; v = 7'd0;
            for (a = 0; a < 7; a = a + 1)
                for (b = a + 1; b < 7; b = b + 1)
                    for (c = b + 1; c < 7; c = c + 1) begin
                        if (n == i) v = (7'd1 << a) | (7'd1 << b) | (7'd1 << c);
                        n = n + 1;
                    end
            colv = v;
        end
    endfunction
    function automatic [32*7-1:0] cols_all(input integer dummy);
        integer i; reg [32*7-1:0] r;
        begin r = '0; for (i = 0; i < 32; i = i + 1) r[i*7 +: 7] = colv(i); cols_all = r; end
    endfunction
    localparam [32*7-1:0] COLS = cols_all(0);
    function automatic [7*32-1:0] rows_all(input integer dummy);
        integer i, j; reg [7*32-1:0] r;
        begin r = '0; for (j = 0; j < 7; j = j + 1) for (i = 0; i < 32; i = i + 1) r[j*32 + i] = COLS[i*7 + j]; rows_all = r; end
    endfunction
    localparam [7*32-1:0] ROWM = rows_all(0);
    function automatic [6:0] chk(input [31:0] d);
        integer j; reg [6:0] c;
        begin for (j = 0; j < 7; j = j + 1) c[j] = ^(d & ROWM[j*32 +: 32]); chk = c; end
    endfunction
    function automatic [311:0] enc8(input [255:0] d);
        integer k; reg [311:0] r;
        begin for (k = 0; k < 8; k = k + 1) r[k*39 +: 39] = {chk(d[k*32 +: 32]), d[k*32 +: 32]}; enc8 = r; end
    endfunction
    function automatic [33:0] dec(input [38:0] w);
        reg [6:0] syn; integer i; reg [31:0] d; reg hit;
        begin
            d = w[31:0]; syn = chk(w[31:0]) ^ w[38:32]; hit = 1'b0;
            if (syn != 7'd0) begin
                for (i = 0; i < 32; i = i + 1) if (syn == COLS[i*7 +: 7]) begin d[i] = ~d[i]; hit = 1'b1; end
                if (syn == 7'd1 || syn == 7'd2 || syn == 7'd4 || syn == 7'd8 || syn == 7'd16 || syn == 7'd32 || syn == 7'd64) hit = 1'b1;
            end
            dec = {(syn != 7'd0) && !hit, (syn != 7'd0) && hit, (MUT == 1) ? w[31:0] : d};
        end
    endfunction

    // ---------------------------------------------------------------- regional reset relay
    // regions: 0 hub, 1 top pin band, 2 left face, 3 right face, 4 group L banks, 5 group M banks, 6 group R banks,
    // 7 return tree
    wire [7:0] rn;
    ot_rst_relay #(.REGIONS(8), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rn));

    // ---------------------------------------------------------------- client pin flops (top face) and relay
    reg [NC-1:0] q0_v, q1_v; reg [NC*337-1:0] q0_d, q1_d;
    always @(posedge clk or negedge rn[1])
        if (!rn[1]) q0_v <= '0; else for (integer c = 0; c < NC; c = c + 1) q0_v[c] <= cq[c*338 + 337];
    always @(posedge clk) for (integer c = 0; c < NC; c = c + 1) q0_d[c*337 +: 337] <= cq[c*338 +: 337];
    always @(posedge clk or negedge rn[0]) if (!rn[0]) q1_v <= '0; else q1_v <= q0_v;
    always @(posedge clk) q1_d <= q0_d;

    // ---------------------------------------------------------------- hub: stations (ot_hgi_vm_unit's, fed from q1)
    wire [NC-1:0] h_v, ovf, pk_rng; wire [NC*337-1:0] h_q; reg [NC-1:0] acc;
    genvar gc;
    for (gc = 0; gc < NC; gc = gc + 1) begin : g_st
        reg [336:0] e0, e1, e2, e3; reg rflt;
        reg [1:0] sh, stl; reg [2:0] sn;
        wire push = q1_v[gc];
        wire [336:0] qd = q1_d[gc*337 +: 337];
        wire rng = (MUT != 12) && (qd[324 +: 12] != 12'd0);
        wire [336:0] cqe = rng ? {qd[48 +: 289], 32'd0, qd[0 +: 16]} : qd;
        wire pop = h_v[gc] && acc[gc];
        assign ovf[gc] = push && sn == 3'd4 && !pop;
        wire wr = push && !ovf[gc];
        assign h_v[gc] = sn != 3'd0;
        assign h_q[gc*337 +: 337] = (sh == 2'd0) ? e0 : (sh == 2'd1) ? e1 : (sh == 2'd2) ? e2 : e3;
        assign pk_rng[gc] = rflt;
        always @(posedge clk) begin
            if (wr && stl == 2'd0) e0 <= cqe;
            if (wr && stl == 2'd1) e1 <= cqe;
            if (wr && stl == 2'd2) e2 <= cqe;
            if (wr && stl == 2'd3) e3 <= cqe;
        end
        always @(posedge clk or negedge rn[0])
            if (!rn[0]) begin sh <= 2'd0; stl <= 2'd0; sn <= 3'd0; rflt <= 1'b0; end
            else begin
                if (push && rng) rflt <= 1'b1;
                if (wr) stl <= stl + 2'd1;
                if (pop) sh <= sh + 2'd1;
                sn <= sn + {2'd0, wr} - {2'd0, pop};
            end
    end

    // ---------------------------------------------------------------- hub: the core's grant logic (ot_hgi_vm_core, RP = W2 = 0)
    wire          c_we   [0:NC-1];
    wire [14:0]   c_sec  [0:NC-1];
    wire [4:0]    c_bank [0:NC-1];
    wire [7:0]    c_wm   [0:NC-1];
    wire          c_mf   [0:NC-1];
    for (gc = 0; gc < NC; gc = gc + 1) begin : g_c
        wire [336:0] q = h_q[gc*337 +: 337];
        wire [31:0] bm = q[47:16];
        assign c_sec[gc] = q[323:309];
        assign c_we[gc]  = q[336];
        assign c_bank[gc] = (MUT == 2) ? c_sec[gc][5:1] : c_sec[gc][4:0];
        for (genvar k = 0; k < 8; k = k + 1) begin : g_w
            assign c_wm[gc][k] = &bm[k*4 +: 4];
        end
        assign c_mf[gc] = |(bm & ~{{4{c_wm[gc][7]}}, {4{c_wm[gc][6]}}, {4{c_wm[gc][5]}}, {4{c_wm[gc][4]}},
                                   {4{c_wm[gc][3]}}, {4{c_wm[gc][2]}}, {4{c_wm[gc][1]}}, {4{c_wm[gc][0]}}});
    end
    wire [NB-1:0] wb_hit, wb_dup;                          // the wide lanes' bank hits, relayed from the faces (h3)
    reg [NC-1:0] busy; reg [NC-1:0][2:0] ocnt; reg [NC-1:0] a1, a2, a3, a4;
    reg [NC-1:0] gr_r [0:NB-1]; reg [NC-1:0] gr_w [0:NB-1];
    always @* begin
        for (integer ab = 0; ab < NB; ab = ab + 1) begin
            gr_r[ab] = {NC{1'b0}}; gr_w[ab] = {NC{1'b0}};
            for (integer ac = NC - 1; ac >= 0; ac = ac - 1) begin
                if (h_v[ac] && !busy[ac] && c_bank[ac] == ab && !c_we[ac]) gr_r[ab] = {NC{1'b0}} | ({{(NC-1){1'b0}}, 1'b1} << ac);
                if (h_v[ac] && !busy[ac] && c_bank[ac] == ab &&  c_we[ac] && !wb_hit[ab]) gr_w[ab] = {NC{1'b0}} | ({{(NC-1){1'b0}}, 1'b1} << ac);
            end
        end
        acc = {NC{1'b0}};
        for (integer ab = 0; ab < NB; ab = ab + 1) acc = acc | gr_r[ab] | gr_w[ab];
    end
    // busy / outstanding: the reference pops a response exactly 4 edges after its grant (rsp_r = 1), so pop = acc 4 back
    reg proto, mfault, wlc;
    always @(posedge clk or negedge rn[0])
        if (!rn[0]) begin
            busy <= '0; a1 <= '0; a2 <= '0; a3 <= '0; a4 <= '0; proto <= 1'b0; mfault <= 1'b0; wlc <= 1'b0;
            for (integer c = 0; c < NC; c = c + 1) ocnt[c] <= 3'd0;
        end else begin
            a1 <= acc; a2 <= a1; a3 <= a2; a4 <= a3;
            for (integer c = 0; c < NC; c = c + 1) begin
                ocnt[c] <= ocnt[c] + {2'd0, acc[c]} - {2'd0, a4[c]};
                busy[c] <= (ocnt[c] + {2'd0, acc[c]} - {2'd0, a4[c]}) >= 3'(OUT);
            end
            if (|ovf) proto <= 1'b1;
            if (|wb_dup) wlc <= 1'b1;
            for (integer ab = 0; ab < NB; ab = ab + 1)
                for (integer c = 0; c < NC; c = c + 1) if (gr_w[ab][c] && c_mf[c]) mfault <= 1'b1;
        end
    // grant register s0: the 8 client lanes + per-bank {rv, rcid 3, wv, wcid 3}
    function automatic [2:0] oh2i(input [7:0] oh);
        integer i; reg [2:0] r; begin r = 3'd0; for (i = 0; i < 8; i = i + 1) if (oh[i]) r = 3'(i); oh2i = r; end
    endfunction
    reg [NC*LW-1:0] s0_l; reg [NB*8-1:0] s0_g;
    always @(posedge clk)
        for (integer c = 0; c < NC; c = c + 1) s0_l[c*LW +: LW] <= {c_sec[c][14:5], h_q[c*337 + 48 +: 256], c_wm[c]};
    always @(posedge clk or negedge rn[0])
        if (!rn[0]) s0_g <= '0;
        else for (integer ab = 0; ab < NB; ab = ab + 1)
            s0_g[ab*8 +: 8] <= {|gr_r[ab], oh2i(8'(gr_r[ab])), |gr_w[ab], oh2i(8'(gr_w[ab]))};
    // tag line: {v, we, tag} from the grant to the response register (9 stages)
    localparam integer TLN = 9;
    reg [TLN-1:0][NC-1:0] tl_v, tl_we; reg [TLN-1:0][NC*16-1:0] tl_tag;
    always @(posedge clk or negedge rn[0])
        if (!rn[0]) for (integer s = 0; s < TLN; s = s + 1) tl_v[s] <= '0;
        else begin tl_v[0] <= acc; for (integer s = 1; s < TLN; s = s + 1) tl_v[s] <= tl_v[s-1]; end
    always @(posedge clk) begin
        for (integer c = 0; c < NC; c = c + 1) begin tl_we[0][c] <= c_we[c]; tl_tag[0][c*16 +: 16] <= h_q[c*337 +: 16]; end
        for (integer s = 1; s < TLN; s = s + 1) begin tl_we[s] <= tl_we[s-1]; tl_tag[s] <= tl_tag[s-1]; end
    end

    // ---------------------------------------------------------------- down tree: one kept relay copy per group
    wire [NC*LW-1:0] r1_l [0:2]; wire [NB*8-1:0] r1_g [0:2];
    for (genvar g = 0; g < 3; g = g + 1) begin : g_r1
        (* keep = "true" *) reg [NC*LW-1:0] l; (* keep = "true" *) reg [NB*8-1:0] gr;
        always @(posedge clk) l <= s0_l;
        always @(posedge clk or negedge rn[0]) if (!rn[0]) gr <= '0; else gr <= s0_g;
        assign r1_l[g] = l; assign r1_g[g] = gr;
    end

    // ---------------------------------------------------------------- wide lanes (faces): pin flop, hit relay, data line, done
    localparam integer WLN = 6;                            // data line depth: p0 -> w1..w6 -> m_* (= h1..h3 + hub + s0 + r1 + cs)
    localparam integer DNN = 9;                            // done: p0 -> d1..d9 (the write is in the macro at d8)
    wire [NB-1:0] w6_hit; wire [NB*10-1:0] w6_row; wire [NB*312-1:0] w6_enc; wire [NB*8-1:0] w6_wm;
    genvar gl;
    for (gl = 0; gl < NB; gl = gl + 1) begin : g_wl
        localparam integer RF = (gl < 16) ? 2 : 3;          // face reset region
        reg p0_v; reg [279:0] p0_d;
        always @(posedge clk or negedge rn[RF]) if (!rn[RF]) p0_v <= 1'b0; else p0_v <= wq[gl*280 + 279];
        always @(posedge clk) p0_d <= wq[gl*280 +: 280];
        wire hit = p0_v && p0_d[264 +: 5] == 5'(gl), dup = p0_v && p0_d[264 +: 5] != 5'(gl);
        reg [2:0] hh, hd;                                  // h1..h3 (hit, dup) toward the hub
        reg [DNN-1:0] dn;
        always @(posedge clk or negedge rn[RF])
            if (!rn[RF]) begin hh <= '0; hd <= '0; dn <= '0; end
            else begin hh <= {hh[1:0], hit}; hd <= {hd[1:0], dup}; dn <= {dn[DNN-2:0], p0_v}; end
        assign wb_hit[gl] = hh[2]; assign wb_dup[gl] = hd[2];
        assign wq_done[gl] = dn[DNN-1];
        // data line {hit, row 10, wdata 256, mask 8}; the last stage carries the encoded word
        reg [WLN-2:0] wv; reg [WLN-2:0][273:0] wd;
        reg w6h; reg [9:0] w6r; reg [311:0] w6e; reg [7:0] w6m;
        always @(posedge clk or negedge rn[RF])
            if (!rn[RF]) begin wv <= '0; w6h <= 1'b0; end
            else begin wv <= {wv[WLN-3:0], hit}; w6h <= wv[WLN-2]; end
        always @(posedge clk) begin
            wd[0] <= {p0_d[264 + 5 +: 10], p0_d[8 +: 256], p0_d[7:0]};
            for (integer s = 1; s < WLN - 1; s = s + 1) wd[s] <= wd[s-1];
            w6r <= wd[WLN-2][273:264]; w6e <= enc8(wd[WLN-2][263:8]); w6m <= wd[WLN-2][7:0];
        end
        assign w6_hit[gl] = w6h; assign w6_row[gl*10 +: 10] = w6r; assign w6_enc[gl*312 +: 312] = w6e; assign w6_wm[gl*8 +: 8] = w6m;
    end

    // ---------------------------------------------------------------- bank tiles
    wire [NB-1:0] u_v; wire [NB*3-1:0] u_c; wire [NB*256-1:0] u_d; wire [NB*4-1:0] u_ce; wire [NB-1:0] u_ue;
    genvar gb;
    for (gb = 0; gb < NB; gb = gb + 1) begin : g_bk
        localparam integer G = grp(gb), RB = 4 + grp(gb);
        wire [7:0] gi = r1_g[G][gb*8 +: 8];
        wire [LW-1:0] lr = r1_l[G][gi[6:4]*LW +: LW], lw = r1_l[G][gi[2:0]*LW +: LW];
        // column-node select + encode
        reg cs_re, cs_we; reg [2:0] cs_rc; reg [9:0] cs_ra, cs_wa; reg [311:0] cs_wd; reg [7:0] cs_wm;
        always @(posedge clk or negedge rn[RB]) if (!rn[RB]) begin cs_re <= 1'b0; cs_we <= 1'b0; end
            else begin cs_re <= gi[7]; cs_we <= gi[3]; end
        always @(posedge clk) begin
            cs_rc <= gi[6:4]; cs_ra <= lr[LW-1 -: 10];
            cs_wa <= lw[LW-1 -: 10]; cs_wd <= enc8(lw[263:8]); cs_wm <= lw[7:0];
        end
        // macro input registers (next to the macros); the wide lane writes when it hits (the hub kept clients off)
        reg m_re, m_we, rp1; reg [9:0] m_ra, m_wa; reg [311:0] m_wd; reg [7:0] m_wm; reg [2:0] rc1;
        always @(posedge clk or negedge rn[RB]) if (!rn[RB]) begin m_re <= 1'b0; m_we <= 1'b0; rp1 <= 1'b0; end
            else begin m_re <= cs_re; m_we <= cs_we | w6_hit[gb]; rp1 <= cs_re; end
        always @(posedge clk) begin
            m_ra <= cs_ra; rc1 <= cs_rc;
            m_wa <= w6_hit[gb] ? w6_row[gb*10 +: 10] : cs_wa;
            m_wd <= w6_hit[gb] ? w6_enc[gb*312 +: 312] : cs_wd;
            m_wm <= w6_hit[gb] ? (w6_wm[gb*8 +: 8] | {8{MUT == 4}}) : cs_wm;
        end
        wire [311:0] wme;
        for (genvar w = 0; w < 8; w = w + 1) begin : g_wm
            assign wme[w*39 +: 39] = {39{m_wm[w]}};
        end
        wire [511:0] wdx = {200'd0, m_wd}, wmx = {200'd0, wme}; wire [511:0] rd;
        ot_sram_1r1w_1024x256_m2_r2c2 u_lo (.clk(clk), .r_ce_in(m_re), .r_addr_in(m_ra), .rd_out(rd[255:0]),
            .w_ce_in(m_we), .w_addr_in(m_wa), .wd_in(wdx[255:0]), .w_mask_in(wmx[255:0]),
            .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_1024x256_m2_r2c2 u_hi (.clk(clk), .r_ce_in(m_re), .r_addr_in(m_ra), .rd_out(rd[511:256]),
            .w_ce_in(m_we), .w_addr_in(m_wa), .wd_in(wdx[511:256]), .w_mask_in(wmx[511:256]),
            .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        // read return: macro edge (rp2) -> raw capture (no logic before it) -> decode (d) -> relay (u)
        reg rp2, rp3, d_v, uv; reg [2:0] rc2, rc3, d_c, uc; reg [311:0] raw; reg [255:0] d_d, ud; reg [3:0] d_ce, uce; reg d_ue, uue;
        always @(posedge clk or negedge rn[RB]) if (!rn[RB]) begin rp2 <= 1'b0; rp3 <= 1'b0; d_v <= 1'b0; end
            else begin rp2 <= rp1; rp3 <= rp2; d_v <= rp3; end
        always @(posedge clk or negedge rn[7]) if (!rn[7]) uv <= 1'b0; else uv <= d_v;
        always @(posedge clk) begin
            rc2 <= rc1; rc3 <= rc2; d_c <= rc3;
            if (rp2) raw <= rd[311:0];
            begin : dc
                reg [33:0] x; reg [3:0] n; reg u;
                n = 4'd0; u = 1'b0;
                for (integer q = 0; q < 8; q = q + 1) begin
                    x = dec(raw[q*39 +: 39]); d_d[q*32 +: 32] <= x[31:0];
                    n = n + {3'd0, x[32]}; u = u | x[33];
                end
                d_ce <= rp3 ? n : 4'd0; d_ue <= rp3 && u;
            end
            uc <= d_c; ud <= d_d; uce <= d_v ? d_ce : 4'd0; uue <= d_v && d_ue;
        end
        assign u_v[gb] = uv; assign u_c[gb*3 +: 3] = uc; assign u_d[gb*256 +: 256] = ud;
        assign u_ce[gb*4 +: 4] = uce; assign u_ue[gb] = uue;
    end

    // ---------------------------------------------------------------- per-group per-client merge (hm) -> hub response
    reg [2:0][NC*256-1:0] hm_d; reg [2:0][7:0] hm_ce; reg [2:0] hm_ue;
    always @(posedge clk) begin
        for (integer g = 0; g < 3; g = g + 1) begin : mg
            reg [NC*256-1:0] o; reg [7:0] s; reg e;
            o = '0; s = 8'd0; e = 1'b0;
            for (integer b = 0; b < NB; b = b + 1) if (grp(b) == g) begin
                for (integer c = 0; c < NC; c = c + 1)
                    if (u_v[b] && u_c[b*3 +: 3] == 3'(c)) o[c*256 +: 256] = o[c*256 +: 256] | u_d[b*256 +: 256];
                s = s + {4'd0, u_ce[b*4 +: 4]}; e = e | u_ue[b];
            end
            hm_d[g] <= o; hm_ce[g] <= s; hm_ue[g] <= e;
        end
    end
    localparam integer TLX = (MUT == 3) ? TLN - 2 : TLN - 1;
    reg [NC*274-1:0] hr, crr; reg [NC-1:0] hr_v, crr_v; reg [15:0] ce_h; reg ue_h;
    always @(posedge clk or negedge rn[0])
        if (!rn[0]) begin hr_v <= '0; ce_h <= 16'd0; ue_h <= 1'b0; end
        else begin
            hr_v <= tl_v[TLX];
            ce_h <= ce_h + {8'd0, hm_ce[0]} + {8'd0, hm_ce[1]} + {8'd0, hm_ce[2]};
            if (|hm_ue) ue_h <= 1'b1;
        end
    always @(posedge clk)
        for (integer c = 0; c < NC; c = c + 1)
            hr[c*274 +: 274] <= tl_v[TLX][c] ? {1'b0, tl_tag[TLX][c*16 +: 16], tl_we[TLX][c],
                                               tl_we[TLX][c] ? 256'd0 : (hm_d[0][c*256 +: 256] | hm_d[1][c*256 +: 256] | hm_d[2][c*256 +: 256])}
                                             : 274'd0;
    // status: the reference's sticky faults delayed to line up with ce / ue (6 edges), then relay + pin flop
    localparam integer FDN = 6;
    reg [FDN-1:0][1:0] fd; reg [18:0] st_h, st_r;
    always @(posedge clk or negedge rn[0])
        if (!rn[0]) begin for (integer s = 0; s < FDN; s = s + 1) fd[s] <= 2'd0; st_h <= 19'd0; end
        else begin
            fd[0] <= {proto | wlc | (|pk_rng), mfault};
            for (integer s = 1; s < FDN; s = s + 1) fd[s] <= fd[s-1];
            st_h <= {fd[FDN-1], ue_h, ce_h};
        end
    always @(posedge clk or negedge rn[1])
        if (!rn[1]) begin crr_v <= '0; st_r <= 19'd0; status <= 19'd0; for (integer c = 0; c < NC; c = c + 1) cr[c*274 + 273] <= 1'b0; end
        else begin
            crr_v <= hr_v; st_r <= st_h; status <= st_r;
            for (integer c = 0; c < NC; c = c + 1) cr[c*274 + 273] <= crr_v[c];
        end
    always @(posedge clk) begin
        crr <= hr;
        for (integer c = 0; c < NC; c = c + 1) cr[c*274 +: 273] <= crr[c*274 +: 273];
    end
endmodule
`default_nettype wire
