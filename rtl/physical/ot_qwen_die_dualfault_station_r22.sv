`timescale 1ns/1ps
// Candidate, default off. Actual fixed-schedule tile command: {xl[127:0],
// ib_go, ib[378:0]}; no instruction assembly and no tile-ready handshake.
// Clock/reset distribution is outside this508-bit data packet. Two reverse
// fault rails add2 bits. Receiver decodes fault | ~fault_n; an invalid00/11 pair
// is a fault. Forward ib/go has NO protection credit; fullsystem adoption held.
//
// Selected data latency =1 cycle; reverse fault latency =2 cycles. The caller
// MUST hold result publication until the latest possible tile fault has crossed
// the complete return tree. a_fault is not a retirement acknowledgement.
// Cold POR only: launch stays0 through pipeline fill. No accepted work may be
// discarded by warm reset. Mutable fault-state protection, publication guard,
// actual pin placement and die-context SS/FF remain qualification gates.
module ot_qwen_die_dualfault_station_r22 #(
    parameter integer ENABLE_FULLWIDTH = 0,
    parameter integer TAP = 1,
    parameter integer SPLIT = 0
) (
    input wire clk, rst_n,
    input wire [507:0] a_d,
    output wire [507:0] b_d,
    output wire [((TAP != 0) ? 508 : 1)-1:0] t_d,
    output wire [((SPLIT != 0) ? 508 : 1)-1:0] c_d,
    input wire b_fault, t_fault, c_fault,
    output wire a_fault,
    input wire b_fault_n, t_fault_n, c_fault_n,
    output wire a_fault_n
);
    generate if (ENABLE_FULLWIDTH != 0) begin : g_selected
        // Kept copies are intentional. Mapped netlist must confirm output
        // drivers were not merged before their pin-to-pin load is qualified.
        (* keep *) reg [507:0] b_q;
        (* keep = 1, dont_touch = 1 *) always @(posedge clk) b_q <= a_d;
        assign b_d = b_q;
        if (TAP != 0) begin : g_tap
            (* keep *) reg [507:0] t_q;
            (* keep = 1, dont_touch = 1 *) always @(posedge clk) t_q <= a_d;
            assign t_d = t_q;
        end else begin : g_notap
            assign t_d = 1'b0;
        end
        if (SPLIT != 0) begin : g_split
            (* keep *) reg [507:0] c_q;
            (* keep = 1, dont_touch = 1 *) always @(posedge clk) c_q <= a_d;
            assign c_d = c_q;
        end else begin : g_nosplit
            assign c_d = 1'b0;
        end
        (* keep = 1, dont_touch = 1 *) reg bf_q, tf_q, cf_q, af_q;
        (* keep = 1, dont_touch = 1 *) reg bfn_q, tfn_q, cfn_q, afn_q;
        wire bad_pair = (bf_q == bfn_q) | (tf_q == tfn_q) | (cf_q == cfn_q);
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                bf_q <= 0; tf_q <= 0; cf_q <= 0; af_q <= 0;
                bfn_q <= 1; tfn_q <= 1; cfn_q <= 1; afn_q <= 1;
            end else begin
                bf_q <= b_fault;
                tf_q <= (TAP != 0) ? t_fault : 1'b0;
                cf_q <= (SPLIT != 0) ? c_fault : 1'b0;
                bfn_q <= b_fault_n;
                tfn_q <= (TAP != 0) ? t_fault_n : 1'b1;
                cfn_q <= (SPLIT != 0) ? c_fault_n : 1'b1;
                af_q <= bf_q | tf_q | cf_q | bad_pair;
                afn_q <= bfn_q & tfn_q & cfn_q & ~bad_pair;
            end
        end
        assign a_fault = af_q;
        assign a_fault_n = afn_q;
    end else begin : g_bypass
        assign b_d = a_d;
        if (TAP != 0) assign t_d = a_d;
        else assign t_d = 1'b0;
        if (SPLIT != 0) assign c_d = a_d;
        else assign c_d = 1'b0;
        assign a_fault = b_fault | ((TAP != 0) && t_fault) | ((SPLIT != 0) && c_fault);
        assign a_fault_n = b_fault_n & ((TAP == 0) || t_fault_n) & ((SPLIT == 0) || c_fault_n);
    end endgenerate
endmodule
