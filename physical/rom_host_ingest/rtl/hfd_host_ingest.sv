`timescale 1ns/1ps
// hfd_host_ingest (stream ingest 2026-10-08, coverage T3): the HBM accelerator die's GPU-prefill KV-ingest master =
// ot_rom_host_ingest (QKV_EN 0, RMW_EN 0: ROWS for window / compressed rows, RAW for packed index keys) + ot_hbm_ingest_xlat
// (linear ingest sectors -> the DS-V4.1 decode KV layout of ot_hbm_accel_dskv_wb, on the stack write-request port format
// wq_*).  The wq_* port shares the die's HBM write fabric with the per-token write-back (decode first) and the loader
// (mtp-die wiring); eop_v / eop_d carry the BOOT_END marker (loader boot check).  Clocks as ot_rom_host_ingest.
// COMPLETION FENCE (reviewer 2026-10-08, required before adoption): a descriptor's completion word (it carries the
// engine's cumulative sector count at done) is held in the die domain until the write fabric has ACKed that many posted
// ingest writes (ack_n: ACKs returned this ck cycle by the per-stack write merge); only then does it go to the host and
// pulse slot_done_v / slot_done_tag (ck) for the decode scheduler, so decode can never read a slot whose writes are still
// in flight.  Fault words pass at once.  FENCE 0 (bench mutant, must FAIL) releases completions without waiting.
module hfd_host_ingest #(parameter integer IQ = 4, parameter integer FENCE = 1,
    parameter integer HCUT = `ifdef OT_HING_HCUT 1 `else 0 `endif,
    // sys-takeover 2026-10-09: engine options (ot_rom_host_ingest ENG_TRIM / APIPE), opt-in
    parameter integer ENG_TRIM = `ifdef OT_HING_ETRIM 1 `else 0 `endif,
    parameter integer APIPE = `ifdef OT_HING_APIPE2 2 `elsif OT_HING_APIPE 1 `else 0 `endif,
    // RPIPE (sys-takeover 2026-10-09, with HCUT; hing_pipe_a TT -290: hk_d -> acked >= hk_d compare -> rel -> u_ca read
    // pointer / u_cb write / hk_d reload, 36-37 levels): the release condition of the held head is a REGISTER (hr_q),
    // recomputed every edge and cleared whenever the head is consumed or reloaded (acked only grows: never early).
    // +1 ck edge per completion word.
    // RPIPE 2 (redesign-ds 2026-10-09; hing_pipec_a/b-18f1b50d4 TT -114: acked[0] -> 32-bit acked >= hk_d compare,
    // re-rippled by ABC into 26 MAJ levels -> hr_q): the fence compare is split into registered 16-bit partials
    // (hi >, hi ==, lo >=) and the ACK counter into two 16-bit halves whose carry is applied one edge late.  Both only
    // UNDER-estimate acked (it only grows), so a release is never early; a partial is used only while hk_d has been
    // stable for an edge (cmp_ok).  +1 ck edge per done word on top of RPIPE 1 (fault / non-done words unchanged).
    parameter integer RPIPE = `ifdef OT_HING_RPIPE2 2 `elsif OT_HING_RPIPE 1 `else 0 `endif) (
    input  wire          rst_n,
    input  wire          clk_h,
    input  wire          h_v,
    input  wire [1:0]    h_cls,
    input  wire [511:0]  h_d,
    output wire [4:0]    h_crn,
    output wire          t_v,
    output wire [63:0]   t_d,
    input  wire          t_cr,
    input  wire          clk_i,
    input  wire          ck,
    output wire          wq_v,
    output wire [1:0]    wq_stack,
    output wire [4:0]    wq_pc,
    output wire [4:0]    wq_bank,
    output wire [18:0]   wq_row,
    output wire [4:0]    wq_col,
    output wire [255:0]  wq_data,
    input  wire          wq_r,
    input  wire [5:0]    ack_n,
    output reg           slot_done_v,
    output reg  [7:0]    slot_done_tag,
    output wire          eop_v,
    output wire [63:0]   eop_d,
    output wire          fault
);
    wire o_v, o_we, o_cr, f_hi, f_x;
    wire u_tv, u_tcr;
    wire [63:0] u_td;
    wire [31:0] o_addr;
    wire [255:0] o_d;
    wire rn_c;
    ot_reset_sync u_rs (.clk(ck), .async_rst_n(rst_n), .sync_rst_n(rn_c));
    ot_rom_host_ingest #(.KVHMAX(1), .HDMAX(16), .QKV_EN(0), .RMW_EN(0), .OCRED(IQ), .ENG_TRIM(ENG_TRIM), .APIPE(APIPE)) u_hi (
        .rst_n(rst_n), .clk_h(clk_h), .h_v(h_v), .h_cls(h_cls), .h_d(h_d), .h_crn(h_crn), .t_v(u_tv), .t_d(u_td),
        .t_cr(u_tcr), .clk_i(clk_i), .ck(ck), .o_v(o_v), .o_we(o_we), .o_addr(o_addr), .o_d(o_d), .o_cr(o_cr),
        .i_rv(1'b0), .i_rd(256'd0), .fault(f_hi));
    ot_hbm_ingest_xlat #(.IQ(IQ)) u_x (
        .ck(ck), .rst_n(rn_c), .o_v(o_v), .o_we(o_we), .o_addr(o_addr), .o_d(o_d), .o_cr(o_cr),
        .wq_v(wq_v), .wq_stack(wq_stack), .wq_pc(wq_pc), .wq_bank(wq_bank), .wq_row(wq_row), .wq_col(wq_col),
        .wq_data(wq_data), .wq_r(wq_r), .eop_v(eop_v), .eop_d(eop_d), .fault(f_x));
    assign fault = f_hi | f_x;

    // ---- completion fence ---------------------------------------------------------------------------------------
    wire rn_h;
    ot_reset_sync u_rsh (.clk(clk_h), .async_rst_n(rst_n), .sync_rst_n(rn_h));
    // clk_h -> ck: the block's completion words (credit to the block: one per word the die side pops)
    wire       a_full, a_empty, a_ovf; wire [3:0] a_freed, a_cnt; wire [63:0] a_head;
    reg        a_pop;
    ot_link_afifo #(.W(64), .AW(3)) u_ca (.wclk(clk_h), .wrst_n(rn_h), .wr(u_tv), .wdata(u_td), .wfull(a_full),
        .wfreed(a_freed), .ovf(a_ovf), .rclk(ck), .rrst_n(rn_c), .rd(a_pop), .rempty(a_empty), .rdata(a_head), .rcount(a_cnt));
    reg [4:0] ucr_pend;
    reg       ucr_q;
    always @(posedge clk_h or negedge rn_h)
        if (!rn_h) begin ucr_pend <= 0; ucr_q <= 1'b0; end
        else begin ucr_q <= ucr_pend != 0; ucr_pend <= ucr_pend + a_freed - (ucr_pend != 0 ? 5'd1 : 5'd0); end
    assign u_tcr = ucr_q;
    // ck: ACK count, release when acked >= the word's sector count (fault words at once)
    // struct-close 2026-10-09 (HCUT, drive-0849: hfd_host_ingest f5-lvt EF -404 / -467 = u_ca.rbin -> the u_ca read mux ->
    // fence compare -> u_cb.mem write, 1,159 ps cell, fanout 15): HCUT = 1 moves the u_ca head into a REGISTER (hk_v / hk_d,
    // refilled from u_ca when empty or released) and the fence / release / u_cb write work from it.  +1 ck edge per word;
    // order, fence and credits unchanged (h is one extra slot, never more words in flight than the host credited).
    reg  [31:0] acked;
    wire        b_full;
    reg         hk_v; reg [63:0] hk_d;
    wire [63:0] r_head = (HCUT != 0) ? hk_d : a_head;
    wire        is_done = r_head[63:56] == 8'h01;
    reg         hr_q;
`ifndef OT_HING_MUT_HCUT_NOFENCE
    wire        rel = (RPIPE != 0) ? (hk_v && hr_q && !b_full) :
                      ((HCUT != 0) ? hk_v : !a_empty) && !b_full && (!is_done || FENCE == 0 || acked >= r_head[31:0]);
`else
    wire        rel = ((HCUT != 0) ? hk_v : !a_empty) && !b_full;   // mutant: the fence is skipped on the head register
`endif
    always @(*) a_pop = (HCUT != 0) ? (!a_empty && (!hk_v || rel)) : rel;
    always @(posedge ck or negedge rn_c)
        if (!rn_c) hk_v <= 1'b0;
        else if (HCUT != 0) begin if (a_pop) hk_v <= 1'b1; else if (rel) hk_v <= 1'b0; end
    always @(posedge ck) if (HCUT != 0 && a_pop) hk_d <= a_head;
    // RPIPE 2: split ACK counter + registered compare partials (see the parameter note)
    reg  [15:0] ack_lo, ack_hi; reg ack_c;
    reg         p_gt, p_eq, p_ge, cmp_ok;
    wire [16:0] ack_lo_n = {1'b0, ack_lo} + {11'd0, ack_n};
    always @(posedge ck or negedge rn_c)
        if (!rn_c) begin ack_lo <= 16'd0; ack_hi <= 16'd0; ack_c <= 1'b0; cmp_ok <= 1'b0; end
        else begin
            ack_lo <= ack_lo_n[15:0]; ack_c <= ack_lo_n[16]; ack_hi <= ack_hi + {15'd0, ack_c};
`ifdef OT_HING_MUT_RP2STALE
            cmp_ok <= hk_v;                                                   // mutant: partials of the previous head used
`else
            cmp_ok <= hk_v && !rel && !a_pop;
`endif
        end
    always @(posedge ck) begin
        p_gt <= ack_hi > hk_d[31:16]; p_eq <= ack_hi == hk_d[31:16]; p_ge <= ack_lo >= hk_d[15:0];
    end
    wire        ge2 = cmp_ok && (p_gt || (p_eq && p_ge));
    always @(posedge ck or negedge rn_c)
        if (!rn_c) hr_q <= 1'b0;
        else if (RPIPE == 2) hr_q <= hk_v && !rel && !a_pop && (!is_done || FENCE == 0 || ge2);
`ifdef OT_HING_MUT_RPSTALE
        else hr_q <= hk_v && (!is_done || FENCE == 0 || acked >= hk_d[31:0]);                    // mutant: not cleared
`else
        else hr_q <= hk_v && !rel && !a_pop && (!is_done || FENCE == 0 || acked >= hk_d[31:0]);
`endif
    always @(posedge ck or negedge rn_c)
        if (!rn_c) begin acked <= 0; slot_done_v <= 1'b0; slot_done_tag <= 0; end
        else begin
            acked <= acked + ack_n;
            slot_done_v <= rel && is_done;
            if (rel && is_done) slot_done_tag <= r_head[47:40];
        end
    // ck -> clk_h: released words to the host (host credits TCRED 4, pin flops)
    wire       b_empty, b_ovf; wire [3:0] b_freed, b_cnt; wire [63:0] b_head;
    reg  [2:0] hcr; reg hcr_q; reg tv_q; reg [63:0] td_q;
    wire       b_pop = !b_empty && hcr != 0;
    ot_link_afifo #(.W(64), .AW(3)) u_cb (.wclk(ck), .wrst_n(rn_c), .wr(rel), .wdata(r_head), .wfull(b_full),
        .wfreed(b_freed), .ovf(b_ovf), .rclk(clk_h), .rrst_n(rn_h), .rd(b_pop), .rempty(b_empty), .rdata(b_head), .rcount(b_cnt));
    always @(posedge clk_h or negedge rn_h)
        if (!rn_h) begin hcr <= 3'd4; hcr_q <= 1'b0; tv_q <= 1'b0; td_q <= 0; end
        else begin
            hcr_q <= t_cr;
            hcr <= hcr + (hcr_q ? 3'd1 : 3'd0) - (b_pop ? 3'd1 : 3'd0);
            tv_q <= b_pop;
            if (b_pop) td_q <= b_head;
        end
    assign t_v = tv_q;
    assign t_d = td_q;
endmodule
