`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 FUSED HC engine station (el1011-hbm-fused, 2026-10-12): the body of the die element hfd_hc_eng (slot hb_hc_eng).
// The FUSED record in hb_quant (ot_hgi_fused_record HCE = 2) hands its d = HCD HC_POST / HC_PRE_NORM jobs to this block
// over the die net fused_ne; the one-pass lane-local engine (ot_hgi_hc_eng LL = 1) runs them on its OWN lgE lane-group
// slot (KE slot 3, hfd_stn_lgE station hb_stn_lgE_hce), so the record's stream unit keeps its lanes and the FUSED mover
// keeps the slot-2 write group while it streams the gain (the engine takes the write group only after g_rdy on
// HC_PRE_NORM: ot_hgi_hc_ctl_ll).
//   fused_ne (record -> here, 151 b): {g_rdy, job_v, job 149}   job_v: a level held until the record sees job_rdy; this
//                                                                 side takes a job on its RISING edge (one job a level)
//   fused_ne_r (here -> record, 3 b): {job_rdy, fault, done}       job_rdy = the engine idle (a level); fault / done pulses
//   Both directions cross the die on relays (same latency for every bit of a bundle), so g_rdy rides with its job.
// Boundaries: every die input is a pin flop here (the engine's own pin flops follow), every output a flop.
// lgE tap packing (LSB first, ot_hgi_vm_lanestation local side, as ot_hgi_fused_station):
//   rup {wrq 32 x 16, rg_req} 513 | rdn {wrr 32 x 257, wrq_cr 32, rg_gnt} 8,257 | wup {wwq 32 x 280, wg_req} 8,961 |
//   wdn {wwq_done 32, wwq_cr 32, wg_gnt} 65.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_hc_eng_station #(
    parameter integer D   = 5120,
    parameter integer LQ  = 32,
    parameter integer MUT = 0,           // ot_hgi_hc_eng MUT (bench negatives)
    parameter integer RL  = 10
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [150:0]  ne_i,           // {g_rdy, job_v, job}
    output reg  [2:0]    ne_o,           // {job_rdy, fault, done}
    output wire [512:0]  lg_rup,
    input  wire [8256:0] lg_rdn,
    output wire [8960:0] lg_wup,
    input  wire [64:0]   lg_wdn
);
    // ---- pin flops (die inputs)
    reg [148:0] p_job; reg p_v, p_g, p_vq;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin p_v <= 1'b0; p_g <= 1'b0; p_vq <= 1'b0; end
        else begin p_v <= ne_i[149]; p_g <= ne_i[150]; p_vq <= p_v; end
    always @(posedge clk) p_job <= ne_i[148:0];
    // ---- one-entry job hold: a rising job_v level is ONE job; held to the engine until it leaves idle
    wire e_rdy, e_done, e_fault;
    reg h_v; reg [148:0] h_job;
    wire take = p_v && !p_vq;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) h_v <= 1'b0;
        else if (take) h_v <= 1'b1;
        else if (h_v && e_rdy) h_v <= 1'b0;          // the engine's job pin flop captures it this edge (it is idle)
    always @(posedge clk) if (take) h_job <= p_job;
    // ---- the engine
    wire [32*16-1:0] wrq; wire [32*280-1:0] wwq; wire rg_req, wg_req;
    ot_hgi_hc_eng #(.D(D), .LQ(LQ), .MUT(MUT), .LL(1), .RL(RL)) u_e (.clk(clk), .rst_n(rst_n),
        .job_v(h_v), .job_rdy(e_rdy), .job(h_job), .g_rdy(p_g), .done(e_done), .fault(e_fault), .idle(),
        .wrq(wrq), .wrq_cr(lg_rdn[32:1]), .wrr(lg_rdn[8256:33]), .wwq(wwq), .wwq_cr(lg_wdn[32:1]),
        .wwq_done(lg_wdn[64:33]), .rg_req(rg_req), .rg_gnt(lg_rdn[0]), .wg_req(wg_req), .wg_gnt(lg_wdn[0]));
    assign lg_rup = {wrq, rg_req};
    assign lg_wup = {wwq, wg_req};
    // ---- registered return (job_rdy is not taken while a job is held: the record never sees a stale idle)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) ne_o <= 3'b000;
        else ne_o <= {e_rdy && !h_v && !take, e_fault, e_done};
endmodule

`default_nettype wire
