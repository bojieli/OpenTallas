`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_wfc_vmx: the WFC's vector-memory and core-endpoint transport across the related 1.2 / 0.9 GHz (3:4)
// boundary (stream mtp-rom, 2026-10-08; WFC integration bindings 1 "vm_*" and 3 "core_*" of 4).
//
// Why one block for two bindings: on the S81 die the WFC runs in the 1.2 GHz streaming domain and the stage's VM
// (sp_vm) and stage core run at 0.9 GHz.  The WFC writes the last payload word of a job and raises core_start on
// the SAME edge, and reads the outbound payload right after core_done: so a start may not overtake the payload
// writes and a done may not overtake the outbound payload.  Both orders are kept by sending each through the
// same in-order crossing as the data it must follow:
//   fast -> slow  one ratio FIFO (ot_ratio_cdc_fifo) carries {WRITE addr data} and {START user token pos} in WFC
//                 order; the slow side issues the writes to the VM (valid / ready, write ACK) and raises k_start
//                 only once every earlier write is ACKed (VM visible);
//   slow -> fast  on k_done the slow side reads the outbound words (TXB .. TXB+XWORDS-1, SIDE_TXB ..
//                 +SIDE_WORDS-1) from the VM (valid / ready, in-order responses) and sends {DATA idx word} then
//                 {DONE token val} through a second ratio FIFO; the fast side writes the words into a staging
//                 buffer and raises core_done (a level, dropped on core_start, as the WFC's core contract) only
//                 after the last word.  The WFC's fixed one-edge read (VM_REG) is served from the staging buffer.
// Write flow control: the WFC's VM writes cannot be stalled, so ot_dsrom_wfc_lnk forwards a payload flit (one
// write each) only against a credit; a credit returns (vc_ret) when its write has been issued to the VM.
// Capacity check: VCRED <= PRE + DEPTH - 1 (a START needs one slot beyond the writes).
// Cycles (bench): start = WFC start -> k_start; done = k_done -> WFC done (XWORDS + SIDE_WORDS slow reads +
// the crossing), both charged per stage hop.  The crossings are flop -> flop at the 278 ps VCO window (the
// ratio FIFO's contract; no synchroniser, no exception).
// Mutants: OT_WFCVMX_MUT_STARTEARLY (k_start without waiting for the write ACKs),
//          OT_WFCVMX_MUT_DONEEARLY (core_done before the staging buffer is complete).
// ---------------------------------------------------------------------------
module ot_dsrom_wfc_vmx #(
    parameter integer FLIT   = 512,
    parameter integer NW     = 21,
    parameter integer USER_W = 10,
    parameter integer VWA    = 15,
    parameter integer TXB    = 0,
    parameter integer XWORDS = 41,
    parameter integer SIDE_TXB   = 0,
    parameter integer SIDE_WORDS = 0,
    parameter integer DEPTH  = 8,       // fast -> slow ratio FIFO entries
    parameter integer PRE    = 4,       // fast-side pre-queue (two pushes a cycle: last write + start)
    parameter integer RQ     = 16,       // slow-side read-response queue
    parameter integer RDEPTH = 8,       // slow -> fast ratio FIFO entries
    parameter integer RQFREE = `ifdef OT_WFCVMX_PRED 2 `elsif OT_WFCVMX_RQ_FREE 1 `else 0 `endif,   // struct-close: vm_rq without the vm_re enable
    parameter integer LAG    = 0        // ot_ratio_cdc_fifo LAG on both crossings (route variant: mem -> shadow arcs become
                                        // a max-delay write-period path with no hold check; +1 write cycle each way)
) (
    // ---- fast (WFC) domain
    input  wire              fclk,
    input  wire              frst_n,            // synchronous to fclk
    input  wire              vm_we,
    input  wire [VWA-1:0]    vm_waddr,
    input  wire [FLIT-1:0]   vm_wdata,
    input  wire              vm_re,
    input  wire [VWA-1:0]    vm_raddr,
    output reg  [FLIT-1:0]   vm_rq,
    input  wire              core_start,
    input  wire [NW-1:0]     core_token,
    input  wire [NW-1:0]     core_pos,
    input  wire [USER_W-1:0] core_user,
    output reg               core_done,
    output reg  [NW-1:0]     core_next_token,
    output reg  [31:0]       core_next_val,
    output reg               vc_ret,
    // ---- slow (VM / core) domain
    input  wire              sclk,
    input  wire              srst_n,            // synchronous to sclk
    output wire              sw_valid,
    input  wire              sw_ready,
    output wire [VWA-1:0]    sw_addr,
    output wire [FLIT-1:0]   sw_data,
    input  wire              sw_ack,            // one pulse per completed (visible) write, in order
    output wire              sr_valid,
    input  wire              sr_ready,
    output wire [VWA-1:0]    sr_addr,
    input  wire              sr_rv,             // read response, in order
    input  wire [FLIT-1:0]   sr_rq,
    output reg               k_start,
    output reg  [USER_W-1:0] k_user,
    output reg  [NW-1:0]     k_token,
    output reg  [NW-1:0]     k_pos,
    input  wire              k_done,
    input  wire [NW-1:0]     k_next_token,
    input  wire [31:0]       k_next_val,
    output reg               fault
);
    localparam integer SD = XWORDS + SIDE_WORDS;
    localparam integer IB = $clog2(SD + 1);
    localparam integer SP = USER_W + 2 * NW;
    localparam integer PW = 1 + ((VWA + FLIT > SP) ? VWA + FLIT : SP);
    localparam integer RW = 1 + ((IB + FLIT > NW + 32) ? IB + FLIT : NW + 32);
    localparam integer PB = $clog2(PRE);
    initial if (PRE < 2 || (PRE & (PRE - 1)) != 0 || RQ < 2 || (RQ & (RQ - 1)) != 0)
        $fatal(1, "ot_dsrom_wfc_vmx: PRE and RQ powers of two >= 2");

    // =========================================================== fast domain
    // pin flops on the WFC's write / start outputs (+1 cycle; the read port keeps the WFC's one-edge timing)
    reg pw_v, ps_v; reg [VWA-1:0] pw_a; reg [FLIT-1:0] pw_d; reg [SP-1:0] ps_d;
    always @(posedge fclk) begin
        pw_v <= vm_we && frst_n; pw_a <= vm_waddr; pw_d <= vm_wdata;
        ps_v <= core_start && frst_n; ps_d <= {core_user, core_token, core_pos};
    end
    // pre-queue: up to two pushes a cycle (write first, then start), one pop into the ratio FIFO
    reg [PW-1:0] pq [0:PRE-1]; reg [PB:0] pq_n; reg [PB-1:0] pq_r, pq_w;
    wire f_wv, f_wr; wire [PW-1:0] f_wd = pq[pq_r];
    assign f_wv = pq_n != 0;
    wire pq_pop = f_wv && f_wr;
    wire [1:0] npush = {1'b0, pw_v} + {1'b0, ps_v};
    always @(posedge fclk) begin
        if (!frst_n) begin pq_n <= 0; pq_r <= 0; pq_w <= 0; end
        else begin
            if (pw_v) pq[pq_w] <= PW'({pw_a, pw_d});                          // kind 0 (MSB) = write
            if (ps_v) pq[pw_v ? pq_w + 1'b1 : pq_w] <= PW'(ps_d) | (PW'(1) << (PW - 1));   // kind 1 = start
            pq_w <= pq_w + npush;
            if (pq_pop) pq_r <= pq_r + 1'b1;
            pq_n <= pq_n + npush - (pq_pop ? 1'b1 : 1'b0);
        end
    end
    // core_done: a level; dropped on the WFC's core_start (one gate from the pin), set by the DONE marker
    wire r_v; wire [RW-1:0] r_d;
    wire r_done = r_v && r_d[RW-1];
    localparam integer SDP = 1 << IB;              // staging entries rounded to a power of two (every index in range)
    reg [SDP-1:0] got;                             // staging words written since the last start
    reg [FLIT-1:0] stg [0:SDP-1];
    reg fault_f;
    always @(posedge fclk) begin
        if (!frst_n) begin core_done <= 1'b0; got <= 0; fault_f <= 1'b0; end
        else begin
            if (core_start) begin core_done <= 1'b0; got <= 0; end
            if (r_v && !r_d[RW-1]) begin
                stg[r_d[FLIT +: IB]] <= r_d[FLIT-1:0];
                got[r_d[FLIT +: IB]] <= 1'b1;
            end
            if (r_done) begin
                core_done <= 1'b1;
                core_next_token <= r_d[32 +: NW]; core_next_val <= r_d[31:0];
`ifndef OT_WFCVMX_MUT_DONEEARLY
                if (got[SD-1:0] != {SD{1'b1}}) fault_f <= 1'b1;
`endif
            end
            if (pq_n == PRE[PB:0] && npush != 0) fault_f <= 1'b1;      // credit / capacity violated
        end
    end
    // the WFC's synchronous read (one edge) from the staging buffer
    // (fixed one-edge read: with no SIDE region the staging index is the address minus a constant, no compare)
    wire [VWA-1:0] ra;
    generate if (SIDE_WORDS == 0) begin : g_ra_tx
        assign ra = vm_raddr - TXB[VWA-1:0];
    end else begin : g_ra_side
        wire [VWA-1:0] ra_tx = vm_raddr - TXB[VWA-1:0];
        wire [VWA-1:0] ra_sd = vm_raddr - SIDE_TXB[VWA-1:0] + XWORDS[VWA-1:0];
        assign ra = (ra_tx < XWORDS) ? ra_tx : ra_sd;
    end endgenerate
    // struct-close 2026-10-09 ("-cl" line).  RQFREE 1: the read register loads every edge (no vm_re enable; the WFC
    // samples vm_rq exactly one edge after vm_re, so other cycles are never observed).
    // RQFREE 2 (PREDICTED READ): the WFC reads the outbound words in staging order (TXB + tx_k, then the SIDE words,
    // one read per word per job), so the staging index of the next read is a counter: vm_rq <= stg[pred] every edge
    // (reg -> reg; no pin in the 64:1 x 512 data path, which failed at -488 ps from f_vr), pred advances on vm_re
    // and wraps after SD reads.  The pin address is checked one edge later (registered compare, 6 bits + the high
    // bits): a read whose index differs from pred raises the sticky fault (fail-closed, never silent).  0 cycles.
    // RQFREE 0 = the enabled register indexed from the pin.
    reg [IB-1:0] pred; reg pchk_v; reg [VWA-1:0] pchk_a; reg [IB-1:0] pchk_p; reg pfault;
    always @(posedge fclk) begin
        if (RQFREE == 2) vm_rq <= stg[pred];
        else if (vm_re || RQFREE != 0) vm_rq <= stg[ra[IB-1:0]];
        if (!frst_n) begin pred <= `ifdef OT_WFCVMX_MUT_PREDOFF 1 `else 0 `endif; pchk_v <= 1'b0; pfault <= 1'b0; end
        else begin
            if (vm_re) pred <= (pred == SD - 1) ? {IB{1'b0}} : pred + 1'b1;
            pchk_v <= vm_re && RQFREE == 2; pchk_a <= ra; pchk_p <= pred;
`ifndef OT_WFCVMX_MUT_NOPCHK
            if (pchk_v && pchk_a != {{(VWA-IB){1'b0}}, pchk_p}) pfault <= 1'b1;
`endif
        end
    end
    // credit return: the slow side's issued-write count, sampled flop -> flop
    reg [3:0] wcnt_s, wcnt_f, wcnt_seen;
    always @(posedge fclk) begin
        wcnt_f <= wcnt_s;
        if (!frst_n) begin wcnt_seen <= 0; vc_ret <= 1'b0; end
        else begin
            vc_ret <= wcnt_f != wcnt_seen;
            if (wcnt_f != wcnt_seen) wcnt_seen <= wcnt_seen + 1'b1;
        end
    end

    // =========================================================== the crossings
    wire s_v; wire [PW-1:0] s_d; wire s_rdy;
    ot_ratio_cdc_fifo #(.W(PW), .DEPTH(DEPTH), .LAG(LAG)) u_f2s (.wclk(fclk), .wrst_n(frst_n), .w_v(f_wv), .w_rdy(f_wr), .w_d(f_wd),
        .rclk(sclk), .rrst_n(srst_n), .r_v(s_v), .r_rdy(s_rdy), .r_d(s_d), .w_live(), .r_live());
    wire q_v; wire [RW-1:0] q_d; wire q_rdy;
    ot_ratio_cdc_fifo #(.W(RW), .DEPTH(RDEPTH), .LAG(LAG)) u_s2f (.wclk(sclk), .wrst_n(srst_n), .w_v(q_v), .w_rdy(q_rdy), .w_d(q_d),
        .rclk(fclk), .rrst_n(frst_n), .r_v(r_v), .r_rdy(1'b1), .r_d(r_d), .w_live(), .r_live());

    // =========================================================== slow domain
    // writes: issued in FIFO order; a START waits for every earlier write's ACK
    reg [4:0] wout;                                 // writes issued, not yet ACKed
    reg       busy;                                 // a job started, k_done not yet seen
    wire s_is_w = s_v && !s_d[PW-1];
    wire s_is_s = s_v && s_d[PW-1];
`ifdef OT_WFCVMX_MUT_STARTEARLY
    wire s_go = s_is_s && !busy && !k_start;
`else
    wire s_go = s_is_s && !busy && !k_start && wout == 0 && !sw_ack;
`endif
    assign sw_valid = s_is_w;
    assign sw_addr = s_d[FLIT +: VWA];
    assign sw_data = s_d[FLIT-1:0];
    wire sw_fire = sw_valid && sw_ready;
    assign s_rdy = sw_fire || s_go;
    // outbound prefetch after k_done
    reg pf; reg [IB-1:0] pf_i, pf_n; reg [NW-1:0] pf_tok; reg [31:0] pf_val; reg pf_dn;
    reg [RW-1:0] rq [0:RQ-1]; reg [$clog2(RQ):0] rq_n, r_out; reg [$clog2(RQ)-1:0] rq_r, rq_w;
    // read address: no compare when there is no SIDE region (the ORFS ABC flow asserts in &dch on the redundant
    // pf_i < XWORDS / pf_i < SD pair, aigDup.c:602; the issue-done state is a flop instead of a compare)
    reg pf_all;                                     // every outbound word's read issued
    wire [VWA-1:0] pf_a;
    generate if (SIDE_WORDS == 0) begin : g_pfa_tx
        assign pf_a = TXB[VWA-1:0] + pf_i;
    end else begin : g_pfa_side
        assign pf_a = (pf_i < XWORDS) ? TXB[VWA-1:0] + pf_i : SIDE_TXB[VWA-1:0] + (pf_i - XWORDS[IB-1:0]);
    end endgenerate
    assign sr_valid = pf && !pf_all && (rq_n + r_out) < RQ;
    assign sr_addr = pf_a;
    wire sr_fire = sr_valid && sr_ready;
    assign q_v = rq_n != 0;
    assign q_d = rq[rq_r];
    wire q_pop = q_v && q_rdy;
    reg fault_s;
    always @(posedge sclk) begin
        k_start <= 1'b0;
        if (!srst_n) begin
            wout <= 0; busy <= 1'b0; pf <= 1'b0; rq_n <= 0; r_out <= 0; rq_r <= 0; rq_w <= 0; wcnt_s <= 0;
            fault_s <= 1'b0; pf_dn <= 1'b0; pf_all <= 1'b1;
        end else begin
            wout <= wout + (sw_fire ? 1'b1 : 1'b0) - (sw_ack ? 1'b1 : 1'b0);
            if (sw_fire) wcnt_s <= wcnt_s + 1'b1;
            if (sw_ack && wout == 0) fault_s <= 1'b1;
            if (s_go) begin
                k_start <= 1'b1; busy <= 1'b1;
                {k_user, k_token, k_pos} <= s_d[SP-1:0];
            end
            if (k_done) begin
                if (!busy || pf) fault_s <= 1'b1;
                busy <= 1'b0; pf <= 1'b1; pf_i <= 0; pf_n <= 0; pf_tok <= k_next_token; pf_val <= k_next_val;
                pf_dn <= 1'b0; pf_all <= 1'b0;
            end
            if (sr_fire) begin pf_i <= pf_i + 1'b1; if (pf_i == SD - 1) pf_all <= 1'b1; end
            // response queue: data words in order, then the DONE marker
            begin : rqq
                reg push_d, push_m;
                push_d = sr_rv;
`ifdef OT_WFCVMX_MUT_DONEEARLY
                push_m = pf && !pf_dn && !sr_rv;                     // DONE before the outbound words
`else
                push_m = pf && !pf_dn && pf_n == SD && !sr_rv;
`endif
                if (sr_rv) begin
                    rq[rq_w] <= RW'({pf_n, sr_rq});                              // data word (MSB 0)
                    pf_n <= pf_n + 1'b1;
                end else if (push_m) begin
                    rq[rq_w] <= RW'({pf_tok, pf_val}) | (RW'(1) << (RW - 1));     // DONE marker (MSB 1)
                    pf_dn <= 1'b1;
                end
                if (pf && (pf_dn || push_m) && (sr_rv ? pf_n + 1'b1 : pf_n) == SD) pf <= 1'b0;
                if (push_d || push_m) rq_w <= rq_w + 1'b1;
                if (q_pop) rq_r <= rq_r + 1'b1;
                rq_n <= rq_n + ((push_d || push_m) ? 1'b1 : 1'b0) - (q_pop ? 1'b1 : 1'b0);
                r_out <= r_out + (sr_fire ? 1'b1 : 1'b0) - (sr_rv ? 1'b1 : 1'b0);
            end
        end
    end
    reg fs_f;
    always @(posedge fclk) begin fs_f <= fault_s; fault <= fault_f || fs_f || pfault; end
endmodule
