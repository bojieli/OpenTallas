`timescale 1ns/1ps
`default_nettype none
// HBM-TIE 2026-10-17 (stub audit 0da, H-3 refresh_reload): the boot-configuration PRODUCER of the per-PC refresh phase.
//
// Before: every ot_hbm_svc_pc_ctrl_leaf_cfg_h9b on the die had refresh_reload strapped to a die constant
// (RELOAD = 118+RP+((RP+118+P)%2), RP = P*118/32 % 118; tools/hbm_die_v15/full_die_v16.py _pc_refresh_reload).
// The coordinator ruling 0da(d) rejects functional config straps: the refresh phase is a schedule parameter the
// compiler must own (it fixes which HBM row slots a PC loses to REFpb), so it now comes from the host boot
// configuration load through the static F20 ingress, like every other programme/operand row.
//
// One instance per HBM stack (32 PCs). F20 frames (ot_hbm_host_static_ingress broadcast) addressed to tgt:
//   0x800  operand row 0: data[p*8+:8] = refresh_reload of PC p (p = 0..NPC-1). Accepted once per power-on:
//          every byte must lie in [RMIN, RMAX] (the controller's legal reload range for REFpb tREFI/32 = 118),
//          otherwise the row is refused and fault is set. A second write after a successful load is refused
//          (fault): the phase cannot change under running controllers.
//   other  fault.
// Release: pc_rst_n (HBM domain, one register) holds the stack's PC controllers in reset until the row is loaded:
//   loaded (stream flop) -> 2-flop synchroniser on clk_hbm -> pc_rst_n flop, AND rst_hbm_n (asynchronous assert).
//   The controllers' own ot_rst_relay adds 3 HBM edges before the r14 sequencer loads ref_c <= refresh_reload, so the
//   refresh_reload bus is stable >= 5 HBM edges before it is sampled; after the load it never changes (quasi-static
//   bus: STA treats refresh_reload as a multicycle/false path, same as the strap it replaces).
// Status (stream domain, to the host status join as one more F20 target): ready = loaded & !fault,
//   active = loaded & release not yet seen back from the HBM domain, fault = sticky.
// No ready/credit/backpressure: configuration-time only; the controllers' production schedule is unchanged.
// Pins: every input lands in a pin flop, every output is a flop Q (owner rule 10-15 19:50).
// Reset (ELEM-GAPS/HBMN2 2026-10-18, native capture 217.3 > 190 at rst_n on hbm_refcfg_q_1018): the rst_n PORT drives
// only ot_rst_relay (2 sync flops + 1 relay flop, async assert); every stream-domain flop resets from rs_n. Release
// takes RST_RELEASE = 3 rising clk edges after the port (compiler/host boot: the first F20 frame to this target may
// not arrive within 3 stream edges of rst_n release -- boot frames come >= tens of edges later). No other cycle change.
// MUT (bench only): 1 range check off, 2 release ignores loaded, 3 rewrite after load accepted, 4 PC byte order swapped.
module ot_hbm_pc_refresh_cfg #(
    parameter integer NPC  = 32,
    parameter integer RMIN = 118,
    parameter integer RMAX = 236,
    parameter integer MUT  = 0
)(
    input  wire clk, rst_n,              // stream (F20 ingress) domain
    input  wire clk_hbm, rst_hbm_n,      // PC controller domain of this stack
    input  wire [7:0] tgt,               // identity strap: F20 target id of this instance
    input  wire cfg_v,
    input  wire [7:0] cfg_target,
    input  wire [11:0] cfg_addr,
    input  wire [255:0] cfg_data,
    output reg  [NPC*8-1:0] refresh_reload,
    output wire pc_rst_n,
    output reg  ready, active, fault
);
    initial if (NPC < 1 || NPC > 32) $fatal(1, "ot_hbm_pc_refresh_cfg: NPC out of range");
    // ---- reset relay (the rst_n port net reaches 3 flops only)
    localparam integer RST_RELEASE = 3;
    wire rs_n;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rst(.clk(clk), .rst_n_in(rst_n), .rst_n(rs_n));
    // ---- pin flops
    reg cv; reg [7:0] ct, tg; reg [11:0] ca; reg [255:0] cd;
    always @(posedge clk) begin tg <= tgt; ct <= cfg_target; ca <= cfg_addr; cd <= cfg_data; end
    always @(posedge clk or negedge rs_n) if (!rs_n) cv <= 1'b0; else cv <= cfg_v;
    wire hit = cv && ct == tg;
    // ---- row check
    reg in_range; integer p;
    always @* begin
        in_range = 1'b1;
        for (p = 0; p < NPC; p = p + 1)
            if (cd[p*8 +: 8] < RMIN || cd[p*8 +: 8] > RMAX) in_range = 1'b0;
        if (MUT == 1) in_range = 1'b1;
    end
    reg loaded, rel_seen_s1, rel_seen;
    integer b;
    always @(posedge clk or negedge rs_n) begin
        if (!rs_n) begin loaded <= 1'b0; fault <= 1'b0; refresh_reload <= {NPC*8{1'b0}}; end
        else if (hit) begin
            if (ca != 12'h800 || !in_range || (loaded && MUT != 3)) fault <= 1'b1;
            else begin
                loaded <= 1'b1;
                for (b = 0; b < NPC; b = b + 1)
                    refresh_reload[b*8 +: 8] <= cd[((MUT == 4) ? (b ^ 1) : b)*8 +: 8];
            end
        end
    end
    // ---- release into the HBM domain
    reg [1:0] ls; reg prst;
    always @(posedge clk_hbm or negedge rst_hbm_n)
        if (!rst_hbm_n) begin ls <= 2'b00; prst <= 1'b0; end
        else begin ls <= {ls[0], (MUT == 2) ? 1'b1 : loaded}; prst <= ls[1]; end
    assign pc_rst_n = prst;
    // ---- status (release observed back in the stream domain)
    always @(posedge clk or negedge rs_n)
        if (!rs_n) begin rel_seen_s1 <= 1'b0; rel_seen <= 1'b0; ready <= 1'b0; active <= 1'b0; end
        else begin
            rel_seen_s1 <= prst; rel_seen <= rel_seen_s1;
            ready <= loaded && !fault;
            active <= loaded && !rel_seen;
        end
endmodule
`default_nettype wire
