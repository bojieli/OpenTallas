`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_cap_p -- PIPELINED S81 die return capture core (CLAUDE S81-PH capture, 2026-10-06).  Same ports and
// contract (results/rtl/s81_ph_20261006/capture/contract.json) as ot_s81ph_capture; the capture function of the
// unchanged ot_dsrom_rd64_vm_capture (ENABLE, ROOTS 128, CAPACITY 1, VM_AW 19, VM_ALWAYS_ACCEPT 1) with the canonical
// S81 profile quota, restructured for 1.2 GHz with margin on a 1015-um-wide view.  cap_m1 (the rd64 core) routed at
// -3.0 ns post-CTS: rd64 closes every per-root decision through 128-wide one-cycle loops (|r_valid, |vm_accept,
// |invalid -> sticky -> every push; all_done -> active), the profile quota sits in the phase-accept path, and the
// stream reset reaches ~68k flops in one net (-2.2 ns recovery).
//
// Structure (stream clock; fq = the caller's pin register, cycle t):
//   rows   R1 (t+1, bf16 RNE) -> R2 -> R3 (t+3: check) -> W (t+4: write into the root's pair packer)
//   phase  C0 (t+1, ctl copy) -> C (t+2: accept decision, central state) -> B1 (t+3, 4 kept copies) ->
//          held constants (t+4, NG kept copies, one per 8 roots) + per-root quota/received reset (t+4)
//          => a row checked at t+3 sees exactly the phases the reference had accepted before its cycle t
//   check  per root: received >= quota (over), pos > np, error row, address = obase + row + pos*ops >= 2^19 (range)
//          -> a bad row is never written (fail closed, as rd64 never commits it) and raises the per-root flag
//   fault  per-root flag (W) -> 16-root group OR -> half OR -> sticky (C) -> B1 -> per-group gate: every write
//          stops 6 cycles after the first bad row (rd64: 1 cycle).  Rows written in that window are individually
//          valid rows of the faulted phase (right address, right value); the phase is void either way (status
//          fault, the VM never consumes a faulted phase).  The bench checks: fault raised and every DUT write is a
//          write of an individually valid row.  Non-fault phases: every root's writes = the reference's.
//   done   per root (received == quota, no row in R1..W) -> group AND -> AND -> active/drained (C)
// Phase-ready deviates from rd64 in one term: rd64 also refuses a phase word in a cycle with a row valid or a VM
// accept; such a row is invalid in rd64 (no active phase) and here (received >= quota of the previous phase): both
// fault.  The VM issues a phase only after `drained`, so it never happens in protocol.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_cap_p #(
    parameter integer NR = 128,
    parameter integer LD = 4                 // per-root crossing depth (power of two)
) (
    input  wire             clk,
    input  wire             rst_n,           // stream, synchronised (rst_s[1] of the caller: 2-cycle release)
    input  wire             ckv,
    input  wire             rsv_n,           // serial, synchronised
    input  wire [NR-1:0]    row_v,
    input  wire [NR*52-1:0] row_d,           // {e, pos3, row16, fp32}
    input  wire             ctl_v,
    input  wire [158:0]     ctl_d,           // f_vm[159:1]
    input  wire             g_fault, g_busy, g_live,
    output reg  [2*NR-1:0]  w_v,
    output reg  [NR*102-1:0] w_d,
    output reg  [63:0]      st
);
    localparam integer NG = NR / 8;          // groups of 8 roots: held constants, gates, reset copies
    localparam integer NB = 4;               // B1 copies
    localparam integer GB = NG / NB;         // groups per B1 copy
    localparam integer NO = NR / 16;         // OR/AND tree groups of 16 roots
    genvar g;
    integer i;

    // ------------------------------------------------------------ reset copies (one per 8 roots, kept)
    (* keep *) reg [NG-1:0] rst_g;
    always @(posedge clk or negedge rst_n) if (!rst_n) rst_g <= {NG{1'b0}}; else rst_g <= {NG{1'b1}};
    (* keep *) reg [NG-1:0] rsv_g;
    always @(posedge ckv or negedge rsv_n) if (!rsv_n) rsv_g <= {NG{1'b0}}; else rsv_g <= {NG{1'b1}};

    // ------------------------------------------------------------ phase / control path
    reg c0_v; reg [158:0] c0_d;
    always @(posedge clk or negedge rst_n) if (!rst_n) c0_v <= 1'b0; else c0_v <= ctl_v;
    always @(posedge clk) c0_d <= ctl_d;
    wire [1:0]  kind     = c0_d[1:0];
    wire [46:0] identity = c0_d[48:2];
    wire [9:0]  phase_id = c0_d[58:49];
    wire [15:0] prows    = c0_d[157:142];
    wire [1:0]  fmt_in   = c0_d[123:122];
    reg act, stk, rq, drained, proto_fault;
    reg [3:0] hold;                          // done-tree holdoff after an accept
    wire phase_v = c0_v && kind == 2'd0;
    wire phase_ok = !act && !stk && !rq && prows != 16'd0 && fmt_in != 2'd3;
    wire go = phase_v && phase_ok;
    reg c_go; reg [29:0] c_ob, c_ops; reg [2:0] c_np; reg [1:0] c_fmt; reg [15:0] c_rs, c_rows; reg c_lo, c_hi;
    reg [46:0] h_id; reg [9:0] h_ph;
    wire all_done;                           // AND tree output (registered)
    wire any_bad;                            // OR tree output (registered)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            act <= 1'b0; stk <= 1'b0; rq <= 1'b0; drained <= 1'b1; proto_fault <= 1'b0; hold <= 4'd0; c_go <= 1'b0;
            h_id <= 47'd0; h_ph <= 10'd0;
        end else begin
            c_go <= go;
            if (c0_v && kind == 2'd1) rq <= c0_d[158];
            if (phase_v && !phase_ok) proto_fault <= 1'b1;
            if (rq || any_bad) stk <= 1'b1;
            if (go) begin act <= 1'b1; drained <= 1'b0; hold <= 4'd8; h_id <= identity; h_ph <= phase_id; end
            else begin
                if (hold != 4'd0) hold <= hold - 4'd1;
                if (act && hold == 4'd0 && all_done && !stk) begin act <= 1'b0; drained <= 1'b1; end
            end
        end
    always @(posedge clk) if (go) begin
        c_ob <= c0_d[88:59]; c_ops <= c0_d[118:89]; c_np <= c0_d[121:119]; c_fmt <= fmt_in; c_rs <= c0_d[139:124];
        c_lo <= c0_d[140]; c_hi <= c0_d[141]; c_rows <= prows;
    end
    // B1: 4 kept copies of {go, constants, gate}
    localparam integer KW = 1 + 30 + 30 + 3 + 2 + 16 + 16 + 1 + 1;
    wire [KW-1:0] c_k = {c_go, c_ob, c_ops, c_np, c_fmt, c_rs, c_rows, c_lo, c_hi};
    (* keep *) reg [KW-1:0] b1_k [0:NB-1];
    (* keep *) reg [NB-1:0] b1_gate;
    always @(posedge clk) for (i = 0; i < NB; i = i + 1) b1_k[i] <= c_k;
    always @(posedge clk or negedge rst_n) if (!rst_n) b1_gate <= {NB{1'b0}}; else b1_gate <= {NB{stk | rq}};

    // ------------------------------------------------------------ per-group held constants + gates
    wire [NG-1:0] grp_gate;
    wire [NR-1:0] r_bad, r_done;
    wire [NR-1:0] vm_valid; wire [NR*19-1:0] vm_addr; wire [NR*32-1:0] vm_data;
    generate for (g = 0; g < NG; g = g + 1) begin : g_grp
        localparam integer BI = g / GB;
        wire [KW-1:0] k = b1_k[BI];
        wire k_go = k[KW-1];
        (* keep *) reg [29:0] ob, ops; (* keep *) reg [2:0] np; (* keep *) reg [1:0] fmt; (* keep *) reg [15:0] rs;
        (* keep *) reg lo, hi;
        reg gate, go_g;
        always @(posedge clk) if (k_go) {ob, ops, np, fmt, rs, lo, hi} <= {k[KW-2 -: 30], k[KW-32 -: 30], k[KW-62 -: 3],
                                                                         k[KW-65 -: 2], k[KW-67 -: 16], k[1], k[0]};
        always @(posedge clk or negedge rst_g[g]) if (!rst_g[g]) begin gate <= 1'b0; go_g <= 1'b0; end
                                                 else begin gate <= b1_gate[BI]; go_g <= k_go; end
        assign grp_gate[g] = gate;
        wire [15:0] k_rows = k[KW-83 -: 16];
        wire [2:0]  k_np = k[KW-62 -: 3];
        wire [3:0]  positions = {1'b0, k_np} + 4'd1;
        // ---- the 8 roots of this group
        genvar j;
        for (j = 0; j < 8; j = j + 1) begin : g_r
            localparam integer R = 8 * g + j;
            // quota exactly as ot_dsrom_s81_phase_capture_profile (root R)
            wire [9:0] rows_r = {1'b0, k_rows[15:8], 1'b0} + 10'(k_rows[7:0] > 8'(2 * R)) + 10'(k_rows[7:0] > 8'(2 * R + 1));
            wire [13:0] quota_r = rows_r * positions;
            // rows: R1 (bf16 RNE), R2, R3 (check), W (write)
            reg v1, v2, v3, vw; reg [51:0] d1, d2, d3; reg [15:0] bf1, bf2, bf3;
            wire [51:0] d0 = row_d[52 * R +: 52];
            wire [32:0] rb = {1'b0, d0[31:0]} + 33'h7FFF + {32'd0, d0[16]};
            always @(posedge clk or negedge rst_g[g])
                if (!rst_g[g]) begin v1 <= 1'b0; v2 <= 1'b0; v3 <= 1'b0; end
                else begin v1 <= row_v[R]; v2 <= v1; v3 <= v2; end
`ifdef S81PH_MUTANT_BF16_TRUNC
            always @(posedge clk) begin d1 <= d0; bf1 <= d0[31:16]; d2 <= d1; bf2 <= bf1; d3 <= d2; bf3 <= bf2; end
`else
            always @(posedge clk) begin d1 <= d0; bf1 <= rb[31:16]; d2 <= d1; bf2 <= bf1; d3 <= d2; bf3 <= bf2; end
`endif
            // per-root quota / received (reset by the accept, aligned with the held constants)
            reg [13:0] exp_q; reg [18:0] rcv;
            always @(posedge clk or negedge rst_g[g])
                if (!rst_g[g]) begin exp_q <= 14'd0; rcv <= 19'd0; end
                else if (k_go) begin exp_q <= quota_r; rcv <= 19'd0; end
                else if (v3) rcv <= rcv + 19'd1;
            // check (R3)
            wire [15:0] row = d3[47:32]; wire [2:0] pos = d3[50:48]; wire e = d3[51];
            wire [33:0] address = {4'b0, ob} + {18'b0, row} + ({31'b0, pos} * {4'b0, ops});
            wire range_error = address >= (34'b1 << 19);
`ifdef S81PH_MUT_NOOVER
            wire over = 1'b0;                                      // MUTANT: no per-root quota check
`else
            wire over = rcv >= {5'd0, exp_q};
`endif
            wire bad = v3 && (e || pos > np || over || range_error);
            wire [31:0] data = (fmt == 2'd1 || (fmt == 2'd0 && (row < rs ? lo : hi))) ? d3[31:0] : {bf3, 16'b0};
            reg w_ok, w_bad; reg [18:0] w_a; reg [31:0] w_dt;
            always @(posedge clk or negedge rst_g[g])
                if (!rst_g[g]) begin w_ok <= 1'b0; w_bad <= 1'b0; vw <= 1'b0; end
                else begin w_ok <= v3 && !bad; w_bad <= bad; vw <= v3; end
            always @(posedge clk) begin w_a <= address[18:0]; w_dt <= data; end
            assign vm_valid[R] = w_ok && !gate;
            assign vm_addr[19 * R +: 19] = w_a;
            assign vm_data[32 * R +: 32] = w_dt;
            assign r_bad[R] = w_bad;
            assign r_done[R] = rcv == {5'd0, exp_q} && !(v1 || v2 || v3 || vw);
        end
    end endgenerate

    // ------------------------------------------------------------ OR (fault) / AND (done) trees, registered
    reg [NO-1:0] o1, a1; reg [1:0] o2, a2; reg o3, a3;
    wire [NR-1:0] hovf_now;
    integer q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin o1 <= 0; a1 <= 0; o2 <= 0; a2 <= 0; o3 <= 1'b0; a3 <= 1'b0; end
        else begin
            for (q = 0; q < NO; q = q + 1) begin
                o1[q] <= |(r_bad[16 * q +: 16] | hovf_now[16 * q +: 16]);
                a1[q] <= &r_done[16 * q +: 16];
            end
            o2 <= {|o1[NO-1:NO/2], |o1[NO/2-1:0]};
            a2 <= {&a1[NO-1:NO/2], &a1[NO/2-1:0]};
            o3 <= |o2; a3 <= &a2;
        end
    assign any_bad = o3;
    assign all_done = a3;

    // ------------------------------------------------------------ per-root pair packer + crossing (as ot_s81ph_capture)
    wire [NR-1:0] cv;
    wire [NR*103-1:0] cd;
    reg [NR-1:0] hovf;
    generate for (g = 0; g < NR; g = g + 1) begin : g_x
        localparam integer GG = g / 8;
        reg [50:0] h [0:3];
        reg [1:0] hr, hw;
        reg [2:0] hc;
        wire wr;
        wire [50:0] din = {vm_data[32*g +: 32], vm_addr[19*g +: 19]};
        wire [2:0] npop = (!wr || hc == 3'd0) ? 3'd0 : (hc == 3'd1) ? 3'd1 : 3'd2;
        wire crdy = (hc - npop) < 3'd4;
        assign hovf_now[g] = vm_valid[g] && !crdy;
        always @(posedge clk or negedge rst_g[GG])
            if (!rst_g[GG]) begin hr <= 2'd0; hw <= 2'd0; hc <= 3'd0; hovf[g] <= 1'b0; end
            else begin
                hr <= hr + npop[1:0];
                if (vm_valid[g] && crdy) begin hw <= hw + 2'd1; h[hw] <= din; end
                hc <= hc - npop + ((vm_valid[g] && crdy) ? 3'd1 : 3'd0);
                if (vm_valid[g] && !crdy) hovf[g] <= 1'b1;
            end
        ot_ratio_cdc_fifo #(.W(103), .DEPTH(LD)) u_x (.wclk(clk), .wrst_n(rst_g[GG]), .w_v(hc != 3'd0), .w_rdy(wr),
            .w_d({h[hr + 2'd1], hc >= 3'd2, h[hr]}), .rclk(ckv), .rrst_n(rsv_g[GG]), .r_v(cv[g]), .r_rdy(1'b1),
            .r_d(cd[103*g +: 103]), .w_live(), .r_live());
        always @(posedge ckv or negedge rsv_g[GG])
            if (!rsv_g[GG]) w_v[2*g +: 2] <= 2'b00; else w_v[2*g +: 2] <= {cv[g] & cd[103*g + 51], cv[g]};
        always @(posedge ckv) begin w_d[102*g +: 51] <= cd[103*g +: 51]; w_d[102*g + 51 +: 51] <= cd[103*g + 52 +: 51]; end
    end endgenerate

    // ------------------------------------------------------------ status lane
    wire phase_live = act, phase_idle = !rq && !act && !stk, phase_drained = !rq && drained && !stk;
    wire cfault = stk || rq;
    reg [63:0] s_now;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) s_now <= 64'd0;
        else s_now <= {g_busy, g_live, 1'b0, h_id, h_ph, cfault | proto_fault | g_fault, phase_drained, phase_idle, phase_live};
    wire s_v; wire [63:0] s_d;
    ot_ratio_cdc_fifo #(.W(64), .DEPTH(2)) u_s (.wclk(clk), .wrst_n(rst_n), .w_v(1'b1), .w_rdy(), .w_d(s_now),
        .rclk(ckv), .rrst_n(rsv_n), .r_v(s_v), .r_rdy(1'b1), .r_d(s_d), .w_live(), .r_live());
    always @(posedge ckv or negedge rsv_n) if (!rsv_n) st <= 64'd0; else if (s_v) st <= s_d;
`ifndef SYNTHESIS
    initial if (NR % 16 != 0) $fatal(1, "ot_s81ph_cap_p: NR %% 16");
`endif
endmodule
