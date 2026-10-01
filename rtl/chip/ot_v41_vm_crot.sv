`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// C_ROTATE: the DeepSeek-V4.1 die's vector memory as ONE CENTRAL banked strip with a rotate (barrel) network
// between the bank array and the stream unit's lane array (root ruling 2026-10-01; priced as option C_rotate in
// results/uarch/w11_vm_options.json).  INTERFACE v1 -- FROZEN for the die spine (W17), 2026-10-01.
// Supersedes VM-H (rtl/chip/ot_v41_vm_h.sv, kept as history): every stream-unit op pays the strip round trip;
// there is no per-op class decision and no layout rule (no 128-alignment, no packed-row ban).
//
// Floorplan.  SU_W | VM strip | SU_E: the strip runs the full hub height in the middle of the lane array; the
// lane-group tiles (8 lanes each) sit on both sides, every lane within ~3,850 um of the strip.  The strip holds
// the bank array (full shape: 128 bank columns x 2 banks x 6 read replicas = 1,536 ot_sram_1r1w_256x256_m2_r2c2,
// element e in column e mod 128 at local word e / 128, rows of 8 elements), the operand rotate networks
// (ot_v41_vm_rot: a 1,024-lane x 32 b logarithmic rotator, 7 mux levels a 1.111 ns stage at SS), the
// permutation network for gathered operands, the write rotate, the 128 return roots of the element array and the
// VM port of the non-SU clients.
//
// Ports -- IDENTICAL to ot_v41_vm_h v1, plus lead_hazards:
//   rd_*   NRD element reads with a class each (0..3 SU operand streams A..D, 4 SU gather index, 5 any other
//          reader: the matvec x gather, HE x, QE 32-element reads, the expert index, XU, word ports A / B).
//          Reads 0 .. 4*NL-1 are SU lane l stream s at 4*l + s, 4*NL .. 5*NL-1 the SU gather-index reads, the rest
//          class 5.  Answered the next cycle.
//   wr_*   NWR element writes in the flat memory's statement order (WE0 .. WE0+NL-1: the SU element writes, lane
//          l at WE0 + l); the collective write and the result scatter are entries here; landed end of cycle in
//          list order (a later entry wins).
//   rt_*   NROOT return roots of the element array (the field-result port, 5,461 b a slow cycle at full shape):
//          partials {tag, FP32, e} (ot_v41_ret_pkg); a root finishes a row (golden csum order) and writes it as
//          FP32 (ret_fmt 0) or BF16 RNE in the upper half (ret_fmt 1) at ret_obase + pos * ret_ps + row * ret_rs.
//          C_rotate: ANY root may write ANY address (VM-H's "root j writes rows == j mod NG" rule is dropped;
//          ret_nonlocal / wr_nonlocal still count such rows, as statistics only).  RQD queue, fault on overflow.
//   ret_cfg, ret_rows, ret_clr, ret_e, bd_load / bd_dump (simulation backdoor, u_vmd.bd_img), fault: as VM-H.
//   lead_hazards (simulation only; 0 in synthesis): stream-unit operand reads (classes 0..4) whose word was
//          written in the CR_RD cycles before the read.  The stream unit is built with its lanes reading CR_RD
//          cycles after the strip read (ot_hdc_v41x_vec BCAST_STAGES = CR_LEAD + CR_RD, RD_LEAD = CR_LEAD); a
//          write landing between the two would make the pipeline's word differ from the bench's.  Gates require 0.
//
// Stream-unit side (ot_hdc_core_v41x VM_CROT = 1; register stages in the unit, not here):
//   CR_LEAD  controller -> strip address broadcast           CR_RD   strip -> lane operands (bank reg + rotate + wire)
//   CR_GX    extra stages of a gathered A (permutation)      CR_WR   lane -> strip element writes (write rotate + wire)
//   CR_RES   reducer -> strip results
// Non-SU clients at the VM port (callers' register stages: ot_hdc_core_v41x X_GATHER_STAGES /
// RET_SCATTER_STAGES, ot_chip_v41x_tile COLL_WRITE_STAGES), W18's 4/3 ratio-FIFO widths a slow (0.9 GHz) cycle:
//   x read 732 b | field results 5,461 b | attention scores / PV 683 b | collective 683 b in, 2,731 b out |
//   indexer query 341 b | SU -> attention p-words 1,536 b.
// ---------------------------------------------------------------------------
module ot_v41_vm_crot #(
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
    parameter integer NWP   = 32,
    // wr_* entries WRT0 .. WRT0+NG-1 are the element array's finished rows written by root j at entry WRT0 + j
    // (die spine option (b)); C_rotate: any address (one outside group j is counted in wr_nonlocal, statistics
    // only).  -1: none.
    parameter integer WRT0  = -1,
    parameter integer CR_RD = 8              // strip -> lane operand stages (the lead-hazard window)
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
    output reg  [31:0]          wr_nonlocal,// root-row entries (WRT0) whose address is not in their root's group
    // ---- simulation backdoor and status
    input  wire                 bd_load,
    input  wire                 bd_dump,
    output wire                 fault,
    output reg  [31:0]          lead_hazards
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
    integer wq;
    reg [31:0] wfar;
    always @(*) begin
        wfar = 0;
        if (WRT0 >= 0)
            for (wq = 0; wq < NG; wq = wq + 1)
                if (wr_we[WRT0 + wq] && (NG > 1) && ((32'(wr_addr[(WRT0 + wq)*VMA +: VMA]) % NG) != wq)) wfar = wfar + 1;
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) wr_nonlocal <= 0; else wr_nonlocal <= wr_nonlocal + wfar;
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

    // ---- lead hazards (simulation only): an SU operand read whose word landed in the last CR_RD cycles ------
`ifndef SYNTHESIS
    integer lw [0:(1<<VMA)-1];
    integer hcyc, hi, hn;
    initial begin for (hi = 0; hi < (1 << VMA); hi = hi + 1) lw[hi] = -1000000; hcyc = 0; lead_hazards = 0; end
    always @(posedge clk) begin
        hn = 0;
        for (hi = 0; hi < 5 * NL && hi < NRD; hi = hi + 1)
            if (rd_re[hi] && rd_cls[hi*3 +: 3] <= 3'd4 && hcyc - lw[32'(rd_addr[hi*VMA +: VMA])] <= CR_RD) hn = hn + 1;
        for (hi = 0; hi < NWR; hi = hi + 1) if (wr_we[hi]) lw[32'(wr_addr[hi*VMA +: VMA])] = hcyc;
        for (hi = 0; hi < NROOT; hi = hi + 1) if (t_we[hi]) lw[32'(t_addr[hi*VMA +: VMA])] = hcyc;
        if (bd_load) for (hi = 0; hi < (1 << VMA); hi = hi + 1) lw[hi] = -1000000;
        lead_hazards <= lead_hazards + 32'(hn);
        hcyc = hcyc + 1;
    end
`else
    always @(posedge clk) lead_hazards <= 32'd0;
`endif
    task report;
        u_vmd.report();
        $display("VMCROT roots=%0d rows=%0d nonlocal=%0d e=%0d wr_nonlocal=%0d cr_rd=%0d lead_hazards=%0d", NROOT, ret_rows,
                 ret_nonlocal, ret_e, wr_nonlocal, CR_RD, lead_hazards);
    endtask
endmodule
