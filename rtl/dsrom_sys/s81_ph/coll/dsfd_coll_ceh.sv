// el1011-ds-coll 2026-10-11 (owner TEXTBOOK AUDIT + PHYSICAL SPEC BEFORE RTL; spec in el1011-ds-coll.log): the collective
// core's middle tile dsfd_coll_ce rebuilt as HARDENED sub-elements.  The flat ce had 147,734 flops on one clock root
// in 680.4 x 680.4 (g_l face links 44.3k, VM queues 37.6k, engine 35.3k + 9.6k adders), single-cycle cones across the
// tile (pop -> 2,188 s0 enables; adder valid -> 2,099-bit b_word; oq credit -> pass-through round robin -> rr: -1,266).
//
//   dsfd_coll_ces x 4  engine LANE-SLICE: the unmodified collective engine at LANES 4 (4 FP32 lanes x 4 sources, PW 163)
//                      with its remote FIFOs outside (EXTF), the local source FIFO inside, + the slice packer.  Every
//                      slice gets identical control inputs on identical cycles, so all decisions (fire, pop, gather,
//                      pass-through pick, status beats) are taken in lockstep with no cross-slice wire; slice 0
//                      returns the credits and builds the b_word header.
//   dsfd_coll_cef x 3  one REMOTE source's receive FIFOs (2 parities x 3 SRAM macros) + their PULL credit streams,
//                      split to the 4 slices (credit from slice 0).
//   dsfd_coll_cel x 8  one LANE: face credit tx / rx (the flat ce's g_l) + its glue: lanes 0..2 engine port (tx
//                      buffer, piggyback credit counters, rx -> cef), lanes 3..7 pass-through (queue landing -> lane;
//                      lane -> 4 slice landings).
//   dsfd_coll_ceq      f_vm -> 6 VM queues (SRAM), q0 -> slices, q1..5 -> pass-through lanes, rank / enable /
//                      queue-pop broadcast, fault collector.
//   dsfd_coll_ceh      the composition: dsfd_coll_ce's ports (slab: +define+OT_S81PH_COLL_CEH).
// Every tile synchronises rs itself; every seam is a credit link or a registered stream (pin flop both ends).
`timescale 1ns/1ps

// COVERAGE of the split lane-slice seams (bench only: Verilator builds with OT_S81PH_COLL_CES_SPLIT; never synthesised).
// Every wires-only parent counts the beats that cross each of its seams; tb_s81ph_coll_sys REFUSES a pass in which a
// seam carried nothing, a parent is missing, or the ces0 and cesn counts differ (lockstep).  [k]: 0 = ces0, 1 = cesn.
`ifdef OT_S81PH_COLL_CES_SPLIT
`ifdef VERILATOR
package s81ph_ces_cov;
    int unsigned inst [0:1];                                  // parents elaborated
    int unsigned ln [0:1], lny [0:1];                         // lane seam: operands out, sums back (per lane beat)
    int unsigned xl [0:1][1:3];                               // xl relay -> core, per remote source
    int unsigned xli [0:1][1:3];                              // FIFO tile -> xl relay
    int unsigned pt [0:1][0:4];                               // pass-through relay -> core, per lane
    int unsigned pti [0:1][0:4];                              // lane tile -> pass-through relay
    int unsigned ow [0:1], bw [0:1];                          // core -> output leaf, output leaf -> face
endpackage
`endif
`endif

// ------------------------------------------------------------------------------------------------ remote FIFO tile
module dsfd_coll_cef #(parameter integer PW = 547, parameter integer PD = 256, parameter integer XD = 6) (
    input  wire              ck, input wire rs,
    input  wire              e_en,                          // engine enable broadcast (FIFO reset = engine reset)
    input  wire              rx_v, input wire [PW-1:0] rx_d,  // from the lane tile (registered stream)
    output wire [1:0]        x_v,                           // per parity: valid to the 4 slices
    output wire [8*163-1:0]  x_d,                           // [(q*4 + s)*163 +: 163] slice s record of parity q
    input  wire [1:0]        x_cr,                          // credit from slice 0
    output reg               flt
);
    localparam integer PAR_B = 512;
    reg [1:0] rst_s;
    always @(posedge ck or negedge rs) if (!rs) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    reg en_q, erst_n;
    always @(posedge ck or negedge rst_n) if (!rst_n) begin en_q <= 1'b0; erst_n <= 1'b0; end else begin en_q <= e_en; erst_n <= en_q; end
    reg rv_q; reg [PW-1:0] rd_q;                            // pin flops
    always @(posedge ck or negedge erst_n) if (!erst_n) rv_q <= 1'b0; else rv_q <= rx_v;
    always @(posedge ck) rd_q <= rx_d;
    wire [1:0] ovf;
    genvar q, s;
    generate for (q = 0; q < 2; q = q + 1) begin : g_p
        wire fhv, f_rdy, lv, lcr; wire [PW-1:0] fhd, ld;
        reg cr_q;
        always @(posedge ck or negedge erst_n) if (!erst_n) cr_q <= 1'b0; else cr_q <= x_cr[q];
        ot_fifo_sram_fwft #(.W(PW), .DEPTH(PD), .MACRO(1)) u_f (.clk(ck), .rst_n(erst_n),
            .push(rv_q && rd_q[PAR_B] == q), .wdata(rd_q), .pop(fhv && f_rdy), .hv(fhv), .head(fhd), .ovf(ovf[q]));
        ot_link_credit_tx #(.W(PW), .CRED(XD), .DFREE(1)) u_pt (.clk(ck), .rst_n(erst_n), .i_valid(fhv), .i_ready(f_rdy),
            .i_data(fhd), .l_valid(lv), .l_data(ld), .l_credit(cr_q));
        assign x_v[q] = lv;
        for (s = 0; s < 4; s = s + 1) begin : g_s
            assign x_d[(q*4 + s)*163 +: 163] = {ld[PW-1:512], ld[s*128 +: 128]};
        end
    end endgenerate
    always @(posedge ck or negedge erst_n) if (!erst_n) flt <= 1'b0; else if (|ovf) flt <= 1'b1;
endmodule

// ------------------------------------------------------------------------------------------------ engine lane-slice
// SEAM (s81-cesn 2026-10-13, opt-in; 0 = byte-identical): this module is the CORE leaf of the split lane-slice.  The
// flat slice had 22,816 flops on one root (yosys stat: xl landings 6 x 1,160, pass-through landings 5 x 922, lanes
// 12 x 206) and three routes missed hold.  With SEAM the engine runs at LSEAM 1 (FP32 lanes in 4 dsfd_coll_cesl leaves,
// reduce +2 cycles), and the xl / pass-through links arrive from relay leaves (dsfd_coll_cesx / cesp, D XD towards the
// sender, +2 cycles each way) into XLD / PTD-deep landings here.  All four slices of a composition MUST use the same
// SEAM (they run in lockstep with no cross-slice wire): dsfd_coll_ceh asserts it.
// With SEAM the OUTPUT STAGE (bd_q / bh_q / bv_q, the header error OR and the bw pin registers: 1,078 flops in cesn,
// 1,180 in ces0) is the dsfd_coll_ceso leaf: the core's last flops w1_v / w1_d / w1_h leave on ow_*.  Same flops, same
// cycles (zero added latency); it takes the cesn core from 14,889 to ~13.8k sinks and ces0's below 15k.
module dsfd_coll_ces #(parameter integer S = 0, parameter integer XD = 6, parameter integer OQX_D = 16,
    parameter integer SEAM = 0, parameter integer XLD = 3, parameter integer PTD = 2) (
    input  wire              ck, input wire rs,
    input  wire              e_en, input wire [1:0] rank_i,
    input  wire [5:0]        qp,                            // VM queue pops (broadcast, VM credit replicas)
    input  wire [7:0]        fv_i,                          // global fault vector (broadcast)
    // q0: this slice's part of the engine input records {last, mode, tag, data 128}
    input  wire              q_v, input wire [161:0] q_d, output wire q_cr,
    // remote sources' landing links [2g + q] (g = 1..3)
    input  wire [7:0]        xl_v, input wire [8*163-1:0] xl_d, output wire [7:0] xl_cr,
    // engine ports 1..3 (lanes 0..2)
    output reg  [3:1]        tx_v, output reg [162:0] tx_d, input wire [3:1] tx_rdy,
    input  wire [7:2]        cr_i, output reg [7:2] cr_o,
    // pass-through landings, lanes 3..7: {last, data slice}
    input  wire [4:0]        pt_v, input wire [5*(S == 0 ? 169 : 129)-1:0] pt_d, output wire [4:0] pt_cr,
    // output to cb
    input  wire              bw_cr,
    output reg               bw_v, output reg [(S == 0 ? 563 : 512)-1:0] bw_d,   // SEAM: tied 0 (dsfd_coll_ceso drives the face)
    // SEAM: output seam to the dsfd_coll_ceso leaf (the registered word one stage before the old bd_q / bh_q)
    output wire              ow_v, output wire [511:0] ow_d, output wire [50:0] ow_h,
    // slice faults to ceq, header error bits to / from slice 0
    output reg  [1:0]        lf,                            // {e_flt, mq_flt}
    output reg               pe_o, input wire [3:1] pe_i,
    // SEAM: lane seam to the 4 dsfd_coll_cesl leaves (lane g: ln_d[r*128 + 32*g +: 32], r = source 0..3)
    output wire              ln_v, output wire [511:0] ln_d,
    input  wire [127:0]      ln_y, input wire [3:0] ln_yv, input wire [7:0] ln_ye, input wire [3:0] ln_pe
);
    // OT_S81PH_COLL_CSTRESS (bench only): 8-deep receive FIFOs per parity, so the inter-die credit loop runs dry and
    // must work (277 records per die never exhaust the 256-deep production FIFOs)
    localparam integer EDEPTH = `ifdef OT_S81PH_COLL_CSTRESS 16 `else 512 `endif;
    localparam integer SFW = 128, PW = 163, TAGW = 32, MQD = EDEPTH, MQB = $clog2(MQD);
    localparam integer PTW = (S == 0) ? 169 : 129;
    reg [1:0] rst_s;
    always @(posedge ck or negedge rs) if (!rs) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    // broadcast pin flops (control)
    reg en_q, erst_n; reg [3:0] eg; reg [1:0] rank; reg [5:0] qp_q; reg [7:0] fv_q; reg [3:1] trd_q; reg [7:2] cri_q;
    reg bcr_q; reg [3:1] pe_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin en_q <= 1'b0; erst_n <= 1'b0; eg <= 4'd0; rank <= 2'd0; qp_q <= 6'd0; fv_q <= 8'd0;
                          trd_q <= 3'd0; cri_q <= 6'd0; bcr_q <= 1'b0; pe_q <= 3'd0; end
        else begin
            en_q <= e_en; erst_n <= en_q; eg <= {eg[2:0], en_q}; rank <= rank_i; qp_q <= qp; fv_q <= fv_i;
            trd_q <= tx_rdy; cri_q <= cr_i; bcr_q <= bw_cr; pe_q <= pe_i;
        end
    // q0 landing
    wire lq_v; wire [161:0] lq_d; wire lq_pop;
    ot_link_credit_rx #(.W(162), .DEPTH(XD), .OREG(0), .WFREE(2)) u_lq (.clk(ck), .rst_n(rst_n), .l_valid(q_v),
        .l_data(q_d), .l_credit(q_cr), .o_valid(lq_v), .o_ready(lq_pop), .o_data(lq_d), .fault());
    // ---- engine
    reg  mq_ok;
    wire e_iv = lq_v && eg[3] && mq_ok;
    wire e_ir;
    assign lq_pop = e_iv && e_ir;
    wire [3:0] e_txv; wire [PW-1:0] e_txr; wire [7:0] e_cro;
    wire o_v, o_last, o_err, o_red; wire [1:0] o_rank; wire [4*SFW-1:0] o_d, o_gdat; wire [SFW-1:0] o_rdat;
    reg  o_rdy;
    wire e_flt; wire [2:0] e_code; wire e_rpop;
    ot_w15_rom_oneshot_die_px_acceptedpop #(.FIX_ACCEPTED_POP(1), .N(4), .RANK(0), .LANES(4), .TAGW(TAGW),
        .DEPTH(EDEPTH), .PKG_DIES(2), .RELAY(0), .ADD_LAT(3), .PAIRWISE(1), .GW(4), .OUT_BP(1), .FIFO_SRAM(1),
        .SRAM_MACRO(1), .PULL(1), .PULL_D(XD), .PCOPY(1), .PSL(1), .LQW(2), .EXTF(1), .RHOLD(1), .LSEAM(SEAM),
        .XF_D((SEAM != 0) ? XLD : XD)) u_eng (
        .clk(ck), .rst_n(erst_n),
        .in_valid(e_iv), .in_ready(e_ir), .in_data(lq_d[SFW-1:0]), .in_last(lq_d[161]), .in_mode(lq_d[160]),
        .in_tag(lq_d[SFW +: TAGW]),
        .tx_valid(e_txv), .tx_rec(e_txr), .tx_ready({trd_q, 1'b1}), .cr_in({cri_q, 2'b00}),
        .rx_valid(4'd0), .rx_rec({4*PW{1'b0}}), .cr_out(e_cro),
        .rl_tx_valid(), .rl_tx_rec(), .rl_rx_valid(4'd0), .rl_rx_rec({4*PW{1'b0}}),
        .out_valid(o_v), .out_ready(o_rdy), .out_data(o_d), .out_last(o_last), .out_rank(o_rank), .out_err(o_err),
        .out_red(o_red), .out_rdat(o_rdat), .out_gdat(o_gdat),
        .fault(e_flt), .fault_code(e_code), .red_hold(!room2), .out_rpop(e_rpop), .xl_v(xl_v), .xl_d(xl_d), .xl_cr(xl_cr),
        .ln_v(ln_v), .ln_d(ln_d), .ln_y(ln_y), .ln_yv(ln_yv), .ln_ye(ln_ye), .ln_pe(ln_pe));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin tx_v <= 3'd0; cr_o <= 6'd0; end
        else begin tx_v <= e_txv[3:1]; cr_o <= e_cro[7:2]; end
    always @(posedge ck) tx_d <= e_txr;
    // ---- pass-through landings
    wire [4:0] ep_ov, ep_or; wire [PTW-1:0] ep_od [0:4];
    genvar l;
    generate for (l = 0; l < 5; l = l + 1) begin : g_pt
        ot_link_credit_rx #(.W(PTW), .DEPTH((SEAM != 0) ? PTD : XD), .OREG(0), .WFREE(2)) u_lp (.clk(ck), .rst_n(rst_n), .l_valid(pt_v[l]),
            .l_data(pt_d[l*PTW +: PTW]), .l_credit(pt_cr[l]), .o_valid(ep_ov[l]), .o_ready(ep_or[l]), .o_data(ep_od[l]),
            .fault());
    end endgenerate
    // ---- packer (the flat core's ORX packer at FW 128 per word; see ot_s81ph_coll_core.sv)
    reg  [MQD-1:0] mq;
    reg  [MQB:0] mq_w, mq_r, mq_r1;
    reg          mq_flt, hm;
    wire [MQB:0] mq_occ = mq_w - mq_r;
    wire         e_fire = e_iv && e_ir;
    reg  [4*SFW-1:0] pk_d;
    reg  [3:0]   pk_l;
    reg          pk_err;
    reg  [2:0]   pk_n;
    reg          r_v, r_last, r_err;
    reg  [SFW-1:0] r_d;
    always @(posedge ck or negedge erst_n) if (!erst_n) r_v <= 1'b0; else r_v <= o_red;
    always @(posedge ck) begin r_d <= o_rdat; r_last <= o_last; r_err <= o_err; end
    // room2 = (cred - w_r) >= 2, registered from the next values: w_r = reduce words popped and not yet emitted, each
    // holding a reserved output slot (reduce words are not back-pressured at the output); also the engine's reduce-pop
    // gate (red_hold).  Slow-VM-drain fix (1-in-8 take overflowed the remote queue in the flat and the split designs).
    reg          room2;
    wire         in_red = r_v && !hm;
    always @(*) o_rdy = hm && (pk_n == 0) && room2;
    wire         in_gat = o_v && !o_red && hm && o_rdy;
    wire         o_take = in_red || in_gat;
    reg  [4*SFW-1:0] gat_d;
    always @(*) for (integer i = 0; i < 4; i = i + 1) gat_d[i*SFW +: SFW] = o_gdat[(i ^ rank)*SFW +: SFW];
    wire         pk_emit = (pk_n != 0) && (pk_n == 4 || !in_red);
    // pass-through pick REGISTERED one cycle ahead (ce cex / ceh p4 ces0: landing valid -> round robin -> 5:1 x 169
    // -> b_d -> w1_d -125.5): pk_q = the round robin's one-hot choice among the lanes landed last cycle and not taken
    // then; such a lane is still landed now (only this packer pops), so the mux is steered by flops.  Per-lane order
    // is unchanged; a lane that lands this cycle competes from the next.
    reg  [2:0]   rr;
    reg  [4:0]   pk_q;
    wire         pt_push = !pk_emit && !in_gat && room2 && (|pk_q);
    reg  [2:0]   pt_lx;
    always @(*) begin pt_lx = 3'd0; for (integer i = 0; i < 5; i = i + 1) if (pk_q[i]) pt_lx = i; end
    wire [2:0]   pt_l = pt_lx;
    assign ep_or = pt_push ? pk_q : 5'd0;
    wire [2:0]   rr_nx = pt_push ? ((pt_l == 4) ? 3'd0 : pt_l + 1'b1) : rr;
    wire [4:0]   cand = ep_ov & ~ep_or;
    reg  [4:0]   pk_nx;
    always @(*) begin
        pk_nx = 5'd0;
        for (integer i = 4; i >= 0; i = i - 1) if (cand[(rr_nx + i) % 5]) pk_nx = 5'd1 << ((rr_nx + i) % 5);
    end
    always @(posedge ck or negedge erst_n) if (!erst_n) pk_q <= 5'd0; else pk_q <= pk_nx;
    reg  [4:0]   qc [0:5];
    reg  [3:0]   qf [0:5];
    always @(*) for (integer i = 0; i < 6; i = i + 1) qf[i] = (qc[i] > 15) ? 4'd15 : qc[i][3:0];
    reg          fault, fault_sent;
    wire         st_need = (qc[0] != 0 || qc[1] != 0 || qc[2] != 0 || qc[3] != 0 || qc[4] != 0 || qc[5] != 0 ||
                            (fault && !fault_sent));
    wire         st_push = !pk_emit && !in_gat && !pt_push && st_need && room2;
    wire         oq_push = pk_emit || in_gat || pt_push || st_push;
    wire [1:0]   b_type = (pk_emit || in_gat) ? 2'd1 : pt_push ? 2'd2 : 2'd3;
    wire [3:0]   b_mask = pk_emit ? ((pk_n == 4) ? 4'hF : (pk_n == 3) ? 4'h7 : (pk_n == 2) ? 4'h3 : 4'h1) :
                          in_gat ? 4'hF : 4'h0;
    wire [3:0]   b_last = pk_emit ? pk_l : in_gat ? {o_last, 3'b000} : 4'h0;
    wire [PTW-1:0] ptw = ep_od[pt_lx];
    wire [4*SFW-1:0] ptd;
    generate if (S == 0) begin : g_pt0
        assign ptd = {{(2*SFW){1'b0}}, {(SFW-40){1'b0}}, ptw[167:128], ptw[127:0]};
    end else begin : g_ptn
        assign ptd = {{(3*SFW){1'b0}}, ptw[127:0]};
    end endgenerate
    wire [4*SFW-1:0] b_d = pk_emit ? pk_d : in_gat ? gat_d : pt_push ? ptd : {4*SFW{1'b0}};
    wire [23:0]  b_cr = {qf[5], qf[4], qf[3], qf[2], qf[1], qf[0]};
    wire         pe = pk_emit ? pk_err : 1'b0;
    wire [50:0]  hdr = {rank, fv_q, fault, b_cr, pe, in_gat && !pk_emit, pt_push ? ptw[PTW-1] : 1'b0, b_last, b_mask,
                        pt_push ? pt_l : 3'd0, b_type};
`ifdef OT_S81PH_MUT_ORC
    reg  signed [7:0] cred;
    reg  [7:0]   w_r;
    wire [7:0]   cred_nx = cred - (oq_push ? 8'sd1 : 8'sd0) + (bcr_q ? 8'sd1 : 8'sd0);
    wire [7:0]   w_nx = w_r + (e_rpop ? 8'd1 : 8'd0) - (pk_emit ? {5'd0, pk_n} : 8'd0);
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin cred <= OQX_D; room2 <= 1'b1; w_r <= 8'd0; end
        else begin
            cred <= cred_nx; w_r <= w_nx;
            room2 <= $signed(cred_nx) >= 8'sd2;                              // negative control: no reservation
        end
`else
    // ces0 pb TT -46.34 (SS -109.3): qc -> st_need -> st_push -> oq_push -> cred_nx adder -> (cred_nx - w_nx) 9-bit
    // subtract -> >= 2 -> room2, one cycle.  Restructured as ONE available-slot counter av = cred - w_r (identical
    // value, 10-bit signed) whose early part av_e = av + bcr_q + emit-release is computed from flops, while the two
    // late decrements (oq_push, e_rpop: k = 0..2) only SELECT among precomputed av_e - k and (av_e >= 2 + k)
    // (carry-select).  Cycle-exact: room2 / red_hold are the same bits every cycle as before.
    reg  signed [9:0] av;
    wire signed [9:0] av_e = av + $signed({9'd0, bcr_q}) + (pk_emit ? $signed({7'd0, pk_n}) : 10'sd0);
    wire signed [9:0] av_m1 = av_e - 10'sd1;
    wire signed [9:0] av_m2 = av_e - 10'sd2;
    wire         ge2 = av_e >= 10'sd2, ge3 = av_e >= 10'sd3, ge4 = av_e >= 10'sd4;
    wire         dk1 = oq_push ^ e_rpop, dk2 = oq_push & e_rpop;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin av <= OQX_D; room2 <= 1'b1; end
        else begin
            av <= dk2 ? av_m2 : dk1 ? av_m1 : av_e;
            room2 <= dk2 ? ge4 : dk1 ? ge3 : ge2;
        end
`endif
    always @(posedge ck) if (in_red) pk_d[(pk_emit ? 0 : pk_n) * SFW +: SFW] <= r_d;
    always @(posedge ck or negedge erst_n) begin
        if (!erst_n) begin
            mq_w <= 0; mq_r <= 0; mq_r1 <= 1; mq_flt <= 1'b0; hm <= 1'b0; mq_ok <= 1'b0; pk_n <= 0; pk_l <= 0;
            pk_err <= 1'b0; rr <= 0; fault <= 1'b0; fault_sent <= 1'b0;
            for (integer i = 0; i < 6; i = i + 1) qc[i] <= 0;
        end else begin
            if (e_fire) begin mq[mq_w[MQB-1:0]] <= lq_d[160]; mq_w <= mq_w + 1'b1; end
            if (o_take) begin mq_r <= mq_r + 1'b1; mq_r1 <= mq_r1 + 1'b1; end
            hm <= o_take ? mq[mq_r1[MQB-1:0]] : mq[mq_r[MQB-1:0]];
            mq_ok <= (mq_occ + (e_fire ? 1'b1 : 1'b0) - (o_take ? 1'b1 : 1'b0)) <= MQD - 2;
            if ((r_v || (o_v && !o_red)) && mq_w == mq_r) mq_flt <= 1'b1;
            if (e_fire && mq_occ == MQD) mq_flt <= 1'b1;
            if (pk_emit) begin pk_n <= 0; pk_l <= 0; pk_err <= 1'b0; end
            if (in_red) begin
                if (pk_emit) begin pk_n <= 1; pk_l <= {3'b000, r_last}; pk_err <= r_err; end
                else begin pk_n <= pk_n + 1'b1; pk_l[pk_n] <= r_last; pk_err <= pk_err | r_err; end
            end
            rr <= rr_nx;
            for (integer i = 0; i < 6; i = i + 1)
                qc[i] <= qc[i] - (oq_push ? {1'b0, qf[i]} : 5'd0) + (qp_q[i] ? 5'd1 : 5'd0);
            if (|fv_q) fault <= 1'b1;
            if (st_push && fault) fault_sent <= 1'b1;
        end
    end
    // ---- output: +1 stage where slice 0 ORs the other slices' error bits into the header, then the pin registers
    reg w1_v; reg [4*SFW-1:0] w1_d; reg [50:0] w1_h; reg [4*SFW-1:0] bd_q; reg [50:0] bh_q; reg bv_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin w1_v <= 1'b0; pe_o <= 1'b0; lf <= 2'd0; end
        else begin
            w1_v <= oq_push; pe_o <= pe;
            lf <= {e_flt, mq_flt};
        end
    always @(posedge ck) begin w1_d <= b_d; w1_h <= hdr; end
    assign ow_v = w1_v; assign ow_d = w1_d; assign ow_h = w1_h;
    // pe_q (pin flops) holds the other slices' error bits of the word now in bd_q / bh_q (emit + 2)
    generate if (SEAM != 0) begin : g_oseam                    // the output stage is the dsfd_coll_ceso leaf
        always @(*) begin bw_v = 1'b0; bw_d = {(S == 0 ? 563 : 512){1'b0}}; bv_q = 1'b0; bd_q = {4*SFW{1'b0}}; bh_q = 51'd0; end
        wire unused_o = &{1'b0, bv_q, bd_q, bh_q, pe_q};
    end else begin : g_oflat
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin bv_q <= 1'b0; bw_v <= 1'b0; end
        else begin bv_q <= w1_v; bw_v <= bv_q; end
    always @(posedge ck) begin
        bd_q <= w1_d;
        bh_q <= w1_h;
    end
    if (S == 0) begin : g_o0
`ifdef OT_S81PH_MUT_CEH
        always @(posedge ck) bw_d <= {bd_q, bh_q};            // negative control: the other slices' errors are lost
`else
        always @(posedge ck) bw_d <= {bd_q, bh_q[50:16], bh_q[15] | (|pe_q), bh_q[14:0]};
`endif
    end else begin : g_on
        always @(posedge ck) bw_d <= bd_q;
        wire unused_h = &{1'b0, bh_q, pe_q};
    end
    end endgenerate
    wire unused_ok = &{1'b0, o_rank, e_code, o_d, e_txv[0], e_cro[1:0]};
endmodule

// ------------------------------------------------------------------------------------------------ lane link tile
// KIND 0: engine port (lanes 0..2); KIND 1: pass-through (lanes 3..7)
module dsfd_coll_cel #(parameter integer KIND = 0, parameter integer XD = 6) (
    input  wire              ck, input wire rs,
    input  wire              e_en,
    // lane face (credit link both ways, 553 = {last, payload 552})
    output wire              f_lo_v, input wire f_lo_r, output wire [552:0] f_lo_d,
    input  wire              f_li_v, output wire f_li_r, input wire [552:0] f_li_d,
    input  wire [2:0]        x_flt, output reg [3:0] lf,    // {tx-buffer fault, lane fault triplet}
    // KIND 0: slices -> tx records (4 x 163, ctrl from slice 0), room flag, credits; rx -> the source's FIFO tile
    input  wire              tx_v, input wire [4*163-1:0] tx_d, output reg tx_rdy,
    input  wire [1:0]        cr_o, output reg [1:0] cr_i,
    output reg               rx_v, output reg [546:0] rx_d,
    // KIND 1: VM queue landing in (credit), pass-through out to the 4 slices (credit from slice 0)
    input  wire              q_v, input wire [552:0] q_d, output wire q_cr,
    output wire              p_v, output wire [168+3*129:0] p_d, input wire p_cr
);
    localparam integer PW = 547, W = 552;
    reg [1:0] rst_s;
    always @(posedge ck or negedge rs) if (!rs) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    reg en_q, erst_n;
    always @(posedge ck or negedge rst_n) if (!rst_n) begin en_q <= 1'b0; erst_n <= 1'b0; end else begin en_q <= e_en; erst_n <= en_q; end
    // face credit link (the flat ce's g_l)
    wire x_lo_v, x_lo_r, x_li_v, x_li_r; wire [552:0] x_lo_d, x_li_d; wire ff;
    ot_link_credit_tx #(.W(553), .CRED(8)) u_so (.clk(ck), .rst_n(rst_n), .i_valid(x_lo_v), .i_ready(x_lo_r),
        .i_data(x_lo_d), .l_valid(f_lo_v), .l_data(f_lo_d), .l_credit(f_lo_r));
    ot_link_credit_rx #(.W(553), .DEPTH(8), .OREG(0), .WFREE(1), .RREP(16)) u_si (.clk(ck), .rst_n(rst_n), .l_valid(f_li_v),
        .l_data(f_li_d), .l_credit(f_li_r), .o_valid(x_li_v), .o_ready(x_li_r), .o_data(x_li_d), .fault(ff));
    reg [2:0] xf_q; reg skf;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin xf_q <= 3'd0; lf <= 4'd0; end else begin xf_q <= x_flt; lf <= {skf, xf_q}; end
    generate if (KIND == 0) begin : g_ep
        // tx: assemble the record from the 4 slices, buffer, piggyback credit returns (as the flat core's g_ep)
        reg tv_q; reg [4*163-1:0] td_q; reg [1:0] cro_q;
        always @(posedge ck or negedge erst_n) if (!erst_n) begin tv_q <= 1'b0; cro_q <= 2'd0; end else begin tv_q <= tx_v; cro_q <= cr_o; end
        always @(posedge ck) td_q <= tx_d;
`ifdef OT_S81PH_MUT_CEL
        // negative control: slices 1 and 2 swapped in the record sent to the remote dies
        wire [PW-1:0] rec = {td_q[162:128], td_q[3*163 +: 128], td_q[163 +: 128], td_q[2*163 +: 128], td_q[127:0]};
`else
        wire [PW-1:0] rec = {td_q[162:128], td_q[3*163 +: 128], td_q[2*163 +: 128], td_q[163 +: 128], td_q[127:0]};
`endif
        wire sk_hv, sk_f; wire [PW-1:0] sk_hd;
        wire flit_go = x_lo_v && x_lo_r;
        reg [9:0] crx0, crx1, crs0, crs1;
        wire [1:0] cs0 = (crs0 > 3) ? 2'd3 : crs0[1:0], cs1 = (crs1 > 3) ? 2'd3 : crs1[1:0];
        ot_s81ph_hfifo #(.W(PW), .D(16), .RREP(16)) u_sk (.clk(ck), .rst_n(erst_n), .push(tv_q), .wd(rec), .pop(flit_go && sk_hv),
            .hv(sk_hv), .hd(sk_hd), .fault(sk_f));
        // room flag for the slices: registered here, registered there; covers the pushes in flight (<= 4)
        reg [5:0] occ;
        always @(posedge ck or negedge erst_n)
            if (!erst_n) begin occ <= 0; tx_rdy <= 1'b0; skf <= 1'b0; end
            else begin
                occ <= occ + (tv_q ? 1'b1 : 1'b0) - ((flit_go && sk_hv) ? 1'b1 : 1'b0);
                tx_rdy <= (occ + (tv_q ? 1'b1 : 1'b0)) <= 6'd17 - 6'd8;
                if (sk_f) skf <= 1'b1;
            end
        assign x_lo_v = erst_n && (sk_hv || crs0 != 0 || crs1 != 0);
`ifdef OT_S81PH_MUT_NOCREDIT
        assign x_lo_d = {1'b0, 2'b00, 2'b00, sk_hv, sk_hd};
`else
        assign x_lo_d = {1'b0, cs1, cs0, sk_hv, sk_hd};
`endif
        assign x_li_r = 1'b1;
        wire [1:0] in0 = x_li_v ? x_li_d[PW + 1 +: 2] : 2'd0;
        wire [1:0] in1 = x_li_v ? x_li_d[PW + 3 +: 2] : 2'd0;
        always @(posedge ck or negedge erst_n) begin
            if (!erst_n) begin
                crx0 <= 0; crx1 <= 0; crs0 <= 0; crs1 <= 0; rx_v <= 1'b0; cr_i <= 2'd0;
            end else begin
                rx_v <= x_li_v && x_li_d[PW];
                crx0 <= crx0 - ((crx0 != 0) ? 1'b1 : 1'b0) + in0;
                crx1 <= crx1 - ((crx1 != 0) ? 1'b1 : 1'b0) + in1;
                cr_i <= {crx1 != 0, crx0 != 0};
                crs0 <= crs0 + (cro_q[0] ? 1'b1 : 1'b0) - (flit_go ? cs0 : 2'd0);
                crs1 <= crs1 + (cro_q[1] ? 1'b1 : 1'b0) - (flit_go ? cs1 : 2'd0);
            end
        end
        always @(posedge ck) if (x_li_v) rx_d <= x_li_d[PW-1:0];
        assign q_cr = 1'b0; assign p_v = 1'b0; assign p_d = {(169+3*129){1'b0}};
        wire unused_k = &{1'b0, q_v, q_d, p_cr};
    end else begin : g_pt
        // tx: the VM queue's records land here (credit), then leave on the lane
        ot_link_credit_rx #(.W(553), .DEPTH(XD), .OREG(0), .WFREE(2)) u_lq (.clk(ck), .rst_n(rst_n), .l_valid(q_v),
            .l_data(q_d), .l_credit(q_cr), .o_valid(x_lo_v), .o_ready(x_lo_r), .o_data(x_lo_d), .fault());
        // rx: the lane's records to the 4 slices' landings (credit from slice 0)
        reg pcr_q;
        always @(posedge ck or negedge rst_n) if (!rst_n) pcr_q <= 1'b0; else pcr_q <= p_cr;
        wire [552:0] ld;
        ot_link_credit_tx #(.W(553), .CRED(XD), .DFREE(1)) u_pt (.clk(ck), .rst_n(rst_n), .i_valid(x_li_v),
            .i_ready(x_li_r), .i_data(x_li_d), .l_valid(p_v), .l_data(ld), .l_credit(pcr_q));
        // slice 0: {last, data[551:512], data[127:0]}; slice s: {last, data[s*128 +: 128]}
`ifdef OT_S81PH_MUT_CEL
        // negative control: slices 1 and 2 swapped in the pass-through split
        assign p_d = {ld[552], ld[3*128 +: 128], ld[552], ld[128 +: 128], ld[552], ld[2*128 +: 128],
                      ld[552], ld[551:512], ld[127:0]};
`else
        assign p_d = {ld[552], ld[3*128 +: 128], ld[552], ld[2*128 +: 128], ld[552], ld[128 +: 128],
                      ld[552], ld[551:512], ld[127:0]};
`endif
        always @(posedge ck or negedge rst_n) if (!rst_n) begin tx_rdy <= 1'b0; cr_i <= 2'd0; rx_v <= 1'b0; skf <= 1'b0; end
        always @(posedge ck) rx_d <= {PW{1'b0}};
        wire unused_k = &{1'b0, tx_v, tx_d, cr_o, erst_n};
    end endgenerate
    wire unused_f = &{1'b0, ff};
endmodule

// ------------------------------------------------------------------------------------------------ VM queue tile
// ------------------------------------------------------------------------------------------------ VM queue tiles
// el1011-ds-coll 21:45 (ceq p7 -29.4 / FF -50.7: the 586-bit record broadcast to 6 queues stacked over 680 um + one
// 11.3k-flop clock root over 679 um).  ceq is split into one hardened tile PER QUEUE (140.4 x 203.04, 3 macros in one
// column); f_vm reaches the queues as an abutted, registered nearest-neighbour chain (each tile forwards a kept copy
// of its input one cycle later), the overflow faults return along a registered chain into ceq0's fault collector.
module dsfd_coll_ceqt #(parameter integer Q0 = 0, parameter integer XD = 6, parameter integer QD = 8,
                        parameter integer OW = Q0 ? 4 * 162 : 553) (
    input  wire          ck, input wire rs,
    input  wire [591:0]  f_i,                               // pin side (S)
    output wire [591:0]  f_o,                               // registered copy to the next tile (N)
    input  wire [2:0]    lid,                               // p tile: link id strap (queue j: j - 1)
    output wire          o_v, output wire [OW-1:0] o_d, input wire o_cr,
    output wire          qp,                                // queue pop, registered
    output wire          rst_n_o,                           // synchronised reset (tile-local)
    output wire [591:0]  f,                                 // pin-flopped record (tile-local)
    output reg           qf                                 // queue overflow, registered
);
    localparam integer W = 552;
    reg [1:0] rst_s;
    always @(posedge ck or negedge rs) if (!rs) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    assign rst_n_o = rst_n;
    reg fv_v; reg [591:1] fv_p;                             // pin flops
    always @(posedge ck or negedge rst_n) if (!rst_n) fv_v <= 1'b0; else fv_v <= f_i[0];
    always @(posedge ck) fv_p <= f_i[591:1];
    assign f = {fv_p, fv_v};
    // forward copy: separate kept flops straight from the pins (a merged flop would drive the N face and the local
    // decode from one Q)
    (* keep = "true" *) reg fo_v; (* keep = "true" *) reg [591:1] fo_p;
    always @(posedge ck or negedge rst_n) if (!rst_n) fo_v <= 1'b0; else fo_v <= f_i[0];
    always @(posedge ck) fo_p <= f_i[591:1];
    assign f_o = {fo_p, fo_v};
    reg [2:0] lid_q; always @(posedge ck) lid_q <= lid;
    wire fvv = f[0]; wire [1:0] ftype = f[2:1]; wire [2:0] flink = f[5:3];
    reg psh_q; reg [W+33:0] rec;                            // {last, mode, tag, data}
    always @(posedge ck or negedge rst_n)
        if (!rst_n) psh_q <= 1'b0;
        else psh_q <= fvv && ((Q0 != 0) ? (ftype == 2'd1) : (ftype == 2'd2 && flink == lid_q));
    always @(posedge ck) rec <= {f[6], f[7], f[39:8], f[40 +: W]};
    wire hv, rdy, ovf; wire [W+33:0] hd;
    ot_fifo_sram_fwft #(.W(W + 34), .DEPTH(QD), .MACRO(2)) u_q (.clk(ck), .rst_n(rst_n),
        .push(psh_q), .wdata(rec), .pop(hv && rdy), .hv(hv), .head(hd), .ovf(ovf));
    reg cr_q; always @(posedge ck or negedge rst_n) if (!rst_n) cr_q <= 1'b0; else cr_q <= o_cr;
    wire [OW-1:0] od;
    generate if (Q0 != 0) begin : g_q0
        assign od = {{hd[W+33], hd[W+32], hd[W +: 32], hd[384 +: 128]}, {hd[W+33], hd[W+32], hd[W +: 32], hd[256 +: 128]},
                     {hd[W+33], hd[W+32], hd[W +: 32], hd[128 +: 128]}, {hd[W+33], hd[W+32], hd[W +: 32], hd[0 +: 128]}};
    end else begin : g_qp
        assign od = {hd[W+33], hd[W-1:0]};
    end endgenerate
    ot_link_credit_tx #(.W(OW), .CRED(XD), .DFREE(1)) u_t (.clk(ck), .rst_n(rst_n), .i_valid(hv),
        .i_ready(rdy), .i_data(od), .l_valid(o_v), .l_data(o_d), .l_credit(cr_q));
    (* keep = "true" *) reg qp_k;
    always @(posedge ck or negedge rst_n) if (!rst_n) begin qp_k <= 1'b0; qf <= 1'b0; end
                                          else begin qp_k <= hv && rdy; qf <= ovf; end
    assign qp = qp_k;
endmodule

// queue 0 (-> the engine slices) + rank / enable decode + fault collector.  Hard tile: no parameters.
module dsfd_coll_ceq0 (
    input  wire              ck, input wire rs,
    input  wire [591:0]      fvm_u,                         // S: from cb (f_vm pass-through)
    output wire [591:0]      f_o,                           // N: to ceqp 1
    output reg               e_en, output reg [1:0] rank, output wire qp, output reg [7:0] fv,
    output wire              q_v, output wire [4*162-1:0] q_d, input wire q_cr,
    input  wire [8*4-1:0]    lane_f, input wire [4*2-1:0] slice_f, input wire [2:0] fifo_f, input wire bw_flt,
    input  wire              qf_i                           // N: overflow chain from ceqp 1
);
    wire rst_n, qf0; wire [591:0] f;
    dsfd_coll_ceqt #(.Q0(1), .QD(16)) u_c (.ck(ck), .rs(rs), .f_i(fvm_u), .f_o(f_o), .lid(3'd0), .o_v(q_v), .o_d(q_d),
        .o_cr(q_cr), .qp(qp), .rst_n_o(rst_n), .f(f), .qf(qf0));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin e_en <= 1'b0; rank <= 2'd0; end
        else if (f[0] && f[2:1] == 2'd3) begin rank <= f[41:40]; e_en <= f[42]; end
    // fault vector {lane, mq, oq, queue, engine, gearbox, endpoint, tx buffer} (the flat core's fv_flt), sticky
    reg [31:0] lf_q; reg [7:0] sf_q; reg [2:0] ff_q; reg bf_q, qi_q;
    reg [7:0] lane_st;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin fv <= 8'd0; lf_q <= 0; sf_q <= 0; ff_q <= 0; bf_q <= 1'b0; qi_q <= 1'b0; lane_st <= 0; end
        else begin
            lf_q <= lane_f; sf_q <= slice_f; ff_q <= fifo_f; bf_q <= bw_flt; qi_q <= qf_i;
            for (integer i = 0; i < 8; i = i + 1) if (lf_q[4*i+2]) lane_st[i] <= 1'b1;
            fv <= fv | {|lane_st, sf_q[0] | sf_q[2] | sf_q[4] | sf_q[6], bf_q, qf0 | qi_q,
                        sf_q[1] | sf_q[3] | sf_q[5] | sf_q[7] | (|ff_q),
                        lf_q[1] | lf_q[5] | lf_q[9] | lf_q[13] | lf_q[17] | lf_q[21] | lf_q[25] | lf_q[29],
                        lf_q[0] | lf_q[4] | lf_q[8] | lf_q[12] | lf_q[16] | lf_q[20] | lf_q[24] | lf_q[28],
                        lf_q[3] | lf_q[7] | lf_q[11] | lf_q[15] | lf_q[19] | lf_q[23] | lf_q[27] | lf_q[31]};
        end
endmodule

// one pass-through VM queue (queue j = lid + 1 -> lane).  Hard tile: no parameters.
module dsfd_coll_ceqp (
    input  wire          ck, input wire rs,
    input  wire [591:0]  f_i,                               // S
    output wire [591:0]  f_o,                               // N
    input  wire [2:0]    lid,                               // W strap
    output wire          p_v, output wire [552:0] p_d, input wire p_cr,
    output wire          qp,
    input  wire          qf_i,                              // N
    output reg           qf_o                               // S
);
    wire rst_n, qf; wire [591:0] f;
    dsfd_coll_ceqt #(.Q0(0), .QD(8)) u_c (.ck(ck), .rs(rs), .f_i(f_i), .f_o(f_o), .lid(lid), .o_v(p_v), .o_d(p_d),
        .o_cr(p_cr), .qp(qp), .rst_n_o(rst_n), .f(f), .qf(qf));
    reg qi_q;
    always @(posedge ck or negedge rst_n) if (!rst_n) begin qi_q <= 1'b0; qf_o <= 1'b0; end
                                          else begin qi_q <= qf_i; qf_o <= qi_q | qf; end
    wire unused_ok = &{1'b0, f};
endmodule

// composition (wiring only): ceq0 + 5 x ceqp, abutted S -> N
module dsfd_coll_ceq #(parameter integer XD = 6, parameter integer QD0 = 16, parameter integer QD = 8) (
    input  wire              ck, input wire rs,
    input  wire [591:0]      fvm_u,                         // from cb (f_vm pass-through)
    output wire              e_en, output wire [1:0] rank, output wire [5:0] qp, output wire [7:0] fv,
    output wire              q_v, output wire [4*162-1:0] q_d, input wire q_cr,
    output wire [4:0]        p_v, output wire [5*553-1:0] p_d, input wire [4:0] p_cr,
    input  wire [8*4-1:0]    lane_f,                        // per lane {tx-buffer fault, lane fault triplet}
    input  wire [4*2-1:0]    slice_f,                       // per slice {e_flt, mq_flt}
    input  wire [2:0]        fifo_f,                        // remote FIFO tiles
    input  wire              bw_flt
);
    generate if (XD != 6 || QD0 != 16 || QD != 8) begin : g_bad
        initial $error("dsfd_coll_ceq: hard tiles are built at XD 6 / QD0 16 / QD 8");
    end endgenerate
    wire [591:0] fc [0:5]; wire [6:1] qfc;
    assign qfc[6] = 1'b0;
    dsfd_coll_ceq0 u_q0 (.ck(ck), .rs(rs), .fvm_u(fvm_u), .f_o(fc[0]), .e_en(e_en), .rank(rank), .qp(qp[0]), .fv(fv),
        .q_v(q_v), .q_d(q_d), .q_cr(q_cr), .lane_f(lane_f), .slice_f(slice_f), .fifo_f(fifo_f), .bw_flt(bw_flt),
        .qf_i(qfc[1]));
    genvar j;
    generate for (j = 1; j < 6; j = j + 1) begin : g_p
        localparam [2:0] LID = j - 1;
        dsfd_coll_ceqp u_p (.ck(ck), .rs(rs), .f_i(fc[j-1]), .f_o(fc[j]), .lid(LID), .p_v(p_v[j-1]),
            .p_d(p_d[(j-1)*553 +: 553]), .p_cr(p_cr[j-1]), .qp(qp[j]), .qf_i(qfc[j+1]), .qf_o(qfc[j]));
    end endgenerate
endmodule

// ------------------------------------------------------------------------------------------------ composition
module dsfd_coll_ceh #(parameter integer OD = 16, parameter integer CR = 1, parameter integer PULL = 1,
    parameter integer RSTR = 0, parameter integer PCOPY = 1, parameter integer CEX = 1, parameter integer QPIPE = 1) (
    input  wire [0:0]       ck,
    input  wire [0:0]       rs,
    output wire [1:0]       wlo_v,  input  wire [1:0] wlo_r, output wire [2*553-1:0] wlo_d,
    input  wire [1:0]       wli_v,  output wire [1:0] wli_r, input  wire [2*553-1:0] wli_d,
    input  wire [5:0]       wflt,
    output wire [1:0]       elo_v,  input  wire [1:0] elo_r, output wire [2*553-1:0] elo_d,
    input  wire [1:0]       eli_v,  output wire [1:0] eli_r, input  wire [2*553-1:0] eli_d,
    input  wire [5:0]       eflt,
    input  wire [591:0]     fvm_u,
    input  wire [5:0]       flt_u,
    output wire [0:0] lo0_v,  input wire [0:0] lo0_r, output wire [552:0] lo0_d,
    input wire [0:0] li0_v,  output wire [0:0] li0_r, input  wire [552:0] li0_d,
    output wire [0:0] lo4_v,  input wire [0:0] lo4_r, output wire [552:0] lo4_d,
    input wire [0:0] li4_v,  output wire [0:0] li4_r, input  wire [552:0] li4_d,
    output wire [0:0] bw_v,
    output wire [2099:1]    bw_d,
    input wire [0:0] bw_cr,
    input wire [0:0] bw_flt,
    output wire [0:0] lo3_v,  input wire [0:0] lo3_r, output wire [552:0] lo3_d,
    input wire [0:0] li3_v,  output wire [0:0] li3_r, input  wire [552:0] li3_d,
    output wire [0:0] lo7_v,  input wire [0:0] lo7_r, output wire [552:0] lo7_d,
    input wire [0:0] li7_v,  output wire [0:0] li7_r, input  wire [552:0] li7_d,
    input  wire [5:0]       flt_d
);
    wire c = ck[0], r = rs[0];
    // lane faces: [l] = lane l
    wire [7:0] lo_v, lo_r, li_v, li_r; wire [552:0] lo_d [0:7]; wire [552:0] li_d [0:7]; wire [2:0] lflt [0:7];
    assign lo0_v = lo_v[0]; assign lo_r[0] = lo0_r; assign lo0_d = lo_d[0]; assign li_v[0] = li0_v; assign li0_r = li_r[0]; assign li_d[0] = li0_d;
    assign lo4_v = lo_v[4]; assign lo_r[4] = lo4_r; assign lo4_d = lo_d[4]; assign li_v[4] = li4_v; assign li4_r = li_r[4]; assign li_d[4] = li4_d;
    assign lo3_v = lo_v[3]; assign lo_r[3] = lo3_r; assign lo3_d = lo_d[3]; assign li_v[3] = li3_v; assign li3_r = li_r[3]; assign li_d[3] = li3_d;
    assign lo7_v = lo_v[7]; assign lo_r[7] = lo7_r; assign lo7_d = lo_d[7]; assign li_v[7] = li7_v; assign li7_r = li_r[7]; assign li_d[7] = li7_d;
    genvar k;
    generate for (k = 0; k < 2; k = k + 1) begin : g_loc
        assign wlo_v[k] = lo_v[1 + k]; assign lo_r[1 + k] = wlo_r[k]; assign wlo_d[k*553 +: 553] = lo_d[1 + k];
        assign li_v[1 + k] = wli_v[k]; assign wli_r[k] = li_r[1 + k]; assign li_d[1 + k] = wli_d[k*553 +: 553];
        assign elo_v[k] = lo_v[5 + k]; assign lo_r[5 + k] = elo_r[k]; assign elo_d[k*553 +: 553] = lo_d[5 + k];
        assign li_v[5 + k] = eli_v[k]; assign eli_r[k] = li_r[5 + k]; assign li_d[5 + k] = eli_d[k*553 +: 553];
    end endgenerate
    assign lflt[0] = flt_u[2:0]; assign lflt[1] = wflt[2:0]; assign lflt[2] = wflt[5:3]; assign lflt[3] = flt_d[2:0];
    assign lflt[4] = flt_u[5:3]; assign lflt[5] = eflt[2:0]; assign lflt[6] = eflt[5:3]; assign lflt[7] = flt_d[5:3];
    // broadcasts
    wire e_en; wire [1:0] rank; wire [5:0] qp; wire [7:0] fv;
    // q0, pass-through queue streams
    wire q_v, q_cr; wire [4*162-1:0] q_d;
    wire [4:0] pq_v, pq_cr; wire [5*553-1:0] pq_d;
    // engine ports
    wire [3:1] tx_v_s [0:3]; wire [162:0] tx_d_s [0:3]; wire [3:1] tx_rdy; wire [7:2] cr_i; wire [7:2] cr_o_s [0:3];
    wire [3:1] rx_v; wire [546:0] rx_d [1:3];
    // remote FIFO tiles -> slices
    wire [1:0] xv [1:3]; wire [8*163-1:0] xd [1:3]; wire [7:0] xl_cr_s [0:3]; wire [2:0] fifo_f;
    // pass-through lanes -> slices
    wire [4:0] p_v; wire [169+3*129-1:0] p_d [0:4];
    wire [4:0] p_cr_s [0:3];
    wire [8*4-1:0] lane_f; wire [7:0] slice_f; wire [3:0] pe;
    wire [3:0] q_cr_s;
    dsfd_coll_ceq u_q (.ck(c), .rs(r), .fvm_u(fvm_u), .e_en(e_en), .rank(rank), .qp(qp), .fv(fv),
        .q_v(q_v), .q_d(q_d), .q_cr(q_cr_s[0]), .p_v(pq_v), .p_d(pq_d), .p_cr(pq_cr),
        .lane_f(lane_f), .slice_f(slice_f), .fifo_f(fifo_f), .bw_flt(bw_flt[0]));
    generate for (k = 0; k < 8; k = k + 1) begin : g_l
        if (k < 3) begin : g_e
            dsfd_coll_cel #(.KIND(0)) u_l (.ck(c), .rs(r), .e_en(e_en),
                .f_lo_v(lo_v[k]), .f_lo_r(lo_r[k]), .f_lo_d(lo_d[k]), .f_li_v(li_v[k]), .f_li_r(li_r[k]), .f_li_d(li_d[k]),
                .x_flt(lflt[k]), .lf(lane_f[4*k +: 4]),
                .tx_v(tx_v_s[0][k + 1]), .tx_d({tx_d_s[3], tx_d_s[2], tx_d_s[1], tx_d_s[0]}), .tx_rdy(tx_rdy[k + 1]),
                .cr_o(cr_o_s[0][2*(k+1) +: 2]), .cr_i(cr_i[2*(k+1) +: 2]), .rx_v(rx_v[k + 1]), .rx_d(rx_d[k + 1]),
                .q_v(1'b0), .q_d(553'd0), .q_cr(), .p_v(), .p_d(), .p_cr(1'b0));
        end else begin : g_p
            dsfd_coll_cel #(.KIND(1)) u_l (.ck(c), .rs(r), .e_en(e_en),
                .f_lo_v(lo_v[k]), .f_lo_r(lo_r[k]), .f_lo_d(lo_d[k]), .f_li_v(li_v[k]), .f_li_r(li_r[k]), .f_li_d(li_d[k]),
                .x_flt(lflt[k]), .lf(lane_f[4*k +: 4]),
                .tx_v(1'b0), .tx_d({4*163{1'b0}}), .tx_rdy(), .cr_o(2'b00), .cr_i(), .rx_v(), .rx_d(),
                .q_v(pq_v[k - 3]), .q_d(pq_d[(k-3)*553 +: 553]), .q_cr(pq_cr[k - 3]),
                .p_v(p_v[k - 3]), .p_d(p_d[k - 3]), .p_cr(p_cr_s[0][k - 3]));
        end
    end endgenerate
    generate for (k = 1; k < 4; k = k + 1) begin : g_f
        dsfd_coll_cef #(.PD(`ifdef OT_S81PH_COLL_CSTRESS 8 `else 256 `endif)) u_f (.ck(c), .rs(r), .e_en(e_en), .rx_v(rx_v[k]), .rx_d(rx_d[k]), .x_v(xv[k]), .x_d(xd[k]),
            .x_cr(xl_cr_s[0][2*k +: 2]), .flt(fifo_f[k - 1]));
    end endgenerate
    // slices
    wire [3:0] bwv_s; wire [562:0] bwd0; wire [511:0] bwd_s [1:3];
    // SEAM_V[s] = slice s is the split lane-slice.  OT_S81PH_MUT_LOCKSTEP (negative control): slice 3 is the flat slice at
    // the old latency -- the lockstep assertion below refuses it; with OT_S81PH_LOCKSTEP_NOASSERT the bench must.
`ifdef OT_S81PH_COLL_CES_SPLIT
    localparam [3:0] SEAM_V = `ifdef OT_S81PH_MUT_LOCKSTEP 4'b0111 `else 4'b1111 `endif;
`else
    localparam [3:0] SEAM_V = 4'b0000;
`endif
    genvar s;
    generate for (s = 0; s < 4; s = s + 1) begin : g_s
        localparam integer PTW = (s == 0) ? 169 : 129;
        wire [5*PTW-1:0] ptd;
        for (k = 0; k < 5; k = k + 1) begin : g_pd
            if (s == 0) begin : g_0 assign ptd[k*PTW +: PTW] = p_d[k][168:0]; end
            else begin : g_n assign ptd[k*PTW +: PTW] = p_d[k][169 + (s-1)*129 +: 129]; end
        end
        wire [7:0] xlv = {xv[3], xv[2], xv[1], 2'b00};
        wire [8*163-1:0] xld = {xd[3][(4+s)*163 +: 163], xd[3][s*163 +: 163], xd[2][(4+s)*163 +: 163], xd[2][s*163 +: 163],
                                xd[1][(4+s)*163 +: 163], xd[1][s*163 +: 163], {2*163{1'b0}}};
        wire [(s == 0 ? 563 : 512)-1:0] bwd;
        wire po;
`ifdef OT_S81PH_COLL_CES_SPLIT
        if (!SEAM_V[s]) begin : g_flat                         // split lane-slices (route masters)
            dsfd_coll_ces #(.S(s)) u_s (.ck(c), .rs(r), .e_en(e_en), .rank_i(rank), .qp(qp), .fv_i(fv),
                .q_v(q_v), .q_d(q_d[s*162 +: 162]), .q_cr(q_cr_s[s]),
                .xl_v(xlv), .xl_d(xld), .xl_cr(xl_cr_s[s]),
                .tx_v(tx_v_s[s]), .tx_d(tx_d_s[s]), .tx_rdy(tx_rdy), .cr_i(cr_i), .cr_o(cr_o_s[s]),
                .pt_v(p_v), .pt_d(ptd), .pt_cr(p_cr_s[s]),
                .bw_cr(bw_cr[0]), .bw_v(bwv_s[s]), .bw_d(bwd), .lf(slice_f[2*s +: 2]), .pe_o(pe[s]), .pe_i(pe[3:1]),
                .ow_v(), .ow_d(), .ow_h(), .ln_v(), .ln_d(), .ln_y(128'd0), .ln_yv(4'd0), .ln_ye(8'd0), .ln_pe(4'd0));
        end else if (s == 0) begin : g_sp0
            dsfd_coll_ces0 u_s (.ck(c), .rs(r), .e_en(e_en), .rank_i(rank), .qp(qp), .fv_i(fv),
                .q_v(q_v), .q_d(q_d[s*162 +: 162]), .q_cr(q_cr_s[s]),
                .xl_v(xlv), .xl_d(xld), .xl_cr(xl_cr_s[s]),
                .tx_v(tx_v_s[s]), .tx_d(tx_d_s[s]), .tx_rdy(tx_rdy), .cr_i(cr_i), .cr_o(cr_o_s[s]),
                .pt_v(p_v), .pt_d(ptd), .pt_cr(p_cr_s[s]),
                .bw_cr(bw_cr[0]), .bw_v(bwv_s[s]), .bw_d(bwd), .lf(slice_f[2*s +: 2]), .pe_o(pe[s]), .pe_i(pe[3:1]));
        end else begin : g_spn
            dsfd_coll_cesn u_s (.ck(c), .rs(r), .e_en(e_en), .rank_i(rank), .qp(qp), .fv_i(fv),
                .q_v(q_v), .q_d(q_d[s*162 +: 162]), .q_cr(q_cr_s[s]),
                .xl_v(xlv), .xl_d(xld), .xl_cr(xl_cr_s[s]),
                .tx_v(tx_v_s[s]), .tx_d(tx_d_s[s]), .tx_rdy(tx_rdy), .cr_i(cr_i), .cr_o(cr_o_s[s]),
                .pt_v(p_v), .pt_d(ptd), .pt_cr(p_cr_s[s]),
                .bw_cr(bw_cr[0]), .bw_v(bwv_s[s]), .bw_d(bwd), .lf(slice_f[2*s +: 2]), .pe_o(pe[s]));
        end
`else
        dsfd_coll_ces #(.S(s)) u_s (.ck(c), .rs(r), .e_en(e_en), .rank_i(rank), .qp(qp), .fv_i(fv),
            .q_v(q_v), .q_d(q_d[s*162 +: 162]), .q_cr(q_cr_s[s]),
            .xl_v(xlv), .xl_d(xld), .xl_cr(xl_cr_s[s]),
            .tx_v(tx_v_s[s]), .tx_d(tx_d_s[s]), .tx_rdy(tx_rdy), .cr_i(cr_i), .cr_o(cr_o_s[s]),
            .pt_v(p_v), .pt_d(ptd), .pt_cr(p_cr_s[s]),
            .bw_cr(bw_cr[0]), .bw_v(bwv_s[s]), .bw_d(bwd), .lf(slice_f[2*s +: 2]), .pe_o(pe[s]), .pe_i(pe[3:1]),
            .ow_v(), .ow_d(), .ow_h(), .ln_v(), .ln_d(), .ln_y(128'd0), .ln_yv(4'd0), .ln_ye(8'd0), .ln_pe(4'd0));
`endif
        if (s == 0) begin : g_b0 assign bwd0 = bwd; end
        else begin : g_bn assign bwd_s[s] = bwd; end
    end endgenerate
    // LOCKSTEP (s81-cesn 2026-10-13, coordinator rule): no slice may run at a seam latency different from the others
`ifndef OT_S81PH_LOCKSTEP_NOASSERT
    generate if (SEAM_V != 4'b0000 && SEAM_V != 4'b1111) begin : g_lockstep_refused
        initial begin
            $display("TB_S81PH_COLL_SYS FAIL lockstep: slices at different seam latencies (split mask %b)", SEAM_V);
            $fatal(1, "dsfd_coll_ceh: lockstep violated");
        end
    end endgenerate
`endif
    assign q_cr = q_cr_s[0];
    // b_word = {b_d[2047:0], header[50:0]}; b_d[w*512 + s*128 + i] = slice s word w bit i
    assign bw_v[0] = bwv_s[0];
    assign bw_d[51:1] = bwd0[50:0];
    generate for (s = 0; s < 4; s = s + 1) begin : g_bw
        for (k = 0; k < 4; k = k + 1) begin : g_w
            if (s == 0) begin : g_0 assign bw_d[52 + k*512 + s*128 +: 128] = bwd0[51 + k*128 +: 128]; end
            else begin : g_n assign bw_d[52 + k*512 + s*128 +: 128] = bwd_s[s][k*128 +: 128]; end
        end
    end endgenerate
    wire unused_ok = &{1'b0, bwv_s[3:1], q_cr_s[3:1], tx_v_s[1], tx_v_s[2], tx_v_s[3], cr_o_s[1], cr_o_s[2], cr_o_s[3],
                       xl_cr_s[1], xl_cr_s[2], xl_cr_s[3], p_cr_s[1], p_cr_s[2], p_cr_s[3], xl_cr_s[0][1:0]};
endmodule

// ---- route masters (one per hardened variant; the composition instantiates the parameterised modules above)
// ---- split lane-slice (s81-cesn 2026-10-13): hardened leaves + wires-only parents.  ces0 and cesn are the SAME structure
// (same lane / xl-relay leaves, one parameterised parent, their own core and pass-through-relay masters).
// lane leaf: one FP32 lane of the pairwise reduce, ((a + b) + (c + d)); pin flops in, the adders' output flops out.
// e_en builds the engine reset exactly as the core does (same two flops), so lane and core reset on the same cycle.
module dsfd_coll_cesl (input wire ck, input wire rs, input wire e_en, input wire i_v, input wire [127:0] i_d,
    output wire [31:0] o_y, output wire o_yv, output wire [1:0] o_ye, output wire o_pe);
    reg [1:0] rst_s;
    always @(posedge ck or negedge rs) if (!rs) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    reg en_q, erst_n;
    always @(posedge ck or negedge rst_n) if (!rst_n) begin en_q <= 1'b0; erst_n <= 1'b0; end else begin en_q <= e_en; erst_n <= en_q; end
    reg v_q; reg [127:0] d_q;                                 // pin flops
    always @(posedge ck or negedge erst_n) if (!erst_n) v_q <= 1'b0; else v_q <= i_v;
    always @(posedge ck) d_q <= i_d;
    wire [31:0] ab, cd; wire av, cv; wire [1:0] ae, ce;
    ot_hdc_fp32_add_fast u_ab (.clk(ck), .rst_n(erst_n), .valid_in(v_q), .a(d_q[31:0]), .b(d_q[63:32]), .y(ab), .err(ae), .valid_out(av));
    ot_hdc_fp32_add_fast u_cd (.clk(ck), .rst_n(erst_n), .valid_in(v_q), .a(d_q[95:64]), .b(d_q[127:96]), .y(cd), .err(ce), .valid_out(cv));
`ifdef OT_S81PH_MUT_CESL
    // negative control (lane leaf): the second level adds (a + b) to itself, the (c + d) half is lost
    ot_hdc_fp32_add_fast u_y (.clk(ck), .rst_n(erst_n), .valid_in(av), .a(ab), .b(ab), .y(o_y), .err(o_ye), .valid_out(o_yv));
    wire unused_cd = &{1'b0, cd};
`else
    ot_hdc_fp32_add_fast u_y (.clk(ck), .rst_n(erst_n), .valid_in(av), .a(ab), .b(cd), .y(o_y), .err(o_ye), .valid_out(o_yv));
`endif
    reg [2:0] pe_d;                                           // first-level errors, aligned to o_ye (the engine's err_delay)
    always @(posedge ck or negedge erst_n) if (!erst_n) pe_d <= 3'd0; else pe_d <= {pe_d[1:0], (|ae) || (|ce)};
    assign o_pe = pe_d[2];
    wire unused_ok = &{1'b0, cv};
endmodule
// xl relay leaf: ONE remote source's two parity links, FIFO tile (cef, XD credits) -> relay -> core landing (XLD slots)
module dsfd_coll_cesx #(parameter integer XD = 6, parameter integer XLD = 3) (input wire ck, input wire rs, input wire e_en,
    input wire [1:0] i_v, input wire [2*163-1:0] i_d, output wire [1:0] i_cr,
    output wire [1:0] o_v, output wire [2*163-1:0] o_d, input wire [1:0] o_cr);
    reg [1:0] rst_s;
    always @(posedge ck or negedge rs) if (!rs) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    reg en_q, erst_n;
    always @(posedge ck or negedge rst_n) if (!rst_n) begin en_q <= 1'b0; erst_n <= 1'b0; end else begin en_q <= e_en; erst_n <= en_q; end
    genvar q;
    generate for (q = 0; q < 2; q = q + 1) begin : g_q
`ifdef OT_S81PH_MUT_CESX
        // negative control (xl relay leaf): the two parity links' data leave on each other's link
        ot_s81ph_cr_relay #(.W(163), .D(XD), .DO(XLD)) u_r (.clk(ck), .rst_n(erst_n), .i_v(i_v[q]), .i_cr(i_cr[q]),
            .i_d(i_d[q*163 +: 163]), .o_v(o_v[q]), .o_cr(o_cr[q]), .o_d(o_d[(1-q)*163 +: 163]));
`else
        ot_s81ph_cr_relay #(.W(163), .D(XD), .DO(XLD)) u_r (.clk(ck), .rst_n(erst_n), .i_v(i_v[q]), .i_cr(i_cr[q]),
            .i_d(i_d[q*163 +: 163]), .o_v(o_v[q]), .o_cr(o_cr[q]), .o_d(o_d[q*163 +: 163]));
`endif
    end endgenerate
endmodule
// pass-through relay leaf: the five pass-through lane links (lane tiles, XD credits) -> relay -> core landing (PTD slots)
module dsfd_coll_cesp #(parameter integer PTW = 129, parameter integer XD = 6, parameter integer PTD = 2) (input wire ck, input wire rs,
    input wire [4:0] i_v, input wire [5*PTW-1:0] i_d, output wire [4:0] i_cr,
    output wire [4:0] o_v, output wire [5*PTW-1:0] o_d, input wire [4:0] o_cr);
    reg [1:0] rst_s;
    always @(posedge ck or negedge rs) if (!rs) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    genvar l;
    generate for (l = 0; l < 5; l = l + 1) begin : g_l
`ifdef OT_S81PH_MUT_CESP
        // negative control (pass-through relay leaf): lanes 0 and 1 leave with each other's data
        localparam integer LO = (l == 0) ? 1 : (l == 1) ? 0 : l;
        ot_s81ph_cr_relay #(.W(PTW), .D(XD), .DO(PTD)) u_r (.clk(ck), .rst_n(rst_n), .i_v(i_v[l]), .i_cr(i_cr[l]),
            .i_d(i_d[l*PTW +: PTW]), .o_v(o_v[l]), .o_cr(o_cr[l]), .o_d(o_d[LO*PTW +: PTW]));
`else
        ot_s81ph_cr_relay #(.W(PTW), .D(XD), .DO(PTD)) u_r (.clk(ck), .rst_n(rst_n), .i_v(i_v[l]), .i_cr(i_cr[l]),
            .i_d(i_d[l*PTW +: PTW]), .o_v(o_v[l]), .o_cr(o_cr[l]), .o_d(o_d[l*PTW +: PTW]));
`endif
    end endgenerate
endmodule
// output-stage leaf (ONE master for ces0 and cesn): the lane-slice's last two register stages.  i_* = the core's w1
// flops; bd_q / bh_q / bv_q are the pin flops, bw_v / bw_d the face registers; slice 0 ORs the other slices' error
// bits (pe_i, pin flops) into header bit 15.  cesn ties i_h / pe_i to 0 and takes bw_d[562:51].  Same reset as the
// core's output stage (rs synchronised here), same cycles: the flat slice's flops, moved.
module dsfd_coll_ceso (input wire ck, input wire rs, input wire i_v, input wire [511:0] i_d, input wire [50:0] i_h,
    input wire [3:1] pe_i, output reg bw_v, output reg [562:0] bw_d);
    reg [1:0] rst_s;
    always @(posedge ck or negedge rs) if (!rs) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    reg bv_q; reg [511:0] bd_q; reg [50:0] bh_q; reg [3:1] pe_q;   // pin flops
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin bv_q <= 1'b0; bw_v <= 1'b0; pe_q <= 3'd0; end
        else begin bv_q <= i_v; bw_v <= bv_q; pe_q <= pe_i; end
    always @(posedge ck) begin bd_q <= i_d; bh_q <= i_h; end
`ifdef OT_S81PH_MUT_CEH
    always @(posedge ck) bw_d <= {bd_q, bh_q};                // negative control: the other slices' errors are lost
    wire unused_pe = &{1'b0, pe_q};
`else
    always @(posedge ck) bw_d <= {bd_q, bh_q[50:16], bh_q[15] | (|pe_q), bh_q[14:0]};
`endif
endmodule
// parameter-free leaf masters
module dsfd_coll_cesp0 (input wire ck, input wire rs, input wire [4:0] i_v, input wire [5*169-1:0] i_d, output wire [4:0] i_cr,
    output wire [4:0] o_v, output wire [5*169-1:0] o_d, input wire [4:0] o_cr);
    dsfd_coll_cesp #(.PTW(169)) u (.*);
endmodule
module dsfd_coll_cespn (input wire ck, input wire rs, input wire [4:0] i_v, input wire [5*129-1:0] i_d, output wire [4:0] i_cr,
    output wire [4:0] o_v, output wire [5*129-1:0] o_d, input wire [4:0] o_cr);
    dsfd_coll_cesp #(.PTW(129)) u (.*);
endmodule
module dsfd_coll_cesc0 (input wire ck, input wire rs, input wire e_en, input wire [1:0] rank_i, input wire [5:0] qp,
    input wire [7:0] fv_i, input wire q_v, input wire [161:0] q_d, output wire q_cr, input wire [7:0] xl_v,
    input wire [8*163-1:0] xl_d, output wire [7:0] xl_cr, output wire [3:1] tx_v, output wire [162:0] tx_d,
    input wire [3:1] tx_rdy, input wire [7:2] cr_i, output wire [7:2] cr_o, input wire [4:0] pt_v,
    input wire [5*169-1:0] pt_d, output wire [4:0] pt_cr, input wire bw_cr,
    output wire ow_v, output wire [511:0] ow_d, output wire [50:0] ow_h,
    output wire [1:0] lf, output wire pe_o,
    output wire ln_v, output wire [511:0] ln_d, input wire [127:0] ln_y, input wire [3:0] ln_yv, input wire [7:0] ln_ye,
    input wire [3:0] ln_pe);
    dsfd_coll_ces #(.S(0), .SEAM(1)) u (.*, .bw_v(), .bw_d(), .pe_i(3'd0));
endmodule
module dsfd_coll_cescn (input wire ck, input wire rs, input wire e_en, input wire [1:0] rank_i, input wire [5:0] qp,
    input wire [7:0] fv_i, input wire q_v, input wire [161:0] q_d, output wire q_cr, input wire [7:0] xl_v,
    input wire [8*163-1:0] xl_d, output wire [7:0] xl_cr, output wire [3:1] tx_v, output wire [162:0] tx_d,
    input wire [3:1] tx_rdy, input wire [7:2] cr_i, output wire [7:2] cr_o, input wire [4:0] pt_v,
    input wire [5*129-1:0] pt_d, output wire [4:0] pt_cr, input wire bw_cr,
    output wire ow_v, output wire [511:0] ow_d,
    output wire [1:0] lf, output wire pe_o,
    output wire ln_v, output wire [511:0] ln_d, input wire [127:0] ln_y, input wire [3:0] ln_yv, input wire [7:0] ln_ye,
    input wire [3:0] ln_pe);
    dsfd_coll_ces #(.S(1), .SEAM(1)) u (.*, .bw_v(), .bw_d(), .ow_h(), .pe_i(3'd0));
endmodule
// wires-only parent of the split lane-slice (S = 0: ces0, else cesn): 4 lane leaves, 3 xl relay leaves, 1 pass-through
// relay leaf, 1 output-stage leaf, the core.  No logic and no flop here: every seam is leaf flop -> wire -> leaf flop.
module dsfd_coll_cess #(parameter integer S = 0, parameter integer PTW = (S == 0) ? 169 : 129, parameter integer BW = (S == 0) ? 563 : 512) (
    input wire ck, input wire rs, input wire e_en, input wire [1:0] rank_i, input wire [5:0] qp,
    input wire [7:0] fv_i, input wire q_v, input wire [161:0] q_d, output wire q_cr, input wire [7:0] xl_v,
    input wire [8*163-1:0] xl_d, output wire [7:0] xl_cr, output wire [3:1] tx_v, output wire [162:0] tx_d,
    input wire [3:1] tx_rdy, input wire [7:2] cr_i, output wire [7:2] cr_o, input wire [4:0] pt_v,
    input wire [5*PTW-1:0] pt_d, output wire [4:0] pt_cr, input wire bw_cr, output wire bw_v, output wire [BW-1:0] bw_d,
    output wire [1:0] lf, output wire pe_o, input wire [3:1] pe_i);
    wire ln_v; wire [511:0] ln_d; wire [127:0] ln_y; wire [3:0] ln_yv, ln_pe; wire [7:0] ln_ye;
    wire [7:0] cx_v, cx_cr; wire [8*163-1:0] cx_d;
    wire [4:0] cp_v, cp_cr; wire [5*PTW-1:0] cp_d;
    wire ow_v; wire [511:0] ow_d; wire [50:0] ow_h; wire [562:0] ob_d;
    assign cx_v[1:0] = 2'b00; assign cx_d[2*163-1:0] = {2*163{1'b0}}; assign xl_cr[1:0] = 2'b00;
    genvar g;
    generate
        for (g = 0; g < 4; g = g + 1) begin : g_ln
            dsfd_coll_cesl u_l (.ck(ck), .rs(rs), .e_en(e_en), .i_v(ln_v),
                .i_d({ln_d[3*128 + 32*g +: 32], ln_d[2*128 + 32*g +: 32], ln_d[128 + 32*g +: 32], ln_d[32*g +: 32]}),
                .o_y(ln_y[32*g +: 32]), .o_yv(ln_yv[g]), .o_ye(ln_ye[2*g +: 2]), .o_pe(ln_pe[g]));
        end
        for (g = 1; g < 4; g = g + 1) begin : g_x
            dsfd_coll_cesx u_x (.ck(ck), .rs(rs), .e_en(e_en), .i_v(xl_v[2*g +: 2]), .i_d(xl_d[2*g*163 +: 2*163]),
                .i_cr(xl_cr[2*g +: 2]), .o_v(cx_v[2*g +: 2]), .o_d(cx_d[2*g*163 +: 2*163]), .o_cr(cx_cr[2*g +: 2]));
        end
        if (S == 0) begin : g_0
            dsfd_coll_cesp0 u_p (.ck(ck), .rs(rs), .i_v(pt_v), .i_d(pt_d), .i_cr(pt_cr), .o_v(cp_v), .o_d(cp_d), .o_cr(cp_cr));
            dsfd_coll_cesc0 u_c (.ck(ck), .rs(rs), .e_en(e_en), .rank_i(rank_i), .qp(qp), .fv_i(fv_i), .q_v(q_v), .q_d(q_d),
                .q_cr(q_cr), .xl_v(cx_v), .xl_d(cx_d), .xl_cr(cx_cr), .tx_v(tx_v), .tx_d(tx_d), .tx_rdy(tx_rdy), .cr_i(cr_i),
                .cr_o(cr_o), .pt_v(cp_v), .pt_d(cp_d), .pt_cr(cp_cr), .bw_cr(bw_cr), .ow_v(ow_v), .ow_d(ow_d), .ow_h(ow_h), .lf(lf),
                .pe_o(pe_o), .ln_v(ln_v), .ln_d(ln_d), .ln_y(ln_y), .ln_yv(ln_yv), .ln_ye(ln_ye), .ln_pe(ln_pe));
            dsfd_coll_ceso u_o (.ck(ck), .rs(rs), .i_v(ow_v), .i_d(ow_d), .i_h(ow_h), .pe_i(pe_i), .bw_v(bw_v), .bw_d(ob_d));
            assign bw_d = ob_d;
        end else begin : g_n
            dsfd_coll_cespn u_p (.ck(ck), .rs(rs), .i_v(pt_v), .i_d(pt_d), .i_cr(pt_cr), .o_v(cp_v), .o_d(cp_d), .o_cr(cp_cr));
            dsfd_coll_cescn u_c (.ck(ck), .rs(rs), .e_en(e_en), .rank_i(rank_i), .qp(qp), .fv_i(fv_i), .q_v(q_v), .q_d(q_d),
                .q_cr(q_cr), .xl_v(cx_v), .xl_d(cx_d), .xl_cr(cx_cr), .tx_v(tx_v), .tx_d(tx_d), .tx_rdy(tx_rdy), .cr_i(cr_i),
                .cr_o(cr_o), .pt_v(cp_v), .pt_d(cp_d), .pt_cr(cp_cr), .bw_cr(bw_cr), .ow_v(ow_v), .ow_d(ow_d), .lf(lf),
                .pe_o(pe_o), .ln_v(ln_v), .ln_d(ln_d), .ln_y(ln_y), .ln_yv(ln_yv), .ln_ye(ln_ye), .ln_pe(ln_pe));
            assign ow_h = 51'd0;
            dsfd_coll_ceso u_o (.ck(ck), .rs(rs), .i_v(ow_v), .i_d(ow_d), .i_h(ow_h), .pe_i(3'd0), .bw_v(bw_v), .bw_d(ob_d));
            assign bw_d = ob_d[562:51];
            wire unused_pe = &{1'b0, pe_i, ob_d[50:0]};
        end
    endgenerate
    wire unused_ok = &{1'b0, cx_cr[1:0]};
`ifdef OT_S81PH_COLL_CES_SPLIT
`ifdef VERILATOR
    // bench-only seam coverage (see package s81ph_ces_cov); blocking adds: many parents count in one time step
    localparam integer K = (S == 0) ? 0 : 1;
    initial s81ph_ces_cov::inst[K] = s81ph_ces_cov::inst[K] + 1;
    always @(posedge ck) begin
        if (ln_v) s81ph_ces_cov::ln[K] = s81ph_ces_cov::ln[K] + 1;
        for (integer i = 0; i < 4; i = i + 1) if (ln_yv[i]) s81ph_ces_cov::lny[K] = s81ph_ces_cov::lny[K] + 1;
        for (integer i = 1; i < 4; i = i + 1) begin
            if (cx_v[2*i] || cx_v[2*i+1]) s81ph_ces_cov::xl[K][i] = s81ph_ces_cov::xl[K][i] + 1;
            if (xl_v[2*i] || xl_v[2*i+1]) s81ph_ces_cov::xli[K][i] = s81ph_ces_cov::xli[K][i] + 1;
        end
        for (integer i = 0; i < 5; i = i + 1) begin
            if (cp_v[i]) s81ph_ces_cov::pt[K][i] = s81ph_ces_cov::pt[K][i] + 1;
            if (pt_v[i]) s81ph_ces_cov::pti[K][i] = s81ph_ces_cov::pti[K][i] + 1;
        end
        if (ow_v) s81ph_ces_cov::ow[K] = s81ph_ces_cov::ow[K] + 1;
        if (bw_v) s81ph_ces_cov::bw[K] = s81ph_ces_cov::bw[K] + 1;
    end
`endif
`endif
endmodule
// Wires-only independent clock entries. Each port directly drives one unchanged hardened leaf.
module dsfd_coll_cess_pc #(parameter integer S = 0, parameter integer PTW = (S == 0) ? 169 : 129, parameter integer BW = (S == 0) ? 563 : 512) (
    input wire ck_x1, ck_x2, ck_x3, ck_core, ck_l0, ck_l1, ck_l2, ck_l3, ck_o, ck_pt, input wire rs, input wire e_en, input wire [1:0] rank_i, input wire [5:0] qp,
    input wire [7:0] fv_i, input wire q_v, input wire [161:0] q_d, output wire q_cr, input wire [7:0] xl_v,
    input wire [8*163-1:0] xl_d, output wire [7:0] xl_cr, output wire [3:1] tx_v, output wire [162:0] tx_d,
    input wire [3:1] tx_rdy, input wire [7:2] cr_i, output wire [7:2] cr_o, input wire [4:0] pt_v,
    input wire [5*PTW-1:0] pt_d, output wire [4:0] pt_cr, input wire bw_cr, output wire bw_v, output wire [BW-1:0] bw_d,
    output wire [1:0] lf, output wire pe_o, input wire [3:1] pe_i);
    wire [3:0] ck_lane = {ck_l3,ck_l2,ck_l1,ck_l0};
    wire [2:0] ck_x = {ck_x3,ck_x2,ck_x1};
    wire ln_v; wire [511:0] ln_d; wire [127:0] ln_y; wire [3:0] ln_yv, ln_pe; wire [7:0] ln_ye;
    wire [7:0] cx_v, cx_cr; wire [8*163-1:0] cx_d;
    wire [4:0] cp_v, cp_cr; wire [5*PTW-1:0] cp_d;
    wire ow_v; wire [511:0] ow_d; wire [50:0] ow_h; wire [562:0] ob_d;
    assign cx_v[1:0] = 2'b00; assign cx_d[2*163-1:0] = {2*163{1'b0}}; assign xl_cr[1:0] = 2'b00;
    genvar g;
    generate
        for (g = 0; g < 4; g = g + 1) begin : g_ln
            dsfd_coll_cesl u_l (.ck(ck_lane[g]), .rs(rs), .e_en(e_en), .i_v(ln_v),
                .i_d({ln_d[3*128 + 32*g +: 32], ln_d[2*128 + 32*g +: 32], ln_d[128 + 32*g +: 32], ln_d[32*g +: 32]}),
                .o_y(ln_y[32*g +: 32]), .o_yv(ln_yv[g]), .o_ye(ln_ye[2*g +: 2]), .o_pe(ln_pe[g]));
        end
        for (g = 1; g < 4; g = g + 1) begin : g_x
            dsfd_coll_cesx u_x (.ck(ck_x[g-1]), .rs(rs), .e_en(e_en), .i_v(xl_v[2*g +: 2]), .i_d(xl_d[2*g*163 +: 2*163]),
                .i_cr(xl_cr[2*g +: 2]), .o_v(cx_v[2*g +: 2]), .o_d(cx_d[2*g*163 +: 2*163]), .o_cr(cx_cr[2*g +: 2]));
        end
        if (S == 0) begin : g_0
            dsfd_coll_cesp0 u_p (.ck(ck_pt), .rs(rs), .i_v(pt_v), .i_d(pt_d), .i_cr(pt_cr), .o_v(cp_v), .o_d(cp_d), .o_cr(cp_cr));
            dsfd_coll_cesc0 u_c (.ck(ck_core), .rs(rs), .e_en(e_en), .rank_i(rank_i), .qp(qp), .fv_i(fv_i), .q_v(q_v), .q_d(q_d),
                .q_cr(q_cr), .xl_v(cx_v), .xl_d(cx_d), .xl_cr(cx_cr), .tx_v(tx_v), .tx_d(tx_d), .tx_rdy(tx_rdy), .cr_i(cr_i),
                .cr_o(cr_o), .pt_v(cp_v), .pt_d(cp_d), .pt_cr(cp_cr), .bw_cr(bw_cr), .ow_v(ow_v), .ow_d(ow_d), .ow_h(ow_h), .lf(lf),
                .pe_o(pe_o), .ln_v(ln_v), .ln_d(ln_d), .ln_y(ln_y), .ln_yv(ln_yv), .ln_ye(ln_ye), .ln_pe(ln_pe));
            dsfd_coll_ceso u_o (.ck(ck_o), .rs(rs), .i_v(ow_v), .i_d(ow_d), .i_h(ow_h), .pe_i(pe_i), .bw_v(bw_v), .bw_d(ob_d));
            assign bw_d = ob_d;
        end else begin : g_n
            dsfd_coll_cespn u_p (.ck(ck_pt), .rs(rs), .i_v(pt_v), .i_d(pt_d), .i_cr(pt_cr), .o_v(cp_v), .o_d(cp_d), .o_cr(cp_cr));
            dsfd_coll_cescn u_c (.ck(ck_core), .rs(rs), .e_en(e_en), .rank_i(rank_i), .qp(qp), .fv_i(fv_i), .q_v(q_v), .q_d(q_d),
                .q_cr(q_cr), .xl_v(cx_v), .xl_d(cx_d), .xl_cr(cx_cr), .tx_v(tx_v), .tx_d(tx_d), .tx_rdy(tx_rdy), .cr_i(cr_i),
                .cr_o(cr_o), .pt_v(cp_v), .pt_d(cp_d), .pt_cr(cp_cr), .bw_cr(bw_cr), .ow_v(ow_v), .ow_d(ow_d), .lf(lf),
                .pe_o(pe_o), .ln_v(ln_v), .ln_d(ln_d), .ln_y(ln_y), .ln_yv(ln_yv), .ln_ye(ln_ye), .ln_pe(ln_pe));
            assign ow_h = 51'd0;
            dsfd_coll_ceso u_o (.ck(ck_o), .rs(rs), .i_v(ow_v), .i_d(ow_d), .i_h(ow_h), .pe_i(3'd0), .bw_v(bw_v), .bw_d(ob_d));
            assign bw_d = ob_d[562:51];
            wire unused_pe = &{1'b0, pe_i, ob_d[50:0]};
        end
    endgenerate
    wire unused_ok = &{1'b0, cx_cr[1:0]};
`ifdef OT_S81PH_COLL_CES_SPLIT
`ifdef VERILATOR
    // bench-only seam coverage (see package s81ph_ces_cov); blocking adds: many parents count in one time step
    localparam integer K = (S == 0) ? 0 : 1;
    initial s81ph_ces_cov::inst[K] = s81ph_ces_cov::inst[K] + 1;
    always @(posedge ck_core) begin
        if (ln_v) s81ph_ces_cov::ln[K] = s81ph_ces_cov::ln[K] + 1;
        for (integer i = 0; i < 4; i = i + 1) if (ln_yv[i]) s81ph_ces_cov::lny[K] = s81ph_ces_cov::lny[K] + 1;
        for (integer i = 1; i < 4; i = i + 1) begin
            if (cx_v[2*i] || cx_v[2*i+1]) s81ph_ces_cov::xl[K][i] = s81ph_ces_cov::xl[K][i] + 1;
            if (xl_v[2*i] || xl_v[2*i+1]) s81ph_ces_cov::xli[K][i] = s81ph_ces_cov::xli[K][i] + 1;
        end
        for (integer i = 0; i < 5; i = i + 1) begin
            if (cp_v[i]) s81ph_ces_cov::pt[K][i] = s81ph_ces_cov::pt[K][i] + 1;
            if (pt_v[i]) s81ph_ces_cov::pti[K][i] = s81ph_ces_cov::pti[K][i] + 1;
        end
        if (ow_v) s81ph_ces_cov::ow[K] = s81ph_ces_cov::ow[K] + 1;
        if (bw_v) s81ph_ces_cov::bw[K] = s81ph_ces_cov::bw[K] + 1;
    end
`endif
`endif
endmodule

module dsfd_coll_ces0_pc (input wire ck_x1, ck_x2, ck_x3, ck_core, ck_l0, ck_l1, ck_l2, ck_l3, ck_o, ck_pt, input wire rs, input wire e_en, input wire [1:0] rank_i, input wire [5:0] qp,
    input wire [7:0] fv_i, input wire q_v, input wire [161:0] q_d, output wire q_cr, input wire [7:0] xl_v,
    input wire [8*163-1:0] xl_d, output wire [7:0] xl_cr, output wire [3:1] tx_v, output wire [162:0] tx_d,
    input wire [3:1] tx_rdy, input wire [7:2] cr_i, output wire [7:2] cr_o, input wire [4:0] pt_v,
    input wire [5*169-1:0] pt_d, output wire [4:0] pt_cr, input wire bw_cr, output wire bw_v, output wire [562:0] bw_d,
    output wire [1:0] lf, output wire pe_o, input wire [3:1] pe_i);
    dsfd_coll_cess_pc #(.S(0)) u (.*);
endmodule
module dsfd_coll_cesn_pc (input wire ck_x1, ck_x2, ck_x3, ck_core, ck_l0, ck_l1, ck_l2, ck_l3, ck_o, ck_pt, input wire rs, input wire e_en, input wire [1:0] rank_i, input wire [5:0] qp,
    input wire [7:0] fv_i, input wire q_v, input wire [161:0] q_d, output wire q_cr, input wire [7:0] xl_v,
    input wire [8*163-1:0] xl_d, output wire [7:0] xl_cr, output wire [3:1] tx_v, output wire [162:0] tx_d,
    input wire [3:1] tx_rdy, input wire [7:2] cr_i, output wire [7:2] cr_o, input wire [4:0] pt_v,
    input wire [5*129-1:0] pt_d, output wire [4:0] pt_cr, input wire bw_cr, output wire bw_v, output wire [511:0] bw_d,
    output wire [1:0] lf, output wire pe_o);
    dsfd_coll_cess_pc #(.S(1)) u (.*, .pe_i(3'd0));
endmodule
// ---- route masters of the lane-slice: OT_S81PH_COLL_CES_SPLIT selects the split structure for BOTH (one define, so no
// committed configuration can mix seam latencies); without it both are the flat slices (the closed ces0 view).
`ifdef OT_S81PH_COLL_CES_SPLIT
module dsfd_coll_ces0 (input wire ck, input wire rs, input wire e_en, input wire [1:0] rank_i, input wire [5:0] qp,
    input wire [7:0] fv_i, input wire q_v, input wire [161:0] q_d, output wire q_cr, input wire [7:0] xl_v,
    input wire [8*163-1:0] xl_d, output wire [7:0] xl_cr, output wire [3:1] tx_v, output wire [162:0] tx_d,
    input wire [3:1] tx_rdy, input wire [7:2] cr_i, output wire [7:2] cr_o, input wire [4:0] pt_v,
    input wire [5*169-1:0] pt_d, output wire [4:0] pt_cr, input wire bw_cr, output wire bw_v, output wire [562:0] bw_d,
    output wire [1:0] lf, output wire pe_o, input wire [3:1] pe_i);
`ifdef OT_S81PH_COLL_CES_ENTRIES
    dsfd_coll_cess_pc #(.S(0)) u (.ck_x1(ck), .ck_x2(ck), .ck_x3(ck), .ck_core(ck), .ck_l0(ck), .ck_l1(ck), .ck_l2(ck), .ck_l3(ck), .ck_o(ck), .ck_pt(ck), .*);
`else
    dsfd_coll_cess #(.S(0)) u (.*);
`endif
endmodule
module dsfd_coll_cesn (input wire ck, input wire rs, input wire e_en, input wire [1:0] rank_i, input wire [5:0] qp,
    input wire [7:0] fv_i, input wire q_v, input wire [161:0] q_d, output wire q_cr, input wire [7:0] xl_v,
    input wire [8*163-1:0] xl_d, output wire [7:0] xl_cr, output wire [3:1] tx_v, output wire [162:0] tx_d,
    input wire [3:1] tx_rdy, input wire [7:2] cr_i, output wire [7:2] cr_o, input wire [4:0] pt_v,
    input wire [5*129-1:0] pt_d, output wire [4:0] pt_cr, input wire bw_cr, output wire bw_v, output wire [511:0] bw_d,
    output wire [1:0] lf, output wire pe_o);
`ifdef OT_S81PH_COLL_CES_ENTRIES
    dsfd_coll_cess_pc #(.S(1)) u (.ck_x1(ck), .ck_x2(ck), .ck_x3(ck), .ck_core(ck), .ck_l0(ck), .ck_l1(ck), .ck_l2(ck), .ck_l3(ck), .ck_o(ck), .ck_pt(ck), .*, .pe_i(3'd0));
`else
    dsfd_coll_cess #(.S(1)) u (.*, .pe_i(3'd0));
`endif
endmodule
`else
module dsfd_coll_ces0 (input wire ck, input wire rs, input wire e_en, input wire [1:0] rank_i, input wire [5:0] qp,
    input wire [7:0] fv_i, input wire q_v, input wire [161:0] q_d, output wire q_cr, input wire [7:0] xl_v,
    input wire [8*163-1:0] xl_d, output wire [7:0] xl_cr, output wire [3:1] tx_v, output wire [162:0] tx_d,
    input wire [3:1] tx_rdy, input wire [7:2] cr_i, output wire [7:2] cr_o, input wire [4:0] pt_v,
    input wire [5*169-1:0] pt_d, output wire [4:0] pt_cr, input wire bw_cr, output wire bw_v, output wire [562:0] bw_d,
    output wire [1:0] lf, output wire pe_o, input wire [3:1] pe_i);
    dsfd_coll_ces #(.S(0)) u (.*, .ow_v(), .ow_d(), .ow_h(), .ln_v(), .ln_d(), .ln_y(128'd0), .ln_yv(4'd0), .ln_ye(8'd0), .ln_pe(4'd0));
endmodule
module dsfd_coll_cesn (input wire ck, input wire rs, input wire e_en, input wire [1:0] rank_i, input wire [5:0] qp,
    input wire [7:0] fv_i, input wire q_v, input wire [161:0] q_d, output wire q_cr, input wire [7:0] xl_v,
    input wire [8*163-1:0] xl_d, output wire [7:0] xl_cr, output wire [3:1] tx_v, output wire [162:0] tx_d,
    input wire [3:1] tx_rdy, input wire [7:2] cr_i, output wire [7:2] cr_o, input wire [4:0] pt_v,
    input wire [5*129-1:0] pt_d, output wire [4:0] pt_cr, input wire bw_cr, output wire bw_v, output wire [511:0] bw_d,
    output wire [1:0] lf, output wire pe_o);
    dsfd_coll_ces #(.S(1)) u (.*, .pe_i(3'd0), .ow_v(), .ow_d(), .ow_h(), .ln_v(), .ln_d(), .ln_y(128'd0), .ln_yv(4'd0), .ln_ye(8'd0), .ln_pe(4'd0));
endmodule
`endif
module dsfd_coll_cele (input wire ck, input wire rs, input wire e_en, output wire f_lo_v, input wire f_lo_r,
    output wire [552:0] f_lo_d, input wire f_li_v, output wire f_li_r, input wire [552:0] f_li_d, input wire [2:0] x_flt,
    output wire [3:0] lf, input wire tx_v, input wire [4*163-1:0] tx_d, output wire tx_rdy, input wire [1:0] cr_o,
    output wire [1:0] cr_i, output wire rx_v, output wire [546:0] rx_d);
    dsfd_coll_cel #(.KIND(0)) u (.*, .q_v(1'b0), .q_d(553'd0), .q_cr(), .p_v(), .p_d(), .p_cr(1'b0));
endmodule
module dsfd_coll_celp (input wire ck, input wire rs, output wire f_lo_v, input wire f_lo_r,
    output wire [552:0] f_lo_d, input wire f_li_v, output wire f_li_r, input wire [552:0] f_li_d, input wire [2:0] x_flt,
    output wire [3:0] lf, input wire q_v, input wire [552:0] q_d, output wire q_cr, output wire p_v,
    output wire [168+3*129:0] p_d, input wire p_cr);
    dsfd_coll_cel #(.KIND(1)) u (.*, .e_en(1'b0), .tx_v(1'b0), .tx_d({4*163{1'b0}}), .tx_rdy(), .cr_o(2'b00), .cr_i(),
        .rx_v(), .rx_d());
endmodule
