`timescale 1ns/1ps
// KV-BOOTAGE 2026-10-19 (coordinator decision, lanes/KVR-DERIVE.md "SPEC for the ONE later re-harden"): qkd_kv_die_cfg plus
// the STATIC-SCHEDULE AGE words (AGES=1).  Identical to rtl/qwen_sys/static_kv_20261014/qkd_kv_die_cfg.sv (kept byte-identical
// for the closed control tile) except NA = 19 age words between the capability word and the seal (AGES=1):
//   word A = 32 + NRST + CAP            attention tile: data[7:0] = PV_LEAD (attn root), data[15:8] = F_DLY (result face,
//                                       root END, cal gen R), data[23:16] = D_QK, data[31:24] = D_RL (cal gen)
//   words A + 1 + p, p = 0, 1           PV pair p control: data[7:0] = FIRST_INPUT_AGE
//   words A + 3 + i, i = 4 s + k        V port vport_<STACKS[s]>_<k>: data[7:0] = RT, data[15:8] = DQ
//   every other data bit must be 0; the seal moves to word A + 19.
// The values are the die's derived static schedule (kv_static_params.schedule on the post-station netlist), written by the
// compiler's boot image (kv_static_kvjf_join.die_cfg_image ages=...); the generator fails when an image value differs from
// the netlist-derived one.  Outputs are static after the seal and read 0 until it (an unloaded age is an invalid schedule
// in every consumer: RT 0 / FIRST_INPUT_AGE 0 / F_DLY 0 fault; PV_LEAD consumers are gated by the sealed capability).
// No handshake, credit or ready: configuration nets, POR-held across the functional re-reset (as the ECTL / reset words).
// MUT: 1-5 as qkd_kv_die_cfg; 6 = age words written one word off (vport i takes word i + 1); 7 = age outputs not gated
// by the seal.
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
module qkd_kv_die_cfg_a #(parameter integer NRST = 43, parameter integer CAP = 0, parameter integer AGES = 1, parameter integer MUT = 0) (
    input  wire               ck, por_n,
    input  wire               cfg_we, input wire [7:0] cfg_addr, input wire [63:0] cfg_data,
    output reg  [32*5-1:0]    ectl_a_cfg, ectl_b_cfg, ectl_c_cfg,
    output reg  [NRST*8-1:0]  rst_dly,
    output wire               fused_program_capability,
    output wire [31:0]        age_attn,         // {D_RL, D_QK, F_DLY, PV_LEAD}
    output wire [15:0]        age_pv,           // {pair 1, pair 0} FIRST_INPUT_AGE
    output wire [255:0]       age_vport,        // port i: [16 i +: 16] = {DQ, RT}
    output reg                sealed, fault
);
    localparam integer NA = (AGES != 0) ? 19 : 0;
    localparam integer A0 = 32 + NRST + ((CAP != 0) ? 1 : 0);   // first age word
    localparam integer NW = A0 + NA;                              // data words before the seal
    localparam [63:0] SEAL = 64'h514b5644_43464731;
    generate if (NRST < 1 || NW + 1 > 256) begin : g_bad
        initial $fatal(1, "qkd_kv_die_cfg: NRST %0d CAP %0d", NRST, CAP);
    end endgenerate
    // POR: two-flop synchronised release (async assert), as qkd_rst_region
    reg [1:0] ps;
    always @(posedge ck or negedge por_n) if (!por_n) ps <= 2'b00; else ps <= {ps[0], 1'b1};
    wire pr_n = ps[1];
    // write port pin registers
    reg we_q; reg [7:0] a_q; reg [63:0] d_q;
    always @(posedge ck or negedge pr_n) if (!pr_n) we_q <= 1'b0; else we_q <= cfg_we;
    always @(posedge ck) begin a_q <= cfg_addr; d_q <= cfg_data; end
    reg [8:0] next;
    wire is_ectl = a_q < 8'd32;
    wire is_rst  = !is_ectl && a_q < 8'(32 + NRST);
    wire is_cap  = (CAP != 0) && a_q == 8'(32 + NRST);
    wire is_age  = (AGES != 0) && a_q >= 8'(A0) && a_q < 8'(A0 + NA);
    wire [7:0] g_ix = a_q - 8'(A0) + ((MUT == 6) ? 8'd1 : 8'd0);
    wire is_seal = a_q == NW[7:0];
    wire age_pad = (g_ix == 8'd0) ? (d_q[63:32] != 0) : (g_ix == 8'd1 || g_ix == 8'd2) ? (d_q[63:8] != 0) : (d_q[63:16] != 0);
    reg  cap_q;
    reg [31:0] ag_attn; reg [15:0] ag_pv; reg [255:0] ag_vp;
    wire [7:0] r_ix = a_q - 8'd32 + ((MUT == 3) ? 8'd1 : 8'd0);
    wire bad = sealed || ({1'b0, a_q} != next) ||
               (MUT != 2 && ((is_ectl && d_q[63:15] != 0) || (is_rst && d_q[63:8] != 0) || (is_cap && d_q[63:1] != 0) || (is_age && age_pad))) ||
               (is_seal && (d_q != SEAL || next != NW[8:0])) || (!is_ectl && !is_rst && !is_cap && !is_age && !is_seal);
    integer i;
    always @(posedge ck or negedge pr_n) begin
        if (!pr_n) begin
            ectl_a_cfg <= 0; ectl_b_cfg <= 0; ectl_c_cfg <= 0; rst_dly <= 0; cap_q <= 1'b0;
            ag_attn <= 32'd0; ag_pv <= 16'd0; ag_vp <= 256'd0;
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
                if (is_age) begin
                    if (g_ix == 8'd0) ag_attn <= d_q[31:0];
                    else if (g_ix < 8'd3) ag_pv[8 * (g_ix - 8'd1) +: 8] <= d_q[7:0];
                    else if (g_ix < 8'd19) ag_vp[16 * (g_ix - 8'd3) +: 16] <= d_q[15:0];
                end
                if (is_seal) sealed <= 1'b1;
            end
        end
    end
    assign fused_program_capability = cap_q && ((MUT == 5) || sealed);
    wire ag_on = (MUT == 7) || sealed;
    assign age_attn = ag_on ? ag_attn : 32'd0;
    assign age_pv = ag_on ? ag_pv : 16'd0;
    assign age_vport = ag_on ? ag_vp : 256'd0;
endmodule
