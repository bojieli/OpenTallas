`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81_cfg7_seq_local: per-pair configuration sequencer of the DS-ROM S81 die (CLAUDE S81-DIE, 2026-10-06).
//
// The S81 die gives every field pair NROM = 7 real cfg ROMs (ot_rom_4096x72_m8): 2^PHW = 1,024 phases x CW = 25 words
// = 25,600 words per pair (results/uarch/dsrom_c_w4_20261003/s82_inputs/inventory.json, words_per_pair_by_stage).
// The pinned single-macro loader (ot_v41_pair_pq_ld_cfgrom) stops at one 4,096-row macro ($fatal for PHW 10), so the
// die needs this sequencer: the loader of ot_v41_pair_pq_ld_frontend (PQ = 0, the pinned load-at-broadcast loader)
// with its linear word address split into a macro select (a[AW-1:12]) and a row (a[11:0]):
//   * one shared 12-bit row address to all NROM macros, one chip enable per macro (only the addressed macro reads);
//   * the 48-bit payload (rd_out[47:0]; rd_out[71:48] are spare macro columns) taken from the macro that was read on
//     the previous edge (bank select registered with the read), so the configuration word reaches c_d on exactly the
//     edge the combinational-read reference loader captures it (same-edge address lookahead, as ot_v41_pair_cfgrom_context).
// Ports: lc = {cfg_np[2:0], cfg_ph[PHW-1:0], cfg_go, go} from the slot station; cfg = {c_v, c_d[47:0], c_a[4:0]} in the
// q element's cfg pin order (cfg_a, cfg_d, cfg_v); go_e gates the element's go (W17 class-valid gate); st = {fault,
// ld_busy}.  fault is the reference loader's (constant 0 at PQ = 0: the q element exposes no shadow-free signals, so the
// die runs the pinned PQ = 0 loader).
// PQ = 1 (s81-die-2 2026-10-08, tie-off audit TA-10: the adopted PQ q element ot_v41_rom_elem_q_qxpq_w10 had go_tag /
// bank_free / sh_free floating on the die): the loader of ot_v41_pair_pq_ld_frontend PQ = 1 -- a broadcast that finds
// the element's configuration shadow full or the output-tag bank it would write still draining (ef = {bank_free,
// sh_free}) is held (pending) and loaded when both clear; a second broadcast before the load, or a go before the load
// finished, is a FAULT.  go_tag = the op tag of ot_v41_spine_pq_w17w10 (bt_tag = ist, which advances by one on every
// go broadcast, from 0 at reset): a 2-bit count of the broadcast gos this pair has seen (lc[0], before the class gate),
// so no tag wires leave the hub.  PQ = 0: go_tag = 0, ef ignored, cycle-identical to the pinned loader.
// Exact gate: rtl/v41die/test/tb_ot_s81_cfg7_seq.sv (cycle lockstep against ot_v41_pair_pq_ld_frontend PHW 10, PQ 0 and 1).
// LAYOUT = 1 (FILL-S2 2026-10-15, structural timing fix, 0 cycles): the hardened tile at LAYOUT 0 fails TT setup by -179 ps
// on lc[cfg_go/cfg_ph] -> phase*25 multiply -> 15-b add -> bank decode -> ce/a output pins (a combinational input-to-
// output path through an adder behind the pins).  LAYOUT 1 places configuration word k of phase p in macro k % 7, row
// 4p + k / 7 (25 <= 28 = 4 rows x 7 macros; 1,024 phases x 4 rows = 4,096 rows), so the start read is macro 0 at row
// {phase, 2'b00} (wiring only) and every later read takes macro/row from the registered next-word counters nb / nr:
// a and ce are one mux / one decode level from flops or from cfg_go.  Same edges, same payload, same c_d timing as
// LAYOUT 0 (lockstep gate with +define+TB_CFG7_IL7); the cfg ROM image must be emitted in the same layout
// (tools/s81_static_control/field_cfg7_image.py --layout il7).
// PINREG = 1 (S-ELEM-PQ/COLL 2026-10-16, VIS-ROM S81F-04 + owner rule 19:50 "register every pin"): every input (lc, ef,
// q0..q6) is captured in a pin flop and every output (a, ce0..6, cfg, go_e, st, go_tag) leaves from a pin flop, so the
// tile has NO combinational input-to-output path (LAYOUT 1 left 20: lc/ef -> a[11:0], ce0..6 and lc.go -> go_e).  The
// macro read loop (a/ce out flop -> ROM -> q in flop) is 2 edges longer, so the capture side (bank select, ld_run/ld_k/
// ld_np at capture, c_v/c_a/c_d, act) and the go side (go, cfg_go, pend, ld_start, the second-broadcast fault event, the
// tag count) run DL = 2 edges behind the loader; the output flops add 1.  Exact: the tile equals the PINREG 0 tile
// with its inputs delayed 1 edge and cfg/go_e/st/go_tag delayed 3 more (lc -> cfg/go_e/st/go_tag +4 edges, lc -> a/ce
// +2 edges, a fixed compiler-schedule shift, no runtime handshake added); reset flushes every pipeline flop.  The rst_n
// port drives only an ot_rst_relay (rtl/lib/ot_rst_relay.sv): assert immediate, release 3 edges after the port.
// Gate: tb_ot_s81_cfg7_seq.sv +define+TB_CFG7_PINREG (lockstep against the reference loader behind the same delays);
// negative control +define+OT_S81_CFG7_MUT_PRDL (capture 1 edge early) must FAIL.  PINREG = 0 is byte-for-byte the
// previous behaviour.
// ---------------------------------------------------------------------------
module ot_s81_cfg7_seq_local #(
    parameter integer NSEG = 8,
    parameter integer PHW = 10,
    parameter integer NROM = 7,
    parameter integer PQ = 0,
    parameter integer LAYOUT = 0,
    parameter integer LOCAL_COPY = 0,
    parameter integer PINREG = 0,
    parameter integer CW = 3 * NSEG + 1,
    parameter integer AW = $clog2(CW << PHW)
) (
    input  wire [0:0]          clk,
    input  wire [0:0]          rst_n,
    input  wire [PHW+4:0]      lc,
    output wire [11:0]         a,
    output wire [0:0]          ce0, ce1, ce2, ce3, ce4, ce5, ce6,
    input  wire [47:0]         q0, q1, q2, q3, q4, q5, q6,
    output wire [53:0]         cfg,
    output wire [0:0]          go_e,
    output wire [1:0]          st,
    input  wire [1:0]          ef,          // PQ: {bank_free, sh_free} of the element
    output wire [1:0]          go_tag,      // PQ: the op tag that rides with go
    output wire [6:0]          ce_local,
    output wire [5:0]          cfg_local,   // {cfg[53] (valid), cfg[4:0] (addr)}: the only cfg bits the BFP programme reads
    output wire               go_local
);
    initial begin
        if (NROM != 7) $fatal(1, "ot_s81_cfg7_seq_local: the port list is written for NROM = 7");
        if ((CW << PHW) > NROM * 4096) $fatal(1, "ot_s81_cfg7_seq_local: CW x 2^PHW words exceed NROM 4096-row macros");
        if (CW > 32 || AW < 12) $fatal(1, "ot_s81_cfg7_seq_local: CW <= 32 and AW >= 12 required");
        if (LAYOUT == 1 && (CW > 4 * NROM || PHW + 2 > 12)) $fatal(1, "ot_s81_cfg7_seq_local: LAYOUT 1 needs CW <= 28 and PHW <= 10");
    end
    // ---- reset (PINREG): the rst_n port drives only an ot_rst_relay (async assert, release 3 edges later); pin flops
    // reset from region 0, the sequencer from region 1 (native audit pr2: the port -> 564 async clears was capture 303 ps)
    wire rst_p, rst_c;
    generate if (PINREG != 0) begin : g_rst
        wire [1:0] rr_;
`ifdef OT_S81_CFG7_MUT_RSTREL
        ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(2)) u_rst (.clk(clk[0]), .rst_n_in(rst_n[0]), .rst_n(rr_));  // negative control: release 1 edge late
`else
        ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rst (.clk(clk[0]), .rst_n_in(rst_n[0]), .rst_n(rr_));
`endif
        assign rst_p = rr_[0]; assign rst_c = rr_[1];
    end else begin : g_rst0
        assign rst_p = rst_n[0]; assign rst_c = rst_n[0];
    end endgenerate
    // ---- pin registers (PINREG): inputs captured at the pin, outputs launched from the pin ----
    wire [PHW+4:0] lc_i;
    wire [1:0]     ef_i;
    wire [47:0]    q0_i, q1_i, q2_i, q3_i, q4_i, q5_i, q6_i;
    wire [11:0]    a_c;
    wire [6:0]     ce_c;
    wire [53:0]    cfg_c;
    wire           go_e_c;
    wire [1:0]     st_c, go_tag_c;
    generate if (PINREG != 0) begin : g_pin
        reg [PHW+4:0] lc_r; reg [1:0] ef_r;
        reg [47:0] q0_r, q1_r, q2_r, q3_r, q4_r, q5_r, q6_r;
        reg [11:0] a_r; reg [6:0] ce_r; reg [53:0] cfg_r; reg go_e_r; reg [1:0] st_r, go_tag_r;
        always @(posedge clk[0] or negedge rst_p)
            if (!rst_p) begin lc_r <= '0; ef_r <= 2'b00; end
            else begin lc_r <= lc; ef_r <= ef; end
        always @(posedge clk[0]) begin q0_r <= q0; q1_r <= q1; q2_r <= q2; q3_r <= q3; q4_r <= q4; q5_r <= q5; q6_r <= q6; end
        always @(posedge clk[0] or negedge rst_p)
            if (!rst_p) begin a_r <= 12'd0; ce_r <= 7'd0; cfg_r <= 54'd0; go_e_r <= 1'b0; st_r <= 2'b00; go_tag_r <= 2'b00; end
            else begin a_r <= a_c; ce_r <= ce_c; cfg_r <= cfg_c; go_e_r <= go_e_c; st_r <= st_c; go_tag_r <= go_tag_c; end
        // Same-edge private copies keep boundary output Qs free of local loads.  keep sits on the private copies only:
        // ot_keep_regs.tcl then keeps those flop cells, opt_merge leaves them alone, and the port flops ce_r/cfg_r/go_e_r
        // stay plain (a keep on the port-flop wire made Yosys hang a dangling BUFx2 off ce0..6/go_e = face_guard shared).
        if (LOCAL_COPY != 0) begin : g_local
        (* keep = "true" *) reg [6:0] ce_l;
        (* keep = "true" *) reg [5:0] cfg_l;
        (* keep = "true" *) reg go_l;
        always @(posedge clk[0] or negedge rst_p)
            if (!rst_p) begin ce_l <= '0; cfg_l <= '0; go_l <= 1'b0; end
            else begin ce_l <= ce_c; cfg_l <= {cfg_c[53], cfg_c[4:0]}; go_l <= go_e_c; end
        assign ce_local = ce_l; assign cfg_local = cfg_l; assign go_local = go_l;
        end else begin : g_no_local
            assign ce_local = ce_r; assign cfg_local = {cfg_r[53], cfg_r[4:0]}; assign go_local = go_e_r;
        end
        assign lc_i = lc_r; assign ef_i = ef_r;
        assign q0_i = q0_r; assign q1_i = q1_r; assign q2_i = q2_r; assign q3_i = q3_r; assign q4_i = q4_r; assign q5_i = q5_r; assign q6_i = q6_r;
        assign a = a_r; assign {ce6, ce5, ce4, ce3, ce2, ce1, ce0} = ce_r;
        assign cfg = cfg_r; assign go_e = go_e_r; assign st = st_r; assign go_tag = go_tag_r;
    end else begin : g_nopin
        assign ce_local = ce_c; assign cfg_local = {cfg_c[53], cfg_c[4:0]}; assign go_local = go_e_c;
        assign lc_i = lc; assign ef_i = ef;
        assign q0_i = q0; assign q1_i = q1; assign q2_i = q2; assign q3_i = q3; assign q4_i = q4; assign q5_i = q5; assign q6_i = q6;
        assign a = a_c; assign {ce6, ce5, ce4, ce3, ce2, ce1, ce0} = ce_c;
        assign cfg = cfg_c; assign go_e = go_e_c; assign st = st_c; assign go_tag = go_tag_c;
    end endgenerate
    wire           go      = lc_i[0];
    wire           cfg_go  = lc_i[1];
    wire [PHW-1:0] cfg_ph  = lc_i[PHW+1:2];
    wire [2:0]     cfg_np  = lc_i[PHW+4:PHW+2];
    reg [AW-1:0] ld_a;
    reg         c_v;
    reg [4:0]   c_a;
    reg [47:0]  c_d;
    reg         fault;
    reg         ld_run;
    reg [4:0]   ld_k;
    reg [2:0]   ld_np;
    reg         pend;
    reg [PHW-1:0] pend_ph;
    reg [2:0]   pend_np;
    reg [1:0]   tag;
    wire        ld_ok = (PQ == 0) || (ef_i[0] && ef_i[1]);
    wire        ld_start = (cfg_go && ld_ok) || (PQ != 0 && pend && !cfg_go && ld_ok);
    // same-edge lookahead of the reference's combinational cm_a = ld_a: read ld_a's word one edge early
    wire          rce = rst_c && (ld_start || (ld_run && ld_k < 5'(CW - 1)));
    wire [AW-13:0] rbank;
    reg  [AW-13:0] bank_q;
    generate if (LAYOUT == 1) begin : g_il7
        // registered next-word position: nb = macro, nr = row-in-phase of word ld_k + 1; lph = the loading phase
        reg [2:0] nb;
        reg [1:0] nr;
        reg [PHW-1:0] lph;
        wire [PHW-1:0] sph = cfg_go ? cfg_ph : pend_ph;
`ifdef OT_S81_CFG7_MUT_STRIDE
        wire [PHW-1:0] sph_m = {sph[PHW-1:1], 1'b0};     // negative control: wrong phase row base
`else
        wire [PHW-1:0] sph_m = sph;
`endif
        always @(posedge clk[0]) begin
            if (ld_start) begin nb <= 3'd1; nr <= 2'd0; lph <= sph_m; end
            else if (ld_run) begin nb <= (nb == 3'(NROM - 1)) ? 3'd0 : nb + 3'd1; nr <= (nb == 3'(NROM - 1)) ? nr + 2'd1 : nr; end
        end
        assign a_c = ld_start ? {sph_m, 2'b00} : {lph, nr};
        assign rbank = ld_start ? (AW-12)'(0) : (AW-12)'(nb);
    end else begin : g_lin
        wire [AW-1:0] ra = ld_start ? AW'(cfg_go ? cfg_ph : pend_ph) * AW'(CW) : ld_a + 1'b1;
        assign rbank = ra[AW-1:12];
        assign a_c = ra[11:0];
    end endgenerate
    assign ce_c[0] = rce && rbank == 0;
    assign ce_c[1] = rce && rbank == 1;
    assign ce_c[2] = rce && rbank == 2;
    assign ce_c[3] = rce && rbank == 3;
    assign ce_c[4] = rce && rbank == 4;
    assign ce_c[5] = rce && rbank == 5;
    assign ce_c[6] = rce && rbank == 6;
    always @(posedge clk[0]) if (rce) bank_q <= rbank;
    // ---- capture / go side DL edges behind the loader (PINREG: a/ce out flop + q in flop = +2 on the macro read) ----
    wire          ld_run_x, cfg_go_x, ld_start_x, go_x, pend_x, ev1_x;
    wire [4:0]    ld_k_x;
    wire [2:0]    ld_np_x;
    wire [AW-13:0] bank_x;
`ifndef OT_S81_CFG7_MUT_NOFAULT
    wire          ev1 = (PQ != 0) && cfg_go && (pend || ld_run);   // a second broadcast before the load
`else
    wire          ev1 = 1'b0;
`endif
    generate if (PINREG != 0) begin : g_dl
        reg [1:0] d_run, d_cgo, d_st, d_go, d_pend, d_ev1;
        reg [4:0] d_k [0:1];
        reg [2:0] d_np [0:1];
        reg [AW-13:0] d_bk [0:1];
        always @(posedge clk[0] or negedge rst_c)
            if (!rst_c) begin d_run <= 2'b00; d_cgo <= 2'b00; d_st <= 2'b00; d_go <= 2'b00; d_pend <= 2'b00; d_ev1 <= 2'b00; end
            else begin
                d_run <= {d_run[0], ld_run}; d_cgo <= {d_cgo[0], cfg_go}; d_st <= {d_st[0], ld_start};
                d_go <= {d_go[0], go}; d_pend <= {d_pend[0], pend}; d_ev1 <= {d_ev1[0], ev1};
            end
        always @(posedge clk[0]) begin
            d_k[0] <= ld_k; d_k[1] <= d_k[0]; d_np[0] <= ld_np; d_np[1] <= d_np[0]; d_bk[0] <= bank_q; d_bk[1] <= d_bk[0];
        end
        assign ld_run_x = d_run[1]; assign cfg_go_x = d_cgo[1]; assign ld_start_x = d_st[1]; assign go_x = d_go[1];
        assign pend_x = d_pend[1]; assign ev1_x = d_ev1[1]; assign ld_k_x = d_k[1]; assign ld_np_x = d_np[1];
`ifdef OT_S81_CFG7_MUT_PRDL
        assign bank_x = d_bk[0];             // negative control: payload selected one edge early
`else
        assign bank_x = d_bk[1];
`endif
    end else begin : g_nodl
        assign ld_run_x = ld_run; assign cfg_go_x = cfg_go; assign ld_start_x = ld_start; assign go_x = go;
        assign pend_x = pend; assign ev1_x = ev1; assign ld_k_x = ld_k; assign ld_np_x = ld_np; assign bank_x = bank_q;
    end endgenerate
`ifdef OT_S81_CFG7_MUT_BANK
    wire [AW-13:0] sel = rbank;          // negative control: select by the current (not the read) address
`else
    wire [AW-13:0] sel = bank_x;
`endif
    reg [47:0] cm_q;
    always @(*) begin
        case (sel)
            0: cm_q = q0_i;
            1: cm_q = q1_i;
            2: cm_q = q2_i;
            3: cm_q = q3_i;
            4: cm_q = q4_i;
            5: cm_q = q5_i;
            default: cm_q = q6_i;
        endcase
    end
    always @(posedge clk[0] or negedge rst_c) begin
        if (!rst_c) begin
            ld_run <= 1'b0; ld_k <= 5'd0; c_v <= 1'b0; fault <= 1'b0; pend <= 1'b0; tag <= 2'd0;
        end else begin
            fault <= fault;
            pend <= pend;
            c_v <= ld_run_x;
            if (PQ != 0) begin
                if (cfg_go && !ld_ok) begin pend <= 1'b1; pend_ph <= cfg_ph; pend_np <= cfg_np; end
                else if (ld_start) pend <= 1'b0;
                if (ev1_x) fault <= 1'b1;                                         // a second broadcast before the load
                if (go_x && (pend_x || ld_run_x || c_v || cfg_go_x)) fault <= 1'b1;  // go before the load finished
                if (go_x) tag <= tag + 2'd1;
            end
            if (ld_start) begin
                ld_run <= 1'b1; ld_k <= 5'd0;
`ifdef OT_S81_CFG7_MUT_STRIDE
                ld_a <= AW'(cfg_ph) * AW'(CW + 1);   // negative control: wrong phase stride
`else
                ld_a <= AW'(cfg_go ? cfg_ph : pend_ph) * AW'(CW);
`endif
                ld_np <= cfg_go ? cfg_np : pend_np;
            end else if (ld_run) begin
                ld_k <= ld_k + 5'd1;
                ld_a <= ld_a + 1'b1;
                if (ld_k == 5'(CW - 1)) ld_run <= 1'b0;
            end
        end
    end
    reg act;
    always @(posedge clk[0] or negedge rst_c) begin
        if (!rst_c) act <= 1'b0;
        else if (cfg_go_x || ld_start_x) act <= 1'b0;
        else if (c_v && c_a >= 5'(NSEG) && c_a < 5'(2 * NSEG) && c_d[0]) act <= 1'b1;
    end
    always @(posedge clk[0]) begin
        c_a <= ld_k_x;
        if (ld_run_x) c_d <= (ld_k_x == 5'(2 * NSEG)) ? (cm_q | {42'd0, ld_np_x, 3'd0}) : cm_q;
    end
    assign go_e_c = go_x && act;
    assign cfg_c = {c_v, c_d, c_a};
`ifdef OT_S81_CFG7_MUT_NOHOLD
    wire ld_busy = ld_run_x || c_v;            // negative control: pending load not reported busy
`else
    wire ld_busy = ld_run_x || c_v || pend_x;
`endif
    assign st_c = {fault, ld_busy};
`ifdef OT_S81_CFG7_MUT_TAG
    assign go_tag_c = (PQ != 0) ? tag + 2'd1 : 2'd0;   // negative control: tag one op ahead
`else
    assign go_tag_c = (PQ != 0) ? tag : 2'd0;
`endif
endmodule

// ot_s81_cfg7_seq_bf_local (s81-die-rtl-bind 2026-10-14): the BF pair's configuration sequencer die master.  The BF pair's
// front (ot_s81_bf_front: the DS q element ot_v41_rom_elem_qx_w10 re-cut, not the PQ element) exposes no configuration-
// shadow handshake, so its loader is the pinned PQ 0 loader of ot_s81_cfg7_seq_local (load at broadcast, go_tag 0): the same
// RTL at PQ 0 with no ef / go_tag pins (the PQ 0 loader never reads ef; cycle-identical to ot_s81_cfg7_seq_local PQ 0, gate
// rtl/v41die/test/tb_ot_s81_cfg7_seq.sv PQ 0).
module ot_s81_cfg7_seq_bf_local #(
    parameter integer NSEG = 8,
    parameter integer PHW = 10,
    parameter integer NROM = 7,
    parameter integer LAYOUT = 0,
    parameter integer LOCAL_COPY = 0,
    parameter integer PINREG = 0
) (
    input  wire [0:0]          clk,
    input  wire [0:0]          rst_n,
    input  wire [PHW+4:0]      lc,
    output wire [11:0]         a,
    output wire [0:0]          ce0, ce1, ce2, ce3, ce4, ce5, ce6,
    input  wire [47:0]         q0, q1, q2, q3, q4, q5, q6,
    output wire [53:0]         cfg,
    output wire [0:0]          go_e,
    output wire [1:0]          st,
    output wire [6:0]          ce_local,
    output wire [5:0]          cfg_local,
    output wire               go_local
);
    wire [1:0] go_tag_0;      // constant 0 at PQ 0
    ot_s81_cfg7_seq_local #(.NSEG(NSEG), .PHW(PHW), .NROM(NROM), .PQ(0), .LAYOUT(LAYOUT), .LOCAL_COPY(LOCAL_COPY), .PINREG(PINREG)) u (.clk(clk), .rst_n(rst_n), .lc(lc), .a(a),
        .ce0(ce0), .ce1(ce1), .ce2(ce2), .ce3(ce3), .ce4(ce4), .ce5(ce5), .ce6(ce6),
        .q0(q0), .q1(q1), .q2(q2), .q3(q3), .q4(q4), .q5(q5), .q6(q6),
        .cfg(cfg), .go_e(go_e), .st(st), .ef(2'b00), .go_tag(go_tag_0), .ce_local(ce_local), .cfg_local(cfg_local), .go_local(go_local));
endmodule

// Preserve the released top-level pin and parameter contract.
module ot_s81_cfg7_seq #(
    parameter integer NSEG = 8,
    parameter integer PHW = 10,
    parameter integer NROM = 7,
    parameter integer PQ = 0,
    parameter integer LAYOUT = 0,
    parameter integer PINREG = 0,
    parameter integer CW = 3 * NSEG + 1,
    parameter integer AW = $clog2(CW << PHW)
) (
    input  wire [0:0]          clk,
    input  wire [0:0]          rst_n,
    input  wire [PHW+4:0]      lc,
    output wire [11:0]         a,
    output wire [0:0]          ce0, ce1, ce2, ce3, ce4, ce5, ce6,
    input  wire [47:0]         q0, q1, q2, q3, q4, q5, q6,
    output wire [53:0]         cfg,
    output wire [0:0]          go_e,
    output wire [1:0]          st,
    input  wire [1:0]          ef,          // PQ: {bank_free, sh_free} of the element
    output wire [1:0]          go_tag       // PQ: the op tag that rides with go
);
    ot_s81_cfg7_seq_local #(.NSEG(NSEG),.PHW(PHW),.NROM(NROM),.PQ(PQ),.LAYOUT(LAYOUT),.PINREG(PINREG),.CW(CW),.AW(AW)) u_impl (.clk(clk),.rst_n(rst_n),.lc(lc),.a(a),.ce0(ce0),.ce1(ce1),.ce2(ce2),.ce3(ce3),.ce4(ce4),.ce5(ce5),.ce6(ce6),.q0(q0),.q1(q1),.q2(q2),.q3(q3),.q4(q4),.q5(q5),.q6(q6),.cfg(cfg),.go_e(go_e),.st(st),.ef(ef),.go_tag(go_tag));
endmodule

// Preserve the released top-level pin and parameter contract.
module ot_s81_cfg7_seq_bf #(
    parameter integer NSEG = 8,
    parameter integer PHW = 10,
    parameter integer NROM = 7,
    parameter integer LAYOUT = 0,
    parameter integer PINREG = 0
) (
    input  wire [0:0]          clk,
    input  wire [0:0]          rst_n,
    input  wire [PHW+4:0]      lc,
    output wire [11:0]         a,
    output wire [0:0]          ce0, ce1, ce2, ce3, ce4, ce5, ce6,
    input  wire [47:0]         q0, q1, q2, q3, q4, q5, q6,
    output wire [53:0]         cfg,
    output wire [0:0]          go_e,
    output wire [1:0]          st
);
    ot_s81_cfg7_seq_bf_local #(.NSEG(NSEG),.PHW(PHW),.NROM(NROM),.LAYOUT(LAYOUT),.PINREG(PINREG)) u_impl (.clk(clk),.rst_n(rst_n),.lc(lc),.a(a),.ce0(ce0),.ce1(ce1),.ce2(ce2),.ce3(ce3),.ce4(ce4),.ce5(ce5),.ce6(ce6),.q0(q0),.q1(q1),.q2(q2),.q3(q3),.q4(q4),.q5(q5),.q6(q6),.cfg(cfg),.go_e(go_e),.st(st));
endmodule
