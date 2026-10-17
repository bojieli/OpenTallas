`timescale 1ns/1ps
`default_nettype none
// =====================================================================================================================
// ot_hbm_sm_vm_wr_q_lanes (H-WRQ 2026-10-17): the STATIC SM result -> VM writer of ot_hbm_sm_vm_wr_q_faces4 with ONE
// CLOCK ROOT PER SM LANE.  Behaviour, timing contract, address contract, descriptor ABI, faults and MUT 1/2/3 are those of
// ot_hbm_sm_vm_wr_q_faces4 / ot_hbm_sm_vm_wr_q (see the header there); only the clock partition differs:
//   clk_l[k] clocks EVERYTHING of SM lane k: its W pin flops (rv/rrow/rdata/sm_fault/sm_sched_fault), its DEPTH-row FIFO,
//            its serial server (wp/rp/cnt/ps/acc/flt), its wq launch flops (o_* with one o_wr copy per wq data pin) and a lane
//            copy of the descriptor (d_*: same reset, same update on cv_q as the shared copy it replaces).
//   clk      the shared core: cmd pin register (cv_q/cmd_q), quad strap pin flop, cmd_fault, busy, fault, rst_q.
// Why (results/rtl/hsm_wrq_1017/DESIGN_NOTE.md): faces4 put the pin flops on face roots and the 8.6k FIFO flops on the
// core root, so every wide data path crossed clock entries (210 ps setup / 100 ps hold die-skew reserve each): f4hc TT
// -46.5 (rp -> o_w), ~32k hold buffers.  Here every wide path is inside one lane root; the only cross-entry signals are
// the quasi-static descriptor (core -> lane), quad_q (core -> o_sec) and the busy / fault OR terms (lane -> core).
// All roots are the same PLL output at phase 0 (benches tie them to one clock): zero edges added, rv(t) -> wq at t+3.
// =====================================================================================================================
module ot_hbm_sm_vm_wr_q_lanes #(
    parameter integer DEPTH = 4,
    parameter integer MUT   = 0      // 1 wrong row (stride ignored), 2 wrong phase (one edge late), 3 quad strap ignored
) (
    input  wire          clk,               // shared core root
    input  wire [7:0]    clk_l,             // lane k root (SM k)
    input  wire          rst_n,
    input  wire [1:0]    quad,
    input  wire [7:0]    rv,
    input  wire [95:0]   rrow,
    input  wire [2047:0] rdata,
    input  wire          cmd_v,
    input  wire [25:0]   cmd,
    input  wire [7:0]    sm_fault,
    input  wire [7:0]    sm_sched_fault,
    output wire [2247:0] wq,
    output reg           busy,
    output reg           fault
);
    initial if (DEPTH < 1 || DEPTH > 16) $fatal(1, "ot_hbm_sm_vm_wr_q_lanes: DEPTH 1..16");
    localparam integer AW = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    function automatic [31:0] rb(input [31:0] x, input en);     // to_bf16 (RNE) as a BF16-valued FP32 word
        reg [31:0] r;
        begin
            if (!en) rb = x;
            else if (x[30:23] == 8'hFF && x[22:0] != 0) rb = {x[31:16] | 16'h0040, 16'd0};
            else begin r = x + 32'h7FFF + {31'd0, x[16]}; rb = {r[31:16], 16'd0}; end
        end
    endfunction
    // ---------------- core: local reset release, cmd pin register, quad strap ----------------
    reg rst_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) rst_q <= 1'b0; else rst_q <= 1'b1;
    reg cv_q; reg [25:0] cmd_q; reg [1:0] quad_q;
    always @(posedge clk) begin cmd_q <= cmd; quad_q <= quad; end
    always @(posedge clk or negedge rst_q) if (!rst_q) cv_q <= 1'b0; else cv_q <= cmd_v;
    wire [7:0] rv_q, smf_q, sms_q, sm_busy, lane_fault;
    reg cmd_fault;
    always @(posedge clk or negedge rst_q)
        if (!rst_q) cmd_fault <= 1'b0;
        else if (cv_q && (busy || (|rv_q) || cmd_q[23:20] == 4'd0 || cmd_q[23:20] > 4'd8)) cmd_fault <= 1'b1;
    always @(posedge clk or negedge rst_q)
        if (!rst_q) begin busy <= 1'b0; fault <= 1'b0; end
        else begin busy <= |sm_busy || |rv_q; fault <= fault | cmd_fault | (|lane_fault) | (|smf_q) | (|sms_q); end
    // ---------------- lanes ----------------
    genvar k;
    generate for (k = 0; k < 8; k = k + 1) begin : g_sm
        wire lclk = clk_l[k];
        // pin flops (lane root)
        reg rv_r, smf_r, sms_r; reg [11:0] rrow_r; reg [255:0] rdata_r;
        always @(posedge lclk) begin rrow_r <= rrow[12*k +: 12]; rdata_r <= rdata[256*k +: 256]; end
        always @(posedge lclk or negedge rst_q)
            if (!rst_q) begin rv_r <= 1'b0; smf_r <= 1'b0; sms_r <= 1'b0; end
            else begin rv_r <= rv[k]; smf_r <= sm_fault[k]; sms_r <= sm_sched_fault[k]; end
        assign rv_q[k] = rv_r; assign smf_q[k] = smf_r; assign sms_q[k] = sms_r;
        // lane copy of the descriptor (identical update rule to the shared copy of ot_hbm_sm_vm_wr_q_faces4)
        reg d_v, d_fmt, d_mir; reg [3:0] d_p; reg [9:0] d_base, d_stride;
        always @(posedge lclk or negedge rst_q)
            if (!rst_q) begin d_v <= 1'b0; d_fmt <= 1'b0; d_mir <= 1'b0; d_p <= 4'd0; d_base <= 10'd0; d_stride <= 10'd0; end
            else if (cv_q) begin
                d_v <= 1'b1; d_base <= cmd_q[9:0]; d_stride <= cmd_q[19:10]; d_p <= cmd_q[23:20];
                d_mir <= cmd_q[24]; d_fmt <= cmd_q[25];
            end
        // serial server (unchanged logic)
        reg [267:0] fq [0:DEPTH-1];                 // {rrow12, rdata256}
        reg [AW-1:0] wp, rp; reg [AW:0] cnt;
        reg [3:0] ps; reg [10:0] acc;
        reg flt;
        // wq launch flops: o_wr = 8 kept copies of the slot word, one launch flop per replicated wq data pin (recipe 4 has no
        // pin_reg_split; physical/common_flow/ot_keep_regs.tcl keeps every bit of a (* keep *) register its own flop)
        reg o_v; reg [15:0] o_sec; reg [7:0] o_m;
        (* keep *) reg [255:0] o_wr;
        reg l_v; reg [15:0] l_sec; reg [255:0] l_wr; reg [7:0] l_m;   // MUT 2 late copy
        wire [267:0] hd = fq[rp];
        wire [11:0] hr = hd[267:256];
        wire [10:0] row = (ps == 4'd0 || MUT == 1) ? ({1'b0, d_base} + {2'b0, hr[11:3]}) : acc;
        wire push = rv_r;
        wire full = (cnt == DEPTH[AW:0]);
        wire emit = (cnt != 0);
        wire last = (ps + 4'd1 >= d_p);
        wire pop = emit && last;
        wire [31:0] col = hd[32*ps[2:0] +: 32];
        assign sm_busy[k] = emit || o_v;
        assign lane_fault[k] = flt;
        always @(posedge lclk or negedge rst_q)
            if (!rst_q) begin wp <= '0; rp <= '0; cnt <= '0; ps <= 4'd0; acc <= 11'd0; flt <= 1'b0; end
            else begin
                if (push && !d_v) flt <= 1'b1;
                if (push && full && !pop) flt <= 1'b1;
                else if (push) wp <= (wp == AW'(DEPTH-1)) ? '0 : wp + 1'b1;
                if (pop) rp <= (rp == AW'(DEPTH-1)) ? '0 : rp + 1'b1;
                cnt <= cnt + ((push && !(full && !pop)) ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
                if (emit) begin ps <= last ? 4'd0 : ps + 4'd1; acc <= row + {1'b0, d_stride}; end
                if (emit && row[10]) flt <= 1'b1;
            end
        always @(posedge lclk or negedge rst_q)
            if (!rst_q) begin o_v <= 1'b0; l_v <= 1'b0; end
            else begin o_v <= emit && !row[10]; l_v <= o_v; end
        always @(posedge lclk)
            if (push && !(full && !pop)) fq[wp] <= {rrow_r, rdata_r};
        always @(posedge lclk) begin
            o_sec <= {d_mir, d_mir ? 2'b00 : ((MUT == 3) ? 2'b00 : quad_q), row[9:0], 3'(k)};
            o_wr <= {8{rb(col, d_fmt)}};
            o_m <= 8'd1 << hr[2:0];
            l_sec <= o_sec; l_wr <= o_wr; l_m <= o_m;
        end
        if (MUT == 2) begin : g_late
            assign wq[k*281 +: 281] = {l_v, l_sec, l_wr, l_m};
        end else begin : g_on
            assign wq[k*281 +: 281] = {o_v, o_sec, o_wr, o_m};
        end
    end endgenerate
endmodule
`default_nettype wire
