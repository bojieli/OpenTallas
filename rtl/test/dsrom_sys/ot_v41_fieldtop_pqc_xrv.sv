// BENCH ONLY (ds-1010/pqc, 2026-10-10): no hardware, no adoption claim.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_fieldtop_pqc_xrv: the field vehicle ot_v41_fieldtop_pqc_w17w10 around the v13b / v14 spine
// (physical/s81_pq_xrv/pinned/rtl/v41die/ot_v41_spine_pqc_w17w10.sv) with its co-located one-edge vector-memory
// read replaced by a REQUEST-DRIVEN stationed VM model: every x_re reads the VM row block at its own address and the
// data returns D edges later (+OT_XD=D; 1 = the co-located read, 2 + (QD + 6) + 2 = the S81 die path), in order,
// optionally with a random extra delay (+OT_XJIT=J, in-order, one return a cycle; seed +OT_XSEED), with the return
// valid x_rv.  Mutants: +OT_XSKEW=1 (valid one edge EARLY: data one edge after its valid), 2 (valid one edge LATE).
// XRV = 0: the spine ignores x_rv and takes x_q one edge after x_re (the v13b contract) whatever D is.
// xstall: cycles the loader held a read because XCAP requests were outstanding; xomax: max outstanding.
// ---------------------------------------------------------------------------
// (the original vehicle header follows)
// ot_v41_fieldtop_pqc_w17w10: ot_v41_fieldtop_pq_w17w10 with its spine replaced by the timing-closed successor
// ot_v41_spine_pqc_w17w10 (Claude:dsrom-field-spine, 2026-10-04); vector-memory model, PQ field and ports unchanged.
// The vehicle of tools/dsrom_field_spine.py (PQ = 0: the closed baseline spine; PQ = 1: the closed PQ spine).
// ---------------------------------------------------------------------------
module ot_v41_fieldtop_pqc_xrv #(
    parameter integer FAST = 0,
    parameter integer PP = 0,
    parameter integer BP = 0,
    parameter integer NP = 8,
    parameter integer R = 2,
    parameter integer NBF = 2,
    parameter integer PHW = 6,
    parameter integer SAW = 14,
    parameter integer VAW = 14,
    parameter integer VRD = 64,
    parameter integer KMAX = 6144,
    parameter integer BST = 2,
    parameter integer RST = 1,
    parameter integer PQ = 0,
    parameter integer GAP = 12,
    parameter integer GUARD = 180,
    parameter integer GSLACK = 6,
    parameter integer XRV = 0,
    parameter integer XCAP = 16
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    input  wire [PHW-1:0]    i_ph,
    input  wire [2:0]        i_np,
    input  wire [VAW-1:0]    i_xbase,
    input  wire [VAW-1:0]    i_xps,
    input  wire [VAW-1:0]    i_obase,
    input  wire [VAW-1:0]    i_ops,
    output wire              ready,
    output wire              idle,
    output wire [R-1:0]      o_we,
    output wire [R*VAW-1:0]  o_addr,
    output wire [R*32-1:0]   o_data,
    output wire              fault,
    output wire [31:0]       phase_cycles,
    output wire              ev_go,
    output wire              ev_end,
    output wire [1:0]        ev_tag,
    output reg  [31:0]       xstall,
    output reg  [31:0]       xomax
);
    // vector memory
    reg [31:0] vm [0:(1 << VAW)-1] /*verilator public_flat_rw*/;
    reg [8*1024-1:0] rom_dir;
    integer ii;
    initial begin
        for (ii = 0; ii < (1 << VAW); ii = ii + 1) vm[ii] = 32'd0;
        if ($value$plusargs("OT_ROM_DIR=%s", rom_dir)) $readmemh({rom_dir, "/vm.hex"}, vm);
    end
    wire              x_re;
    wire [VAW-1:0]    x_addr;
    wire [VRD*32-1:0] x_q;
    wire              x_rv;
    wire [R-1:0]      w_we;
    wire [R*VAW-1:0]  w_addr;
    wire [R*32-1:0]   w_data;
    integer k;
    // stationed, request-driven VM read model
    localparam integer QN = 256;
    integer xd, xjit, xskew, xseed;
    initial begin
        xd = 1; xjit = 0; xskew = 0; xseed = 1;
        if ($value$plusargs("OT_XD=%d", xd)) ;
        if ($value$plusargs("OT_XJIT=%d", xjit)) ;
        if ($value$plusargs("OT_XSKEW=%d", xskew)) ;
        if ($value$plusargs("OT_XSEED=%d", xseed)) ;
        if (xd < 1) xd = 1;
    end
    reg [VRD*32-1:0] qd [0:QN-1];
    reg [63:0]       qdue [0:QN-1];
    integer          qh, qt, qn;
    reg [63:0]       mcyc, last_due, due;
    reg [VRD*32-1:0] xq0, xq1, dtmp;
    reg              xv0, xv1;
    integer          xo_m;
    initial begin qh = 0; qt = 0; qn = 0; mcyc = 0; last_due = 0; xv0 = 0; xv1 = 0; xo_m = 0; xq0 = '0; xq1 = '0;
        xstall = 0; xomax = 0; end
    always @(posedge clk) begin
        mcyc = mcyc + 64'd1;
        if (x_re) begin
            for (k = 0; k < VRD; k = k + 1) dtmp[32*k +: 32] = vm[x_addr + VAW'(k)];
            due = mcyc + 64'(xd - 1) + ((xjit > 0) ? 64'($urandom % (xjit + 1)) : 64'd0);
            if (qn > 0 && due <= last_due) due = last_due + 64'd1;
            qd[qt] = dtmp; qdue[qt] = due; qt = (qt + 1) % QN; qn = qn + 1; last_due = due;
            if (qn >= QN) $fatal(1, "VM model queue overflow");
        end
        xq1 <= xq0; xv1 <= xv0;
        if (qn > 0 && qdue[qh] == mcyc) begin
            xq0 <= qd[qh]; xv0 <= 1'b1; qh = (qh + 1) % QN; qn = qn - 1;
        end else xv0 <= 1'b0;
        if (qn > 0 && qdue[qh] < mcyc) $fatal(1, "VM model missed a due return");
        if (u_sp.ld_run && !u_sp.x_ok) xstall <= xstall + 32'd1;
        if (32'(u_sp.xo) > xomax) xomax <= 32'(u_sp.xo);
        for (k = 0; k < R; k = k + 1) if (w_we[k]) vm[w_addr[VAW*k +: VAW]] <= w_data[32*k +: 32];
    end
    assign x_q  = (xskew == 1) ? xq1 : xq0;
    assign x_rv = (xskew == 2) ? xv1 : xv0;
    assign o_we = w_we; assign o_addr = w_addr; assign o_data = w_data;

    wire              c_go, c_gobf, c_cfg, c_xs_v, c_xb_v;
    wire [1:0]        c_tag;
    wire [PHW-1:0]    c_ph;
    wire [2:0]        c_np, c_xs_b, c_xs_pos, c_xb_pos, c_xb_b;
    wire [7:0]        c_xs_p;
    wire [1:0]        c_xs_sv;
    wire [255:0]      c_xs_q0, c_xs_q1;
    wire [9:0]        c_xs_e0, c_xs_e1;
    wire [3:0]        c_xb_sv;
    wire [31:0]       c_xb_u;
    wire [1023:0]     c_xb_d;
    wire [R-1:0]      r_v, r_e;
    wire [16*R-1:0]   r_row, r_bf16;
    wire [3*R-1:0]    r_pos;
    wire [32*R-1:0]   r_fp32;
    wire              f_fault;
    ot_v41_spine_pqc_w17w10 #(.PHW(PHW), .SAW(SAW), .R(R), .VAW(VAW), .VRD(VRD), .KMAX(KMAX), .BST(BST), .PQ(PQ),
                             .GAP(GAP), .GUARD(GUARD), .GSLACK(GSLACK), .XRV(XRV), .XCAP(XCAP)) u_sp (
        .clk(clk), .rst_n(rst_n), .go(go), .i_ph(i_ph), .i_np(i_np), .i_xbase(i_xbase), .i_xps(i_xps),
        .i_obase(i_obase), .i_ops(i_ops), .i_fmt(2'd0), .ready(ready), .idle(idle), .x_re(x_re), .x_addr(x_addr), .x_q(x_q), .x_rv(x_rv),
        .w_we(w_we), .w_addr(w_addr), .w_data(w_data),
        .f_cfg_go(c_cfg), .f_cfg_ph(c_ph), .f_cfg_np(c_np), .f_go(c_go), .f_go_bf(c_gobf), .f_go_tag(c_tag), .f_xs_v(c_xs_v),
        .f_xs_p(c_xs_p), .f_xs_b(c_xs_b), .f_xs_sv(c_xs_sv), .f_xs_q0(c_xs_q0), .f_xs_e0(c_xs_e0),
        .f_xs_q1(c_xs_q1), .f_xs_e1(c_xs_e1), .f_xs_pos(c_xs_pos), .f_xb_pos(c_xb_pos), .f_xb_v(c_xb_v),
        .f_xb_b(c_xb_b), .f_xb_sv(c_xb_sv), .f_xb_u(c_xb_u), .f_xb_d(c_xb_d), .f_bus(),
        .r_v(r_v), .r_row(r_row), .r_pos(r_pos), .r_fp32(r_fp32), .r_bf16(r_bf16), .r_e(r_e),
        .f_fault(f_fault), .fault(fault), .phase_cycles(phase_cycles),
        .ev_go(ev_go), .ev_end(ev_end), .ev_tag(ev_tag));
    wire f_busy;
    ot_v41_field_pq_w17w10 #(.FAST(FAST), .PP(PP), .BP(BP), .NP(NP), .R(R), .NBF(NBF), .PHW(PHW), .RST(RST), .PQ(PQ)) u_f (
        .clk(clk), .rst_n(rst_n), .cfg_go(c_cfg), .cfg_ph(c_ph), .cfg_np(c_np), .go(c_go), .go_bf(c_gobf), .go_tag(c_tag),
        .xs_v(c_xs_v), .xs_p(c_xs_p), .xs_b(c_xs_b), .xs_sv(c_xs_sv), .xs_q0(c_xs_q0), .xs_e0(c_xs_e0),
        .xs_q1(c_xs_q1), .xs_e1(c_xs_e1), .xs_pos(c_xs_pos), .xb_pos(c_xb_pos), .xb_v(c_xb_v), .xb_b(c_xb_b),
        .xb_sv(c_xb_sv), .xb_u(c_xb_u), .xb_d(c_xb_d), .r_v(r_v), .r_row(r_row), .r_pos(r_pos),
        .r_fp32(r_fp32), .r_bf16(r_bf16), .r_e(r_e), .busy(f_busy), .fault(f_fault));
endmodule
