`timescale 1ns/1ps
`default_nettype none
// ot_hgi_vm_tunit: the HGI VM block (ot_hgi_vm_unit) rebuilt as a floorplanned, pipelined tile array
// (el1011-hbm-hcvm/vm, 2026-10-11).  Same ports as ot_hgi_vm_unit (drop-in master).  Builds at the die VM's
// configuration (ot_hgi_vm_die u_vmu: NC 9, WP 32, WDIRECT 1, RP 96, W2 96, LQ 32, AP 1) and at the reduced one
// (NC <= 8, RP = W2 = AP = 0, the earlier hfd_hgi_vm4 instance).
//
// Why (textbook audit of the flat unit, hgi_vm_{a,b}-cf6920af3 / hgi_vm-fb{a,b}-0dbd56701 PREROUTE_MARGIN at -2.1 ns,
// 23k endpoints < -750 ps): the flat unit decides every bank's grant in one cycle from the station heads and the 96
// lane-queue heads spread over the block and drives the granted word to a bank up to ~1.5 mm away in the same cycle,
// muxes 32 banks' macro outputs into the clients across the die in one cycle, splits a bank's two macros up to 1.2 mm
// apart, puts the async reset of all flops (incl. the data pin flops) on one port net.
//
// Physical spec (floorplan hgi_vm_place_ta.tcl):
//   * bank tile b = the bank's two VM macros stacked in one column + its own lane endpoints: the RP read lanes
//     g*32+b (pin flop, local LQ+8-deep row queue in flops), the W2 write lanes g*32+b (pin flop, local 64-deep SRAM
//     queue, one 64x512 macro a lane, raw capture flop at its output), the per-bank select / SECDED encode stages and
//     the read capture / decode.  Banks 0-14 left group, 15-16 middle, 17-31 right (DMA lanes 0-15 on the left face,
//     16-31 on the right face).
//   * hub (stations + arbiter + SHADOW lane-queue state + tag line + response merge) in the middle column; every bus
//     leaves the hub through >= 1 relay register per <= ~450 um.  The hub keeps only 1-bit-a-entry shadows of the lane
//     queues (occupancy, head bank-match): the lane data never travels to the hub.
//   * aperture block (AP): the 32 DMA lanes' aperture queues + the 8-way bank-keyed arbiter beside the hub, fed by a
//     3-stage relay line from each face; ap_q leaves through an output flop.
//   * down tree: hub decision register s0 (client lanes {row, wdata, mask} + per bank {client rd, client wr, lane rd,
//     lane wr}) -> per-group relay r1 (one kept copy per group) -> bank: the lane queues pop on r1 (the W2 SRAM read
//     is issued from r1, captured raw), client data select + encode (cs) -> c2 -> macro input registers m_*.
//   * reset: rst_n drives only ot_rst_relay (9 regional copies); data / pin / relay data flops carry no reset.
// Behaviour: the hub is a cycle-exact copy of ot_hgi_vm_unit's control (stations, grants, ages, busy, lane queues,
// aperture, faults) seeing cq 2 cycles, wq / rq / w2q 3 cycles and ap_cr / ap_done 1 cycle later than the unit; every
// bank access happens 4 + XR cycles after the unit's.  Outputs vs the unit fed those delayed inputs: cr +8+2XR (payload
// zero when not valid), status +9+2XR, wq_done +4+XR, wq_rdy +2, ap_q +1, rq_cr +2+XR, rr +4+XR (data valid with v),
// w2q_cr +2+XR, w2q_done +4+XR (XR = 1 at the die: cr +10, status +11, wq_done / rr / w2q_done +5, rq_cr / w2q_cr +3)
// (tb/tb_hgi_vm_tunit_full_lock.sv locksteps against the current ot_hgi_vm_unit with those shifts).  Reset release +3.
// A lane queue overflow (a client past its LQ credits) is a sticky protocol fault (status) as in the unit; after it the
// bank-local queue may diverge from the unit (the CP halts on the fault).
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
    parameter integer XR = 1,     // must be 1: relay r2 on the down tree (the bank tile pin flops) and u2 on the return tree
                                  // configuration's ~2 x 2 mm tile array (hub -> far bank = 3 hops of <= ~500 um)
    parameter integer MUT = 0     // 1 no correction, 2 bank index from sector[5:1], 3 responses one slot early,
                                  // 4 wide word mask ignored, 5 a wide read response to group 0, 6 a packet write does
                                  // not yield to a W2 write, 7 no packet-write age promotion, 10 an aperture sector also
                                  // writes VM, 12 no address range check, 13 aperture bank from the wrong sector bits
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
    localparam integer NB = 32, OUT = 4, LW = 274;   // client lane = {row 10, wdata 256, word mask 8}
    localparam integer CW = (NC > 1) ? $clog2(NC) : 1;
    localparam integer RPL = RP > 0 ? RP : 1, W2L = W2 > 0 ? W2 : 1, NGR = RP / 32, NGW = W2 / 32;
    localparam integer WQW = 280 + AP;
    localparam integer LQB = $clog2(LQ);
    localparam integer LRD = LQ + 8;                  // bank-local read-lane queue: LQ credits + 3 up + 2 down in flight
    localparam integer GW = 2 * CW + 8;               // per-bank decision {rv, rc, wv, wc, lv, lg 2, qv, qg 2}
    generate if (NC < 1 || NC > 16 || WP != 32 || WDIRECT != 1 || (RP % 32) != 0 || RP > 96 || (W2 % 32) != 0 ||
                 W2 > 96 || AP > 1 || LQ < 2 || LQ > 32 || (1 << LQB) != LQ || XR != 1) begin : g_cfg_trap
        ot_hgi_vm_tunit_needs_NC_le16_WP32_WDIRECT1_RP_W2_0_32_64_96_AP_0_1_LQ_pow2_2_32_XR1 u_trap ();
    end endgenerate

    function automatic integer grp(input integer b); grp = (b < 15) ? 0 : (b < 17) ? 1 : 2; endfunction
    function automatic [3:0] oh2i(input [15:0] oh);
        integer i; reg [3:0] r; begin r = 4'd0; for (i = 0; i < 16; i = i + 1) if (oh[i]) r = 4'(i); oh2i = r; end
    endfunction

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
    // 7 return tree, 8 aperture block
    wire [8:0] rn;
    ot_rst_relay #(.REGIONS(9), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rn));

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

    // ---------------------------------------------------------------- hub: lane-queue shadows (1 bit an entry)
    // relayed lane events (3 stages from the lane's pin flop): {v, head bank match}
    wire [RPL-1:0] rqh_v, rqh_m; wire [W2L-1:0] w2h_v, w2h_m;
    wire [RPL-1:0] rl_v, rl_m, rq_ovf_l; wire [RPL-1:0] rl_acc;
    wire [W2L-1:0] w2_v, w2_m, w2_qovf; wire [W2L-1:0] w2_acc;
    genvar gl;
    for (gl = 0; gl < RPL; gl = gl + 1) begin : g_rqs
        // the unit's read-lane queue (push from rq_r, pop on acceptance), keeping the bank-match bit of each entry
        reg [LQ-1:0] tq; reg [LQB:0] n; reg [LQB-1:0] h, t; reg ovf_r;
        wire push = (RP > 0) && rqh_v[gl], pop = rl_acc[gl], full = n == LQ;
        assign rl_v[gl] = (RP > 0) && n != 0; assign rl_m[gl] = tq[h]; assign rq_ovf_l[gl] = ovf_r;
        always @(posedge clk) if (push && !(full && !pop)) tq[t] <= rqh_m[gl];
        always @(posedge clk or negedge rn[0])
            if (!rn[0]) begin n <= 0; h <= 0; t <= 0; ovf_r <= 1'b0; end
            else begin
                if (push && full && !pop) ovf_r <= 1'b1;
                else if (push) t <= t + 1'b1;
                if (pop) h <= h + 1'b1;
                n <= n + (push && !(full && !pop)) - pop;
            end
    end
    for (gl = 0; gl < W2L; gl = gl + 1) begin : g_w2s
        // the unit's W2 queue (ot_fifo_sram_fwft DEPTH LQ) control replica with the bank-match bit as its data
        wire hv; wire [0:0] hd; wire ov;
        ot_fifo_fwft_tag #(.TW(1), .DEPTH(LQ)) u_s (.clk(clk), .rst_n(rn[0]), .push((W2 > 0) && w2h_v[gl]),
            .wdata(w2h_m[gl]), .pop(w2_acc[gl]), .hv(hv), .head(hd), .ovf(ov));
        assign w2_v[gl] = (W2 > 0) && hv; assign w2_m[gl] = hd[0]; assign w2_qovf[gl] = ov;
    end

    // ---------------------------------------------------------------- hub: the core's arbitration (ot_hgi_vm_core)
    wire [NB-1:0] wb_hit, wb_dup, wl_vh;                    // DMA lanes, relayed from the faces (h3)
    reg [NC-1:0] busy; reg [NC*3-1:0] ocnt; reg [NC-1:0] a1, a2, a3, a4;
    reg [NC-1:0] gr_r [0:NB-1]; reg [NC-1:0] gr_w [0:NB-1];
    localparam integer CAGE = 8;
    reg [4*NC-1:0] c_wait; reg [NB-1:0] c_old;
    reg [NB-1:0] w2_hit, rl_hit, rl_bad, w2_bad, rl_any; reg [NB*2-1:0] rl_g, w2_g;
    always @* begin
        c_old = {NB{1'b0}};
        for (integer ac = 0; ac < NC; ac = ac + 1)
            if (h_v[ac] && !busy[ac] && c_we[ac] && c_wait[ac*4 +: 4] >= 4'(CAGE)) c_old[c_bank[ac]] = 1'b1;
    end
    always @* begin
        for (integer ab = 0; ab < NB; ab = ab + 1) begin
            w2_hit[ab] = 1'b0; w2_bad[ab] = 1'b0; rl_any[ab] = 1'b0; rl_bad[ab] = 1'b0; rl_g[ab*2 +: 2] = 2'd0; w2_g[ab*2 +: 2] = 2'd0;
            for (integer gg = NGW - 1; gg >= 0; gg = gg - 1) begin
                if (w2_v[gg*32 + ab] && w2_m[gg*32 + ab] && !wb_hit[ab] && !(c_old[ab] && MUT != 7)) begin w2_hit[ab] = 1'b1; w2_g[ab*2 +: 2] = 2'(gg); end
                if (w2_v[gg*32 + ab] && !w2_m[gg*32 + ab]) w2_bad[ab] = 1'b1;
            end
            for (integer gg = NGR - 1; gg >= 0; gg = gg - 1) begin
                if (rl_v[gg*32 + ab] && rl_m[gg*32 + ab]) begin rl_any[ab] = 1'b1; rl_g[ab*2 +: 2] = 2'(gg); end
                if (rl_v[gg*32 + ab] && !rl_m[gg*32 + ab]) rl_bad[ab] = 1'b1;
            end
        end
    end
    always @* begin
        for (integer ab = 0; ab < NB; ab = ab + 1) begin
            gr_r[ab] = {NC{1'b0}}; gr_w[ab] = {NC{1'b0}};
            for (integer ac = NC - 1; ac >= 0; ac = ac - 1) begin
                if (h_v[ac] && !busy[ac] && c_bank[ac] == ab && !c_we[ac]) gr_r[ab] = {NC{1'b0}} | ({{(NC-1){1'b0}}, 1'b1} << ac);
                if (h_v[ac] && !busy[ac] && c_bank[ac] == ab &&  c_we[ac] && !wb_hit[ab] && (!w2_hit[ab] || MUT == 6))
                    gr_w[ab] = {NC{1'b0}} | ({{(NC-1){1'b0}}, 1'b1} << ac);
            end
        end
        acc = {NC{1'b0}};
        for (integer ab = 0; ab < NB; ab = ab + 1) acc = acc | gr_r[ab] | gr_w[ab];
        for (integer ab = 0; ab < NB; ab = ab + 1) rl_hit[ab] = rl_any[ab] && !(|gr_r[ab]);
    end
    for (gl = 0; gl < RPL; gl = gl + 1) begin : g_rlacc
        assign rl_acc[gl] = (RP > 0) && rl_hit[gl % 32] && rl_g[(gl % 32)*2 +: 2] == 2'(gl / 32);
    end
    for (gl = 0; gl < W2L; gl = gl + 1) begin : g_w2acc
        assign w2_acc[gl] = (W2 > 0) && w2_hit[gl % 32] && w2_g[(gl % 32)*2 +: 2] == 2'(gl / 32);
    end
    // busy / outstanding: the unit pops a response exactly 4 edges after its grant (rsp_r = 1), so pop = acc 4 back
    reg proto, mfault, wlc, rlc, w2ovf;
    always @(posedge clk or negedge rn[0])
        if (!rn[0]) begin
            busy <= '0; a1 <= '0; a2 <= '0; a3 <= '0; a4 <= '0; proto <= 1'b0; mfault <= 1'b0; wlc <= 1'b0; rlc <= 1'b0;
            w2ovf <= 1'b0; ocnt <= '0; c_wait <= '0;
        end else begin
            a1 <= acc; a2 <= a1; a3 <= a2; a4 <= a3;
            for (integer c = 0; c < NC; c = c + 1) begin
                ocnt[c*3 +: 3] <= ocnt[c*3 +: 3] + {2'd0, acc[c]} - {2'd0, a4[c]};
                busy[c] <= (ocnt[c*3 +: 3] + {2'd0, acc[c]} - {2'd0, a4[c]}) >= 3'(OUT);
                c_wait[c*4 +: 4] <= (h_v[c] && !busy[c] && c_we[c] && !acc[c]) ?
                                    ((c_wait[c*4 +: 4] == 4'd15) ? 4'd15 : c_wait[c*4 +: 4] + 4'd1) : 4'd0;
            end
            if (|ovf) proto <= 1'b1;
            if (|wb_dup || |w2_bad) wlc <= 1'b1;
            if (|rl_bad) rlc <= 1'b1;
            if (|w2_qovf) w2ovf <= 1'b1;
            for (integer ab = 0; ab < NB; ab = ab + 1)
                for (integer c = 0; c < NC; c = c + 1) if (gr_w[ab][c] && c_mf[c]) mfault <= 1'b1;
        end
    // decision register s0: the client lanes + per bank {rv, rc, wv, wc, lv, lg, qv, qg}
    reg [NC*LW-1:0] s0_l; reg [NB*GW-1:0] s0_g;
    always @(posedge clk)
        for (integer c = 0; c < NC; c = c + 1) s0_l[c*LW +: LW] <= {c_sec[c][14:5], h_q[c*337 + 48 +: 256], c_wm[c]};
    always @(posedge clk or negedge rn[0])
        if (!rn[0]) s0_g <= '0;
        else for (integer ab = 0; ab < NB; ab = ab + 1)
            s0_g[ab*GW +: GW] <= {|gr_r[ab], CW'(oh2i(16'(gr_r[ab]))), |gr_w[ab], CW'(oh2i(16'(gr_w[ab]))),
                                  rl_hit[ab] && (RP > 0), rl_g[ab*2 +: 2], w2_hit[ab] && (W2 > 0), w2_g[ab*2 +: 2]};
    // tag line: {v, we, tag} from the grant to the response register
    localparam integer TLN = 10 + 2 * XR;
    reg [NC-1:0] we_now; reg [NC*16-1:0] tag_now;
    always @* for (integer c = 0; c < NC; c = c + 1) begin we_now[c] = c_we[c]; tag_now[c*16 +: 16] = h_q[c*337 +: 16]; end
    reg [TLN*NC-1:0] tl_v, tl_we; reg [TLN*NC*16-1:0] tl_tag;
    always @(posedge clk or negedge rn[0])
        if (!rn[0]) tl_v <= '0;
        else tl_v <= {tl_v[(TLN-1)*NC-1:0], acc};
    always @(posedge clk) begin
        tl_we <= {tl_we[(TLN-1)*NC-1:0], we_now}; tl_tag <= {tl_tag[(TLN-1)*NC*16-1:0], tag_now};
    end

    // ---------------------------------------------------------------- down tree: one kept relay copy per group
    // (XR: the second relay r2 is each bank tile's own pin flop stage, next to the bank)
    wire [NC*LW-1:0] r1_l [0:2]; wire [NB*GW-1:0] r1_g [0:2];
    for (genvar g = 0; g < 3; g = g + 1) begin : g_r1
        (* keep = "true" *) reg [NC*LW-1:0] l; (* keep = "true" *) reg [NB*GW-1:0] gr;
        always @(posedge clk) l <= s0_l;
        always @(posedge clk or negedge rn[0]) if (!rn[0]) gr <= '0; else gr <= s0_g;
        assign r1_l[g] = l; assign r1_g[g] = gr;   // r2 (XR) = each bank tile's pin flops
    end

    // ---------------------------------------------------------------- DMA lanes (faces): pin flop, hub relays, data line
    localparam integer WLN = 7;                            // data line p0 -> w1..w7 -> tile pin flop -> m_* (= h1..h3 + hub + s0 + r1 + r2 + cs + c2)
    wire [NB-1:0] w7_hit; wire [NB*10-1:0] w7_row; wire [NB*312-1:0] w7_enc; wire [NB*8-1:0] w7_wm;
    wire [NB-1:0] av3; wire [NB*279-1:0] ad3;              // aperture relay line (AP): {v && ap}, {sector 15, wdata 256, mask 8}
    for (gl = 0; gl < NB; gl = gl + 1) begin : g_wl
        localparam integer RF = (gl < 16) ? 2 : 3;          // face reset region
        reg p0_v; reg [WQW-2:0] p0_d;
        always @(posedge clk or negedge rn[RF]) if (!rn[RF]) p0_v <= 1'b0; else p0_v <= wq[gl*WQW + WQW - 1];
        always @(posedge clk) p0_d <= wq[gl*WQW +: WQW - 1];
        wire ap  = (AP != 0) && p0_d[279 - (AP == 0 ? 1 : 0)];
        wire vmw = p0_v && (!ap || MUT == 10);              // a VM write (MUT 10: an aperture sector also writes VM)
        wire hit = vmw && p0_d[264 +: 5] == 5'(gl), dup = vmw && p0_d[264 +: 5] != 5'(gl);
        reg [2:0] hh, hd, hw;                              // h1..h3 (hit, dup, VM write) toward the hub
        always @(posedge clk or negedge rn[RF])
            if (!rn[RF]) begin hh <= '0; hd <= '0; hw <= '0; end
            else begin hh <= {hh[1:0], hit}; hd <= {hd[1:0], dup}; hw <= {hw[1:0], vmw}; end
        assign wb_hit[gl] = hh[2]; assign wb_dup[gl] = hd[2]; assign wl_vh[gl] = hw[2];
        // data line {row 10, wdata 256, mask 8}; the last stage carries the encoded word
        reg [WLN-2:0] wv; reg [(WLN-1)*274-1:0] wd;
        reg w7h; reg [9:0] w7r; reg [311:0] w7e; reg [7:0] w7m;
        always @(posedge clk or negedge rn[RF])
            if (!rn[RF]) begin wv <= '0; w7h <= 1'b0; end
            else begin wv <= {wv[WLN-3:0], hit}; w7h <= wv[WLN-2]; end
        always @(posedge clk) begin
            wd <= {wd[(WLN-2)*274-1:0], p0_d[264 + 5 +: 10], p0_d[8 +: 256], p0_d[7:0]};
            w7r <= wd[(WLN-2)*274 + 264 +: 10]; w7e <= enc8(wd[(WLN-2)*274 + 8 +: 256]); w7m <= wd[(WLN-2)*274 +: 8];
        end
        assign w7_hit[gl] = w7h; assign w7_row[gl*10 +: 10] = w7r; assign w7_enc[gl*312 +: 312] = w7e; assign w7_wm[gl*8 +: 8] = w7m;
        if (AP != 0) begin : g_al
            reg [2:0] av; reg [3*279-1:0] ad;
            always @(posedge clk or negedge rn[RF]) if (!rn[RF]) av <= '0; else av <= {av[1:0], p0_v && ap};
            always @(posedge clk) ad <= {ad[2*279-1:0], p0_d[0 +: 279]};
            assign av3[gl] = av[2]; assign ad3[gl*279 +: 279] = ad[2*279 +: 279];
        end else begin : g_nal
            assign av3[gl] = 1'b0; assign ad3[gl*279 +: 279] = '0;
        end
    end

    // ---------------------------------------------------------------- aperture block + DMA dones (hub column)
    // the unit's aperture logic verbatim, fed from the relay lines (its wq_r = ad3 / av3) and from ap_cr / ap_done
    // through a pin flop + one relay (its ap_cr_q / ap_dn_q)
    reg [7:0] ap_cr_p, ap_dn_p, ap_cr_q, ap_dn_q;
    always @(posedge clk or negedge rn[8])
        if (!rn[8]) begin ap_cr_p <= '0; ap_dn_p <= '0; ap_cr_q <= '0; ap_dn_q <= '0; end
        else begin ap_cr_p <= ap_cr; ap_dn_p <= ap_done; ap_cr_q <= ap_cr_p; ap_dn_q <= ap_dn_p; end
    reg [WP-1:0] wl_d1, wl_done;
    always @(posedge clk or negedge rn[0]) if (!rn[0]) begin wl_d1 <= '0; wl_done <= '0; end else begin wl_d1 <= wl_vh; wl_done <= wl_d1; end
    reg [WP-1:0] apx; reg [15:0] ap_pend;
    reg [WP-1:0] aq_pop; wire [WP-1:0] aq_hv; wire [WP*277-1:0] aq_head; wire [WP-1:0] ap_flt, rdy_h;
    reg [$clog2(APC+1)-1:0] apcr [0:7]; reg [4:0] aprr [0:7]; reg [8*278-1:0] apo;
    for (gl = 0; gl < WP; gl = gl + 1) begin : g_aq
        if (AP != 0) begin : g_ap
            wire [278:0] e = ad3[gl*279 +: 279];
            wire push = av3[gl] && e[264 + 13 +: 2] == 2'd0;
            wire qovf; reg rdy_q, rf; reg [$clog2(APD):0] n;
            ot_fifo_sram_fwft #(.W(277), .DEPTH(APD), .MACRO(QMACRO)) u_aq (.clk(clk), .rst_n(rn[8]), .push(push),
                .wdata({e[264 +: 13], e[0 +: 264]}), .pop(aq_pop[gl]), .hv(aq_hv[gl]),
                .head(aq_head[gl*277 +: 277]), .ovf(qovf));
            always @(posedge clk or negedge rn[8])
                if (!rn[8]) begin n <= '0; rdy_q <= 1'b1; rf <= 1'b0; end
                else begin
                    n <= n + push - aq_pop[gl];
                    rdy_q <= (MUT == 11) || ({1'b0, n} + push < (APD - APS));
                    if (qovf || (av3[gl] && !push)) rf <= 1'b1;
                end
            assign rdy_h[gl] = rdy_q; assign ap_flt[gl] = rf;
        end else begin : g_noap
            assign rdy_h[gl] = 1'b1; assign ap_flt[gl] = 1'b0; assign aq_hv[gl] = 1'b0; assign aq_head[gl*277 +: 277] = '0;
        end
    end
    always @* begin : apxs
        integer left; left = (AP != 0) ? ap_pend : 0; apx = '0;
        for (integer l = 0; l < WP; l = l + 1) if (left > 0 && !wl_done[l]) begin apx[l] = 1'b1; left = left - 1; end
    end
    always @* begin
        aq_pop = '0;
        for (integer k = 0; k < 8; k = k + 1) begin : pk
            reg found; integer i, l;
            found = 1'b0;
            for (i = 0; i < WP; i = i + 1) begin
                l = (aprr[k] + 1 + i) % WP;
                if (AP != 0 && !found && apcr[k] != '0 && aq_hv[l] && aq_head[l*277 + (MUT == 13 ? 272 : 273) +: 3] == 3'(k)) begin
                    found = 1'b1; aq_pop[l] = 1'b1;
                end
            end
        end
    end
    always @(posedge clk or negedge rn[8])
        if (!rn[8]) begin
            apo <= '0; ap_pend <= '0;
            for (integer k = 0; k < 8; k = k + 1) begin apcr[k] <= APC; aprr[k] <= 5'd31; end
        end else begin
            ap_pend <= ap_pend + 16'($countones(ap_dn_q)) - 16'($countones(apx));
            for (integer k = 0; k < 8; k = k + 1) begin : snd
                reg sent; reg [276:0] h; sent = 1'b0; h = '0;
                for (integer l = 0; l < WP; l = l + 1)
                    if (aq_pop[l] && aq_head[l*277 + (MUT == 13 ? 272 : 273) +: 3] == 3'(k)) begin sent = 1'b1; h = aq_head[l*277 +: 277]; aprr[k] <= 5'(l); end
                apo[k*278 +: 278] <= {sent, h};
                apcr[k] <= apcr[k] - sent + ap_cr_q[k];
            end
        end
    // ap_q output flop
    reg [8*278-1:0] apq_r;
    always @(posedge clk) apq_r <= (AP != 0) ? apo : '0;
    assign ap_q = apq_r;
    // DMA dones (VM writes and aperture writes) and the aperture stop, back to the faces: hub register, 2 relays, pin
    // (the done leaves 4 + XR edges after the unit's: after the bank write, which is 4 + XR edges later)
    reg [WP-1:0] dn_h, dn_p, rd_r1, rd_p; reg [(2+XR)*WP-1:0] dn_r;
    always @(posedge clk or negedge rn[0])
        if (!rn[0]) begin dn_h <= '0; dn_r <= '0; dn_p <= '0; rd_r1 <= '1; rd_p <= '1; end
        else begin
            dn_h <= wl_done | ((AP != 0) ? apx : '0); dn_r <= {dn_r[(1+XR)*WP-1:0], dn_h}; dn_p <= dn_r[(1+XR)*WP +: WP];
            rd_r1 <= rdy_h; rd_p <= rd_r1;
        end
    assign wq_done = dn_p; assign wq_rdy = rd_p;

    // ---------------------------------------------------------------- bank tiles (hard ot_hgi_vm_btile, own clock tree)
    // parent side of each tile: the 2 remaining relays of its lane events toward the hub, the XR return relay (u2)
    wire [NB-1:0] u_v; wire [NB*CW-1:0] u_c; wire [NB*256-1:0] u_d; wire [NB*4-1:0] u_ce; wire [NB-1:0] u_ue;
    wire [RPL*257-1:0] rr_w; wire [RPL-1:0] rqcr_w; wire [W2L-1:0] w2cr_w, w2dn_w;
    localparam integer NGRL = NGR > 0 ? NGR : 1, NGWL = NGW > 0 ? NGW : 1;
    genvar gb;
    for (gb = 0; gb < NB; gb = gb + 1) begin : g_bk
        localparam integer G = grp(gb), RB = 4 + grp(gb);
        wire [NGRL*16-1:0] t_rq; wire [NGRL-1:0] t_rv, t_rm, t_rc; wire [NGRL*257-1:0] t_rr;
        wire [NGWL*280-1:0] t_wq; wire [NGWL-1:0] t_wv, t_wm, t_wc, t_wd;
        wire tv, tue; wire [CW-1:0] tc; wire [255:0] td; wire [3:0] tce;
        for (genvar g = 0; g < NGRL; g = g + 1) begin : g_rqp
            if (NGR > 0) begin : g_on
                assign t_rq[g*16 +: 16] = rq[(g*32 + gb)*16 +: 16];
                reg [1:0] rv, rm;                          // h2, h3 toward the hub
                always @(posedge clk or negedge rn[RB]) if (!rn[RB]) begin rv <= '0; rm <= '0; end
                    else begin rv <= {rv[0], t_rv[g]}; rm <= {rm[0], t_rm[g]}; end
                assign rqh_v[g*32 + gb] = rv[1]; assign rqh_m[g*32 + gb] = rm[1];
                assign rqcr_w[g*32 + gb] = t_rc[g]; assign rr_w[(g*32 + gb)*257 +: 257] = t_rr[g*257 +: 257];
            end else begin : g_off
                assign t_rq[g*16 +: 16] = '0;
            end
        end
        for (genvar g = 0; g < NGWL; g = g + 1) begin : g_w2p
            if (NGW > 0) begin : g_on
                assign t_wq[g*280 +: 280] = w2q[(g*32 + gb)*280 +: 280];
                reg [1:0] wv, wm;
                always @(posedge clk or negedge rn[RB]) if (!rn[RB]) begin wv <= '0; wm <= '0; end
                    else begin wv <= {wv[0], t_wv[g]}; wm <= {wm[0], t_wm[g]}; end
                assign w2h_v[g*32 + gb] = wv[1]; assign w2h_m[g*32 + gb] = wm[1];
                assign w2cr_w[g*32 + gb] = t_wc[g]; assign w2dn_w[g*32 + gb] = t_wd[g];
            end else begin : g_off
                assign t_wq[g*280 +: 280] = '0;
            end
        end
`ifdef OT_VM_BTILE_HARD
        ot_hgi_vm_btile u_t (
`else
        ot_hgi_vm_btile #(.NC(NC), .NGR(NGR), .NGW(NGW), .LQ(LQ), .MUT(MUT)) u_t (
`endif
            .clk(clk), .rst_n(rn[RB]), .bid(5'(gb)), .gi(r1_g[G][gb*GW +: GW]), .lanes(r1_l[G]),
            .w_hit(w7_hit[gb]), .w_row(w7_row[gb*10 +: 10]), .w_enc(w7_enc[gb*312 +: 312]), .w_wm(w7_wm[gb*8 +: 8]),
            .rq_in(t_rq), .rqh_v(t_rv), .rqh_m(t_rm), .rq_cr(t_rc), .rr(t_rr),
            .w2q_in(t_wq), .w2h_v(t_wv), .w2h_m(t_wm), .w2q_cr(t_wc), .w2q_done(t_wd),
            .u_v(tv), .u_c(tc), .u_d(td), .u_ce(tce), .u_ue(tue));
        if (XR != 0) begin : g_u2                         // second return relay toward the group merge
            reg v2, e2; reg [CW-1:0] c2x; reg [255:0] d2; reg [3:0] ce2;
            always @(posedge clk or negedge rn[7]) if (!rn[7]) v2 <= 1'b0; else v2 <= tv;
            always @(posedge clk) begin c2x <= tc; d2 <= td; ce2 <= tce; e2 <= tue; end
            assign u_v[gb] = v2; assign u_c[gb*CW +: CW] = c2x; assign u_d[gb*256 +: 256] = d2;
            assign u_ce[gb*4 +: 4] = ce2; assign u_ue[gb] = e2;
        end else begin : g_nu2
            assign u_v[gb] = tv; assign u_c[gb*CW +: CW] = tc; assign u_d[gb*256 +: 256] = td;
            assign u_ce[gb*4 +: 4] = tce; assign u_ue[gb] = tue;
        end
    end
    if (RP == 0) begin : g_norp
        assign rr_w = '0; assign rqcr_w = '0; assign rqh_v = '0; assign rqh_m = '0;
    end
    if (W2 == 0) begin : g_now2
        assign w2cr_w = '0; assign w2dn_w = '0; assign w2h_v = '0; assign w2h_m = '0;
    end
    assign rr = rr_w; assign rq_cr = rqcr_w; assign w2q_cr = w2cr_w; assign w2q_done = w2dn_w;

    // ---------------------------------------------------------------- per-group per-client merge (hm) -> hub response
    reg [3*NC*256-1:0] hm_d; reg [3*8-1:0] hm_ce; reg [2:0] hm_ue;
    always @(posedge clk) begin
        for (integer g = 0; g < 3; g = g + 1) begin : mg
            reg [NC*256-1:0] o; reg [7:0] s; reg e;
            o = '0; s = 8'd0; e = 1'b0;
            for (integer b = 0; b < NB; b = b + 1) if (grp(b) == g) begin
                for (integer c = 0; c < NC; c = c + 1)
                    if (u_v[b] && u_c[b*CW +: CW] == CW'(c)) o[c*256 +: 256] = o[c*256 +: 256] | u_d[b*256 +: 256];
                s = s + {4'd0, u_ce[b*4 +: 4]}; e = e | u_ue[b];
            end
            hm_d[g*NC*256 +: NC*256] <= o; hm_ce[g*8 +: 8] <= s; hm_ue[g] <= e;
        end
    end
    localparam integer TLX = (MUT == 3) ? TLN - 2 : TLN - 1;
    reg [NC*274-1:0] hr, crr; reg [NC-1:0] hr_v, crr_v; reg [15:0] ce_h; reg ue_h;
    always @(posedge clk or negedge rn[0])
        if (!rn[0]) begin hr_v <= '0; ce_h <= 16'd0; ue_h <= 1'b0; end
        else begin
            hr_v <= tl_v[TLX*NC +: NC];
            ce_h <= ce_h + {8'd0, hm_ce[7:0]} + {8'd0, hm_ce[15:8]} + {8'd0, hm_ce[23:16]};
            if (|hm_ue) ue_h <= 1'b1;
        end
    always @(posedge clk)
        for (integer c = 0; c < NC; c = c + 1)
            hr[c*274 +: 274] <= tl_v[TLX*NC + c] ? {1'b0, tl_tag[TLX*NC*16 + c*16 +: 16], tl_we[TLX*NC + c],
                                               tl_we[TLX*NC + c] ? 256'd0 : (hm_d[c*256 +: 256] | hm_d[NC*256 + c*256 +: 256] | hm_d[2*NC*256 + c*256 +: 256])}
                                             : 274'd0;
    // status: the unit's sticky faults delayed to line up with ce / ue (7 edges), then relay + pin flop
    localparam integer FDN = 7 + 2 * XR;
    wire f_now = proto | wlc | rlc | (|rq_ovf_l) | w2ovf | (|ap_flt) | (|pk_rng);
    reg [FDN*2-1:0] fd; reg [18:0] st_h, st_r;
    always @(posedge clk or negedge rn[0])
        if (!rn[0]) begin fd <= '0; st_h <= 19'd0; end
        else begin
            fd <= {fd[(FDN-1)*2-1:0], f_now, mfault};
            st_h <= {fd[FDN*2-1 -: 2], ue_h, ce_h};
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

// Control replica of ot_fifo_sram_fwft (same pointer / occupancy / bypass / ovf equations, so hv and ovf match it
// cycle for cycle) carrying only a TW-bit tag a record in flops: the hub's shadow of a lane queue whose data stays at
// the bank.
module ot_fifo_fwft_tag #(
    parameter integer TW    = 1,
    parameter integer DEPTH = 32
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          push,
    input  wire [TW-1:0] wdata,
    input  wire          pop,
    output wire          hv,
    output wire [TW-1:0] head,
    output reg           ovf
);
    localparam integer AW = $clog2(DEPTH);
    reg  [AW:0]   wp, rp;
    wire [AW:0]   in_arr = wp - rp;
    reg           inflight;
    reg  [TW-1:0] mem [0:DEPTH-1];
    reg  [TW-1:0] rq;
    reg  [TW-1:0] ob [0:1];
    reg  [1:0]    oc;
    reg           oh;
    assign hv = oc != 0;
    assign head = ob[oh];
    wire          do_pop = pop && hv;
    wire [1:0]    oc_after = oc - (do_pop ? 1'b1 : 1'b0);
    wire          bypass = push && in_arr == 0 && !inflight && (oc_after + (inflight ? 1 : 0)) < 2;
    wire          wr_arr = push && !bypass;
    wire          rd_arr = in_arr != 0 && (oc_after + (inflight ? 1 : 0)) < 2;
    wire [1:0]    n_in = (inflight ? 2'd1 : 2'd0) + (bypass ? 2'd1 : 2'd0);
    always @(posedge clk) begin
        if (wr_arr) mem[wp[AW-1:0]] <= wdata;
        if (rd_arr) rq <= mem[rp[AW-1:0]];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wp <= 0; rp <= 0; inflight <= 1'b0; oc <= 0; oh <= 1'b0; ovf <= 1'b0;
        end else begin
            if (wr_arr) begin
                wp <= wp + 1'b1;
                if (in_arr == DEPTH) ovf <= 1'b1;
            end
            if (rd_arr) rp <= rp + 1'b1;
            inflight <= rd_arr;
            if (do_pop) oh <= ~oh;
            oc <= oc_after + n_in;
            if (oc_after + n_in > 2) ovf <= 1'b1;
        end
    end
    always @(posedge clk) begin
        if (inflight) ob[do_pop ? (~oh ^ oc_after[0]) : (oh ^ oc[0])] <= rq;
        if (bypass) ob[(do_pop ? ~oh : oh) ^ (oc_after[0] ^ inflight)] <= wdata;
    end
endmodule
`default_nettype wire
