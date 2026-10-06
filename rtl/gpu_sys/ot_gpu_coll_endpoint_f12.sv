`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_gpu_coll_endpoint_f12: 1.2 GHz successor of ot_gpu_coll_endpoint (noc fmax closure, 2026-10-04).  Same ports,
// same records on the link, same response bits; rtl/gpu_sys/ot_gpu_coll_endpoint.sv is not modified.
//
// The baseline's RX path is one cycle from the RX FIFO read pointer to the reassembly register: rbin -> 16:1 x
// 546-bit FIFO read mux -> {src, word} -> src * count + word * LANES -> per-lane placement compare -> 16:1 lane
// select -> asmb (NL x 32 bits).  Routed in the HA3 context it fails by 1.70 ns at 0.833 ns.  Changes:
//   RX  (+1 clk_sm cycle per collective, none per record: one record a cycle either way)
//       stage A  pop the record (one-hot replicated FIFO read select, ot_gpu_cdc_fifo_oh) and register it with
//                its placement offset off = (gather ? off_tab[src] : 0) + word * LANES, its 16-lane valid mask
//                (word * LANES + k < count) and its tag check; off_tab[r] = r * count is registered once per
//                collective at acceptance, so no multiply sits on the record path;
//       stage B  place: the 16 lanes and their mask are shifted to lane off (a barrel shift over NL lanes, the
//                shift amount registered RDUP times) and merged into asmb; the record counter and the S_RSP
//                transition move here, so coll_rsp_v rises one cycle later than the baseline's, with identical
//                coll_rsp_data.  Records are popped only while fewer than the expected count have been popped
//                (the baseline stopped popping by leaving S_RUN on the last take), so an early record of the
//                next collective stays in the FIFO exactly as before.
//   TX  (zero cycles) the request data is captured raw with a registered lanes < count mask, and the record's word is
//       selected by a one-hot copy of sw (replicated), not by a sw * LANES-indexed lane multiplexer; the TX FIFO
//       is ot_gpu_cdc_fifo_oh.
// The reassembly register is cleared on the first S_RUN cycle instead of at acceptance (the response is not
// valid in between); for a refused zero-count request (req_bad, which goes straight to S_RSP) coll_rsp_data then
// shows the previous response instead of zeros -- a faulted collective's data only.
// Faults: the tag check is the baseline's, latched one cycle later (stage B).  A gather record whose src >= R
// (itself a latched fault) is placed at off_tab[src mod 2^RB] instead of src * count: the response of a
// collective that has already faulted is the only output that can differ.
// ENABLE = 0 (default): inert, every output 0, no logic.
// ---------------------------------------------------------------------------
module ot_gpu_coll_endpoint_f12 #(
    parameter integer ENABLE = 0,
    parameter integer NL     = 128,
    parameter integer LANES  = 16,
    parameter integer R      = 2,
    parameter integer RANK   = 0,
    parameter integer TAGW   = 32,
    parameter integer AW     = 3,
    parameter integer AW_RX  = 4,
    parameter integer SYNC   = 2,
    parameter integer RDUP   = 8,
    parameter integer XREG   = 0,      // 1: one more register before the per-lane select (+1 cycle per collective)
    parameter integer FW     = 32 * LANES,
    parameter integer PW     = FW + 2 + TAGW
) (
    input  wire              clk_sm,
    input  wire              rst_sm_n,
    input  wire              coll_req_v,
    output wire              coll_req_rdy,
    input  wire              coll_mode,
    input  wire [7:0]        coll_count,
    input  wire [NL*32-1:0]  coll_data,
    output wire              coll_rsp_v,
    input  wire              coll_rsp_rdy,
    output wire [NL*32-1:0]  coll_rsp_data,
    output wire              coll_fault,
    input  wire              clk_link,
    input  wire              rst_link_n,
    output wire              lk_tx_v,
    output wire [PW-1:0]     lk_tx_rec,
    input  wire              lk_rx_v,
    input  wire [PW-1:0]     lk_rx_rec
);
    generate if (ENABLE != 0) begin : g_on
        localparam integer GPRE = (R - 1) * ((NL / R + LANES - 1) / LANES);
        localparam [7:0]   RK8  = RANK[7:0];
        localparam integer NW   = (NL + LANES - 1) / LANES;     // record words of a full request
        localparam integer RB   = (R > 1) ? $clog2(R) : 1;
        localparam integer OB   = 9;                            // offset bits (offsets < 2 * 256)
        if (TAGW != 32) begin : g_bad_tagw
            $error("ot_gpu_coll_endpoint_f12: TAGW must be 32 (tag = {src, seq, count, word})");
        end
        if (NL > 255 || NL < 1) begin : g_bad_nl
            $error("ot_gpu_coll_endpoint_f12: NL must be 1..255 (coll_count is 8 bits)");
        end
        if ((1 << AW_RX) < GPRE + 2) begin : g_bad_rx
            $error("ot_gpu_coll_endpoint_f12: RX FIFO depth 2^AW_RX below the early-gather bound + 2");
        end
        if (RANK < 0 || RANK >= R || R > 255) begin : g_bad_rank
            $error("ot_gpu_coll_endpoint_f12: RANK must be in 0..R-1 and R <= 255");
        end

        localparam [1:0] S_IDLE = 2'd0, S_RUN = 2'd1, S_RSP = 2'd2;
        reg  [1:0]        st;
        reg  [NL*32-1:0]  dat;          // request lanes, lanes >= count zeroed at capture
        wire [NL*32-1:0]  asmb;
        reg               mode_q;
        reg  [7:0]        cnt_q;
        reg  [7:0]        seq;
        reg  [7:0]        sw;
        reg  [7:0]        nrec;
        reg  [8:0]        nexp;
        reg  [8:0]        rcv;          // records placed (stage B)
        reg  [8:0]        npop;         // records popped (stage A)
        reg               flt_sm;
        reg  [OB-1:0]     off_tab [0:(1<<RB)-1];

        // ---------------- request capture ----------------
        wire [8:0]  req_nrec = 9'((32'(coll_count) + LANES - 1) / LANES);
        wire        req_bad  = (coll_count == 8'd0) || (32'(coll_count) > NL) ||
                               (coll_mode && 32'(coll_count) * R > NL);
        // the request lanes are captured raw (as the baseline); lanes >= count are zeroed on the TX side by a lane
        // mask registered at the same capture, so the capture path is the SM-side select alone
        reg  [NL-1:0] dmask;
        reg  [NL-1:0] dmask_n;
        always @* for (integer l = 0; l < NL; l = l + 1) dmask_n[l] = (l < 32'(coll_count));

        // request data capture: every cycle while idle (dat is read only in S_RUN), enabled by registered per-slice
        // copies of "idle next cycle", so the SM-side request valid (the mux owner select) does not fan out to the
        // NL*32 capture enables; at acceptance dat holds coll_data of that cycle, as in the baseline
        wire idle_n = (st == S_IDLE) ? !coll_req_v : ((st == S_RSP) && coll_rsp_rdy);
        genvar ci;
        for (ci = 0; ci < RDUP; ci = ci + 1) begin : g_cap
            localparam integer CW = (NL * 32 + RDUP - 1) / RDUP;
            localparam integer LO = ci * CW;
            localparam integer HI = ((ci + 1) * CW > NL * 32) ? NL * 32 : (ci + 1) * CW;
            if (LO < NL * 32) begin : g_on
                wire idle_c;
                ot_gpu_kreg_oh #(.W(1), .RV(1'b1)) u_idle (.clk(clk_sm), .rst_n(rst_sm_n), .d(idle_n), .q(idle_c));
                always @(posedge clk_sm) if (idle_c) dat[HI-1:LO] <= coll_data[HI-1:LO];
            end
        end
        // ---------------- TX: one-hot word select ----------------
        wire tx_in_v = (st == S_RUN) && (sw < nrec);
        wire tx_in_rdy;
        wire tx_adv = tx_in_v && tx_in_rdy;
        wire accept = (st == S_IDLE) && coll_req_v;
        wire [FW-1:0] txd;
        genvar c;
        for (c = 0; c < RDUP; c = c + 1) begin : g_txs
            localparam integer SW_ = (FW + RDUP - 1) / RDUP;
            localparam integer LO = c * SW_;
            localparam integer HI = ((c + 1) * SW_ > FW) ? FW : (c + 1) * SW_;
            if (LO < FW) begin : g_on
                wire [NW-1:0] oh_q;
                wire [NW-1:0] oh_d = accept ? {{(NW-1){1'b0}}, 1'b1} : tx_adv ? (oh_q << 1) : oh_q;
                ot_gpu_kreg_oh #(.W(NW), .RV({{(NW-1){1'b0}}, 1'b1})) u_sw (.clk(clk_sm), .rst_n(rst_sm_n),
                    .d(oh_d), .q(oh_q));
                reg [HI-LO-1:0] ts;
                always @* begin
                    ts = '0;
                    for (integer w = 0; w < NW; w = w + 1)
                        for (integer b = LO; b < HI; b = b + 1)
                            if (w * FW + b < NL * 32) ts[b-LO] = ts[b-LO] | (oh_q[w] & dmask[(w*FW + b) / 32] & dat[w*FW + b]);
                end
                assign txd[HI-1:LO] = ts;
            end
        end
        wire [PW-1:0] tx_rec = {RK8, seq, cnt_q, sw, mode_q, (sw + 8'd1 == nrec), txd};

        // ---------------- RX stage A: pop + register ----------------
        wire          rx_out_v;
        wire [PW-1:0] rx_d;
        wire          rx_take = rx_out_v && (st == S_RUN) && (npop < nexp);
        wire [7:0]    r_src  = rx_d[PW-1 -: 8];
        wire [7:0]    r_seq  = rx_d[PW-9 -: 8];
        wire [7:0]    r_cnt  = rx_d[PW-17 -: 8];
        wire [7:0]    r_word = rx_d[PW-25 -: 8];
        wire          r_mode = rx_d[FW + 1];
        wire          r_bad  = (r_seq != seq) || (r_cnt != cnt_q) || (r_mode != mode_q) || (r_word >= nrec) ||
                               (mode_q ? (32'(r_src) >= R) : (r_src != 8'hFF));
        wire [OB-1:0] r_wb   = OB'(32'(r_word) * LANES);
        wire [OB-1:0] r_off  = (mode_q ? off_tab[r_src[RB-1:0]] : {OB{1'b0}}) + r_wb;
        reg  [LANES-1:0] r_km;
        always @* for (integer k = 0; k < LANES; k = k + 1) r_km[k] = (32'(r_word) * LANES + k < 32'(cnt_q));
        // per destination lane: source lane index and hit, computed from the record's offset (stage A, or one
        // register later with XREG = 1), so stage B is a registered-select 16:1 AND-OR per lane.  The record
        // registers (data copies, per-lane selects, x-stage) load EVERY cycle: they are consumed only under
        // qa_v, so no pop strobe fans out to their thousands of enables.
        localparam integer LB = $clog2(LANES);
        reg              qa_v, qa_bad;
        wire             pa_v;                  // the record whose per-lane select is being formed
        wire [OB-1:0]    pa_off;
        wire [LANES-1:0] pa_km;
        wire [FW-1:0]    pa_d;
        wire             pa_bad;
        if (XREG != 0) begin : g_xreg
            reg xv, xbad; reg [OB-1:0] xoff; reg [LANES-1:0] xkm; reg [FW-1:0] xd;
            always @(posedge clk_sm or negedge rst_sm_n)
                if (!rst_sm_n) xv <= 1'b0; else xv <= rx_take;
            always @(posedge clk_sm) begin xbad <= r_bad; xoff <= r_off; xkm <= r_km; xd <= rx_d[FW-1:0]; end
            assign pa_v = xv; assign pa_off = xoff; assign pa_km = xkm; assign pa_d = xd; assign pa_bad = xbad;
        end else begin : g_noxreg
            assign pa_v = rx_take; assign pa_off = r_off; assign pa_km = r_km; assign pa_d = rx_d[FW-1:0];
            assign pa_bad = r_bad;
        end
        reg [NL*LB-1:0] qa_idx;
        reg [NL-1:0]    qa_hit;
        reg [NL*LB-1:0] pa_idx;
        reg [NL-1:0]    pa_hit;
        always @* for (integer l = 0; l < NL; l = l + 1) begin : sel
            reg [OB:0] k;
            k = {1'b0, OB'(l)} - {1'b0, pa_off};
            pa_idx[l*LB +: LB] = k[LB-1:0];
            pa_hit[l] = !k[OB] && (k < (OB+1)'(LANES)) && pa_km[k[LB-1:0]];
        end
        always @(posedge clk_sm) begin qa_idx <= pa_idx; qa_hit <= pa_hit; end
        // ---------------- RX stage B: registered-select merge ----------------
        wire [NL*32-1:0] asmb_n;
        for (c = 0; c < RDUP; c = c + 1) begin : g_rxs
            localparam integer SL = (NL + RDUP - 1) / RDUP;          // destination lanes of this slice
            localparam integer LO = c * SL;
            localparam integer HI = ((c + 1) * SL > NL) ? NL : (c + 1) * SL;
            if (LO < NL) begin : g_on
                wire [FW-1:0] dq;                                     // this slice's copy of the record data
                ot_gpu_kreg_oh #(.W(FW), .RV({FW{1'b0}})) u_d (.clk(clk_sm), .rst_n(rst_sm_n),
                    .d(pa_d), .q(dq));
                for (genvar l = LO; l < HI; l = l + 1) begin : g_lane
                    assign asmb_n[32*l +: 32] = qa_hit[l] ? dq[32*qa_idx[l*LB +: LB] +: 32] : asmb[32*l +: 32];
                end
                // this slice of the reassembly register: cleared on the first S_RUN cycle (no record can merge
                // then: a record popped in S_RUN merges one cycle later), merged on qa_v; both strobes are
                // per-slice registered copies, so neither the SM-side request valid nor the pop fans out here
                wire [1:0] cq;                                        // {clear, merge}
                ot_gpu_kreg_oh #(.W(2), .RV(2'b00)) u_cq (.clk(clk_sm), .rst_n(rst_sm_n), .d({accept, pa_v}), .q(cq));
                reg [32*(HI-LO)-1:0] a_q;
                always @(posedge clk_sm or negedge rst_sm_n)
                    if (!rst_sm_n) a_q <= '0;
                    else if (cq[1]) a_q <= '0;
                    else if (cq[0]) a_q <= asmb_n[32*HI-1:32*LO];
                assign asmb[32*HI-1:32*LO] = a_q;
            end
        end

        always @(posedge clk_sm or negedge rst_sm_n) begin
            if (!rst_sm_n) begin
                st <= S_IDLE; mode_q <= 1'b0; cnt_q <= 8'd0; seq <= 8'd0; sw <= 8'd0; nrec <= 8'd0;
                nexp <= 9'd0; rcv <= 9'd0; npop <= 9'd0; flt_sm <= 1'b0;
                qa_v <= 1'b0; qa_bad <= 1'b0;
                for (integer r = 0; r < (1 << RB); r = r + 1) off_tab[r] <= '0;
            end else begin
                qa_v <= pa_v;
                qa_bad <= pa_bad;
                case (st)
                    S_IDLE: if (coll_req_v) begin
                        dmask <= dmask_n; mode_q <= coll_mode; cnt_q <= coll_count;
                        sw <= 8'd0; nrec <= req_nrec[7:0]; rcv <= 9'd0; npop <= 9'd0;
                        nexp <= coll_mode ? 9'(32'(req_nrec) * R) : req_nrec;
                        for (integer r = 0; r < (1 << RB); r = r + 1) off_tab[r] <= OB'(r * 32'(coll_count));
                        if (req_bad) flt_sm <= 1'b1;
                        st <= (req_nrec == 9'd0) ? S_RSP : S_RUN;
                    end
                    S_RUN: begin
                        if (tx_adv) sw <= sw + 8'd1;
                        if (rx_take) npop <= npop + 9'd1;
                        if (qa_v) begin
                            if (qa_bad) flt_sm <= 1'b1;
                            rcv <= rcv + 9'd1;
                            if (rcv + 9'd1 >= nexp) st <= S_RSP;
                        end
                    end
                    S_RSP: if (coll_rsp_rdy) begin
                        st <= S_IDLE; seq <= seq + 8'd1;
                    end
                    default: st <= S_IDLE;
                endcase
            end
        end
        assign coll_req_rdy  = (st == S_IDLE);
        assign coll_rsp_v    = (st == S_RSP);
        assign coll_rsp_data = asmb;

        // ---------------- clock crossings ----------------
        wire tx_ovf, rx_ovf, rx_in_rdy;
        ot_gpu_cdc_fifo_oh #(.ENABLE(1), .W(PW), .AW(AW), .SYNC(SYNC), .RDUP(RDUP), .WDUP(RDUP)) u_tx_cdc (
            .wclk(clk_sm), .wrst_n(rst_sm_n), .in_v(tx_in_v), .in_rdy(tx_in_rdy), .in_d(tx_rec),
            .rclk(clk_link), .rrst_n(rst_link_n), .out_v(lk_tx_v), .out_rdy(1'b1), .out_d(lk_tx_rec),
            .ovf_fault(tx_ovf));
        ot_gpu_cdc_fifo_oh #(.ENABLE(1), .W(PW), .AW(AW_RX), .SYNC(SYNC), .RDUP(RDUP)) u_rx_cdc (
            .wclk(clk_link), .wrst_n(rst_link_n), .in_v(lk_rx_v), .in_rdy(rx_in_rdy), .in_d(lk_rx_rec),
            .rclk(clk_sm), .rrst_n(rst_sm_n), .out_v(rx_out_v), .out_rdy((st == S_RUN) && (npop < nexp)),
            .out_d(rx_d), .ovf_fault(rx_ovf));

        reg flt_lk;
        always @(posedge clk_link or negedge rst_link_n)
            if (!rst_link_n) flt_lk <= 1'b0;
            else if ((lk_rx_v && !rx_in_rdy) || rx_ovf) flt_lk <= 1'b1;
        reg [SYNC-1:0] flt_sync;
        always @(posedge clk_sm or negedge rst_sm_n)
            if (!rst_sm_n) flt_sync <= {SYNC{1'b0}};
            else flt_sync <= {flt_sync[SYNC-2:0], flt_lk};
        assign coll_fault = flt_sm || flt_sync[SYNC-1] || tx_ovf;
    end else begin : g_off
        assign coll_req_rdy  = 1'b0;
        assign coll_rsp_v    = 1'b0;
        assign coll_rsp_data = {NL*32{1'b0}};
        assign coll_fault    = 1'b0;
        assign lk_tx_v       = 1'b0;
        assign lk_tx_rec     = {PW{1'b0}};
        /* verilator lint_off UNUSED */
        wire unused_off = &{1'b0, clk_sm, rst_sm_n, coll_req_v, coll_mode, coll_count, coll_data, coll_rsp_rdy,
                            clk_link, rst_link_n, lk_rx_v, lk_rx_rec};
        /* verilator lint_on UNUSED */
    end endgenerate
endmodule
