`timescale 1ns/1ps
`default_nettype none
// HBM-SMBUDGET 2026-10-19 (coordinator decision 0jx: C + P2 + 2,048-word store): the host collar of a RUN target (the SM
// service group cp_svg_<q><k> and the extension calendar xc_<q><k>) = ot_static_cmd_target MODE 0 with
//   * a 2,048-row programme window: AWA 11 maps cfg_addr[11:10] = 0 -> programme rows 0..1023 and = 2 -> rows 1024..2047
//     (window 2 is the MODE 1 command table, absent in MODE 0); window 1 = descriptor rows (AWB) as before;
//   * a run ARGUMENT: the run descriptor's loops field carries layer + 1 (1..256) -> run_arg = loops - 1 with the launch
//     (the relative issuer's run_layer: one resident descriptor table serves every layer; ~33 ingress edges a layer for
//     the 16 SMs' svg + xc run descriptors and the global launch, instead of ~51k edges of table rewrite).
// Everything else is the MODE 0 behaviour of ot_static_cmd_target_core: pin flops on every input, registered outputs,
// cfg -> window write 2 edges, launch_v -> run_v 2 edges, a descriptor arms exactly one launch, cfg while the target is
// active or in the launch edge is a FAULT (static install, no runtime arbitration); a run descriptor MAY be armed while the
// previous run is active (the launch itself must follow the previous run's end: the consumer faults a run while running).  RSYNC = 1: 2-flop reset
// synchroniser at the pin (as the hardened cp_svg r2).  MUT 1: run_arg = loops (off by one); 2: ignore the target id.
module ot_hbm_xcal_target_native #(
    parameter [7:0]  TARGET = 8'd64,
    parameter integer AWA = 11, AWB = 7, RBW = 7, RCW = 8,
    parameter integer NA = 1, NF = 1, MUT = 0, TGT_PIN = 1, RSYNC = 0
)(
    input  wire clk, rst_n,
    input  wire [7:0] tgt,
    input  wire cfg_v,
    input  wire [7:0] cfg_target,
    input  wire [11:0] cfg_addr,
    input  wire [255:0] cfg_data,
    input  wire desc_v,
    input  wire [11:0] desc_base,
    input  wire [12:0] desc_limit,
    input  wire [15:0] desc_loops,
    input  wire launch_v,
    input  wire [NA-1:0] tgt_active,
    input  wire [NF-1:0] tgt_fault,
    output reg  a_we,
    output reg  [AWA-1:0] a_addr,
    output reg  [255:0] a_data,
    output reg  b_we,
    output reg  [AWB-1:0] b_addr,
    output reg  [255:0] b_data,
    output reg  run_v,
    output reg  [RBW-1:0] run_base,
    output reg  [RCW-1:0] run_count,
    output reg  [7:0] run_arg,
    output reg  configured, fault, active
);
    initial if (AWA < 1 || AWA > 11 || AWB < 1 || AWB > 10 || RBW > 12 || RCW > 13) $fatal(1, "ot_static_run_target widths");
    wire rst_q_n;
    generate if (RSYNC == 1) begin : g_rs
        reg [1:0] rsync;
        always @(posedge clk) rsync <= {rsync[0], rst_n};
        assign rst_q_n = rsync[1];
    end else begin : g_rs_raw
        assign rst_q_n = rst_n;
    end endgenerate
    // ---------------- pin flops ----------------
    reg cv, dv, lv;
    reg [NA-1:0] act_q;
    reg [NF-1:0] flt_q;
    reg [7:0] target_q, tgt_q;
    reg [11:0] addr_q, base_q;
    reg [12:0] limit_q;
    reg [15:0] loops_q;
    reg [255:0] data_q;
    always @(posedge clk) begin
        target_q <= cfg_target; addr_q <= cfg_addr; data_q <= cfg_data; tgt_q <= tgt;
        base_q <= desc_base; limit_q <= desc_limit; loops_q <= desc_loops;
        a_addr <= prow[AWA-1:0]; a_data <= data_q;
        b_addr <= row[AWB-1:0]; b_data <= data_q;
        run_base <= RBW'(s_base);run_count <= RCW'(s_limit-s_base);run_arg <= s_arg;
    end
    always @(posedge clk or negedge rst_q_n)
        if (!rst_q_n) begin cv <= 0; dv <= 0; lv <= 0; act_q <= 0; flt_q <= 0; end
        else begin cv <= cfg_v; dv <= desc_v; lv <= launch_v; act_q <= tgt_active; flt_q <= tgt_fault; end
    wire [7:0] tid = (TGT_PIN != 0) ? tgt_q : TARGET;
    wire hit = (MUT == 2) ? 1'b1 : (target_q == tid);
    wire [1:0] win = addr_q[11:10];
    wire [9:0] row = addr_q[9:0];
    // programme row: window 0 = rows 0..1023, window 2 = rows 1024..2047 (AWA 11 only)
    wire [10:0] prow = {win == 2'd2, row};
    wire a_hit = (win == 2'd0 || (win == 2'd2 && AWA == 11)) && {1'b0, prow} < (12'd1 << AWA);
    reg [12:0] s_base, s_limit; reg [7:0] s_arg; reg fault_r;
    wire busy_any = |act_q;
    always @(posedge clk or negedge rst_q_n) begin
        if (!rst_q_n) begin
            a_we <= 0; b_we <= 0; run_v <= 0; configured <= 0; fault_r <= 0; fault <= 0; active <= 0;
            s_base <= 0; s_limit <= 0; s_arg <= 0; 
        end else begin
            a_we <= 0; b_we <= 0; run_v <= 0;
            if (cv && hit) begin
                configured <= 0;
                if (busy_any || lv) fault_r <= 1;
                else if (a_hit) begin a_we <= 1; end
                else if (win == 2'd1 && {1'b0, row} < (11'd1 << AWB)) begin b_we <= 1; end
                else fault_r <= 1;
            end
            if (dv && hit) begin
                configured <= 0;
                if (lv || cv) fault_r <= 1;                      // arming the NEXT run while this one runs is legal
                else if (loops_q == 16'd0 || loops_q > 16'd256 || limit_q <= {1'b0, base_q} || limit_q > (13'd1 << RBW) ||
                         (limit_q - {1'b0, base_q}) >= (14'd1 << RCW)) fault_r <= 1;
                else begin
                    s_base <= {1'b0, base_q}; s_limit <= limit_q; configured <= 1;
                    s_arg <= (MUT == 1) ? loops_q[7:0] : 8'(loops_q - 16'd1);
                end
            end
            if (lv && configured) begin
                configured <= 0;
                if (busy_any || fault_r || (|flt_q) || cv || dv) fault_r <= 1;
                else begin run_v <= 1; end
            end
            fault <= fault_r || (|flt_q);
            active <= |act_q;
        end
    end
endmodule
`default_nettype wire
