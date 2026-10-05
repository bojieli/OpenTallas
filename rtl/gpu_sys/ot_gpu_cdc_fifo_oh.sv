`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_gpu_cdc_fifo_oh: successor of ot_gpu_cdc_fifo (1.2 GHz closure, noc family, 2026-10-04) with the SAME ports,
// behaviour and cycle timing.  The storage and Gray-pointer logic are ot_link_afifo's, line for line
// (ot_link_afifo_oh below; rtl/link/ot_link_afifo.sv is not modified); the only change is how the read data is
// selected.  ot_link_afifo reads rdata = mem[rbin[AW-1:0]]: one binary pointer register fans out to every bit of
// the W-bit 2^AW:1 multiplexer (W = 273..546 here), which the routed mreq CDC showed as a 3-deep buffer tree in
// front of the mux (SS output path -110.75 ps at 0.833 ns).  Here the read side also keeps the one-hot form of
// rbin[AW-1:0], replicated RDUP times as separate keep_hierarchy registers, each copy selecting one W/RDUP-bit
// slice with an AND-OR mux.  The one-hot copy advances on exactly the read handshakes that advance rbin, so
// rdata is bit-identical every cycle.  Zero added cycles.
// ENABLE = 0 (default): inert, every output 0.
// ---------------------------------------------------------------------------
module ot_gpu_cdc_fifo_oh #(
    parameter integer ENABLE = 0,
    parameter integer W      = 64,
    parameter integer AW     = 3,
    parameter integer SYNC   = 2,
    parameter integer RDUP   = 8,
    parameter integer WDUP   = 0      // > 0: replicated look-ahead write enables (see ot_link_afifo_oh)
) (
    input  wire         wclk,
    input  wire         wrst_n,
    input  wire         in_v,
    output wire         in_rdy,
    input  wire [W-1:0] in_d,
    input  wire         rclk,
    input  wire         rrst_n,
    output wire         out_v,
    input  wire         out_rdy,
    output wire [W-1:0] out_d,
    output wire         ovf_fault
);
    generate if (ENABLE != 0) begin : g_on
        wire wfull, rempty, ovf;
        /* verilator lint_off UNUSEDSIGNAL */
        wire [AW:0] wfreed, rcount;
        /* verilator lint_on UNUSEDSIGNAL */
        ot_link_afifo_oh #(.W(W), .AW(AW), .SYNC(SYNC), .RDUP(RDUP), .WDUP(WDUP)) u_fifo (
            .wclk(wclk), .wrst_n(wrst_n), .wr(in_v && !wfull), .wdata(in_d), .wfull(wfull), .wfreed(wfreed),
            .ovf(ovf), .rclk(rclk), .rrst_n(rrst_n), .rd(out_v && out_rdy), .rempty(rempty), .rdata(out_d),
            .rcount(rcount));
        assign in_rdy = !wfull;
        assign out_v = !rempty;
        assign ovf_fault = ovf;
    end else begin : g_off
        assign in_rdy = 1'b0;
        assign out_v = 1'b0;
        assign out_d = {W{1'b0}};
        assign ovf_fault = 1'b0;
    end endgenerate
endmodule

// ot_link_afifo with a replicated one-hot read select (see above).  Everything but rdata is ot_link_afifo's text.
module ot_link_afifo_oh #(
    parameter integer W    = 64,
    parameter integer AW   = 4,
    parameter integer SYNC = 2,
    parameter integer RDUP = 8,
    parameter integer WDUP = 0
) (
    input  wire          wclk,
    input  wire          wrst_n,
    input  wire          wr,
    input  wire [W-1:0]  wdata,
    output wire          wfull,
    output reg  [AW:0]   wfreed,
    output reg           ovf,
    input  wire          rclk,
    input  wire          rrst_n,
    input  wire          rd,
    output wire          rempty,
    output wire [W-1:0]  rdata,
    output wire [AW:0]   rcount
);
    localparam integer D = 1 << AW;
    localparam integer SW = (W + RDUP - 1) / RDUP;          // slice width
    reg [W-1:0] mem [0:D-1];

    function automatic [AW:0] g2b(input [AW:0] g);
        integer k;
        begin
            g2b[AW] = g[AW];
            for (k = AW - 1; k >= 0; k = k - 1) g2b[k] = g2b[k+1] ^ g[k];
        end
    endfunction

    reg  [AW:0] wbin, wgray, rbin_seen;
    reg  [AW:0] rgray_s [0:SYNC-1];
    wire [AW:0] rgray_w = rgray_s[SYNC-1];
    wire [AW:0] wbin_n = wbin + 1'b1;
    wire [AW:0] wgray_n = wbin_n ^ (wbin_n >> 1);
    assign wfull = (wgray == {~rgray_w[AW:AW-1], rgray_w[AW-2:0]});
    wire        push = wr && !wfull;
    wire [AW:0] rbin_w = g2b(rgray_w);
    integer i;
    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin
            wbin <= 0; wgray <= 0; ovf <= 1'b0; rbin_seen <= 0; wfreed <= 0;
            for (i = 0; i < SYNC; i = i + 1) rgray_s[i] <= 0;
        end else begin
            rgray_s[0] <= rgray;
            for (i = 1; i < SYNC; i = i + 1) rgray_s[i] <= rgray_s[i-1];
            wfreed <= rbin_w - rbin_seen;
            rbin_seen <= rbin_w;
            if (wr && wfull) ovf <= 1'b1;
            if (push) begin
                wbin <= wbin_n; wgray <= wgray_n;
            end
        end
    end
    generate if (WDUP == 0) begin : g_wr
        always @(posedge wclk) if (push) mem[wbin[AW-1:0]] <= wdata;
    end else begin : g_wrdup
        // WDUP slices: slot wbin is not visible to the reader until wbin advances, so while the FIFO is not full
        // it is written EVERY cycle (the last write before the push is the pushed record); the enable is !wfull
        // rebuilt per slice from registered look-ahead compares, and the slot select is a registered one-hot.
        // Only the contents of unpublished slots differ from ot_link_afifo, i.e. rdata while rempty.
        localparam integer WS = (W + WDUP - 1) / WDUP;
        wire [AW:0] rnext = rgray_s[SYNC-2];
        wire        c0_n = (wgray   == {~rnext[AW:AW-1], rnext[AW-2:0]});
        wire        c1_n = (wgray_n == {~rnext[AW:AW-1], rnext[AW-2:0]});
        wire [D-1:0] woh_n = {{(D-1){1'b0}}, 1'b1} << (push ? wbin_n[AW-1:0] : wbin[AW-1:0]);
        genvar ws;
        for (ws = 0; ws < WDUP; ws = ws + 1) begin : g_ws
            localparam integer LO = ws * WS;
            localparam integer HI = ((ws + 1) * WS > W) ? W : (ws + 1) * WS;
            if (LO < W) begin : g_on
                wire [2:0]   f_q;
                wire [D-1:0] woh;
                ot_gpu_kreg_oh #(.W(3), .RV(3'b000)) u_f (.clk(wclk), .rst_n(wrst_n), .d({push, c1_n, c0_n}), .q(f_q));
                ot_gpu_kreg_oh #(.W(D), .RV({{(D-1){1'b0}}, 1'b1})) u_w (.clk(wclk), .rst_n(wrst_n), .d(woh_n), .q(woh));
                wire full_c = f_q[2] ? f_q[1] : f_q[0];
                integer e;
                always @(posedge wclk)
                    for (e = 0; e < D; e = e + 1) if (!full_c && woh[e]) mem[e][HI-1:LO] <= wdata[HI-1:LO];
                // synopsys translate_off
                always @(posedge wclk) if (wrst_n && (full_c !== wfull || woh !== ({{(D-1){1'b0}}, 1'b1} << wbin[AW-1:0])))
                    $error("ot_link_afifo_oh: write look-ahead diverged");
                // synopsys translate_on
            end
        end
    end endgenerate

    reg  [AW:0] rbin, rgray;
    reg  [AW:0] wgray_s [0:SYNC-1];
    wire [AW:0] wgray_r = wgray_s[SYNC-1];
    assign rempty = (rgray == wgray_r);
    assign rcount = g2b(wgray_r) - rbin;
    wire [AW:0] rbin_n = rbin + 1'b1;
    wire        radv = rd && !rempty;
    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin
            rbin <= 0; rgray <= 0;
            for (i = 0; i < SYNC; i = i + 1) wgray_s[i] <= 0;
        end else begin
            wgray_s[0] <= wgray;
            for (i = 1; i < SYNC; i = i + 1) wgray_s[i] <= wgray_s[i-1];
            if (radv) begin
                rbin <= rbin_n; rgray <= rbin_n ^ (rbin_n >> 1);
            end
        end
    end
    // one-hot read select = onehot(rbin[AW-1:0]), RDUP keep_hierarchy copies, one per data slice
    wire [D-1:0] oh_cur = {{(D-1){1'b0}}, 1'b1} << rbin[AW-1:0];
    genvar c;
    generate for (c = 0; c < RDUP; c = c + 1) begin : g_sl
        localparam integer LO = c * SW;
        localparam integer HI = ((c + 1) * SW > W) ? W : (c + 1) * SW;
        if (LO < W) begin : g_on
            wire [D-1:0] oh_q;
            wire [D-1:0] oh_d = radv ? {oh_q[D-2:0], oh_q[D-1]} : oh_q;
            ot_gpu_kreg_oh #(.W(D), .RV({{(D-1){1'b0}}, 1'b1})) u_sel (.clk(rclk), .rst_n(rrst_n), .d(oh_d), .q(oh_q));
            reg [HI-LO-1:0] s;
            integer m;
            always @* begin
                s = '0;
                for (m = 0; m < D; m = m + 1) s = s | ({(HI-LO){oh_q[m]}} & mem[m][HI-1:LO]);
            end
            assign rdata[HI-1:LO] = s;
            // simulation-only invariant: the copy is the one-hot of rbin
            // synopsys translate_off
            always @(posedge rclk) if (rrst_n && oh_q !== oh_cur)
                $error("ot_link_afifo_oh: one-hot read select diverged from rbin");
            // synopsys translate_on
        end
    end endgenerate
endmodule

// A W-bit register Yosys keeps as its own instance (opt_merge merges identical flip-flops even under (* keep *);
// a keep_hierarchy instance is never merged): the replicated select copies stay separate cells.
(* keep_hierarchy *)
module ot_gpu_kreg_oh #(
    parameter integer W = 1,
    parameter [W-1:0] RV = '0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= RV; else q <= d;
endmodule
