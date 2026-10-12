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
module dsfd_coll_ces #(parameter integer S = 0, parameter integer XD = 6, parameter integer OQX_D = 16) (
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
    output reg               bw_v, output reg [(S == 0 ? 563 : 512)-1:0] bw_d,
    // slice faults to ceq, header error bits to / from slice 0
    output reg  [1:0]        lf,                            // {e_flt, mq_flt}
    output reg               pe_o, input wire [3:1] pe_i
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
        .SRAM_MACRO(1), .PULL(1), .PULL_D(XD), .PCOPY(1), .PSL(1), .LQW(2), .EXTF(1), .RHOLD(1)) u_eng (
        .clk(ck), .rst_n(erst_n),
        .in_valid(e_iv), .in_ready(e_ir), .in_data(lq_d[SFW-1:0]), .in_last(lq_d[161]), .in_mode(lq_d[160]),
        .in_tag(lq_d[SFW +: TAGW]),
        .tx_valid(e_txv), .tx_rec(e_txr), .tx_ready({trd_q, 1'b1}), .cr_in({cri_q, 2'b00}),
        .rx_valid(4'd0), .rx_rec({4*PW{1'b0}}), .cr_out(e_cro),
        .rl_tx_valid(), .rl_tx_rec(), .rl_rx_valid(4'd0), .rl_rx_rec({4*PW{1'b0}}),
        .out_valid(o_v), .out_ready(o_rdy), .out_data(o_d), .out_last(o_last), .out_rank(o_rank), .out_err(o_err),
        .out_red(o_red), .out_rdat(o_rdat), .out_gdat(o_gdat),
        .fault(e_flt), .fault_code(e_code), .red_hold(!room2), .out_rpop(e_rpop), .xl_v(xl_v), .xl_d(xl_d), .xl_cr(xl_cr));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin tx_v <= 3'd0; cr_o <= 6'd0; end
        else begin tx_v <= e_txv[3:1]; cr_o <= e_cro[7:2]; end
    always @(posedge ck) tx_d <= e_txr;
    // ---- pass-through landings
    wire [4:0] ep_ov, ep_or; wire [PTW-1:0] ep_od [0:4];
    genvar l;
    generate for (l = 0; l < 5; l = l + 1) begin : g_pt
        ot_link_credit_rx #(.W(PTW), .DEPTH(XD), .OREG(0), .WFREE(2)) u_lp (.clk(ck), .rst_n(rst_n), .l_valid(pt_v[l]),
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
    reg  signed [7:0] cred;
    // room2 = (cred - w_r) >= 2, registered from the next values: w_r = reduce words popped and not yet emitted, each
    // holding a reserved output slot (reduce words are not back-pressured at the output); also the engine's reduce-pop
    // gate (red_hold).  Slow-VM-drain fix (1-in-8 take overflowed the remote queue in the flat and the split designs).
    reg          room2;
    reg  [7:0]   w_r;
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
    wire [7:0]   cred_nx = cred - (oq_push ? 8'sd1 : 8'sd0) + (bcr_q ? 8'sd1 : 8'sd0);
    wire [7:0]   w_nx = w_r + (e_rpop ? 8'd1 : 8'd0) - (pk_emit ? {5'd0, pk_n} : 8'd0);
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin cred <= OQX_D; room2 <= 1'b1; w_r <= 8'd0; end
        else begin
            cred <= cred_nx; w_r <= w_nx;
`ifdef OT_S81PH_MUT_ORC
            room2 <= $signed(cred_nx) >= 8'sd2;                              // negative control: no reservation
`else
            room2 <= ($signed({cred_nx[7], cred_nx}) - $signed({1'b0, w_nx})) >= 9'sd2;
`endif
        end
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
        if (!rst_n) begin w1_v <= 1'b0; bv_q <= 1'b0; bw_v <= 1'b0; pe_o <= 1'b0; lf <= 2'd0; end
        else begin
            w1_v <= oq_push; bv_q <= w1_v; bw_v <= bv_q; pe_o <= pe;
            lf <= {e_flt, mq_flt};
        end
    always @(posedge ck) begin
        w1_d <= b_d; w1_h <= hdr;
        bd_q <= w1_d;
        bh_q <= w1_h;
    end
    // pe_q (pin flops) holds the other slices' error bits of the word now in bd_q / bh_q (emit + 2)
    generate if (S == 0) begin : g_o0
`ifdef OT_S81PH_MUT_CEH
        always @(posedge ck) bw_d <= {bd_q, bh_q};            // negative control: the other slices' errors are lost
`else
        always @(posedge ck) bw_d <= {bd_q, bh_q[50:16], bh_q[15] | (|pe_q), bh_q[14:0]};
`endif
    end else begin : g_on
        always @(posedge ck) bw_d <= bd_q;
        wire unused_h = &{1'b0, bh_q, pe_q};
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
        dsfd_coll_ces #(.S(s)) u_s (.ck(c), .rs(r), .e_en(e_en), .rank_i(rank), .qp(qp), .fv_i(fv),
            .q_v(q_v), .q_d(q_d[s*162 +: 162]), .q_cr(q_cr_s[s]),
            .xl_v(xlv), .xl_d(xld), .xl_cr(xl_cr_s[s]),
            .tx_v(tx_v_s[s]), .tx_d(tx_d_s[s]), .tx_rdy(tx_rdy), .cr_i(cr_i), .cr_o(cr_o_s[s]),
            .pt_v(p_v), .pt_d(ptd), .pt_cr(p_cr_s[s]),
            .bw_cr(bw_cr[0]), .bw_v(bwv_s[s]), .bw_d(bwd), .lf(slice_f[2*s +: 2]), .pe_o(pe[s]), .pe_i(pe[3:1]));
        if (s == 0) begin : g_b0 assign bwd0 = bwd; end
        else begin : g_bn assign bwd_s[s] = bwd; end
    end endgenerate
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
module dsfd_coll_ces0 (input wire ck, input wire rs, input wire e_en, input wire [1:0] rank_i, input wire [5:0] qp,
    input wire [7:0] fv_i, input wire q_v, input wire [161:0] q_d, output wire q_cr, input wire [7:0] xl_v,
    input wire [8*163-1:0] xl_d, output wire [7:0] xl_cr, output wire [3:1] tx_v, output wire [162:0] tx_d,
    input wire [3:1] tx_rdy, input wire [7:2] cr_i, output wire [7:2] cr_o, input wire [4:0] pt_v,
    input wire [5*169-1:0] pt_d, output wire [4:0] pt_cr, input wire bw_cr, output wire bw_v, output wire [562:0] bw_d,
    output wire [1:0] lf, output wire pe_o, input wire [3:1] pe_i);
    dsfd_coll_ces #(.S(0)) u (.*);
endmodule
module dsfd_coll_cesn (input wire ck, input wire rs, input wire e_en, input wire [1:0] rank_i, input wire [5:0] qp,
    input wire [7:0] fv_i, input wire q_v, input wire [161:0] q_d, output wire q_cr, input wire [7:0] xl_v,
    input wire [8*163-1:0] xl_d, output wire [7:0] xl_cr, output wire [3:1] tx_v, output wire [162:0] tx_d,
    input wire [3:1] tx_rdy, input wire [7:2] cr_i, output wire [7:2] cr_o, input wire [4:0] pt_v,
    input wire [5*129-1:0] pt_d, output wire [4:0] pt_cr, input wire bw_cr, output wire bw_v, output wire [511:0] bw_d,
    output wire [1:0] lf, output wire pe_o);
    dsfd_coll_ces #(.S(1)) u (.*, .pe_i(3'd0));
endmodule
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
