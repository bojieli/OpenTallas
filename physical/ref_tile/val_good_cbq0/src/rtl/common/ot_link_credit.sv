`timescale 1ns/1ps
// cont-takeover 2026-10-09 (REVIEW ~11:30, structural rule "pin stations + credits die-wide"): the credit-relay boundary
// for a die-link channel.  Every pin is a flop: the link carries {valid, data} forward from sender flops into receiver
// pin flops, and one credit pulse backward from a receiver flop into a sender pin flop.  No pin fans out into logic
// (the valid/ready skid it replaces let out_ready fan out to the 600-bit pop enables: HC join TT -120 ps under the
// die-link budget).
//   ot_link_credit_tx : core valid/ready (internal) -> link.  CRED = the receiver's landing depth; a beat leaves only
//                       with a credit in hand, so the receiver can never overflow.  l_credit is a one-cycle pulse per
//                       freed landing slot.
//   ot_link_credit_rx : link -> landing FIFO (DEPTH) -> core valid/ready (internal); a credit pulse per core pop.
//                       A beat that lands with the FIFO full is a protocol fault (sticky; the beat is dropped).
// Pin registers l_valid / l_credit are (* keep *) (ds-1010 2026-10-10; NOT l_data: its hold-mux feedback would then tap
// the kept net and io_flop_at_pins could no longer anchor the data pin flops -- ct crpc 2214 output ports unanchored): synthesis otherwise merges identical
// credit pulses of two links into one flop driving two face pins (coll ct crpb: u_lo7 l_credit anchored at the E face,
// its merged twin's pin; lo7_r on the S face 250 ps away).  Function unchanged.
// Full throughput needs DEPTH >= the credit round trip (2 x link latency + 4 cycles of pin/landing flops).
// DFREE=1 (ds-1010 2026-10-10, opt-in): l_data loads i_data every cycle (no load enable).  The receiver samples l_data
// only with l_valid, so a non-send cycle's data is a don't-care; send (i_valid && credit, possibly a deep producer
// decision) then reaches only the 1-bit l_valid flop, never a W-bit enable (TU iqs5-a TT -175.9 = retry base ->
// ack/replay classification -> tx_valid -> 568-bit l_data enables).
module ot_link_credit_tx #(parameter integer W=8, CRED=8, DFREE=0)(
    input wire clk, rst_n,
    input wire i_valid, output wire i_ready, input wire [W-1:0] i_data,
    (* keep *) output reg l_valid, output reg [W-1:0] l_data, input wire l_credit
);
    localparam integer CW = $clog2(CRED + 1);
    reg cr_q;
    reg [CW-1:0] cnt;
    assign i_ready = cnt != 0;
    wire send = i_valid && cnt != 0;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cr_q <= 1'b0; cnt <= CW'(CRED); l_valid <= 1'b0; end
        else begin
            cr_q <= l_credit;
            cnt <= cnt + CW'(cr_q) - CW'(send);
            l_valid <= send;
        end
`ifdef OT_LINK_DFREE_MUT
    // bench mutant: with DFREE the data stage lags its valid by one cycle (must be caught by the TU bench)
    reg [W-1:0] mut_q; always @(posedge clk) mut_q <= i_data;
    always @(posedge clk) if (DFREE) l_data <= mut_q; else if (send) l_data <= i_data;
endmodule
`else
    always @(posedge clk) if (DFREE || send) l_data <= i_data;
endmodule
`endif

// OREG=1: the landing FIFO drains into a two-entry output skid, so o_valid / o_data leave flops (no FIFO read
// mux in front of the consumer's logic: HC join -lk TT -107 = rp -> 8:1 landing mux -> SECDED encode -> wd_q).  The
// credit is returned when a beat leaves the FIFO; the skid adds 2 slots beyond DEPTH and 1 cycle of latency.
// WFREE=1 (redesign-ds 2026-10-10): the landing write does not wait for a pop (wr = the landed beat): credits already
// guarantee a free slot, so the consumer's o_ready reaches only the read pointer / count / credit flops, never a W-bit
// write or load enable (coll split3 ce pre-route -832 = consumer ready -> skid 553-bit enables).  Use with OREG=0: o_data
// is the DEPTH:1 read mux of the landing flops.  A beat landing on a full FIFO is still a sticky fault.
// WFREE=2 (ds-1010/coll-tu 2026-10-11, opt-in; OREG=0): as WFREE=1, plus (a) the landing register is written into the
// free slot mem[wp] EVERY cycle the FIFO is not full (a non-valid cycle writes a don't-care into a slot that holds no
// beat; wp advances only with a landed beat), with the per-slot write enables REGISTERED one-hot (computed from the
// next wp / count), so no landed-valid -> 8 x W-bit enable cone (coll lane lcrpx v_q -> mem[7][*] SS -176) and (b)
// o_valid is a registered non-empty flag, so the count compare is not in front of the consumer's accept (lane lcrpi
// n -> pop -> rp SS -574).  Same cycle behaviour as WFREE=1.
module ot_link_credit_rx #(parameter integer W=8, DEPTH=8, OREG=0, WFREE=0)(
    input wire clk, rst_n,
    input wire l_valid, input wire [W-1:0] l_data, (* keep *) output reg l_credit,
    output wire o_valid, input wire o_ready, output wire [W-1:0] o_data,
    output reg fault
);
    wire f_valid, f_ready; wire [W-1:0] f_data;
    generate if (OREG) begin : g_oreg
        reg v0, v1; reg [W-1:0] d0, d1;
        assign f_ready = !v1; assign o_valid = v0; assign o_data = d0;
        wire push = f_valid && !v1, take = v0 && o_ready;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin v0 <= 1'b0; v1 <= 1'b0; end
            else if (take) begin if (v1) v1 <= 1'b0; else v0 <= push; end
            else if (push) begin if (!v0) v0 <= 1'b1; else v1 <= 1'b1; end
        always @(posedge clk)
            if (take) begin if (v1) d0 <= d1; else if (push) d0 <= f_data; end
            else if (push) begin if (!v0) d0 <= f_data; else d1 <= f_data; end
    end else begin : g_direct
        assign o_valid = f_valid; assign f_ready = o_ready; assign o_data = f_data;
    end endgenerate
    localparam integer AW = (DEPTH > 1) ? $clog2(DEPTH) : 1, CW = $clog2(DEPTH + 1);
    reg v_q;
    reg [W-1:0] d_q;
    reg [W-1:0] mem [0:DEPTH-1];
    reg [AW-1:0] wp, rp;
    reg [CW-1:0] n;
    reg nz_r;                        // WFREE 2: n != 0, registered
    reg [DEPTH-1:0] we_r;            // WFREE 2: one-hot (wp == k) && !full, registered
    assign f_valid = (WFREE == 2) ? nz_r : (n != 0);
    assign f_data = mem[rp];
    wire pop = f_valid && f_ready;
    wire full = n == CW'(DEPTH);
    wire wr = WFREE ? (v_q && !full) : (v_q && (!full || pop));
    wire [AW-1:0] wp_nx = wr ? ((wp == AW'(DEPTH - 1)) ? '0 : wp + 1'b1) : wp;
    wire [CW-1:0] n_nx = n + CW'(wr) - CW'(pop);
    integer k, j;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin v_q <= 1'b0; wp <= 0; rp <= 0; n <= 0; l_credit <= 1'b0; fault <= 1'b0; nz_r <= 1'b0;
                          we_r <= DEPTH'(1); end
        else begin
            v_q <= l_valid;
            l_credit <= pop;
            if (v_q && full && !pop) fault <= 1'b1;
            wp <= wp_nx;
            if (pop) rp <= (rp == AW'(DEPTH - 1)) ? '0 : rp + 1'b1;
            n <= n_nx;
            nz_r <= n_nx != 0;
            for (k = 0; k < DEPTH; k = k + 1)
`ifdef OT_LINK_WFREE2_MUT
                we_r[k] <= (wp == AW'(k)) && (n_nx != CW'(DEPTH));      // bench mutant: enable one slot behind
`else
                we_r[k] <= (wp_nx == AW'(k)) && (n_nx != CW'(DEPTH));
`endif
        end
    always @(posedge clk) begin
        d_q <= l_data;
        if (WFREE == 2) begin
            for (j = 0; j < DEPTH; j = j + 1) if (we_r[j]) mem[j] <= d_q;
        end else if (wr) mem[wp] <= d_q;
    end
endmodule

// Testbench-side link model (not for synthesis in a block): a valid/ready producer or consumer reaches a credit port of a
// DUT through LAT cycles of link flops each way.  DIR=0: TB producer -> DUT receiver (TB holds a tx with CRED = the
// DUT's DEPTH); DIR=1: DUT sender -> TB consumer (TB holds an rx with DEPTH = the DUT tx's CRED).
// LEAK > 0 (DIR 0): the TB sender discards the first LEAK returned credits (a lost-credit negative: the channel stalls).
module ot_link_credit_tb_chan #(parameter integer W=8, DIR=0, DEPTH=8, LAT=2, CRED_BIAS=0, LEAK=0)(
    input wire clk, rst_n,
    // TB side
    input wire t_valid, output wire t_ready, input wire [W-1:0] t_data,     // DIR 0
    output wire r_valid, input wire r_ready, output wire [W-1:0] r_data,    // DIR 1
    output wire fault,
    // DUT side
    output wire d_valid, output wire [W-1:0] d_data, input wire d_credit,  // DIR 0: into the DUT rx
    input wire u_valid, input wire [W-1:0] u_data, output wire u_credit    // DIR 1: from the DUT tx
);
    reg [LAT-1:0] vd; reg [W-1:0] dd [0:LAT-1]; reg [LAT-1:0] cd;
    wire sv, sc; wire [W-1:0] sd;
    integer i;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin vd <= 0; cd <= 0; end
        else begin vd <= {vd[LAT-2:0], sv}; cd <= {cd[LAT-2:0], sc}; end
    always @(posedge clk) begin dd[0] <= sd; for (i = 1; i < LAT; i = i + 1) dd[i] <= dd[i-1]; end
    generate if (DIR == 0) begin : g_in
        wire lv; wire [W-1:0] ld;
        integer lost;
        always @(posedge clk or negedge rst_n) if (!rst_n) lost <= 0; else if (cd[LAT-1] && lost < LEAK) lost <= lost + 1;
        ot_link_credit_tx #(.W(W), .CRED(DEPTH + CRED_BIAS)) tx(.clk(clk), .rst_n(rst_n), .i_valid(t_valid), .i_ready(t_ready),
            .i_data(t_data), .l_valid(lv), .l_data(ld), .l_credit(cd[LAT-1] && lost >= LEAK));
        assign sv = lv; assign sd = ld; assign sc = d_credit;
        assign d_valid = vd[LAT-1]; assign d_data = dd[LAT-1];
        assign r_valid = 1'b0; assign r_data = '0; assign u_credit = 1'b0; assign fault = 1'b0;
    end else begin : g_out
        wire lc;
        ot_link_credit_rx #(.W(W), .DEPTH(DEPTH)) rx(.clk(clk), .rst_n(rst_n), .l_valid(vd[LAT-1]), .l_data(dd[LAT-1]),
            .l_credit(lc), .o_valid(r_valid), .o_ready(r_ready), .o_data(r_data), .fault(fault));
        assign sv = u_valid; assign sd = u_data; assign sc = lc; assign u_credit = cd[LAT-1];
        assign t_ready = 1'b0; assign d_valid = 1'b0; assign d_data = '0;
    end endgenerate
endmodule
