`timescale 1ns/1ps
// KVJ-F 2026-10-17 (stub audit K-12, coordinator 0da (d): "REJECT functional config straps: KV ectl cfg and reset delay
// must come from real producers (boot config load)").  The KV die's boot-loaded functional configuration, x1 beside the
// boot dispatcher, written ONLY by qkd_static_kv_boot_dispatch (DIECFG=1) pre-boot image target 10:
//   words 0..31          group i = 8*stack + g: data[4:0] = ECTL A cfg, [9:5] = ECTL B cfg, [14:10] = ECTL C cfg
//                        ({engine 3, stack 2} as the ECTL parts read it); data[63:15] must be 0
//   words 32..32+NRST-1  reset region r: data[7:0] = qkd_rst_region dly (the release calendar D - d_r of region r, from
//                        the die plan's reset relay depths); data[63:8] must be 0
//   word 32+NRST         seal 0x514b5644_43464731 ("QKVDCFG1"): sealed only if every earlier word was written once, in order
// The registers are reset by the package POR ONLY (por_n, the same pad the regional reset roots synchronise), never by a
// functional reset: the HOST loads target 10 after the first (unaligned, dly 0) release, then re-asserts and releases the
// functional resets, which now release aligned; this block keeps its words across that re-reset.  Outputs are static
// after the seal (configuration nets: no production path launches from them after setup).  Any out-of-order, repeated,
// non-zero-padding or post-seal write is a sticky fault (the dispatcher's sink fault), and nothing reads as sealed.
// RTL-BUILD-KV/FAULT 2026-10-18 (P8: attention_programme / attn_root fused_program_capability had no producer): CAP=1
// adds ONE capability word between the reset-region words and the seal:
//   word 32+NRST         data[0] = the boot image's fused attention-programme capability; data[63:1] must be 0
//   seal                 moves to word 32+NRST+CAP
// fused_program_capability = the loaded bit AND sealed: 0 from POR until the whole image is sealed (a request before
// that faults in the service root / programme, as the legacy capability-0 case), then the image's bit, static (POR-only
// reset, survives the functional re-reset).  CAP=0 = the KVJ-F block unchanged (the output is then 0).
// MUT (bench negative controls): 1 = ECTL B / C fields swapped; 2 = padding bits not checked; 3 = reset-region words
// written one region off; 4 = capability taken from data[1]; 5 = capability not gated by the seal.
// KV-SRAM-CTL 10-19: PCOPIES > 1 = that many KEPT identical copies of the POR synchroniser output ps[1] (same D ps[0],
// clock and async clear; family wire g_pc.prv, ot_rst_split) for the synthesis reset split; default 1 = unchanged.
module qkd_kv_die_cfg #(parameter integer NRST = 43, parameter integer CAP = 0, parameter integer MUT = 0, parameter integer PCOPIES = 1) (
    input  wire               ck, por_n,
    input  wire               cfg_we, input wire [7:0] cfg_addr, input wire [63:0] cfg_data,
    output reg  [32*5-1:0]    ectl_a_cfg, ectl_b_cfg, ectl_c_cfg,
    output reg  [NRST*8-1:0]  rst_dly,
    output wire               fused_program_capability,
    output reg                sealed, fault
);
    localparam integer NW = 32 + NRST + ((CAP != 0) ? 1 : 0);   // data words before the seal
    localparam [63:0] SEAL = 64'h514b5644_43464731;
    generate if (NRST < 1 || NW + 1 > 256) begin : g_bad
        initial $fatal(1, "qkd_kv_die_cfg: NRST %0d CAP %0d", NRST, CAP);
    end endgenerate
    // POR: two-flop synchronised release (async assert), as qkd_rst_region
    reg [1:0] ps;
    always @(posedge ck or negedge por_n) if (!por_n) ps <= 2'b00; else ps <= {ps[0], 1'b1};
    wire pr_n = ps[1];
    generate if (PCOPIES > 1) begin : g_pc
        (* keep *) reg [PCOPIES-2:0] pc_q;
        always @(posedge ck or negedge por_n) if (!por_n) pc_q <= {(PCOPIES-1){1'b0}}; else pc_q <= {(PCOPIES-1){ps[0]}};
        (* keep, ot_rst_split *) wire [PCOPIES-1:0] prv = {pc_q, ps[1]};
    end endgenerate
    // write port pin registers
    reg we_q; reg [7:0] a_q; reg [63:0] d_q;
    always @(posedge ck or negedge pr_n) if (!pr_n) we_q <= 1'b0; else we_q <= cfg_we;
    always @(posedge ck) begin a_q <= cfg_addr; d_q <= cfg_data; end
    reg [8:0] next;
    wire is_ectl = a_q < 8'd32;
    wire is_rst  = !is_ectl && a_q < 8'(32 + NRST);
    wire is_cap  = (CAP != 0) && a_q == 8'(32 + NRST);
    wire is_seal = a_q == NW[7:0];
    reg  cap_q;
    wire [7:0] r_ix = a_q - 8'd32 + ((MUT == 3) ? 8'd1 : 8'd0);
    wire bad = sealed || ({1'b0, a_q} != next) ||
               (MUT != 2 && ((is_ectl && d_q[63:15] != 0) || (is_rst && d_q[63:8] != 0) || (is_cap && d_q[63:1] != 0))) ||
               (is_seal && (d_q != SEAL || next != NW[8:0])) || (!is_ectl && !is_rst && !is_cap && !is_seal);
    integer i;
    always @(posedge ck or negedge pr_n) begin
        if (!pr_n) begin
            ectl_a_cfg <= 0; ectl_b_cfg <= 0; ectl_c_cfg <= 0; rst_dly <= 0; cap_q <= 1'b0;
            sealed <= 1'b0; fault <= 1'b0; next <= 9'd0;
        end else if (we_q) begin
            if (bad || fault) fault <= 1'b1;
            else begin
                next <= next + 9'd1;
                if (is_ectl) begin
                    ectl_a_cfg[5*a_q[4:0] +: 5] <= d_q[4:0];
                    ectl_b_cfg[5*a_q[4:0] +: 5] <= (MUT == 1) ? d_q[14:10] : d_q[9:5];
                    ectl_c_cfg[5*a_q[4:0] +: 5] <= (MUT == 1) ? d_q[9:5] : d_q[14:10];
                end
                if (is_rst && r_ix < NRST) rst_dly[8*r_ix +: 8] <= d_q[7:0];
                if (is_cap) cap_q <= (MUT == 4) ? d_q[1] : d_q[0];
                if (is_seal) sealed <= 1'b1;
            end
        end
    end
    assign fused_program_capability = cap_q && ((MUT == 5) || sealed);
endmodule
