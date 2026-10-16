`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_coll_split (redesign-ds 2026-10-09, coordinator: "a 1.36 mm tile with 1,151 ps clock insertion is the root
// problem"): the S81 collective core column (dsfd_coll_core, 540 x 1360.8 um, measured CTS insertion 1,151 ps, every
// route lost to the insertion / hold window) split into THREE abutted hard tiles with registered boundaries
// (Tensix / Cerebras pattern), stacked S -> N in the same column (width CW, the column widened so the engine tile keeps
// its 24 FIFO SRAMs at <= 60 % utilisation):
//
//   dsfd_coll_cb  (bottom, CW x 340.2)  VM side: f_vm / ts / t_vm (S face, the slab's VM interface), the OUTPUT queue
//                                       (16 deep, sliced, push replicas) + t_vm register; relays of lanes 0 (W0) and
//                                       4 (E0) between their lane tiles and the engine tile.
//   dsfd_coll_ce  (middle, CW x 680.4)  ot_s81ph_coll_core (EXT 1, OQX 1): TP4 engine + receive FIFO SRAMs, the 6 VM
//                                       input queues, packer, credits; lanes 1, 2 (W) and 5, 6 (E) at its own faces.
//   dsfd_coll_ct  (top, CW x 340.2)     relays of lanes 3 (W3) and 7 (E3).
//
// Every crossing is latency insensitive: lane streams pass through 2-slot skids (ot_s81ph_skid2: valid, data and
// ready all registered) at BOTH sides of every tile face; the packer word goes down as a registered stream into the
// remote output queue under credits (OQX: the counter starts at the queue depth, the queue returns one pulse a pop);
// f_vm / flt / faults cross as plain pin registers (the VM sends only with credits, so the f_vm pipe never needs a
// ready).  Exact: per-lane order and the engine's reduce / gather sequence are unchanged (transaction level; bench
// tb_s81ph_coll_sys with +define+OT_S81PH_COLL_SPLIT).  Cycle cost vs dsfd_coll_core: f_vm -> queues +2, packer word
// -> t_vm +2, lanes 0 / 3 / 4 / 7 +2 each way (lanes 1 / 2 / 5 / 6 unchanged).
// ---------------------------------------------------------------------------------------------------------------

// ---- two skids in series: one at each face of a relay tile
module ot_s81ph_relay2 #(parameter integer W = 8) (
    input  wire clk, input wire rst_n,
    input  wire in_v, output wire in_r, input wire [W-1:0] in_d,
    output wire out_v, input wire out_r, output wire [W-1:0] out_d
);
    wire m_v, m_r; wire [W-1:0] m_d;
    ot_s81ph_skid2 #(.W(W)) u_a (.clk(clk), .rst_n(rst_n), .in_v(in_v), .in_r(in_r), .in_d(in_d), .out_v(m_v), .out_r(m_r), .out_d(m_d));
    ot_s81ph_skid2 #(.W(W)) u_b (.clk(clk), .rst_n(rst_n), .in_v(m_v), .in_r(m_r), .in_d(m_d), .out_v(out_v), .out_r(out_r), .out_d(out_d));
endmodule

// ---- kept 1-bit register (hardcore-1010 collct 2026-10-10): one instance per physical copy.  The hierarchy boundary
// stops opt_merge from folding equal copies (a plain (* keep *) reg does NOT: see ot_dsrom_window_keep_reg), so two pin
// flops with the same D each anchor at their own pin.  Synthesise with SYNTH_KEEP_MODULES=ot_s81ph_keep_ff.
(* keep_hierarchy = "yes" *)
module ot_s81ph_keep_ff (input wire clk, input wire rst_n, input wire d, output reg q);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;
endmodule

// ---- credit relay (redesign-ds 2026-10-10, split3 CR mode): link -> credit rx (pin flops + FIFO + OREG) -> credit tx -> link
// PS (fill-9 2026-10-10, opt-in, default 0 = byte-identical): PIN STATIONS.  One extra register stage on every pin of the
// relay -- {i_v, i_d} and the returned credit o_cr on the way in, {o_v, o_d} and the issued credit i_cr on the way out --
// so the pin flop (anchored at its pin by io_flop_at_pins) and the FIFO-side flop (rx landing d_q / tx l_data, beside the
// landing FIFO and its 8:1 read mux) are two different flops: the pin-to-FIFO wire across the 340-um ct tile gets its own
// cycle instead of sharing one with the 8:1 read mux / FIFO write (ct-split3cra TT -46.7 = tx l_data -> li3_d / elo_d
// output wire; SS -149 = cnt / rp -> 553-bit l_data).  Exact: each stream is delayed by one cycle each way; credits keep
// counting the same D landing slots (the credit round trip grows by 2 cycles per link, throughput only).
// RSL (hardcore-1010 fe G 2026-10-10, opt-in, default 0 = byte-identical): READ/WRITE-SELECT SLICES.  ct-split3crpb routed
// TT -66.17 (SS -185.8) on rx.rp[*] -> 8:1 landing read mux x 553 -> tx.l_data enable: three read-pointer flops and the
// tx 'send' enable each fan out to ~553 x 8 loads across the tile.  RSL = S keeps S kept copies of a ONE-HOT read pointer
// and of a one-hot write pointer, each copy driving only its W/S-bit slice of the landing FIFO (AND-OR read select), and the
// tx data register loads every cycle (l_data is only sampled with l_valid), so no pointer / enable flop drives more than
// ~W/S x D loads.  Same cycle behaviour as RSL 0 for every valid beat and credit (exact; 0 cycles).
module ot_s81ph_cr_relay #(parameter integer W = 8, parameter integer D = 8, parameter integer PS = 0,
    parameter integer RSL = 0) (
    input  wire clk, input wire rst_n,
    input  wire i_v, output wire i_cr, input wire [W-1:0] i_d,     // upstream link (valid / data in, credit pulse out)
    output wire o_v, input wire o_cr, output wire [W-1:0] o_d      // downstream link (valid / data out, credit pulse in)
);
    wire m_v, m_r, f; wire [W-1:0] m_d;
    wire xi_v, xi_cr, xo_v, xo_cr; wire [W-1:0] xi_d, xo_d;
    generate if (PS != 0) begin : g_ps
        wire iv_q, icr_q, ov_q, ocr_q; reg [W-1:0] id_q, od_q;
        // 1-bit pin stations are separate kept instances (KPS, hardcore-1010 collct): the issued-credit station icr_q and
        // the valid station ov_q both equal 'send' two cycles late, so opt_merge folded them into ONE flop driving two
        // pins on different faces (rslps routed TT -56.65: u_lo7.o_v -> lo7_r S face / elo_v E face, li7_v, wli_r, wlo_v)
        ot_s81ph_keep_ff u_iv (.clk(clk), .rst_n(rst_n), .d(i_v), .q(iv_q));
        ot_s81ph_keep_ff u_icr (.clk(clk), .rst_n(rst_n), .d(xi_cr), .q(icr_q));
        ot_s81ph_keep_ff u_ov (.clk(clk), .rst_n(rst_n), .d(xo_v), .q(ov_q));
        ot_s81ph_keep_ff u_ocr (.clk(clk), .rst_n(rst_n), .d(o_cr), .q(ocr_q));
`ifdef OT_S81PH_MUT_CTPS
        // negative control: the output data station lags its valid by one more cycle (must be caught by the bench)
        reg [W-1:0] od_m;
        always @(posedge clk) begin id_q <= i_d; od_m <= xo_d; od_q <= od_m; end
`else
        always @(posedge clk) begin id_q <= i_d; od_q <= xo_d; end
`endif
        assign xi_v = iv_q; assign xi_d = id_q; assign i_cr = icr_q;
        assign o_v = ov_q; assign o_d = od_q; assign xo_cr = ocr_q;
    end else begin : g_np
        assign xi_v = i_v; assign xi_d = i_d; assign i_cr = xi_cr;
        assign o_v = xo_v; assign o_d = xo_d; assign xo_cr = o_cr;
    end endgenerate
`ifdef OT_S81PH_MUT_CR_CRED
    localparam integer CX = D + 8;   // negative control: the sender believes in 8 more landing slots than exist
`else
    localparam integer CX = D;
`endif
    generate if (RSL == 0) begin : g_std
    ot_link_credit_rx #(.W(W), .DEPTH(D), .OREG(0), .WFREE(1)) u_rx (.clk(clk), .rst_n(rst_n), .l_valid(xi_v), .l_data(xi_d), .l_credit(xi_cr),
        .o_valid(m_v), .o_ready(m_r), .o_data(m_d), .fault(f));
    ot_link_credit_tx #(.W(W), .CRED(CX)) u_tx (.clk(clk), .rst_n(rst_n), .i_valid(m_v), .i_ready(m_r), .i_data(m_d),
        .l_valid(xo_v), .l_data(xo_d), .l_credit(xo_cr));
    end else begin : g_rsl
        localparam integer SW = (W + RSL - 1) / RSL;          // bits per slice (last slice may be short)
        localparam integer CW = $clog2(D + 1), KW = $clog2(CX + 1);
        // rx: landing register, count, credit (same as ot_link_credit_rx WFREE=1 OREG=0)
        reg v_q; reg [W-1:0] d_q; reg [CW-1:0] n; reg flt; wire l_cr;
        // tx: credit counter (same as ot_link_credit_tx)
        reg cr_q; reg [KW-1:0] cnt; wire l_v; wire [W-1:0] l_d;
        wire fv = n != 0, full = n == CW'(D);
        wire send = fv && cnt != 0;                           // = pop
        wire wr = v_q && !full;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin v_q <= 1'b0; n <= 0; flt <= 1'b0; cr_q <= 1'b0; cnt <= KW'(CX); end
            else begin
                v_q <= xi_v; if (v_q && full && !send) flt <= 1'b1;
                n <= n + CW'(wr) - CW'(send);
                cr_q <= xo_cr; cnt <= cnt + KW'(cr_q) - KW'(send);
            end
        // l_cr (credit out, upstream face) and l_v (valid out, downstream face) both = send one cycle late: kept separate
        // instances so each can sit at its own pin (a plain reg pair is merged by opt_merge; cb RSL has no PS stations)
        ot_s81ph_keep_ff u_lcr (.clk(clk), .rst_n(rst_n), .d(send), .q(l_cr));
`ifdef OT_S81PH_MUT_KPS
        // negative control: the kept valid copy is fed one cycle late (valid lags its data word; must be caught)
        reg send_m; always @(posedge clk or negedge rst_n) if (!rst_n) send_m <= 1'b0; else send_m <= send;
        ot_s81ph_keep_ff u_lv (.clk(clk), .rst_n(rst_n), .d(send_m), .q(l_v));
`else
        ot_s81ph_keep_ff u_lv (.clk(clk), .rst_n(rst_n), .d(send), .q(l_v));
`endif
        always @(posedge clk) d_q <= xi_d;
        genvar s, e;
        for (s = 0; s < RSL; s = s + 1) begin : g_s
            localparam integer LO = s * SW, HI = (LO + SW > W) ? W : LO + SW;
            if (LO < W) begin : g_on
                // this slice's landing storage and its own kept one-hot pointer copies
                reg [HI-LO-1:0] ms [0:D-1];
                reg [HI-LO-1:0] ld;
                (* keep = "true", dont_touch = "true" *) reg [D-1:0] rp_oh, wp_oh;
`ifdef OT_S81PH_MUT_RSL
                // negative control: slice 0's read-pointer copy advances one cycle late
                reg adv; always @(posedge clk or negedge rst_n) if (!rst_n) adv <= 1'b0; else adv <= send;
                wire radv = (s == 0) ? adv : send;
`else
                wire radv = send;
`endif
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) begin rp_oh <= D'(1); wp_oh <= D'(1); end
                    else begin
                        if (radv) rp_oh <= {rp_oh[D-2:0], rp_oh[D-1]};
                        if (wr) wp_oh <= {wp_oh[D-2:0], wp_oh[D-1]};
                    end
                reg [HI-LO-1:0] rd;
                integer k;
                always @(*) begin rd = '0; for (k = 0; k < D; k = k + 1) rd = rd | (ms[k] & {(HI-LO){rp_oh[k]}}); end
                for (e = 0; e < D; e = e + 1) begin : g_e
                    always @(posedge clk) if (wr && wp_oh[e]) ms[e] <= d_q[HI-1:LO];
                end
                always @(posedge clk) ld <= rd;               // loads every cycle; sampled only with l_valid
                assign l_d[HI-1:LO] = ld;
            end
        end
        assign xi_cr = l_cr; assign f = flt;
        assign xo_v = l_v; assign xo_d = l_d;
        assign m_v = fv; assign m_r = cnt != 0; assign m_d = '0;
    end endgenerate
endmodule

// ---- bottom tile: VM interface, output queue, lanes 0 / 4 relays
// s81-ctl-1011: with +define+OT_S81PH_COLL_JOB this tile carries the coll command endpoint and is the distinct master
// dsfd_coll_cbj (its own closure / view; dsfd_coll_cb without the define is unchanged, cell names included).
`ifndef OT_S81PH_CB_MASTER
`ifdef OT_S81PH_COLL_JOB
`define OT_S81PH_CB_MASTER dsfd_coll_cbj
`else
`define OT_S81PH_CB_MASTER dsfd_coll_cb
`endif
`endif
module `OT_S81PH_CB_MASTER #(parameter integer OD = 16,
    parameter integer CR = 0,  // redesign-ds: 1 = every lane / seam stream is a credit link (ot_s81ph_cr_relay), see ot_link_credit
    // TREP (ds-1010 2026-10-10, opt-in): the VM take strobe is re-registered once per output-queue slice (keep copies
    // beside each slice) and each slice pops itself, so no single flop drives the 2,100 anchored t_vm pin flops spread
    // along the 680 um S face (cb crpa post-CTS ts_r -> pop -> t_vm[1902] -140 ps, 560 um).  +1 cycle take -> t_vm.
    parameter integer TREP = `ifdef OT_S81PH_COLL_TREP 1 `else 0 `endif,
    // RSL (hardcore-1010 fe G, opt-in): one-hot pointer slices in every credit relay (ot_s81ph_cr_relay RSL), 0 cycles
    parameter integer RSL = `ifdef OT_S81PH_COLL_RSL 8 `else 0 `endif
) (
    input  wire [0:0]     ck,
    input  wire [0:0]     rs,
    // S face: the slab VM interface
    input  wire [591:0]   f_vm,
    input  wire [2:0]     ts,
    output reg  [2099:0]  t_vm,
    // W face: lane 0 (W0) tile;  E face: lane 4 (E0) tile
    output wire [0:0] wlo_v,  input wire [0:0] wlo_r, output wire [552:0] wlo_d,
    input wire [0:0] wli_v,  output wire [0:0] wli_r, input  wire [552:0] wli_d,
    input  wire [2:0]     wflt,
    output wire [0:0] elo_v,  input wire [0:0] elo_r, output wire [552:0] elo_d,
    input wire [0:0] eli_v,  output wire [0:0] eli_r, input  wire [552:0] eli_d,
    input  wire [2:0]     eflt,
    // N face: seam to dsfd_coll_ce
    output reg  [591:0]   fvm_u,
    output reg  [5:0]     flt_u,        // {lane 4 flt, lane 0 flt}
    input wire [0:0] lo0_v,  output wire [0:0] lo0_r, input  wire [552:0] lo0_d,
    output wire [0:0] li0_v,  input wire [0:0] li0_r, output wire [552:0] li0_d,
    input wire [0:0] lo4_v,  output wire [0:0] lo4_r, input  wire [552:0] lo4_d,
    output wire [0:0] li4_v,  input wire [0:0] li4_r, output wire [552:0] li4_d,
    input wire [0:0] bw_v,
    input  wire [2099:1]  bw_d,
    output reg [0:0] bw_cr,
    output reg [0:0] bw_flt
`ifdef OT_S81PH_COLL_JOB
    // s81-ctl-1011: the coll command endpoint (ADAPTER_CONTRACT_1011 engine 3), S face beside t_vm (x 522..680)
    ,
    input  wire [84:0]    c_cmd,
    output wire [8:0]     c_done,
    output wire [1:0]     c_st
`endif
);
    wire clk = ck[0];
    reg [1:0] rst_s;
    always @(posedge clk or negedge rs[0]) if (!rs[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    // VM input: pin register, then the seam register (two edges, no handshake: the VM sends only with credits)
    reg [591:0] fv_r; reg [2:0] ts_r; reg [5:0] flt_r;
    wire [591:0] fv_rel;
`ifdef OT_S81PH_COLL_JOB
    // the endpoint's release mux sits between the pin register and the seam register: records reach the core only under
    // their coll descriptor (+0 cycles); the done is taken from this tile's t_vm output flops (the slab's VM-edge pins)
    wire jf_unused;
    ot_s81_coll_job #(.MUT(`ifdef OT_S81PH_COLL_JOB_MUT `OT_S81PH_COLL_JOB_MUT `else 0 `endif)) u_job (.c_clk(clk), .c_rst_n(rs[0]),
        .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st), .ck(clk), .rs_n(rst_n), .vm_f(fv_r), .core_f(fv_rel),
        .core_h(t_vm[13:0]), .fault(jf_unused));
`else
    assign fv_rel = fv_r;
`endif
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fv_r <= 0; fvm_u <= 0; ts_r <= 0; flt_r <= 0; flt_u <= 0; end
        else begin fv_r <= f_vm; fvm_u <= fv_rel; ts_r <= ts; flt_r <= {eflt, wflt}; flt_u <= flt_r; end
    // lane relays (lane-face skid + seam-face skid; CR: credit relays, the *_r pins carry credit pulses)
    generate if (CR != 0) begin : g_cr
    ot_s81ph_cr_relay #(.W(553), .RSL(RSL)) u_lo0 (.clk(clk), .rst_n(rst_n), .i_v(lo0_v), .i_cr(lo0_r), .i_d(lo0_d), .o_v(wlo_v), .o_cr(wlo_r), .o_d(wlo_d));
    ot_s81ph_cr_relay #(.W(553), .RSL(RSL)) u_li0 (.clk(clk), .rst_n(rst_n), .i_v(wli_v), .i_cr(wli_r), .i_d(wli_d), .o_v(li0_v), .o_cr(li0_r), .o_d(li0_d));
    ot_s81ph_cr_relay #(.W(553), .RSL(RSL)) u_lo4 (.clk(clk), .rst_n(rst_n), .i_v(lo4_v), .i_cr(lo4_r), .i_d(lo4_d), .o_v(elo_v), .o_cr(elo_r), .o_d(elo_d));
    ot_s81ph_cr_relay #(.W(553), .RSL(RSL)) u_li4 (.clk(clk), .rst_n(rst_n), .i_v(eli_v), .i_cr(eli_r), .i_d(eli_d), .o_v(li4_v), .o_cr(li4_r), .o_d(li4_d));
    end else begin : g_sk
    ot_s81ph_relay2 #(.W(553)) u_lo0 (.clk(clk), .rst_n(rst_n), .in_v(lo0_v), .in_r(lo0_r), .in_d(lo0_d), .out_v(wlo_v), .out_r(wlo_r), .out_d(wlo_d));
    ot_s81ph_relay2 #(.W(553)) u_li0 (.clk(clk), .rst_n(rst_n), .in_v(wli_v), .in_r(wli_r), .in_d(wli_d), .out_v(li0_v), .out_r(li0_r), .out_d(li0_d));
`ifdef OT_S81PH_MUT_SPLIT_LO4FLIP
    // negative control: the lane 4 outbound relay flips data bit 0 (a corrupted relay)
    ot_s81ph_relay2 #(.W(553)) u_lo4 (.clk(clk), .rst_n(rst_n), .in_v(lo4_v), .in_r(lo4_r), .in_d(lo4_d ^ 553'd1), .out_v(elo_v), .out_r(elo_r), .out_d(elo_d));
`else
    ot_s81ph_relay2 #(.W(553)) u_lo4 (.clk(clk), .rst_n(rst_n), .in_v(lo4_v), .in_r(lo4_r), .in_d(lo4_d), .out_v(elo_v), .out_r(elo_r), .out_d(elo_d));
`endif
    ot_s81ph_relay2 #(.W(553)) u_li4 (.clk(clk), .rst_n(rst_n), .in_v(eli_v), .in_r(eli_r), .in_d(eli_d), .out_v(li4_v), .out_r(li4_r), .out_d(li4_d));
    end endgenerate
    // packer word: seam pin register, then the output queue (sliced, push replicated per slice; OD 16 = the local
    // queue's 4 + the credit loop: push issue -> ce reg -> pin reg -> queue -> pop -> bw_cr -> ce cred = 6 edges, + margin)
    reg          bw_vq; reg [2099:1] bw_dq;
    always @(posedge clk or negedge rst_n) if (!rst_n) bw_vq <= 1'b0; else bw_vq <= bw_v;
    always @(posedge clk) bw_dq <= bw_d;
    localparam integer OSW = 256, ONS = (2099 + OSW - 1) / OSW;
    (* keep *) reg [ONS-1:0] pq;
    reg [2099:1] wq;
    always @(posedge clk or negedge rst_n) if (!rst_n) pq <= {ONS{1'b0}}; else pq <= {ONS{bw_vq}};
    always @(posedge clk) wq <= bw_dq;
    wire [ONS-1:0] s_hv, s_flt, s_pop; wire [2099:1] oq_hd;
    genvar j;
    generate for (j = 0; j < ONS; j = j + 1) begin : g_s
        localparam integer LO = j * OSW, WS = ((2099 - LO) < OSW) ? (2099 - LO) : OSW;
        if (TREP != 0) begin : g_rep
            (* keep *) reg tk;                        // this slice's copy of the registered take strobe
            always @(posedge clk or negedge rst_n) if (!rst_n) tk <= 1'b0; else tk <= ts_r[0];
`ifdef OT_S81PH_MUT_TREP
            wire sp = s_hv[j] && (j == 1 ? ts_r[0] : tk);    // mutant: slice 1 pops one cycle early
`else
            wire sp = s_hv[j] && tk;                         // identical replicas: every slice pops on the same edge
`endif
            ot_s81ph_rfifo #(.W(WS), .D(OD)) u_oq (.clk(clk), .rst_n(rst_n), .push(pq[j]), .wd(wq[1 + LO +: WS]),
                .pop(sp), .hv(s_hv[j]), .hd(oq_hd[1 + LO +: WS]), .room(), .room2(), .fault(s_flt[j]));
            always @(posedge clk or negedge rst_n)
                if (!rst_n) t_vm[1 + LO +: WS] <= {WS{1'b0}};
                else t_vm[1 + LO +: WS] <= sp ? oq_hd[1 + LO +: WS] : {WS{1'b0}};
            assign s_pop[j] = sp;
        end else begin : g_one
            ot_s81ph_rfifo #(.W(WS), .D(OD)) u_oq (.clk(clk), .rst_n(rst_n), .push(pq[j]), .wd(wq[1 + LO +: WS]),
                .pop(s_hv[0] && ts_r[0]), .hv(s_hv[j]), .hd(oq_hd[1 + LO +: WS]), .room(), .room2(), .fault(s_flt[j]));
            assign s_pop[j] = s_hv[0] && ts_r[0];
        end
    end endgenerate
    wire pop = s_pop[0];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin bw_cr <= 1'b0; bw_flt <= 1'b0; end
        else begin
            bw_cr <= pop;
            if (|s_flt) bw_flt <= 1'b1;
        end
    generate if (TREP != 0) begin : g_tv0
        always @(posedge clk or negedge rst_n) if (!rst_n) t_vm[0] <= 1'b0; else t_vm[0] <= pop;
    end else begin : g_tvall
        always @(posedge clk or negedge rst_n)
            if (!rst_n) t_vm <= 0;
            else t_vm <= pop ? {oq_hd, 1'b1} : 2100'd0;
    end endgenerate
    wire unused_ok = &{1'b0, ts_r[2:1]};
endmodule

// ---- middle tile: the collective core (engine, input queues, packer) + lanes 1, 2 (W) / 5, 6 (E)
module dsfd_coll_ce #(
`ifdef OT_S81PH_COLL_QPIPE
    parameter integer QPIPE = 1,
`else
    parameter integer QPIPE = 0,
`endif
    parameter integer OD = 16,
    parameter integer CR = 0,  // redesign-ds: 1 = every lane / seam face is a credit link (lane tile LCR, cb / ct CR)
    parameter integer PULL = `ifdef OT_S81PH_COLL_PULL 1 `else 0 `endif,  // ds-1010: engine FIFO -> central landing queues
    // fe-push-ds-1010 2026-10-10 (hardcore-1010 CE fallback, both default 0 = the PULL line unchanged):
    //  RSTR  : ot_rst_relay (2 sync + 1 kept relay stage, 10 regions) replaces the single synced rst_s[1] flop that cleared
    //          the 680 um tile: region l = lane l's face credit tx/rx, 8 = core, 9 = the tile's own face registers.
    //          Release +1 cycle (3 edges); assert stays asynchronous.
    //  PCOPY : engine per-source (* keep *) pop copies (ot_w15 PCOPY): each source's landing queues, head mux and s0
    //          load enables follow a local pop_k[r] instead of one pop / ppar net across the tile.  0 cycles.
    parameter integer RSTR = `ifdef OT_S81PH_COLL_RSTR 1 `else 0 `endif,
    parameter integer PCOPY = `ifdef OT_S81PH_COLL_PCOPY 1 `else 0 `endif
) (
    input  wire [0:0]       ck,
    input  wire [0:0]       rs,
    // W face: lanes 1, 2;  E face: lanes 5, 6  (index 0 = the lower lane)
    output wire [1:0]       wlo_v,  input  wire [1:0] wlo_r, output wire [2*553-1:0] wlo_d,
    input  wire [1:0]       wli_v,  output wire [1:0] wli_r, input  wire [2*553-1:0] wli_d,
    input  wire [5:0]       wflt,
    output wire [1:0]       elo_v,  input  wire [1:0] elo_r, output wire [2*553-1:0] elo_d,
    input  wire [1:0]       eli_v,  output wire [1:0] eli_r, input  wire [2*553-1:0] eli_d,
    input  wire [5:0]       eflt,
    // S face: seam to dsfd_coll_cb
    input  wire [591:0]     fvm_u,
    input  wire [5:0]       flt_u,
    output wire [0:0] lo0_v,  input wire [0:0] lo0_r, output wire [552:0] lo0_d,
    input wire [0:0] li0_v,  output wire [0:0] li0_r, input  wire [552:0] li0_d,
    output wire [0:0] lo4_v,  input wire [0:0] lo4_r, output wire [552:0] lo4_d,
    input wire [0:0] li4_v,  output wire [0:0] li4_r, input  wire [552:0] li4_d,
    output reg [0:0] bw_v,
    output reg  [2099:1]    bw_d,
    input wire [0:0] bw_cr,
    input wire [0:0] bw_flt,
    // N face: seam to dsfd_coll_ct
    output wire [0:0] lo3_v,  input wire [0:0] lo3_r, output wire [552:0] lo3_d,
    input wire [0:0] li3_v,  output wire [0:0] li3_r, input  wire [552:0] li3_d,
    output wire [0:0] lo7_v,  input wire [0:0] lo7_r, output wire [552:0] lo7_d,
    input wire [0:0] li7_v,  output wire [0:0] li7_r, input  wire [552:0] li7_d,
    input  wire [5:0]       flt_d          // {lane 7 flt, lane 3 flt}
);
    wire clk = ck[0];
    wire rst_n;                       // tile face registers (region 9)
    wire [7:0] rst_ln;                // lane l face credit tx / rx (region l)
    wire rst_cn;                      // collective core (region 8)
    generate if (RSTR != 0) begin : g_rstr
        wire [9:0] rr;
        ot_rst_relay #(.REGIONS(10), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rstr (.clk(clk), .rst_n_in(rs[0]), .rst_n(rr));
`ifdef OT_S81PH_MUT_RSTR
        // bench mutant: lane 1's face region (engine port 2's lane, traffic-bearing in the TP4 bench) re-asserts from
        // 1,200 cycles after release on (mid-traffic; first send ~1,111) and stays in reset: proves lane 1's credit tx / rx
        // hang off their own region copy.  (Lane 5 carries no bench traffic, and a one-cycle release delay leaves the
        // link in its reset state: both PASS, dropped.)
        reg [11:0] mc; always @(posedge clk or negedge rr[9]) if (!rr[9]) mc <= 0; else if (mc != 12'hfff) mc <= mc + 1'b1;
        assign rst_ln = {rr[7:2], rr[1] && (mc < 12'd1200), rr[0]};
`else
        assign rst_ln = rr[7:0];
`endif
        assign rst_cn = rr[8]; assign rst_n = rr[9];
    end else begin : g_rst1
    reg [1:0] rst_s;
    always @(posedge clk or negedge rs[0]) if (!rs[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    assign rst_n = rst_s[1]; assign rst_ln = {8{rst_s[1]}}; assign rst_cn = rst_s[1];
    end endgenerate
    reg [591:0] fv_r; reg [23:0] flt_r; reg bw_crq, bw_fltq;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fv_r <= 0; flt_r <= 0; bw_crq <= 1'b0; bw_fltq <= 1'b0; end
        else begin
            fv_r <= fvm_u; bw_crq <= bw_cr; bw_fltq <= bw_flt;
            // lane order 0..7 (3 bits each): 0 / 4 from the S seam, 1 / 2 / 5 / 6 local, 3 / 7 from the N seam
            flt_r <= {flt_d[5:3], eflt[5:3], eflt[2:0], flt_u[5:3], flt_d[2:0], wflt[5:3], wflt[2:0], flt_u[2:0]};
        end
    // core <-> the 8 lane streams, each through one skid at this tile's face
    wire [7:0] x_lo_v, x_lo_r, x_lo_l, x_li_v, x_li_r, x_li_l;
    wire [8*552-1:0] x_lo_d, x_li_d;
    // face-side stream ends, per lane (lo: out of the tile; li: into the tile)
    wire [7:0] f_lo_v, f_lo_r, f_li_v, f_li_r;
    wire [552:0] f_lo_d [0:7];
    wire [552:0] f_li_d [0:7];
    assign lo0_v = f_lo_v[0]; assign f_lo_r[0] = lo0_r; assign lo0_d = f_lo_d[0];
    assign f_li_v[0] = li0_v; assign li0_r = f_li_r[0]; assign f_li_d[0] = li0_d;
    assign lo4_v = f_lo_v[4]; assign f_lo_r[4] = lo4_r; assign lo4_d = f_lo_d[4];
    assign f_li_v[4] = li4_v; assign li4_r = f_li_r[4]; assign f_li_d[4] = li4_d;
    assign lo3_v = f_lo_v[3]; assign f_lo_r[3] = lo3_r; assign lo3_d = f_lo_d[3];
    assign f_li_v[3] = li3_v; assign li3_r = f_li_r[3]; assign f_li_d[3] = li3_d;
    assign lo7_v = f_lo_v[7]; assign f_lo_r[7] = lo7_r; assign lo7_d = f_lo_d[7];
    assign f_li_v[7] = li7_v; assign li7_r = f_li_r[7]; assign f_li_d[7] = li7_d;
    genvar l;
    generate for (l = 0; l < 2; l = l + 1) begin : g_loc
        assign wlo_v[l] = f_lo_v[1 + l]; assign f_lo_r[1 + l] = wlo_r[l]; assign wlo_d[l*553 +: 553] = f_lo_d[1 + l];
        assign f_li_v[1 + l] = wli_v[l]; assign wli_r[l] = f_li_r[1 + l]; assign f_li_d[1 + l] = wli_d[l*553 +: 553];
        assign elo_v[l] = f_lo_v[5 + l]; assign f_lo_r[5 + l] = elo_r[l]; assign elo_d[l*553 +: 553] = f_lo_d[5 + l];
        assign f_li_v[5 + l] = eli_v[l]; assign eli_r[l] = f_li_r[5 + l]; assign f_li_d[5 + l] = eli_d[l*553 +: 553];
    end endgenerate
    generate for (l = 0; l < 8; l = l + 1) begin : g_l
      if (CR != 0) begin : g_cr
        wire f;
        ot_link_credit_tx #(.W(553), .CRED(8)) u_so (.clk(clk), .rst_n(rst_ln[l]), .i_valid(x_lo_v[l]), .i_ready(x_lo_r[l]),
            .i_data({x_lo_l[l], x_lo_d[l*552 +: 552]}), .l_valid(f_lo_v[l]), .l_data(f_lo_d[l]), .l_credit(f_lo_r[l]));
        ot_link_credit_rx #(.W(553), .DEPTH(8), .OREG(0), .WFREE(1)) u_si (.clk(clk), .rst_n(rst_ln[l]), .l_valid(f_li_v[l]), .l_data(f_li_d[l]),
            .l_credit(f_li_r[l]), .o_valid(x_li_v[l]), .o_ready(x_li_r[l]), .o_data({x_li_l[l], x_li_d[l*552 +: 552]}), .fault(f));
      end else begin : g_sk
        ot_s81ph_skid2 #(.W(553)) u_so (.clk(clk), .rst_n(rst_ln[l]), .in_v(x_lo_v[l]), .in_r(x_lo_r[l]),
            .in_d({x_lo_l[l], x_lo_d[l*552 +: 552]}), .out_v(f_lo_v[l]), .out_r(f_lo_r[l]), .out_d(f_lo_d[l]));
        ot_s81ph_skid2 #(.W(553)) u_si (.clk(clk), .rst_n(rst_ln[l]), .in_v(f_li_v[l]), .in_r(f_li_r[l]), .in_d(f_li_d[l]),
            .out_v(x_li_v[l]), .out_r(x_li_r[l]), .out_d({x_li_l[l], x_li_d[l*552 +: 552]}));
      end
    end endgenerate
    wire c_bw_v; wire [2099:1] c_bw_d;
    ot_s81ph_coll_core #(.EXT(1), .OQPIPE(1), .QPIPE(QPIPE), .OQX(1), .OQX_D(OD), .EPULL(PULL), .EPCOPY(PCOPY)) u_core (.clk(clk), .rst_n(rst_cn),
        .lane_rx({8*515{1'b0}}), .lane_tx(), .f_vm(fv_r), .ts(3'd0), .t_vm(), .fault(), .rank(), .eng_en(),
        .x_lo_v(x_lo_v), .x_lo_r(x_lo_r), .x_lo_d(x_lo_d), .x_lo_l(x_lo_l),
        .x_li_v(x_li_v), .x_li_r(x_li_r), .x_li_d(x_li_d), .x_li_l(x_li_l), .x_lflt(flt_r),
        .bw_v(c_bw_v), .bw_d(c_bw_d), .bw_cr(bw_crq), .bw_flt(bw_fltq));
    // packer word: one more register at the S face pins
    always @(posedge clk or negedge rst_n) if (!rst_n) bw_v <= 1'b0; else bw_v <= c_bw_v;
    always @(posedge clk) bw_d <= c_bw_d;
endmodule

// ---- lane-facing SENDER with a registered lane ready (redesign-ds 2026-10-10, ct-split3b): the lane tile's core-face
// receiver is an unchanged ot_s81ph_skid2 (lo_r = !sk_v).  ct-split3a lost -168 / -233 to lo_r (pin) -> the relay skid's
// 553-bit load enables.  Here the pin feeds ONE gate into the valid flop: a beat is presented for exactly one cycle, and
// only when the lane's ready was high in the previous cycle with no beat presented then, which proves the lane's skid
// slot is empty, so the beat is always taken (no duplicate, no loss).  out_d is the holding flop h_d, loaded only from
// local flops.  Rate: one beat every 2 cycles on this seam (the lane skid cannot report its drain without a lane change).
module ot_s81ph_send_lr #(parameter integer W = 8) (
    input  wire clk, input wire rst_n,
    input  wire in_v, output wire in_r, input wire [W-1:0] in_d,
    output reg  out_v, input wire out_r, output wire [W-1:0] out_d
);
    reg h_v; reg [W-1:0] h_d;
    assign in_r = !h_v || out_v;            // free, or the held beat is being taken this cycle
    assign out_d = h_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin out_v <= 1'b0; h_v <= 1'b0; end
        else begin
`ifdef OT_S81PH_MUT_SPLIT_SENDLR
            out_v <= out_r && h_v && !out_v || (out_v && h_v && in_v);   // mutant: back-to-back presentation (duplicates)
`else
            out_v <= out_r && !out_v && h_v;
`endif
            if (out_v) h_v <= in_v; else if (!h_v) h_v <= in_v;
        end
    always @(posedge clk) if (in_v && (!h_v || out_v)) h_d <= in_d;
endmodule

// ---- lane-facing RECEIVER with a landing register (redesign-ds 2026-10-10, ct-split3b): the lane's in_v / in_d pins land
// in plain flops (no enable, one load each); a 4-deep FIFO behind them absorbs the beats in flight while the registered
// ready (count <= 1) is seen late.  Full rate, +1 cycle.
module ot_s81ph_land_rx #(parameter integer W = 8) (
    input  wire clk, input wire rst_n,
    input  wire in_v, output reg in_r, input wire [W-1:0] in_d,
    output wire out_v, input wire out_r, output wire [W-1:0] out_d
);
    reg l_v; reg [W-1:0] l_d;
    reg [W-1:0] m [0:3]; reg [1:0] wp, rp; reg [2:0] n;
    wire pop = out_v && out_r;
    wire [2:0] n_n = n + (l_v ? 3'd1 : 3'd0) - (pop ? 3'd1 : 3'd0);
    assign out_v = n != 0;
    assign out_d = m[rp];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin l_v <= 1'b0; in_r <= 1'b0; wp <= 0; rp <= 0; n <= 0; end
        else begin
            l_v <= in_v && in_r;
            if (l_v) wp <= wp + 1'b1;
            if (pop) rp <= rp + 1'b1;
            n <= n_n;
            in_r <= n_n <= 3'd1;
        end
    always @(posedge clk) begin
        l_d <= in_d;
        if (l_v) m[wp] <= l_d;
    end
endmodule

// ---- top tile: lanes 3 / 7 relays
module dsfd_coll_ct #(
    // LR (redesign-ds 2026-10-10, ct-split3b): 1 = the lane-facing ends are ot_s81ph_send_lr (registered lane ready, one beat
    // every 2 cycles toward the lane) and ot_s81ph_land_rx (landing register + FIFO from the lane, full rate), so no lane
    // pin drives a 553-bit enable; 0 = the 2-skid relays of ct-split3a.
    parameter integer LR = 0,
    parameter integer CR = 0,  // redesign-ds: 1 = credit relays on both faces (needs the lane tile LCR and ce CR)
    // PS (fill-9 2026-10-10, CR mode only): pin stations on every relay pin (ot_s81ph_cr_relay PS), +1 cycle each way
    parameter integer PS = `ifdef OT_S81PH_COLL_CTPS 1 `else 0 `endif,
    // RSL (hardcore-1010 fe G, opt-in): one-hot pointer slices in every credit relay (ot_s81ph_cr_relay RSL), 0 cycles
    parameter integer RSL = `ifdef OT_S81PH_COLL_RSL 8 `else 0 `endif
) (
    input  wire [0:0]     ck,
    input  wire [0:0]     rs,
    output wire [0:0] wlo_v,  input wire [0:0] wlo_r, output wire [552:0] wlo_d,
    input wire [0:0] wli_v,  output wire [0:0] wli_r, input  wire [552:0] wli_d,
    input  wire [2:0]     wflt,
    output wire [0:0] elo_v,  input wire [0:0] elo_r, output wire [552:0] elo_d,
    input wire [0:0] eli_v,  output wire [0:0] eli_r, input  wire [552:0] eli_d,
    input  wire [2:0]     eflt,
    // S face: seam to dsfd_coll_ce
    input wire [0:0] lo3_v,  output wire [0:0] lo3_r, input  wire [552:0] lo3_d,
    output wire [0:0] li3_v,  input wire [0:0] li3_r, output wire [552:0] li3_d,
    input wire [0:0] lo7_v,  output wire [0:0] lo7_r, input  wire [552:0] lo7_d,
    output wire [0:0] li7_v,  input wire [0:0] li7_r, output wire [552:0] li7_d,
    output reg  [5:0]     flt_d
);
    wire clk = ck[0];
    reg [1:0] rst_s;
    always @(posedge clk or negedge rs[0]) if (!rs[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    reg [5:0] flt_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin flt_r <= 0; flt_d <= 0; end
        else begin flt_r <= {eflt, wflt}; flt_d <= flt_r; end
    generate if (CR != 0) begin : g_cr
        ot_s81ph_cr_relay #(.W(553), .PS(PS), .RSL(RSL)) u_lo3 (.clk(clk), .rst_n(rst_n), .i_v(lo3_v), .i_cr(lo3_r), .i_d(lo3_d), .o_v(wlo_v), .o_cr(wlo_r), .o_d(wlo_d));
        ot_s81ph_cr_relay #(.W(553), .PS(PS), .RSL(RSL)) u_li3 (.clk(clk), .rst_n(rst_n), .i_v(wli_v), .i_cr(wli_r), .i_d(wli_d), .o_v(li3_v), .o_cr(li3_r), .o_d(li3_d));
        ot_s81ph_cr_relay #(.W(553), .PS(PS), .RSL(RSL)) u_lo7 (.clk(clk), .rst_n(rst_n), .i_v(lo7_v), .i_cr(lo7_r), .i_d(lo7_d), .o_v(elo_v), .o_cr(elo_r), .o_d(elo_d));
        ot_s81ph_cr_relay #(.W(553), .PS(PS), .RSL(RSL)) u_li7 (.clk(clk), .rst_n(rst_n), .i_v(eli_v), .i_cr(eli_r), .i_d(eli_d), .o_v(li7_v), .o_cr(li7_r), .o_d(li7_d));
    end else if (LR != 0) begin : g_lr
        // seam-side skid (u_a) + lane-facing sender / receiver
        wire a3v, a3r, a7v, a7r, b3v, b3r, b7v, b7r; wire [552:0] a3d, a7d, b3d, b7d;
        ot_s81ph_skid2 #(.W(553)) u_lo3a (.clk(clk), .rst_n(rst_n), .in_v(lo3_v), .in_r(lo3_r), .in_d(lo3_d), .out_v(a3v), .out_r(a3r), .out_d(a3d));
        ot_s81ph_send_lr #(.W(553)) u_lo3s (.clk(clk), .rst_n(rst_n), .in_v(a3v), .in_r(a3r), .in_d(a3d), .out_v(wlo_v), .out_r(wlo_r), .out_d(wlo_d));
        ot_s81ph_skid2 #(.W(553)) u_lo7a (.clk(clk), .rst_n(rst_n), .in_v(lo7_v), .in_r(lo7_r), .in_d(lo7_d), .out_v(a7v), .out_r(a7r), .out_d(a7d));
        ot_s81ph_send_lr #(.W(553)) u_lo7s (.clk(clk), .rst_n(rst_n), .in_v(a7v), .in_r(a7r), .in_d(a7d), .out_v(elo_v), .out_r(elo_r), .out_d(elo_d));
        ot_s81ph_land_rx #(.W(553)) u_li3l (.clk(clk), .rst_n(rst_n), .in_v(wli_v), .in_r(wli_r), .in_d(wli_d), .out_v(b3v), .out_r(b3r), .out_d(b3d));
        ot_s81ph_skid2 #(.W(553)) u_li3b (.clk(clk), .rst_n(rst_n), .in_v(b3v), .in_r(b3r), .in_d(b3d), .out_v(li3_v), .out_r(li3_r), .out_d(li3_d));
        ot_s81ph_land_rx #(.W(553)) u_li7l (.clk(clk), .rst_n(rst_n), .in_v(eli_v), .in_r(eli_r), .in_d(eli_d), .out_v(b7v), .out_r(b7r), .out_d(b7d));
        ot_s81ph_skid2 #(.W(553)) u_li7b (.clk(clk), .rst_n(rst_n), .in_v(b7v), .in_r(b7r), .in_d(b7d), .out_v(li7_v), .out_r(li7_r), .out_d(li7_d));
    end else begin : g_rl
    ot_s81ph_relay2 #(.W(553)) u_lo3 (.clk(clk), .rst_n(rst_n), .in_v(lo3_v), .in_r(lo3_r), .in_d(lo3_d), .out_v(wlo_v), .out_r(wlo_r), .out_d(wlo_d));
    ot_s81ph_relay2 #(.W(553)) u_li3 (.clk(clk), .rst_n(rst_n), .in_v(wli_v), .in_r(wli_r), .in_d(wli_d), .out_v(li3_v), .out_r(li3_r), .out_d(li3_d));
    ot_s81ph_relay2 #(.W(553)) u_lo7 (.clk(clk), .rst_n(rst_n), .in_v(lo7_v), .in_r(lo7_r), .in_d(lo7_d), .out_v(elo_v), .out_r(elo_r), .out_d(elo_d));
    ot_s81ph_relay2 #(.W(553)) u_li7 (.clk(clk), .rst_n(rst_n), .in_v(eli_v), .in_r(eli_r), .in_d(eli_d), .out_v(li7_v), .out_r(li7_r), .out_d(li7_d));
    end endgenerate
endmodule
