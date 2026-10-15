`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_host_c (s81-die-rtl-bind 2026-10-14, die item F6): the HOST master of an S81 LAYER die.  A layer die has no host
// link of its own: host traffic reaches it over the die chain through the collective (contract v2: collective <->
// host buses), and the host also loads the die's stage program and reads the die's status.  dsfd_host_s (h_v / h_cls /
// h_d on a host-link clock) is the head-die face; this master is the same ingest (dsfd_host_native ENABLE 1, rev c
// pipeline + dsfd_host_sd per-stack decode) behind the die faces the generator wires on a layer die (--rtl-bind):
//
//   f_collective[515:0] (collective -> host, stream ck): {t_cr, h_cls 2, h_d 512, h_v} -- host-stream words (the
//                       ingest protocol of ot_rom_host_ingest: class 0 CSR, 1 descriptor, 2 payload) + one completion
//                       credit (t_cr) per pulse from the far end
//   t_collective[80:0]  (host -> collective): {st 11 = {fault, wfc_ft 4, sseq_st 6}, h_crn 5, t_v, t_d 64}
//                       -- receive-FIFO credits back to the sender, completion words, status (levels / sticky)
//   t_sseq_pw[35:0] / t_sseq_plen[7:0] (-> dsfd_stage_seq_c f_pw / f_plen, SERIAL clock ckv): stage program load
//   f_sseq_st[5:0] (<- sequencer t_st, ckv), f_wfc_ft[3:0] (<- WFC kit t_ft, stream)
//   hw[292*NS-1:0] / hc[9*NS-1:0]: per-stack host writes (dsfd_host_sd), unchanged
// Sequencer CSR words (class 0, intercepted here, never reach the ingest; their receive credit is returned here):
//   d[7:0] = 8'h10 program word: f_pw = {1, a = d[102:96], d28 = d[59:32]};  d[7:0] = 8'h11 program length: d[39:32]
// The program write crosses ck -> ckv through a PWD-deep async FIFO (16 = the sender's credit window) and leaves on ckv
// paced one word every 4 ckv cycles (the sequencer's own 4-deep crossing FIFO has no ready); its receive credit is
// returned when it leaves (pop toggle synchronised to ck), the length word's at once; plen is a static register
// (2-flop synchronised on ckv).
// MUT 1: program words dropped (bench negative); MUT 2: intercepted CSR credits not returned.
//
// +define+DSFD_HOST_C_STATIC (S-BIND r6 2026-10-15, owner static-cycle rule 10-14 18:59: no credits / backpressure): the
// static layer-die host behind dsfd_sp_collective_static_c's host face (f_host 77 / t_host 515):
//   f_collective[514:0] = {h_cls 2, h_d 512, h_v}   -- no t_cr: the far end sends on the compiler's host slots only
//   t_collective[76:0]  = {alive, st 11, t_v, t_d 64} -- no h_crn: alive (reset released) is a level, st as above, a
//                         completion is a SINGLE-EDGE PULSE {t_v, t_d}; the collective queues it (s81_static_host_queue)
//                         and sends it on its next compiled host tx slot, so the host needs neither a credit nor a slot
//   f_lf[4*NS-1:0]      -- {fault, live} pairs of the forwarded host-lane blocks beside the host (hc end, hw start per
//                         stack), folded into the status fault (fault = any lane fault)
// The ingest's internal completion-credit input t_cr is returned locally one edge after each completion leaves (the
// pulse needs no far-end space: the collective queue is sized by the compiler and faults on overflow); its receive
// credits h_crn are not sent (the compiler's host slots never exceed the receive FIFO, whose overflow faults inside the
// ingest).  CSR program words: no credit return; the crossing FIFO overflow / a word refused is the sticky fault xf.
// MUT 3 (static negative): completion pulses not emitted; MUT 4: lane faults (f_lf) not folded into the status fault.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_host_c #(parameter integer NS = 1, KVS = 1, ENG = -1, MUT = 0, PWD = 16) (
    input  wire [0:0]          ck,
    input  wire [0:0]          rst,
    input  wire [0:0]          ckv,
    input  wire [0:0]          rsv,
`ifdef DSFD_HOST_C_STATIC
    input  wire [514:0]        f_collective,
    output wire [76:0]         t_collective,
    input  wire [4*NS-1:0]     f_lf,
`else
    input  wire [515:0]        f_collective,
    output wire [80:0]         t_collective,
`endif
    output reg  [35:0]         t_sseq_pw,
`ifdef DSFD_HOST_PQ_BOOT
    output reg [35:0] t_pq_pw, // CSR 0x12: same PW36 packing, routed to fixed PQ boot mailbox
`endif
    output reg  [7:0]          t_sseq_plen,
    input  wire [5:0]          f_sseq_st,
    input  wire [3:0]          f_wfc_ft,
    output wire [292*NS-1:0]   hw,
    input  wire [9*NS-1:0]     hc
);
    reg [1:0] rq, rvq;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rq <= 2'b00; else rq <= {rq[0], 1'b1};
    always @(posedge ckv[0] or negedge rsv[0]) if (!rsv[0]) rvq <= 2'b00; else rvq <= {rvq[0], 1'b1};
    wire rn = rq[1], rvn = rvq[1];
    // ---------------- input pin flops
    reg [515:0] fi;
`ifdef DSFD_HOST_C_STATIC
    always @(posedge ck[0]) fi <= rn ? {1'b0, f_collective} : 516'd0;
    reg tcr_l;                           // local completion-credit return: one edge after each completion leaves
    wire        hv = fi[0], tcr = tcr_l;
`else
    always @(posedge ck[0]) fi <= rn ? f_collective : 516'd0;
    wire        hv = fi[0], tcr = fi[515];
`endif
    wire [511:0] hd = fi[512:1];
    wire [1:0]  hcl = fi[514:513];
    wire csr_p = hv && hcl == 2'd0 && hd[7:0] == 8'h10;
    wire csr_l = hv && hcl == 2'd0 && hd[7:0] == 8'h11;
    `ifdef DSFD_HOST_PQ_BOOT
    wire csr_pq = hv && hcl == 2'd0 && hd[7:0] == 8'h12;
    localparam PWW=36;
`else
    wire csr_pq = 1'b0;
    localparam PWW=35;
`endif
    wire to_ing = hv && !csr_p && !csr_l && !csr_pq;
    // ---------------- ingest (single stream clock on a layer die: clk_h = clk_i = ck)
    wire [4:0] crn; wire t_v; wire [63:0] t_d;
    wire ov, owe, ocr, hf, sf; wire [31:0] oa; wire [255:0] od; wire [7:0] ack;
    wire pw_wr, pw_v, pw_ovf, pw_unf, pw_take; wire [PWW-1:0] pw_d;
    reg [1:0] pace;
    dsfd_host_native #(.ENABLE(1), .FPIPE(2), .ENG_TRIM(1), .APIPE(2)) u_h (.rst_n(rn), .clk_h(ck[0]), .h_v(to_ing), .h_cls(hcl),
        .h_d(hd), .h_crn(crn), .t_v(t_v), .t_d(t_d), .t_cr(tcr), .clk_i(ck[0]), .ck(ck[0]), .o_v(ov), .o_we(owe), .o_addr(oa),
        .o_d(od), .o_cr(ocr), .i_rv(1'b0), .i_rd(256'd0), .host_ack_n(ack), .fault(hf));
    dsfd_host_sd #(.NS(NS), .KVS(KVS), .ENG(ENG), .MUT(0)) u_sd (.ck(ck), .rst_n(rn), .o_v(ov), .o_we(owe), .o_addr(oa),
        .o_d(od), .o_cr(ocr), .hw(hw), .hc(hc), .host_ack_n(ack), .fault(sf));
    // ---------------- intercepted CSR words: program -> ckv FIFO, length register; their receive credit returned here:
    // a length word's at once, a program word's when it LEAVES the crossing FIFO on ckv (pop toggle, synchronised), so
    // the sender's credit window (<= PWD words) bounds the FIFO: it never overflows
    reg [6:0] crn_x;                     // credits owed to the sender beyond the ingest's own h_crn
    wire [5:0] crn_sum = crn + ((crn_x != 0) ? 6'd1 : 6'd0);
    reg pop_t; (* async_reg = "true" *) reg [2:0] pop_s;
    always @(posedge ck[0] or negedge rn) if (!rn) pop_s <= 3'b000; else pop_s <= {pop_s[1:0], pop_t};
    always @(posedge ck[0] or negedge rn)
        if (!rn) crn_x <= 0;
        else crn_x <= crn_x + ((csr_l && (MUT != 2)) ? 7'd1 : 7'd0) + (((pop_s[2] ^ pop_s[1]) && (MUT != 2)) ? 7'd1 : 7'd0)
                      - ((crn_x != 0 && crn_sum <= 6'd31) ? 7'd1 : 7'd0);
    ot_async_fifo #(.WIDTH(PWW), .DEPTH(PWD)) u_pw (.wr_clk(ck[0]), .wr_rst_n(rn), .wr_valid((csr_p || csr_pq) && (MUT != 1)), .wr_ready(pw_wr),
        `ifdef DSFD_HOST_PQ_BOOT
        .wr_data({csr_pq, hd[102:96], hd[59:32]}),
`else
        .wr_data({hd[102:96], hd[59:32]}),
`endif .wr_overflow(pw_ovf), .rd_clk(ckv[0]), .rd_rst_n(rvn), .rd_valid(pw_v),
        .rd_ready(pw_take), .rd_data(pw_d), .rd_underflow(pw_unf));
    assign pw_take = pw_v && pace == 2'd0;
    always @(posedge ckv[0] or negedge rvn)
        if (!rvn) begin pace <= 0; t_sseq_pw <= 36'd0;
`ifdef DSFD_HOST_PQ_BOOT
            t_pq_pw <= 36'd0;
`endif
            pop_t <= 1'b0; end
        else begin
            `ifdef DSFD_HOST_PQ_BOOT
            t_pq_pw <= pw_take && pw_d[35] ? {1'b1,pw_d[34:0]} : 36'd0;
            t_sseq_pw <= pw_take && !pw_d[35] ? {1'b1,pw_d[34:0]} : 36'd0;
`else
            t_sseq_pw <= pw_take ? {1'b1, pw_d} : 36'd0;
`endif
            if (pw_take) pop_t <= ~pop_t;
            pace <= pw_take ? 2'd3 : (pace != 0 ? pace - 1'b1 : 2'd0);
        end
    reg [7:0] plen;
    always @(posedge ck[0] or negedge rn) if (!rn) plen <= 8'd0; else if (csr_l) plen <= hd[39:32];
    reg [7:0] pl1;
    always @(posedge ckv[0]) begin pl1 <= plen; t_sseq_plen <= pl1; end
    // ---------------- status (ck): sequencer status (ckv, 2-flop), WFC faults, ingest / decode / crossing faults
    reg [5:0] ss1, ss2; reg [3:0] wf;
    always @(posedge ck[0]) begin ss1 <= f_sseq_st; ss2 <= ss1; wf <= f_wfc_ft; end
    reg xf;
    always @(posedge ck[0] or negedge rn) if (!rn) xf <= 1'b0; else if (pw_ovf || ((csr_p || csr_pq) && !pw_wr) || crn_x == 7'd127) xf <= 1'b1;
`ifdef DSFD_HOST_C_STATIC
    // lane faults (odd bits of f_lf), pin-registered
    reg lf_q; integer li;
    always @(posedge ck[0] or negedge rn)
        if (!rn) lf_q <= 1'b0;
        else begin : lfo
            reg a; a = 1'b0;
            for (li = 0; li < 2 * NS; li = li + 1) a = a | f_lf[2 * li + 1];
            lf_q <= a && (MUT != 4);
        end
    always @(posedge ck[0] or negedge rn) if (!rn) tcr_l <= 1'b0; else tcr_l <= t_v;
    reg [76:0] to;
    always @(posedge ck[0]) to <= rn ? {1'b1, hf | sf | xf | lf_q | ss2[5] | (|wf), wf, ss2, t_v && (MUT != 3), t_d} : 77'd0;
    assign t_collective = to;
`else
    reg [80:0] to;
    always @(posedge ck[0]) to <= rn ? {hf | sf | xf | ss2[5] | (|wf), wf, ss2, crn_sum[4:0], t_v, t_d} : 81'd0;
    assign t_collective = to;
`endif
endmodule
