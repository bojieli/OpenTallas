`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// VM-H: the DeepSeek-V4.1 die's distributed vector memory, option H (root decision 2026-09-30;
// results/uarch/w11_vm_options.json option H_rtl).  INTERFACE v1 (frozen for the die spine, W17).
//
// Organisation.  NG lane groups (full shape 128); element e lives in group e mod NG (local word e / NG),
// stream-unit lane l belongs to group l mod NG.  Each group holds its slice of the VM
// (ot_v41_vm_dist_group: 2 banks x 6 read replicas of 1R1W 8-word rows) and one RETURN ROOT of the element
// array (W10 ot_v41_ret_root: pairs golden-sibling FP32 partials and finishes rows).
//
// Clients (all in one cycle's request lists, exactly as ot_v41_vm_dist; reads answer the next cycle, writes
// land at the end of the cycle in list order):
//   rd_*   NRD element reads with a class each (0..3 SU operand streams A..D, 4 SU gather index, 5 any other
//          reader: the matvec x gather, HE x, QE 32-element reads, the expert index, XU, word ports A / B).
//          The list order is the caller's: reads 0 .. 4*NL-1 are SU lane l stream s at 4*l + s, 4*NL ..
//          5*NL-1 the SU gather-index reads, the rest class 5.
//   wr_*   NWR element writes in the flat memory's statement order (WE0 .. WE0+NL-1: the SU element writes,
//          lane l at WE0 + l); the collective write and the result scatter are entries here.
//   rt_*   NROOT = NG return roots: partial streams of the element array.  A partial is {tag, FP32, e} with
//          tag = {pos[2:0], row[15:0], lo[4:0] (seg), k[2:0] (level), nseg[4:0] (segs)} (ot_v41_ret_pkg);
//          root j must receive every partial of a row whose destination address
//              ret_obase + pos * ret_ps + row * ret_rs
//          is in group j (== j mod NG).  The root finishes the row (golden csum order) and writes it into
//          its own group -- a local write, no network -- as FP32 (ret_fmt 0) or BF16 RNE in the upper half
//          (ret_fmt 1).  A row whose address is not in the root's group is still written (the behavioural
//          banks take any address) and counted in ret_nonlocal: the die gate requires 0.
//          No back-pressure: each root queues RQD partials (fault on overflow).
//   ret_cfg (ret_obase, ret_ps, ret_rs, ret_fmt) is sampled per partial; hold it for the op's lifetime.
//   ret_rows counts rows written (all roots), a credit for the op's consumers (clear with ret_clr).
//
// Stream-unit networks (option H).  The stream unit (ot_hdc_v41x_vec VMD_NG) decides per op whether a
// stream needs the per-row scalar fetch, the residual rotate (ot_v41_vm_rot) or the permutation network and
// holds the op for their stages (SU_*_STAGES of ot_hdc_core_v41x); the reads it then issues arrive through
// these lists.  The trees of the non-SU clients (x gather / result scatter / collective write) are the
// callers' register stages (ot_hdc_core_v41x RET_SCATTER_STAGES, X_GATHER_STAGES; ot_chip_v41x_tile
// COLL_WRITE_STAGES).
//
// Simulation backdoor (bd_load / bd_dump / u_vmd.bd_img) as ot_v41_vm_dist.
// ---------------------------------------------------------------------------
module ot_v41_vm_h #(
    parameter integer NG    = 128,
    parameter integer VMA   = 19,
    parameter integer NL    = 1024,
    parameter integer NRD   = 5 * 1024 + 64,
    parameter integer NWR   = 1024 + 128,
    parameter integer WE0   = 0,
    parameter integer NROOT = NG,
    parameter integer RQD   = 16,            // return-root queue / pending partials (ot_v41_ret_root D, QD)
    parameter integer NB    = 2,
    parameter integer NOVF  = 48,
    parameter integer NWP   = 32
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // ---- element reads / writes (ot_v41_vm_dist lists)
    input  wire [NRD-1:0]       rd_re,
    input  wire [NRD*VMA-1:0]   rd_addr,
    input  wire [NRD*3-1:0]     rd_cls,
    output wire [NRD*32-1:0]    rd_q,
    input  wire [NWR-1:0]       wr_we,
    input  wire [NWR*VMA-1:0]   wr_addr,
    input  wire [NWR*32-1:0]    wr_data,
    // ---- return roots of the element array
    input  wire [NROOT-1:0]     rt_v,
    input  wire [NROOT*32-1:0]  rt_tag,
    input  wire [NROOT*32-1:0]  rt_d,
    input  wire [NROOT-1:0]     rt_e,
    input  wire [VMA-1:0]       ret_obase,
    input  wire [VMA-1:0]       ret_ps,
    input  wire [VMA-1:0]       ret_rs,
    input  wire                 ret_fmt,
    input  wire                 ret_clr,
    output reg  [31:0]          ret_rows,
    output reg  [31:0]          ret_nonlocal,
    output reg                  ret_e,      // an element-array exception flag reached a written row
    // ---- simulation backdoor and status
    input  wire                 bd_load,
    input  wire                 bd_dump,
    output wire                 fault
);
    localparam integer LNG = (NG > 1) ? $clog2(NG) : 0;
    localparam integer GW = (LNG > 0) ? LNG : 1;

    // ---- the return roots: one row a cycle each at most, into the root's own group ------------------------
    wire [NROOT-1:0]       r_v, r_e, r_f;
    wire [NROOT*16-1:0]    r_row;
    wire [NROOT*3-1:0]     r_pos;
    wire [NROOT*32-1:0]    r_fp32;
    wire [NROOT*16-1:0]    r_bf16;
    genvar j;
    generate for (j = 0; j < NROOT; j = j + 1) begin : g_root
        ot_v41_ret_root #(.D(RQD), .QD(RQD)) u_root (.clk(clk), .rst_n(rst_n), .i_v(rt_v[j]),
            .i_t(rt_tag[32*j +: 32]), .i_d(rt_d[32*j +: 32]), .i_e(rt_e[j]),
            .r_v(r_v[j]), .r_row(r_row[16*j +: 16]), .r_pos(r_pos[3*j +: 3]), .r_fp32(r_fp32[32*j +: 32]),
            .r_bf16(r_bf16[16*j +: 16]), .r_e(r_e[j]), .fault(r_f[j]));
    end endgenerate
    reg  [NROOT-1:0]     t_we;
    reg  [NROOT*VMA-1:0] t_addr;
    reg  [NROOT*32-1:0]  t_data;
    reg  [NROOT-1:0]     t_far;
    integer q;
    reg [VMA+3:0] ta;
    always @(*) begin
        for (q = 0; q < NROOT; q = q + 1) begin
            ta = (VMA+4)'(ret_obase) + (VMA+4)'(r_pos[3*q +: 3]) * (VMA+4)'(ret_ps) +
                 (VMA+4)'(r_row[16*q +: 16]) * (VMA+4)'(ret_rs);
            t_we[q] = r_v[q];
            t_addr[q*VMA +: VMA] = ta[VMA-1:0];
            t_data[32*q +: 32] = ret_fmt ? {r_bf16[16*q +: 16], 16'h0000} : r_fp32[32*q +: 32];
            t_far[q] = r_v[q] && (NG > 1) && ((32'(ta[VMA-1:0]) % NG) != (q % NG));
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ret_rows <= 0; ret_nonlocal <= 0; ret_e <= 1'b0; end
        else begin
            ret_rows <= (ret_clr ? 32'd0 : ret_rows) + 32'($countones(r_v));
            ret_nonlocal <= ret_nonlocal + 32'($countones(t_far));
            if (|(r_v & r_e)) ret_e <= 1'b1;
        end
    end

    // ---- the lane-group banks, with the roots' writes after the callers' (their own group's port) ---------
    wire vfault;
    ot_v41_vm_dist #(.NG(NG), .VMA(VMA), .NL(NL), .NRD(NRD), .NWR(NWR + NROOT), .NB(NB), .NOVF(NOVF),
                     .NWP(NWP), .WE0(WE0)) u_vmd (
        .clk(clk), .rst_n(rst_n), .rd_re(rd_re), .rd_addr(rd_addr), .rd_cls(rd_cls), .rd_q(rd_q),
        .wr_we({t_we, wr_we}), .wr_addr({t_addr, wr_addr}), .wr_data({t_data, wr_data}),
        .bd_load(bd_load), .bd_dump(bd_dump), .fault(vfault));
    reg rf;
    always @(posedge clk or negedge rst_n) if (!rst_n) rf <= 1'b0; else if (|r_f) rf <= 1'b1;
    assign fault = vfault | rf;
    task report;
        u_vmd.report();
        $display("VMH roots=%0d rows=%0d nonlocal=%0d e=%0d", NROOT, ret_rows, ret_nonlocal, ret_e);
    endtask
endmodule
