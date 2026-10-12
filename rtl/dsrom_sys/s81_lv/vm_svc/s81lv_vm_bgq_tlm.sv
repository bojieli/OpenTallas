`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// s81lv_vm_bgq_tlm (el1011-s81lv/B, 2026-10-12): transaction-level stand-in for ONE dsfd_vm_bgq28 tile (one 128-b bit
// slice of one 8-bank group) in the S81 layer vehicle.  Same ports and the same cycle behaviour at the pins as
// dsfd_vm_bgq #(NP 28, NPR 10, NB 32, NBL 8, QD 4, DW 128, NSTG 2, EP 2) = dsfd_vm_bgq28:
//   * request bus  i_* -> f_*          NSTG + 1 = 3 registers (rb[0] .. rb[NSTG])
//   * read return  r_* -> o_*          NSTG + 1 = 3 registers (q pin register + NSTG return stages)
//   * own reads    i_* -> o_*          HL + NSTG + 2 = 15 registers (HL = QD + 4 + ED, ED = EP + 1)
//   * status       r_f / r_o -> o_f / o_o  2 registers
// Semantics (the closed tile's contract): every op takes effect in global (issue cycle, port) order; a read returns
// the row as left by every earlier op.  Bank = row[4:0], group = bank[4:3], row-in-bank = row[13:5]; DW/32 = 4 word
// write-mask bits.  o_v carries every read of the chain (all groups); o_d only this group's rows, ORed into r_d.
// ADDRESS CHECKS (fail closed, sticky o_f[3] | code bit 0, and $error): a read on a write-only port (p >= NPR);
// an op of this group outside the vehicle's legal row window [ROW_LO, ROW_HI).  Reads of never-written rows of this
// group are counted (n_uninit) and reported, not faulted (the closed tile returns the macro's power-up state).
// Mutant S81LV_MUT_BGADDR: the TLM decodes the group from row[5:4] instead of row[4:3] (bank-group address mutant).
// ---------------------------------------------------------------------------------------------------------------
module s81lv_vm_bgq_tlm #(
    parameter integer NP = 28, parameter integer NPR = 10, parameter integer DW = 128,
    parameter integer NSTG = 2, parameter integer QD = 4, parameter integer EP = 2,
    parameter integer ROW_LO = 0, parameter integer ROW_HI = 16384
) (
    input  wire [0:0]          ck,
    input  wire [0:0]          rs,
    input  wire [1:0]          grp,
    input  wire [NP-1:0]       i_v,
    input  wire [NP-1:0]       i_we,
    input  wire [NP*14-1:0]    i_row,
    input  wire [NP*(DW/32)-1:0] i_mask,
    input  wire [NP*DW-1:0]    i_d,
    output wire [NP-1:0]       f_v,
    output wire [NP-1:0]       f_we,
    output wire [NP*14-1:0]    f_row,
    output wire [NP*(DW/32)-1:0] f_mask,
    output wire [NP*DW-1:0]    f_d,
    input  wire [NPR-1:0]      r_v,
    input  wire [NPR*DW-1:0]   r_d,
    input  wire [3:0]          r_f,
    input  wire [$clog2(QD):0] r_o,
    output wire [NPR-1:0]      o_v,
    output wire [NPR*DW-1:0]   o_d,
    output reg  [3:0]          o_f,
    output reg  [$clog2(QD):0] o_o
);
    localparam integer MW = DW / 32, ED = (EP == 0) ? 0 : EP + 1, HL = QD + 4 + ED;
    localparam integer LR = HL + NSTG + 2;          // own-read latency (registers)
    localparam integer LQ = NSTG + 1;               // pass-through latency
    localparam integer OW = $clog2(QD) + 1;
    wire clk = ck[0];
    reg [1:0] rst_s;
    always @(posedge clk or negedge rs[0]) if (!rs[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rn = rst_s[1];
    reg [1:0] grp_q;
    always @(posedge clk) grp_q <= grp;

    // ---- request bus relay (f_* = rb[NSTG])
    reg [NP-1:0] rb_v [0:NSTG], rb_we [0:NSTG]; reg [NP*14-1:0] rb_row [0:NSTG];
    reg [NP*MW-1:0] rb_m [0:NSTG]; reg [NP*DW-1:0] rb_d [0:NSTG];
    integer s;
    always @(posedge clk or negedge rn)
        if (!rn) for (s = 0; s <= NSTG; s = s + 1) rb_v[s] <= {NP{1'b0}};
        else begin rb_v[0] <= i_v; for (s = 1; s <= NSTG; s = s + 1) rb_v[s] <= rb_v[s-1]; end
    always @(posedge clk) begin
        rb_we[0] <= i_we; rb_row[0] <= i_row; rb_m[0] <= i_mask; rb_d[0] <= i_d;
        for (s = 1; s <= NSTG; s = s + 1) begin
            rb_we[s] <= rb_we[s-1]; rb_row[s] <= rb_row[s-1]; rb_m[s] <= rb_m[s-1]; rb_d[s] <= rb_d[s-1];
        end
    end
    assign f_v = rb_v[NSTG]; assign f_we = rb_we[NSTG]; assign f_row = rb_row[NSTG]; assign f_mask = rb_m[NSTG];
    assign f_d = rb_d[NSTG];

    // ---- this group's storage (8 banks x 512 rows x DW), applied at rb[0] in port order
    reg [DW-1:0] mem [0:4095];
    reg          wr_ok [0:4095];
    integer n_uninit = 0, n_ops = 0;
    reg [NPR-1:0] rd_v0; reg [NPR*DW-1:0] rd_d0; reg flt_a;
    function automatic [1:0] gof(input [13:0] r);
`ifdef S81LV_MUT_BGADDR
        gof = r[5:4];
`else
        gof = r[4:3];
`endif
    endfunction
    integer p, w, k;
    initial for (k = 0; k < 4096; k = k + 1) begin mem[k] = {DW{1'b0}}; wr_ok[k] = 1'b0; end
    always @(posedge clk) begin : p_mem
        reg [13:0] r; reg [11:0] ix;
        rd_v0 = {NPR{1'b0}}; rd_d0 = {NPR*DW{1'b0}};
        if (!rn) flt_a <= 1'b0;
        else for (p = 0; p < NP; p = p + 1) if (rb_v[0][p]) begin
            r = rb_row[0][14*p +: 14]; ix = {r[2:0], r[13:5]};
            if (!rb_we[0][p] && p < NPR) rd_v0[p] = 1'b1;
            if (!rb_we[0][p] && p >= NPR) begin
                flt_a <= 1'b1; $error("S81LV_TLM grp %0d: read on write-only port %0d", grp_q, p);
            end
            if (gof(r) == grp_q) begin
                n_ops = n_ops + 1;
                if (r < ROW_LO || r >= ROW_HI) begin
                    flt_a <= 1'b1; $error("S81LV_TLM grp %0d: row %0d outside [%0d, %0d)", grp_q, r, ROW_LO, ROW_HI);
                end
                if (rb_we[0][p]) begin
                    for (w = 0; w < MW; w = w + 1) if (rb_m[0][MW*p + w]) mem[ix][32*w +: 32] = rb_d[0][DW*p + 32*w +: 32];
                    wr_ok[ix] = 1'b1;
                end else if (p < NPR) begin
                    if (!wr_ok[ix]) n_uninit = n_uninit + 1;
                    rd_d0[DW*p +: DW] = mem[ix];
                end
            end
        end
    end
    // own-read delay line: rd_* is taken at rb[0] (1 register after the pins) -> LR - 1 further registers
    reg [NPR-1:0] dv [0:LR-2]; reg [NPR*DW-1:0] dd [0:LR-2];
    always @(posedge clk) begin
        if (!rn) for (s = 0; s < LR - 1; s = s + 1) dv[s] <= {NPR{1'b0}};
        else begin dv[0] <= rd_v0; for (s = 1; s < LR - 1; s = s + 1) dv[s] <= dv[s-1]; end
        dd[0] <= rd_d0; for (s = 1; s < LR - 1; s = s + 1) dd[s] <= dd[s-1];
    end
    // upstream return pass-through (LQ registers)
    reg [NPR-1:0] qv [0:LQ-1]; reg [NPR*DW-1:0] qd [0:LQ-1];
    always @(posedge clk) begin
        if (!rn) for (s = 0; s < LQ; s = s + 1) qv[s] <= {NPR{1'b0}};
        else begin qv[0] <= r_v; for (s = 1; s < LQ; s = s + 1) qv[s] <= qv[s-1]; end
        qd[0] <= r_d; for (s = 1; s < LQ; s = s + 1) qd[s] <= qd[s-1];
    end
    assign o_v = qv[LQ-1] | dv[LR-2];
    assign o_d = qd[LQ-1] | dd[LR-2];
    reg [3:0] q_f; reg [OW-1:0] q_o;
    always @(posedge clk or negedge rn)
        if (!rn) begin q_f <= 4'd0; q_o <= {OW{1'b0}}; o_f <= 4'd0; o_o <= {OW{1'b0}}; end
        else begin q_f <= r_f; q_o <= r_o; o_f <= q_f | {flt_a, 2'b00, flt_a}; o_o <= q_o; end
endmodule
