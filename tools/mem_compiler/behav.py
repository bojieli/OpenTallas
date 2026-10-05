"""Behavioural Verilog for compiled macros: the physical array, repair and fault model.

The model stores the PHYSICAL array: ``rows = words / mux`` main rows plus the
spare rows, ``(bits + spare_cols) * mux`` columns with the data bits
interleaved by the column multiplexer (data bit ``b`` of a word with column
select ``s`` sits in physical column ``b * mux + s``).  Repair is applied the
way the hard macro applies it -- a row-address comparator per spare row, an IO
steering multiplexer per spare column -- so a fault injected at a physical
cell is repaired, or not, exactly as silicon would be.

Faults exist only under ``+define+OT_MEM_FAULTS`` (the production model has no
fault logic at all).  A test bench sets up to eight fault slots per instance by
hierarchical assignment::

    f_kind[k]  1 SA0, 2 SA1                 cell (f_r, f_c) stuck
               3 TF_UP, 4 TF_DOWN           cell cannot make the 0->1 / 1->0 transition
               5 CFIN                       aggressor (f_ar, f_ac) transition in direction
                                            f_v[0] (1 = rising) inverts the victim (f_r, f_c)
               6 CFID                       ... forces the victim to f_v[1]
               7 CFST                       victim reads f_v[1] while the aggressor holds f_v[0]
               8 AF_NONE                    row f_r is never selected (reads 0, writes lost)
               9 AF_ALIAS                   an access to row f_r selects row f_ar instead
              10 AF_MULTI                   an access to row f_r also selects row f_ar
                                            (writes both; reads the wired-AND)
              11 ROW_SA                     every cell of row f_r stuck at f_v[0] (wordline)
              12 COL_SA                     every cell of column f_c stuck at f_v[0] (bitline)

Rows and columns are physical indices; row indices at or above ``rows`` name
spare rows, column indices at or above ``bits * mux`` name spare columns.
"""
from __future__ import annotations

from views import Pin

FAULT_BLOCK = r"""
`ifdef OT_MEM_FAULTS
    localparam integer NF = 8;
    reg [3:0]  f_kind [0:NF-1];
    integer    f_r    [0:NF-1];
    integer    f_c    [0:NF-1];
    integer    f_ar   [0:NF-1];
    integer    f_ac   [0:NF-1];
    reg [1:0]  f_v    [0:NF-1];
    integer fk;
    initial for (fk = 0; fk < NF; fk = fk + 1) begin
        f_kind[fk] = 4'd0; f_r[fk] = 0; f_c[fk] = 0; f_ar[fk] = 0; f_ac[fk] = 0; f_v[fk] = 2'd0;
    end
`endif
"""

HELPERS = r"""
    // ---- physical row and column after repair ------------------------------
    function automatic integer phys_row(input integer a);
        integer k, r;
        begin
            r = a / MUX;
            for (k = 0; k < NSR; k = k + 1)
                if (rr_en[k] && rr_addr[k*RA +: RA] == r[RA-1:0]) r = ROWS + k;
            phys_row = r;
        end
    endfunction

    function automatic integer phys_col(input integer b, input integer s);
        integer k, io;
        begin
            io = b;
            for (k = 0; k < NSC; k = k + 1)
                if (cr_en[k] && cr_sel[k*CB +: CB] == b[CB-1:0]) io = BITS + k;
            phys_col = io * MUX + s;
        end
    endfunction

    // ---- one cell, as the sense amplifier sees it ----------------------------
    function automatic cell_read(input integer r, input integer c);
        reg v;
`ifdef OT_MEM_FAULTS
        integer k;
`endif
        begin
            v = arr[r][c];
`ifdef OT_MEM_FAULTS
            for (k = 0; k < NF; k = k + 1) begin
                if ((f_kind[k] == 4'd1 || f_kind[k] == 4'd2) && f_r[k] == r && f_c[k] == c) v = (f_kind[k] == 4'd2);
                if (f_kind[k] == 4'd7 && f_r[k] == r && f_c[k] == c && arr[f_ar[k]][f_ac[k]] == f_v[k][0]) v = f_v[k][1];
                if (f_kind[k] == 4'd11 && f_r[k] == r) v = f_v[k][0];
                if (f_kind[k] == 4'd12 && f_c[k] == c) v = f_v[k][0];
            end
`endif
            cell_read = v;
        end
    endfunction

    task automatic cell_write(input integer r, input integer c, input reg v);
        reg old, nv;
`ifdef OT_MEM_FAULTS
        integer k;
`endif
        begin
            old = arr[r][c];
            nv = v;
`ifdef OT_MEM_FAULTS
            for (k = 0; k < NF; k = k + 1) begin
                if (f_kind[k] == 4'd3 && f_r[k] == r && f_c[k] == c && !old && v) nv = 1'b0;
                if (f_kind[k] == 4'd4 && f_r[k] == r && f_c[k] == c && old && !v) nv = 1'b1;
            end
`endif
            arr[r][c] = nv;
`ifdef OT_MEM_FAULTS
            if (old != nv)
                for (k = 0; k < NF; k = k + 1)
                    if (f_ar[k] == r && f_ac[k] == c && nv == f_v[k][0]) begin
                        if (f_kind[k] == 4'd5) arr[f_r[k]][f_c[k]] = ~arr[f_r[k]][f_c[k]];
                        if (f_kind[k] == 4'd6) arr[f_r[k]][f_c[k]] = f_v[k][1];
                    end
`endif
        end
    endtask

    // ---- decoder: the physical rows an access selects -------------------------
    // returns {sel_n[1:0], r1[31:0], r0[31:0]}; sel_n is 0 (no row: an open decoder
    // output), 1, or 2 (a multi-select).
    function automatic [65:0] decode(input integer a);
        integer r0, r1;
        reg [1:0] sel_n;
`ifdef OT_MEM_FAULTS
        integer k;
`endif
        begin
            r0 = phys_row(a);
            r1 = r0;
            sel_n = 2'd1;
`ifdef OT_MEM_FAULTS
            if (r0 < ROWS)
                for (k = 0; k < NF; k = k + 1) begin
                    if (f_kind[k] == 4'd8 && f_r[k] == r0) sel_n = 2'd0;
                    if (f_kind[k] == 4'd9 && f_r[k] == r0) begin r0 = f_ar[k]; r1 = r0; end
                    if (f_kind[k] == 4'd10 && f_r[k] == r0) begin r1 = f_ar[k]; sel_n = 2'd2; end
                end
`endif
            decode = {sel_n, r1[31:0], r0[31:0]};
        end
    endfunction

    function automatic [BITS-1:0] word_read(input integer a);
        integer b, s, r0, r1, n;
        reg [BITS-1:0] q;
        reg [65:0] dsel;
        begin
            dsel = decode(a);
            r0 = dsel[31:0]; r1 = dsel[63:32]; n = dsel[65:64];
            s = a % MUX;
            for (b = 0; b < BITS; b = b + 1)
                if (n == 0) q[b] = 1'b0;
                else if (n == 1) q[b] = cell_read(r0, phys_col(b, s));
                else q[b] = cell_read(r0, phys_col(b, s)) & cell_read(r1, phys_col(b, s));
            word_read = q;
        end
    endfunction
"""

WRITE_TASK = r"""
    task automatic word_write(input integer a, input [BITS-1:0] d, input [BITS-1:0] m);
        integer b, s, r0, r1, n;
        reg [65:0] dsel;
        begin
            dsel = decode(a);
            r0 = dsel[31:0]; r1 = dsel[63:32]; n = dsel[65:64];
            s = a % MUX;
            for (b = 0; b < BITS; b = b + 1)
                if (m[b] && n != 0) begin
                    cell_write(r0, phys_col(b, s), d[b]);
                    if (n == 2) cell_write(r1, phys_col(b, s), d[b]);
                end
        end
    endtask
"""


def _clog2(n: int) -> int:
    return max(1, (n - 1).bit_length())


def repair_pins(nsr: int, nsc: int, rows: int, bits: int) -> list[Pin]:
    pins: list[Pin] = []
    if nsr:
        pins += [Pin("rr_en", nsr, "input", "control"), Pin("rr_addr", nsr * _clog2(rows), "input", "control")]
    if nsc:
        pins += [Pin("cr_en", nsc, "input", "control"), Pin("cr_sel", nsc * _clog2(bits), "input", "control")]
    return pins


def module_text(name: str, pins: list[Pin], params: dict[str, int], body: str, header: str,
                nsr: int, nsc: int, module_params: str = "") -> str:
    decl = []
    for p in pins:
        rng = f"[{p.width - 1}:0] " if p.width > 1 else ""
        kind = "output reg  " if p.direction == "output" else "input  wire "
        decl.append(f"    {kind}{rng}{p.name}")
    lp = "\n".join(f"    localparam integer {k} = {v};" for k, v in params.items())
    tie = []
    if not nsr:
        tie.append("    wire [0:0] rr_en = 1'b0;\n    wire [RA-1:0] rr_addr = {RA{1'b0}};")
    if not nsc:
        tie.append("    wire [0:0] cr_en = 1'b0;\n    wire [CB-1:0] cr_sel = {CB{1'b0}};")
    return ("`timescale 1ns/1ps\n" f"{header}\n"
            "// verilator lint_off BLKSEQ\n// verilator lint_off WIDTH\n// verilator lint_off UNUSED\n"
            f"module {name} {module_params}(\n" + ",\n".join(decl) + "\n);\n" + lp + "\n" + "\n".join(tie) + "\n" + body +
            "endmodule\n// verilator lint_on BLKSEQ\n// verilator lint_on WIDTH\n// verilator lint_on UNUSED\n")
