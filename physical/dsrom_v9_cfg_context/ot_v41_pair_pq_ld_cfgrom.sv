// Experimental companion: PQ default off; no adoption or clock claim beyond its own screen.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_pair_pq_ld: the configuration loader of ot_v41_pair_w17w10 (cfg ROM address -> registered word -> element
// configuration port, CW = 3*NSEG+1 words; `act` = a class of the phase is valid, which gates `go`) as a module, with
// the PQ addition of DS-ROM recovery lever "field" (2026-10-04): the load fills the element's configuration
// SHADOW, so it may run while the element still walks the current op; a broadcast that finds the shadow still full
// (not yet copied into the live fields) or the output-tag bank it would write still draining is held (pending) and
// loaded when both clear; a second broadcast before the load, or a go before the load finished, is a FAULT.
// PQ = 0: the pinned loader (load at the broadcast).
// ---------------------------------------------------------------------------
module ot_v41_pair_pq_ld_cfgrom #(
    parameter integer NSEG = 8,
    parameter integer PHW = 6,
    parameter integer PQ = 0,
    parameter integer CW = 3 * NSEG + 1,
    parameter integer AW = $clog2(CW << PHW)
) (
    input  wire           clk,
    input  wire           rst_n,
    input  wire           cfg_go,
    input  wire [PHW-1:0] cfg_ph,
    input  wire [2:0]     cfg_np,
    input  wire           go,
    input  wire           e_sh_free,
    input  wire           e_bank_free,
    output wire [AW-1:0]  cm_a,
    output wire [11:0]    cm_read_a,
    output wire           cm_read_ce,
    input  wire [47:0]    cm_q,
    output reg            c_v,
    output reg  [4:0]     c_a,
    output reg  [47:0]    c_d,
    output wire           go_e,
    output wire           ld_busy,
    output reg            fault
);
    reg         ld_run;
    reg [4:0]   ld_k;
    reg [AW-1:0] ld_a;
    reg [2:0]   ld_np;
    reg         pend;
    reg [PHW-1:0] pend_ph;
    reg [2:0]   pend_np;
    wire        ld_ok = (PQ == 0) || (e_sh_free && e_bank_free);
    wire        ld_start = (cfg_go && ld_ok) || (PQ != 0 && pend && !cfg_go && ld_ok);
    assign cm_a = ld_a;
    // Same-edge address lookahead for the real synchronous configuration ROM.
    // No state/capture/GO changes: first read at ld_start, then ld_a+1; the
    // original c_d captures the previous edge's ROM word at the next edge.
    assign cm_read_a = ld_start ? 12'(cfg_go ? cfg_ph : pend_ph) * 12'(CW)
                               : 12'(ld_a) + 12'd1;
    assign cm_read_ce = rst_n && (ld_start || (ld_run && ld_k < 5'(CW-1)));
    initial begin
        if (CW * (1 << PHW) > 4096 || CW > 32 || AW > 12)
            $fatal(1, "configuration provider exceeds one real 4096-row macro");
    end
    assign ld_busy = ld_run || c_v || pend;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ld_run <= 1'b0; ld_k <= 5'd0; c_v <= 1'b0; pend <= 1'b0; fault <= 1'b0;
        end else begin
            // Explicit holds preserve reset-only PQ0 fault/pend in Slang lowering.
            // PQ!=0 fault-set assignments below keep their original precedence.
            fault <= fault;
            pend <= pend;
            c_v <= ld_run;
            if (PQ != 0) begin
                if (cfg_go && !ld_ok) begin pend <= 1'b1; pend_ph <= cfg_ph; pend_np <= cfg_np; end
                else if (ld_start) pend <= 1'b0;
                if (cfg_go && (pend || ld_run)) fault <= 1'b1;               // a second broadcast before the load
                if (go && (pend || ld_run || c_v || cfg_go)) fault <= 1'b1;  // go before the load finished
            end
            if (ld_start) begin
                ld_run <= 1'b1; ld_k <= 5'd0;
                ld_a <= AW'(cfg_go ? cfg_ph : pend_ph) * AW'(CW);
                ld_np <= cfg_go ? cfg_np : pend_np;
            end else if (ld_run) begin
                ld_k <= ld_k + 5'd1;
                ld_a <= ld_a + 1'b1;
                if (ld_k == 5'(CW - 1)) ld_run <= 1'b0;
            end
        end
    end
    // An element with no class in the phase gets no `go` (W17 gate, 2026-09-30): the OR of the phase's class-valid
    // bits as they are loaded
    reg act;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) act <= 1'b0;
        else if (cfg_go || ld_start) act <= 1'b0;
        else if (c_v && c_a >= 5'(NSEG) && c_a < 5'(2 * NSEG) && c_d[0]) act <= 1'b1;
    end
    assign go_e = go && act;
    always @(posedge clk) begin
        c_a <= ld_k;
        if (ld_run) c_d <= (ld_k == 5'(2 * NSEG)) ? (cm_q | {42'd0, ld_np, 3'd0}) : cm_q;
    end
endmodule
