`timescale 1ns/1ps
// ot_dsrom_mtp_skid: 2-entry FIFO used on the valid / ready side of the MTP blocks (stream mtp-rom, 2026-10-08).
// in_ready and out_valid come straight from the count flops (no input-to-output combinational path); full rate.
// OREG 1: out_data also straight from a flop (an output register + one skid register; no read mux at the pins).
// SPUSH 1 (mtp-wfc 2026-10-11): the skid register loads on every push.  The OREG enable `push && !(take && !s_v)` put
// out_ready (a kit pin on dsfd_wfc_crp: f_klir) on the enable of all W skid flops (pin -> 1,026-flop fan-out, TT -5.6);
// a load while the data goes straight to the output register is harmless (s_v stays 0), so s_d's enable is push alone.
// OREG 2 (el1011-ds-wfc 2026-10-11, PIN-REGISTERED): both handshake pins land on a handful of flops only.  The OREG 1
// form still put in_valid on the W-bit skid enable (push) and out_ready on the W-bit output-register enable (take): a
// die/kit pin fanning out to 500-1,000 enables (dsfd_wfc_crp routes 0127f8be9: f_kswv -> s_d SS -162, f_klir ->
// out_data SS -98, TT -42 overall).  Here: 2-slot ring m0/m1; the free slot w is written on every cycle in_ready (a flop)
// is high, whether or not in_valid is (a write into the free slot is harmless; it is never the head unless empty), so
// slot write enables are flop-only; in_valid reaches only n / w / ir_q / ov_q; out_ready reaches only n / ov_q / ir_q
// and the RSEL-bit-sliced copies of the read select r (one keep flop per RSEL data bits, so no flop drives > RSEL mux
// selects); out_data = r ? m1 : m0 (one mux level after a flop).  in_ready / out_valid are dedicated flops.
// Latency and throughput are those of the 2-entry FIFO (g_mux): push at t -> out_valid at t+1, full rate.
module ot_dsrom_mtp_skid #(parameter integer W = 32, parameter integer OREG = 0, parameter bit SPUSH = 0,
                           parameter integer RSEL = 32) (
    input  wire         clk,
    input  wire         rst_n,            // synchronous, active low
    input  wire         in_valid,
    output wire         in_ready,
    input  wire [W-1:0] in_data,
    output wire         out_valid,
    input  wire         out_ready,
    output wire [W-1:0] out_data
);
generate if (OREG == 2) begin : g_pin
    localparam integer NR = (W + RSEL - 1) / RSEL;
    reg [W-1:0] m0, m1;
    reg [1:0] n; reg w;
    (* keep *) reg ir_q;
    (* keep *) reg ov_q;
    (* keep *) reg [NR-1:0] r_q;              // NR identical copies of the read select
    assign in_ready = ir_q;
    assign out_valid = ov_q;
    wire push = in_valid && ir_q, pop = ov_q && out_ready;
    wire [1:0] n_nx = n + {1'b0, push} - {1'b0, pop};
    always @(posedge clk) begin
        if (ir_q && !w) m0 <= in_data;
        if (ir_q && w) m1 <= in_data;
        if (!rst_n) begin n <= 2'd0; w <= 1'b0; r_q <= {NR{1'b0}}; ir_q <= 1'b0; ov_q <= 1'b0; end
        else begin
            n <= n_nx;
            if (push) w <= ~w;
            if (pop) r_q <= ~r_q;
            ir_q <= n_nx != 2'd2;
            ov_q <= n_nx != 2'd0;
        end
    end
    genvar gi;
    for (gi = 0; gi < W; gi = gi + 1) begin : g_o
        assign out_data[gi] = r_q[gi / RSEL] ? m1[gi] : m0[gi];
    end
end else if (OREG) begin : g_oreg
    reg [W-1:0] o_d, s_d; reg o_v, s_v;
    assign in_ready = rst_n && !s_v;
    assign out_valid = o_v;
    assign out_data = o_d;
    wire push = in_valid && in_ready;
    wire take = !o_v || out_ready;                 // the output register is free this cycle
    always @(posedge clk) begin
        if (!rst_n) begin o_v <= 1'b0; s_v <= 1'b0; end
        else if (take) begin
            if (s_v) begin o_v <= 1'b1; s_v <= push; end
            else o_v <= push;
        end else if (push) s_v <= 1'b1;
        if (take) o_d <= s_v ? s_d : in_data;
        if (SPUSH ? push : (push && !(take && !s_v))) s_d <= in_data;
    end
end else begin : g_mux
    reg [W-1:0] m [0:1];
    reg [1:0] n; reg r, w;
    assign in_ready = rst_n && n != 2'd2;
    assign out_valid = n != 2'd0;
    assign out_data = m[r];
    wire push = in_valid && in_ready, pop = out_valid && out_ready;
    always @(posedge clk) begin
        if (push) m[w] <= in_data;
        if (!rst_n) begin n <= 2'd0; r <= 1'b0; w <= 1'b0; end
        else begin
            if (push) w <= ~w;
            if (pop) r <= ~r;
            n <= n + (push ? 2'd1 : 2'd0) - (pop ? 2'd1 : 2'd0);
        end
    end
end endgenerate
endmodule
