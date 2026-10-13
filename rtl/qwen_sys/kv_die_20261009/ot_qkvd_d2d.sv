`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// kv-die 2026-10-09 (OWNER DECISION ~04:00 PT, option 1a): one die's end of the ROM die <-> KV die link.  Our logic
// between the die buses and the UCIe PHY + D2D adapter hard macro (ot_qkvd_ucie_x64_phy: licensed IP, FDI side only;
// the UCIe D2D adapter inside the macro owns CRC / retry per the UCIe spec, so a flit that reaches this block is good
// or the macro has failed -- the sequence check below catches a lost / repeated flit and fails closed).
// Contract: results/arch/qwen_kv_die_20261009/CONTRACT.md (classes, word formats, credits, latency).
//
//   die TX face   per class i < NT: t_v / t_d captured at the pin flops (no logic before them), an IBD[i]-word buffer,
//                 t_cr = one registered credit pulse per word that leaves it (the die-bus sender starts with IBD[i]).
//   link TX       one flit a 1.2 GHz FDI cycle while the macro reports tx_up (idle flits carry credits only):
//                 {seq 8, credit return 4 x 2 b, dv, class 3, word W}.  A word is sent only with a link credit for its
//                 class in hand (FCR[i] = the far receive buffer); round-robin over the classes that have both.
//   link RX       the FDI flit is captured at the macro pins; sequence checked; credit fields add to the TX link
//                 credits; a word goes to its class's RBD[j]-word receive buffer (class - RXB = j).
//   die RX face   r_v / r_d launched from flops, one word per die credit (OCR[j] initial, r_cr returns one, captured at
//                 the pin).  A receive-buffer word's link credit is owed back to the far side when it leaves the buffer.
//   faults        sticky, registered: die-face overrun, receive-buffer overrun, sequence error, credit overflow,
//                 class out of range.
// Order and values are preserved exactly per class; latency is not cycle-fixed (credit flow control end to end).
// Same 1.2 GHz clock on both dies (KV-die PLL, forwarded): the FDI runs on the local core clock; the macro retimes.
// MUT (bench only): 1 = one extra link credit on TX class 0 (overruns the far buffer under back-pressure),
//                   2 = link credit owed at receive-buffer PUSH instead of pop (early credit).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_d2d #(
    parameter integer NT  = 4,                      // TX classes (this die -> far die)
    parameter integer NR  = 3,                      // RX classes (far die -> this die)
    parameter integer TXB = 0,                      // class number of TX class 0
    parameter integer RXB = 4,                      // class number of RX class 0
    parameter integer W   = 528,                    // die word: {tag 16, data 512}
    parameter [31:0]  IBD = {8'd8, 8'd8, 8'd8, 8'd8},   // die-face TX buffer per TX class (byte i = class i)
    parameter [31:0]  FCR = {8'd8, 8'd8, 8'd8, 8'd8},   // far receive buffer per TX class (initial link credits)
    parameter [31:0]  RBD = {8'd8, 8'd8, 8'd8, 8'd8},   // receive buffer per RX class
    parameter [31:0]  OCR = {8'd8, 8'd8, 8'd8, 8'd8},   // die-face RX credits per RX class
    parameter integer MUT = 0,
    // SBD (el1011-q-kvd 2026-10-11; 0 = unchanged): buffers of depth >= SBD use ot_qkvd_fifo_sb (64 x 512 SRAM body +
    // registered head) instead of the flop array whose binary pointers fanned out to every bit (qkd_d2d_b TT -46.65)
    parameter integer SBD = 0,
    // HT (el1011-q-kvd 2026-10-11; 0 = unchanged): every link buffer is a hardened tile (ot_qkvd_buf_tiles.sv: depth > 8
    // -> ot_qkvd_sbuf (SRAM), else ot_qkvd_fbuf8), own clock tree / reset relay / pin flops; occupancy kept here (W 528)
    parameter integer HT  = 0,
    // ORL (el1011-q-kvd 2026-10-12; 0 = unchanged): one relay register on each output datapath -- tx_v/tx_flit (TX
    // link) and r_v/r_d (die RX face) -- so the link buffers sit next to their INPUT face (rx_flit -> RX buffer din,
    // t_d -> TX buffer din: the hard-child din side is the short-budget side) and the far face is reached in two
    // <= 500 um stages (route qkd_d2d_ref-q5b: rq_f -> sbuf din 814 ps of wire).  +1 cycle on each direction; order,
    // values and credits unchanged (r_d = the ORL=0 r_d one cycle later; credit flow is latency-insensitive)
    parameter integer ORL = 0,
    // IRL (el1011-q-kvd 2026-10-12; 0 = unchanged): one relay register on each input datapath between the pin flop and
    // the link buffers, REPLICATED per buffer on RX (rx_word is broadcast to all NR buffers: one kept copy sits next to
    // each buffer's din, the parent -> parent hop takes the wire).  +1 cycle per direction, behaviour = inputs delayed
    parameter integer IRL = 0,
    // PQ (el1011-q-kvd 2026-10-12; 0 = unchanged; needs HT): every hard-buffer POP pin is driven straight from a kept flop
    // (placed at the macro pin), decided ONE CYCLE AHEAD from registered state only.  The hardened buffers' empty is a
    // macro output (~500 ps clk->Q incl. folded insertion) and their pop is a ~660 ps internal cone, so the same-cycle
    // empty -> arbitration -> pop loop could not close (route qkd_d2d_ref-q8-aeca40e24: up_q -> 647 ps TX arbitration ->
    // g_tx[0] sbuf pop, TT -611).  Each buffer gets a parent-side SHADOW of its control (ot_qkvd_sbuf_shadow /
    // ot_qkvd_fbuf8_shadow: exact mirror of the tile's push / pop occupancy pipeline, same reset release), which says
    // whether the buffer still holds a word after this cycle's pop; the arbiter grants from that, the grant is
    // registered and is the next cycle's pop.  Full rate per class is kept (back-to-back pops of one buffer).  TX: the
    // link slot of a decided grant is the next cycle (tx_up one more cycle of latency); RX: r_v / r_d one cycle later.
    // Order, values and credits unchanged; simulation checks every cycle that each shadow's empty equals the tile's.
    // PQ = 2 (q13b-kvend 2026-10-13): the buffers are the pin-registered tiles ot_qkvd_sbufp / ot_qkvd_fbuf8p, whose pop
    // is registered inside (acts one cycle after the pin).  The pop pin flop is unchanged (D = this cycle's decision);
    // the word leaves its buffer TWO cycles after the decision (gq2 / up3 / rq2), and a decision counts the pop still in
    // flight (shadow ne_next = occupancy after the effective pop AND the one at the pin).  Full rate kept; +1 cycle.
    parameter integer PQ  = 0,
    // PF (q13-kvh 2026-10-13; 0 = unchanged; needs HT and IRL): every hard-buffer PUSH pin is driven straight from its own
    // kept flop beside the macro pin (ot_qkvd_pop_ff, as the PQ pop pins).  The flop's D is the SAME decode taken one
    // relay stage earlier (RX: rq_v / rq_f header instead of rq2_v / rq2_h; TX: ci_v instead of ci2_v), so it carries the
    // same value on the same cycle as rb_push / ce_v: no latency, order or credit change (simulation checks equality every
    // cycle).  Why: q10 4_cts (SS): rq2_v -> 5 levels of class decode -> 155 ps unbuffered wire (slew 492) -> u_rb/push
    // (lib setup 137 ps) = -262; the decode now sits before a flop and the pin sees only clk->Q + a local wire.
    parameter integer PF  = 0,
    parameter integer FW  = 8 + 8 + 1 + 3 + W
) (
    input  wire            clk,
    input  wire            rst_n,
    // die TX face
    input  wire [NT-1:0]   t_v,
    input  wire [NT*W-1:0] t_d,
    output reg  [NT-1:0]   t_cr,
    // die RX face
    output reg  [NR-1:0]   r_v,
    output reg  [NR*W-1:0] r_d,
    input  wire [NR-1:0]   r_cr,
    // PHY FDI (hard macro)
    input  wire            tx_up,
    output reg             tx_v,
    output reg  [FW-1:0]   tx_flit,
    input  wire            rx_v,
    input  wire [FW-1:0]   rx_flit,
    output reg             fault,
    output reg  [4:0]      fault_cause
);
    localparam integer PQE = (PQ != 0 && HT != 0) ? 1 : 0;
    localparam integer PQ2 = (PQ == 2 && HT != 0) ? 1 : 0;
    localparam integer PFE = (PF != 0 && HT != 0 && IRL != 0) ? 1 : 0;   // PF applies to the hardened buffers behind the IRL relays      // PQ applies to the hardened buffers only
    // ---- reset copy ----
    // el1011-q-kvd 2026-10-11: two kept copies of the same 2-stage synchroniser (identical release cycle): rs for the
    // parent control flops, rs_t for the hardened buffer tiles' rst_n pins (route qkd_d2d_h-305021c34: one rs net drove
    // 747 loads).  tx_flit is no longer reset (datapath; tx_v qualifies it).
    (* keep *) reg rs0, rs;
    (* keep *) reg rs_t0, rs_t;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin rs0 <= 1'b0; rs <= 1'b0; end else begin rs0 <= 1'b1; rs <= rs0; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin rs_t0 <= 1'b0; rs_t <= 1'b0; end else begin rs_t0 <= 1'b1; rs_t <= rs_t0; end
    // ---- pin capture ----
    reg [NT-1:0]   ci_v;
    reg [NT*W-1:0] ci_d;
    reg [NR-1:0]   cr_q;
    reg            up_q;
    always @(posedge clk) ci_d <= t_d;
    always @(posedge clk or negedge rs)
        if (!rs) begin ci_v <= 0; cr_q <= 0; up_q <= 1'b0; end
        else begin ci_v <= t_v; cr_q <= r_cr; up_q <= tx_up; end
    reg          rq_v;
    reg [FW-1:0] rq_f;
    always @(posedge clk) rq_f <= rx_flit;
    always @(posedge clk or negedge rs) if (!rs) rq_v <= 1'b0; else rq_v <= rx_v;
    // IRL input relays: ce_* (TX), re_* (RX header) / re_w (RX word, one copy per receive buffer)
    wire [NT-1:0]   ce_v;
    wire [NT*W-1:0] ce_d;
    wire            re_v;
    wire [FW-1:W]   re_h;
    wire [NR*W-1:0] re_w;
    genvar g;
    generate if (IRL != 0) begin : g_irl
        reg [NT-1:0]   ci2_v;
        reg [NT*W-1:0] ci2_d;
        reg            rq2_v;
        reg [FW-1:W]   rq2_h;
        always @(posedge clk) begin ci2_d <= ci_d; rq2_h <= rq_f[FW-1:W]; end
        always @(posedge clk or negedge rs) if (!rs) begin ci2_v <= 0; rq2_v <= 1'b0; end else begin ci2_v <= ci_v; rq2_v <= rq_v; end
        for (g = 0; g < NR; g = g + 1) begin : g_rw
            (* keep *) reg [W-1:0] rw;                                            // next to receive buffer g's din
            always @(posedge clk) rw <= rq_f[W-1:0];
            assign re_w[W*g +: W] = rw;
        end
        assign ce_v = ci2_v; assign ce_d = ci2_d; assign re_v = rq2_v; assign re_h = rq2_h;
    end else begin : g_idir
        assign ce_v = ci_v; assign ce_d = ci_d; assign re_v = rq_v; assign re_h = rq_f[FW-1:W];
        assign re_w = {NR{rq_f[W-1:0]}};
    end endgenerate
    wire [7:0]   rx_seq_f = re_h[W + 12 +: 8];
    wire [7:0]   rx_crs   = re_h[W + 4 +: 8];
    wire         rx_dv    = re_v && re_h[W + 3];
    wire [2:0]   rx_cls   = re_h[W +: 3];

    reg f_die, f_rb, f_seq, f_cred, f_cls;
    // ---- TX side ----
    wire [NT-1:0]   ib_empty, ib_full;
    wire [NT*W-1:0] ib_head;
    reg  [NT-1:0]   lc_nz;             // a link credit in hand, per TX class
    reg  [7:0]      lcred [0:NT-1];
    reg  [$clog2(NT+1)-1:0] rr;        // round-robin pointer: class searched first
    // grant: first class at or after rr that has a word and a link credit
    reg  [NT-1:0] gnt;
    reg           any;
    wire [NT-1:0] tx_ne;               // class has a word for the slot being decided (PQ: shadow, after this cycle's pop)
    reg  [NT-1:0] gq;                  // PQ: grant decided last cycle = this cycle's pop / flit word
    reg           up2;                 // PQ: up_q one cycle later = the link slot of a grant decided with up_q
    reg  [NT-1:0] gq2;                 // PQ=2: gq one cycle later = the cycle the tile's registered pop acts
    reg           up3;
    wire [NT-1:0] gsel = (PQ2 != 0) ? gq2 : (PQE != 0) ? gq : gnt;   // word that leaves its buffer / goes in this cycle's flit
    wire          anys = |gsel;
    wire          up_s = (PQ2 != 0) ? up3 : (PQE != 0) ? up2 : up_q;  // this cycle's link slot is up
    integer k, c;
    always @* begin
        gnt = 0; any = 1'b0;
        for (k = 0; k < NT; k = k + 1) begin
            c = (rr + k) % NT;
            if (!any && up_q && tx_ne[c] && lc_nz[c]) begin gnt[c] = 1'b1; any = 1'b1; end
        end
    end
    genvar i, j;
    generate for (i = 0; i < NT; i = i + 1) begin : g_tx
        wire [$clog2(IBD[8*i +: 8]+1)-1:0] cnt;
        if (HT != 0) begin : g_ht
            reg [7:0] oc;
            always @(posedge clk or negedge rs) if (!rs) oc <= 8'd0; else oc <= oc + (ce_v[i] ? 8'd1 : 8'd0) - (gsel[i] ? 8'd1 : 8'd0);
            assign ib_full[i] = (oc == IBD[8*i +: 8]);
            assign cnt = oc[$clog2(IBD[8*i +: 8]+1)-1:0];
            wire pop_i, sh_e, sh_ne;
            if (PQE != 0) begin : g_pq
                // pop pin flop, at the macro: its own kept module so opt_merge cannot fold it into gq[i] (same D) and
                // load it with the 528-bit head mux (q9-b: merged flop -> BUF tree, OT_MPFLOP found 0 of 7).
                wire pp;
                ot_qkvd_pop_ff u_pp (.clk(clk), .rst_n(rs), .d(gnt[i]), .q(pp));
                assign pop_i = pp;
                assign tx_ne[i] = sh_ne;
            end else begin : g_npq
                assign pop_i = gnt[i];
                assign sh_e = 1'b0; assign sh_ne = 1'b0;
                assign tx_ne[i] = !ib_empty[i];
            end
            wire psh_i;
            if (PFE != 0) begin : g_pf
                wire pf;                                                              // push pin flop (same cycle as ce_v[i] = ci2_v[i])
                ot_qkvd_pop_ff u_pf (.clk(clk), .rst_n(rs), .d(ci_v[i]), .q(pf));
                assign psh_i = pf;
`ifndef SYNTHESIS
                always @(posedge clk) if (rs && pf !== ce_v[i])
                    $display("ERROR ot_qkvd_d2d PF: TX class %0d push flop %b != ce_v %b at %0t", i, pf, ce_v[i], $time);
`endif
            end else begin : g_npf
                assign psh_i = ce_v[i];
            end
            if (IBD[8*i +: 8] > 8) begin : g_s
                if (PQ2 != 0) begin : g_p
                    ot_qkvd_sbufp u_ib (.clk(clk), .rst_n(rs_t), .push(psh_i), .din(ce_d[W*i +: W]), .pop(pop_i),
                        .dout(ib_head[W*i +: W]), .empty(ib_empty[i]));
                end else begin : g_np
                    ot_qkvd_sbuf u_ib (.clk(clk), .rst_n(rs_t), .push(psh_i), .din(ce_d[W*i +: W]), .pop(pop_i),
                        .dout(ib_head[W*i +: W]), .empty(ib_empty[i]));
                end
                if (PQE != 0) begin : g_sh
                    ot_qkvd_sbuf_shadow #(.PIQ(PQ2)) u_sh (.clk(clk), .rst_n(rs_t), .push(ce_v[i]), .pop(gq[i]), .empty(sh_e), .ne_next(sh_ne));
                end
            end else begin : g_f
                if (PQ2 != 0) begin : g_p
                    ot_qkvd_fbuf8p u_ib (.clk(clk), .rst_n(rs_t), .push(psh_i), .din(ce_d[W*i +: W]), .pop(pop_i),
                        .dout(ib_head[W*i +: W]), .empty(ib_empty[i]));
                end else begin : g_np
                    ot_qkvd_fbuf8 u_ib (.clk(clk), .rst_n(rs_t), .push(psh_i), .din(ce_d[W*i +: W]), .pop(pop_i),
                        .dout(ib_head[W*i +: W]), .empty(ib_empty[i]));
                end
                if (PQE != 0) begin : g_sh
                    ot_qkvd_fbuf8_shadow #(.PIQ(PQ2)) u_sh (.clk(clk), .rst_n(rs_t), .push(ce_v[i]), .pop(gq[i]), .empty(sh_e), .ne_next(sh_ne));
                end
            end
`ifndef SYNTHESIS
            if (PQE != 0) begin : g_chk
                always @(posedge clk) if (rs && sh_e !== ib_empty[i]) begin
                    $display("ERROR ot_qkvd_d2d PQ: TX class %0d shadow empty %b != buffer empty %b at %0t", i, sh_e, ib_empty[i], $time);
                    $fatal(1);
                end
            end
`endif
        end else if (SBD != 0 && IBD[8*i +: 8] >= SBD) begin : g_sb
        assign tx_ne[i] = !ib_empty[i];
        ot_qkvd_fifo_sb #(.W(W), .D(IBD[8*i +: 8])) u_ib (.clk(clk), .rst_n(rs), .push(ce_v[i]), .din(ce_d[W*i +: W]),
            .pop(gnt[i]), .dout(ib_head[W*i +: W]), .empty(ib_empty[i]), .full(ib_full[i]), .count(cnt));
        end else begin : g_ff
        assign tx_ne[i] = !ib_empty[i];
        ot_qkvd_fifo #(.RH(1), .W(W), .D(IBD[8*i +: 8])) u_ib (.clk(clk), .rst_n(rs), .push(ce_v[i]), .din(ce_d[W*i +: W]),
            .pop(gnt[i]), .dout(ib_head[W*i +: W]), .empty(ib_empty[i]), .full(ib_full[i]), .count(cnt));
        end
    end endgenerate
    reg [W-1:0] sel_word;
    reg [2:0]   sel_cls;
    always @* begin
        sel_word = {W{1'b0}}; sel_cls = 3'd0;
        for (k = 0; k < NT; k = k + 1) if (gsel[k]) begin sel_word = ib_head[W*k +: W]; sel_cls = 3'(TXB + k); end
    end
    // ---- RX side ----
    wire [NR-1:0]   rb_empty, rb_full;
    wire [NR*W-1:0] rb_head;
    reg  [7:0]      ocred [0:NR-1];
    reg  [7:0]      owed  [0:NR-1];
    wire [NR-1:0]   rb_push, rb_pop;
    wire [NR-1:0]   rx_ne;             // receive buffer has a word for the pop being decided (PQ: shadow)
    wire [NR-1:0]   rdec;              // pop decided this cycle (consumes a die-face credit)
    reg  [NR-1:0]   rq2;               // PQ=2: rq_q one cycle later
    reg  [NR-1:0]   rq_q;              // PQ: pop decided last cycle = this cycle's pop
    generate for (j = 0; j < NR; j = j + 1) begin : g_rx
        wire [$clog2(RBD[8*j +: 8]+1)-1:0] cnt;
        assign rb_push[j] = rx_dv && (rx_cls == 3'(RXB + j));
        assign rdec[j]    = rx_ne[j] && (ocred[j] != 0);
        assign rb_pop[j]  = (PQ2 != 0) ? rq2[j] : (PQE != 0) ? rq_q[j] : rdec[j];
        if (HT != 0) begin : g_ht
            reg [7:0] oc;
            always @(posedge clk or negedge rs) if (!rs) oc <= 8'd0; else oc <= oc + (rb_push[j] ? 8'd1 : 8'd0) - (rb_pop[j] ? 8'd1 : 8'd0);
            assign rb_full[j] = (oc == RBD[8*j +: 8]);
            assign cnt = oc[$clog2(RBD[8*j +: 8]+1)-1:0];
            wire pop_j, sh_e, sh_ne;
            if (PQE != 0) begin : g_pq
                wire pp;                                                              // pop pin flop (see g_tx)
                ot_qkvd_pop_ff u_pp (.clk(clk), .rst_n(rs), .d(rdec[j]), .q(pp));
                assign pop_j = pp;
                assign rx_ne[j] = sh_ne;
            end else begin : g_npq
                assign pop_j = rb_pop[j];
                assign sh_e = 1'b0; assign sh_ne = 1'b0;
                assign rx_ne[j] = !rb_empty[j];
            end
            wire psh_j;
            if (PFE != 0) begin : g_pf
                wire pf;                                                              // push pin flop (same cycle as rb_push[j])
                ot_qkvd_pop_ff u_pf (.clk(clk), .rst_n(rs),
                                     .d(rq_v && rq_f[W + 3] && (rq_f[W +: 3] == 3'(RXB + j))), .q(pf));
                assign psh_j = pf;
`ifndef SYNTHESIS
                always @(posedge clk) if (rs && pf !== rb_push[j])
                    $display("ERROR ot_qkvd_d2d PF: RX class %0d push flop %b != rb_push %b at %0t", j, pf, rb_push[j], $time);
`endif
            end else begin : g_npf
                assign psh_j = rb_push[j];
            end
            if (RBD[8*j +: 8] > 8) begin : g_s
                if (PQ2 != 0) begin : g_p
                    ot_qkvd_sbufp u_rb (.clk(clk), .rst_n(rs_t), .push(psh_j), .din(re_w[W*j +: W]), .pop(pop_j),
                        .dout(rb_head[W*j +: W]), .empty(rb_empty[j]));
                end else begin : g_np
                    ot_qkvd_sbuf u_rb (.clk(clk), .rst_n(rs_t), .push(psh_j), .din(re_w[W*j +: W]), .pop(pop_j),
                        .dout(rb_head[W*j +: W]), .empty(rb_empty[j]));
                end
                if (PQE != 0) begin : g_sh
                    ot_qkvd_sbuf_shadow #(.PIQ(PQ2)) u_sh (.clk(clk), .rst_n(rs_t), .push(rb_push[j]), .pop(rq_q[j]), .empty(sh_e), .ne_next(sh_ne));
                end
            end else begin : g_f
                if (PQ2 != 0) begin : g_p
                    ot_qkvd_fbuf8p u_rb (.clk(clk), .rst_n(rs_t), .push(psh_j), .din(re_w[W*j +: W]), .pop(pop_j),
                        .dout(rb_head[W*j +: W]), .empty(rb_empty[j]));
                end else begin : g_np
                    ot_qkvd_fbuf8 u_rb (.clk(clk), .rst_n(rs_t), .push(psh_j), .din(re_w[W*j +: W]), .pop(pop_j),
                        .dout(rb_head[W*j +: W]), .empty(rb_empty[j]));
                end
                if (PQE != 0) begin : g_sh
                    ot_qkvd_fbuf8_shadow #(.PIQ(PQ2)) u_sh (.clk(clk), .rst_n(rs_t), .push(rb_push[j]), .pop(rq_q[j]), .empty(sh_e), .ne_next(sh_ne));
                end
            end
`ifndef SYNTHESIS
            if (PQE != 0) begin : g_chk
                always @(posedge clk) if (rs && sh_e !== rb_empty[j]) begin
                    $display("ERROR ot_qkvd_d2d PQ: RX class %0d shadow empty %b != buffer empty %b at %0t", j, sh_e, rb_empty[j], $time);
                    $fatal(1);
                end
            end
`endif
        end else if (SBD != 0 && RBD[8*j +: 8] >= SBD) begin : g_sb
        assign rx_ne[j] = !rb_empty[j];
        ot_qkvd_fifo_sb #(.W(W), .D(RBD[8*j +: 8])) u_rb (.clk(clk), .rst_n(rs), .push(rb_push[j]), .din(re_w[W*j +: W]),
            .pop(rb_pop[j]), .dout(rb_head[W*j +: W]), .empty(rb_empty[j]), .full(rb_full[j]), .count(cnt));
        end else begin : g_ff
        assign rx_ne[j] = !rb_empty[j];
        ot_qkvd_fifo #(.RH(1), .W(W), .D(RBD[8*j +: 8])) u_rb (.clk(clk), .rst_n(rs), .push(rb_push[j]), .din(re_w[W*j +: W]),
            .pop(rb_pop[j]), .dout(rb_head[W*j +: W]), .empty(rb_empty[j]), .full(rb_full[j]), .count(cnt));
        end
    end endgenerate
    // credit return fields (2 b each, 4 fields; field j = this die's RX class j)
    reg [7:0] cr_ret;
    reg [1:0] ret [0:3];
    always @* begin
        cr_ret = 8'd0;
        for (k = 0; k < 4; k = k + 1) begin
            ret[k] = 2'd0;
            if (k < NR) ret[k] = (owed[k] > 8'd3) ? 2'd3 : owed[k][1:0];
            if (!up_s) ret[k] = 2'd0;
            cr_ret[2*k +: 2] = ret[k];
        end
    end
    reg [7:0] tx_seq, rx_seq;
    reg tv0;                                                                      // ORL: tx_v one stage early
    generate if (ORL != 0) begin : g_torl
        reg [FW-1:0] tf0;                                                         // relay: near the TX buffers
        always @(posedge clk) begin tf0 <= {tx_seq, cr_ret, anys, sel_cls, sel_word}; tx_flit <= tf0; end
    end else begin : g_tdir
        always @(posedge clk) tx_flit <= {tx_seq, cr_ret, anys, sel_cls, sel_word};   // datapath: no reset
    end endgenerate
    reg [NR-1:0] rv0;                                                             // ORL: r_v one stage early
    always @(posedge clk or negedge rs) begin
        if (!rs) begin
            tx_v <= 1'b0; tv0 <= 1'b0; rv0 <= 0; gq <= 0; up2 <= 1'b0; rq_q <= 0; gq2 <= 0; up3 <= 1'b0; rq2 <= 0; tx_seq <= 8'd0; rx_seq <= 8'd0; rr <= 0;
            t_cr <= 0; r_v <= 0;
            f_die <= 1'b0; f_rb <= 1'b0; f_seq <= 1'b0; f_cred <= 1'b0; f_cls <= 1'b0;
            fault <= 1'b0; fault_cause <= 5'd0;
            for (k = 0; k < NT; k = k + 1) begin
                lcred[k] <= FCR[8*k +: 8] + ((MUT == 1 && k == 0) ? 8'd1 : 8'd0);
                lc_nz[k] <= (FCR[8*k +: 8] != 0);
            end
            for (k = 0; k < NR; k = k + 1) begin ocred[k] <= OCR[8*k +: 8]; owed[k] <= 8'd0; end
        end else begin
            // die TX face
            for (k = 0; k < NT; k = k + 1) if (ce_v[k] && ib_full[k] && !gsel[k]) f_die <= 1'b1;
            t_cr <= gsel;
            // link TX
            gq <= gnt; up2 <= up_q; rq_q <= rdec; gq2 <= gq; up3 <= up2; rq2 <= rq_q;
            tv0 <= up_s;
            tx_v <= (ORL != 0) ? tv0 : up_s;
            if (up_s) tx_seq <= tx_seq + 1'b1;
            if (any) rr <= ((rr + 1) % NT);
            for (k = 0; k < NT; k = k + 1) begin : upd_lc
                reg [8:0] nxt;
                nxt = {1'b0, lcred[k]} - (gnt[k] ? 9'd1 : 9'd0) + ((re_v && k < 4) ? {7'd0, rx_crs[2*k +: 2]} : 9'd0);
                lcred[k] <= nxt[7:0];
                lc_nz[k] <= (nxt != 0);
                if (nxt > {1'b0, FCR[8*k +: 8]} + ((MUT == 1 && k == 0) ? 9'd1 : 9'd0)) f_cred <= 1'b1;
            end
            // link RX
            if (re_v) begin
                rx_seq <= rx_seq + 1'b1;
                if (rx_seq_f != rx_seq) f_seq <= 1'b1;
            end
            if (rx_dv && (rx_cls < 3'(RXB) || rx_cls >= 3'(RXB + NR))) f_cls <= 1'b1;
            for (k = 0; k < NR; k = k + 1) begin
                if (rb_push[k] && rb_full[k] && !rb_pop[k]) f_rb <= 1'b1;
                owed[k] <= owed[k] - (up_s ? {6'd0, ret[k]} : 8'd0) + ((MUT == 2 ? rb_push[k] : rb_pop[k]) ? 8'd1 : 8'd0);
                ocred[k] <= ocred[k] - (rdec[k] ? 8'd1 : 8'd0) + (cr_q[k] ? 8'd1 : 8'd0);
            end
            // die RX face
            rv0 <= rb_pop;
            r_v <= (ORL != 0) ? rv0 : rb_pop;
            fault_cause <= {f_cls, f_cred, f_seq, f_rb, f_die};
            fault <= f_die | f_rb | f_seq | f_cred | f_cls;
        end
    end
    generate if (ORL != 0) begin : g_rorl
        reg [NR*W-1:0] rd0;                                                       // relay: head capture next to the RX buffers
        always @(posedge clk) begin
            for (k = 0; k < NR; k = k + 1) if (rb_pop[k]) rd0[W*k +: W] <= rb_head[W*k +: W];
            r_d <= rd0;                                                           // face register: no enable fan-out at the face
        end
    end else begin : g_rdir
        always @(posedge clk) for (k = 0; k < NR; k = k + 1) if (rb_pop[k]) r_d[W*k +: W] <= rb_head[W*k +: W];
    end endgenerate
endmodule

// el1011-q-kvd 2026-10-12 (PQ): parent-side shadows of the hardened link buffers' occupancy control.  Exact mirrors of
// ot_qkvd_sbuf / ot_qkvd_fbuf8 (ot_qkvd_buf_tiles.sv) as functions of push / pop: pin-flop push stage, (sbuf) the
// direct / SRAM path decision and its read pipeline, and the head-queue count (slice 0) whose zero is the tile's empty.
// Reset releases on the same cycle as the tile's ot_rst_relay (2 sync + 1 tree stages).  ne_next: a word remains at the
// head after this cycle's pop (pushes already in the pipeline included), i.e. a pop may be issued for the next cycle.
// Keep in step with ot_qkvd_buf_tiles.sv (the d2d simulation checks shadow empty == tile empty every cycle).
module ot_qkvd_sbuf_shadow #(
    parameter integer PIQ = 0          // 1: mirrors ot_qkvd_sbufp (pop registered inside the tile)
) (
    input  wire clk,
    input  wire rst_n,
    input  wire push,
    input  wire pop,
    output wire empty,
    output wire ne_next
);
`ifdef KVD_SBP
    localparam integer P = `KVD_SBP;
`else
    localparam integer P = 8;
`endif
    localparam integer CW = $clog2(P + 1);
    reg  [2:0]    rsr;
    always @(posedge clk or negedge rst_n) if (!rst_n) rsr <= 3'd0; else rsr <= {rsr[1:0], 1'b1};
    wire          rr = rsr[2];
    reg           push_q, rq, rd_v, cap_vc, capv;
    reg  [6:0]    ns;
    reg  [CW:0]   f;
    reg  [CW-1:0] oc;
`ifdef KVD_FSBMUT
    wire direct = push_q && (oc < P[CW-1:0]);
`else
    wire direct = push_q && (ns == 0) && (f == 0) && (oc < P[CW-1:0]);
`endif
    wire tos   = push_q && !direct;
    wire req   = (ns != 0) && ({1'b0, oc} + f < P);
    wire spush = direct || capv;
    reg  pop_q;
    wire pop_e = (PIQ != 0) ? pop_q : pop;                // the pop that acts on the head queue this cycle
`ifdef KVD_PQ2MUT
    wire [1:0] pops = {1'b0, pop_e};                      // mutant: the pop in flight at the pin is not counted
`else
    wire [1:0] pops = {1'b0, pop_e} + ((PIQ != 0 && pop) ? 2'd1 : 2'd0);   // + the one at the pin (acts next cycle)
`endif
    always @(posedge clk or negedge rr) if (!rr) pop_q <= 1'b0; else pop_q <= pop;
    always @(posedge clk or negedge rr)
        if (!rr) begin push_q <= 1'b0; ns <= 0; f <= 0; rq <= 1'b0; rd_v <= 1'b0; cap_vc <= 1'b0; capv <= 1'b0; oc <= 0; end
        else begin
            push_q <= push; rq <= req; rd_v <= rq; cap_vc <= rd_v; capv <= rd_v;
            ns <= ns + (tos ? 1'b1 : 1'b0) - (req ? 1'b1 : 1'b0);
            f  <= f + (req ? 1'b1 : 1'b0) - (cap_vc ? 1'b1 : 1'b0);
            oc <= oc + (spush ? 1'b1 : 1'b0) - (pop_e ? 1'b1 : 1'b0);
        end
    assign empty   = (oc == 0);
    assign ne_next = ({2'b0, oc} + (spush ? 1'b1 : 1'b0)) > pops;
endmodule

module ot_qkvd_fbuf8_shadow #(
    parameter integer PIQ = 0          // 1: mirrors ot_qkvd_fbuf8p
) (
    input  wire clk,
    input  wire rst_n,
    input  wire push,
    input  wire pop,
    output wire empty,
    output wire ne_next
);
    reg  [2:0] rsr;
    always @(posedge clk or negedge rst_n) if (!rst_n) rsr <= 3'd0; else rsr <= {rsr[1:0], 1'b1};
    wire       rr = rsr[2];
    reg        push_q;
    reg  [3:0] oc;
    reg        pop_q;
    wire       pop_e = (PIQ != 0) ? pop_q : pop;
`ifdef KVD_PQ2MUT
    wire [4:0] pops  = {4'd0, pop_e};
`else
    wire [4:0] pops  = {4'd0, pop_e} + ((PIQ != 0 && pop) ? 5'd1 : 5'd0);
`endif
    always @(posedge clk or negedge rr)
        if (!rr) begin push_q <= 1'b0; oc <= 4'd0; pop_q <= 1'b0; end
        else begin push_q <= push; pop_q <= pop; oc <= oc + (push_q ? 4'd1 : 4'd0) - (pop_e ? 4'd1 : 4'd0); end
    assign empty   = (oc == 4'd0);
    assign ne_next = ({1'b0, oc} + (push_q ? 5'd1 : 5'd0)) > pops;
endmodule

// el1011-q-kvd 2026-10-12 (q10): dedicated pop pin flop of one hardened link buffer.  keep_hierarchy stops Yosys opt_merge
// from folding it into the logically identical grant register (which also drives the head mux / counters), so the macro's
// pop pin is driven by exactly this flop and io_flop_at_pins OT_MPFLOP can anchor it beside the pin.  Fixed width (Yosys
// asserts on parameterised keep_hierarchy modules), as ot_qwen_mpr_reg.
(* keep_hierarchy *)
module ot_qkvd_pop_ff (input wire clk, input wire rst_n, input wire d, output reg q);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;
endmodule
