`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ASAP7 compiled-SRAM black boxes, as the pinned openroad/orfs:latest image
// ships them (docs/CHIP_ARCHITECTURE_DESIGN.md section 11.2).
//
// These declarations are NOT a memory model.  They are the synthesis-visible
// port lists of the FakeRAM 2.0 parts whose abstract LEF lives at
// platforms/asap7/lef/<name>.lef and whose NLDM liberty lives at
// platforms/asap7/lib/NLDM/<name>.lib inside that image.  Every port name,
// width and direction below was read out of those two files on 2026-09-05,
// not guessed:
//
//   LEF   PIN clk / addr_in[AW-1:0] / ce_in / we_in / wd_in[DW-1:0] /
//         rd_out[DW-1:0], plus the VDD / VSS INOUT power pins, which are
//         connected by the PDN and are therefore absent from this Verilog
//         view (the flow's standard treatment for a hard macro).
//   LIB   memory() { type: ram; address_width: AW; word_width: DW }, one
//         clock, a rising_edge memory_read arc from clk to rd_out and a
//         memory_write on wd_in clocked_on clk, setup/hold on addr_in,
//         ce_in, we_in and wd_in.  One port.  No byte enable.  No read
//         enable separate from ce_in.  min_period 0.157 ns on all parts.
//
// The operation the liberty states, and that every wrapper in this cluster
// assumes, is therefore the plain single-port synchronous RAM:
//
//     always @(posedge clk) if (ce_in) begin
//         if (we_in) mem[addr_in] <= wd_in;   // rd_out holds
//         else       rd_out       <= mem[addr_in];
//     end
//
// so a read costs exactly one cycle of latency, there is no simultaneous
// read and write, and a whole word is written or none of it is.
//
// The parts are `fakeram`: plausible geometry with a black-box timing model,
// not characterised silicon (section 11.2, final paragraph).  They establish
// that macro placement, PDN over a macro, halo and pin access work in this
// flow.  No memory energy, array timing or yield figure may be derived from
// them, and the behavioural body below -- compiled only under
// OT_A3_FAKERAM_BEHAVIOURAL, which no physical or lint flow defines -- is a
// convenience for future simulation, not a characterisation either.
//
// Areas and footprints, from the same two files:
//
//   fakeram_256x128    4 KiB   16.72 x  84.00 um   1,375.941 um^2   AW 8  DW 128
//   fakeram_512x128    8 KiB   66.50 x  42.00 um   2,751.883 um^2   AW 9  DW 128
//   fakeram_2048x128  32 KiB   66.50 x 166.60 um  11,007.531 um^2   AW 11 DW 128
//   fakeram_256x64     2 KiB   16.72 x  42.00 um     687.971 um^2   AW 8  DW 64
//   fakeram7_256x32    1 KiB    8.36 x  42.00 um     343.985 um^2   AW 8  DW 32
//
// fakeram_512x8 (512 B, AW 9, DW 8) is declared here too because section
// 11.2 decision (a) names eight of them for the IRS, and the report that
// accompanies this file explains why the issue-record store cannot use them.
// It is declared, not instantiated.
// ---------------------------------------------------------------------------

/* verilator lint_off DECLFILENAME */
/* verilator lint_off UNUSEDSIGNAL */
/* verilator lint_off UNDRIVEN */

`ifdef OT_A3_FAKERAM_BEHAVIOURAL
// Convenience simulation bodies.  Not a characterised memory model.
module fakeram_256x128 (
    input  wire         clk,
    input  wire [7:0]   addr_in,
    input  wire         ce_in,
    input  wire         we_in,
    input  wire [127:0] wd_in,
    output reg  [127:0] rd_out
);
    reg [127:0] mem [0:255];
    always @(posedge clk)
        if (ce_in) begin
            if (we_in) mem[addr_in] <= wd_in;
            else       rd_out       <= mem[addr_in];
        end
endmodule

module fakeram_512x128 (
    input  wire         clk,
    input  wire [8:0]   addr_in,
    input  wire         ce_in,
    input  wire         we_in,
    input  wire [127:0] wd_in,
    output reg  [127:0] rd_out
);
    reg [127:0] mem [0:511];
    always @(posedge clk)
        if (ce_in) begin
            if (we_in) mem[addr_in] <= wd_in;
            else       rd_out       <= mem[addr_in];
        end
endmodule

module fakeram_2048x128 (
    input  wire         clk,
    input  wire [10:0]  addr_in,
    input  wire         ce_in,
    input  wire         we_in,
    input  wire [127:0] wd_in,
    output reg  [127:0] rd_out
);
    reg [127:0] mem [0:2047];
    always @(posedge clk)
        if (ce_in) begin
            if (we_in) mem[addr_in] <= wd_in;
            else       rd_out       <= mem[addr_in];
        end
endmodule

module fakeram_256x64 (
    input  wire        clk,
    input  wire [7:0]  addr_in,
    input  wire        ce_in,
    input  wire        we_in,
    input  wire [63:0] wd_in,
    output reg  [63:0] rd_out
);
    reg [63:0] mem [0:255];
    always @(posedge clk)
        if (ce_in) begin
            if (we_in) mem[addr_in] <= wd_in;
            else       rd_out       <= mem[addr_in];
        end
endmodule

module fakeram7_256x32 (
    input  wire        clk,
    input  wire [7:0]  addr_in,
    input  wire        ce_in,
    input  wire        we_in,
    input  wire [31:0] wd_in,
    output reg  [31:0] rd_out
);
    reg [31:0] mem [0:255];
    always @(posedge clk)
        if (ce_in) begin
            if (we_in) mem[addr_in] <= wd_in;
            else       rd_out       <= mem[addr_in];
        end
endmodule

module fakeram_512x8 (
    input  wire       clk,
    input  wire [8:0] addr_in,
    input  wire       ce_in,
    input  wire       we_in,
    input  wire [7:0] wd_in,
    output reg  [7:0] rd_out
);
    reg [7:0] mem [0:511];
    always @(posedge clk)
        if (ce_in) begin
            if (we_in) mem[addr_in] <= wd_in;
            else       rd_out       <= mem[addr_in];
        end
endmodule

`else
// The synthesis view: an empty module carrying the (* blackbox *) attribute,
// so Yosys keeps every instance as a cell of that name and OpenROAD binds it
// to the LEF/liberty pair the platform supplies.
(* blackbox *)
module fakeram_256x128 (
    input  wire         clk,
    input  wire [7:0]   addr_in,
    input  wire         ce_in,
    input  wire         we_in,
    input  wire [127:0] wd_in,
    output wire [127:0] rd_out
);
endmodule

(* blackbox *)
module fakeram_512x128 (
    input  wire         clk,
    input  wire [8:0]   addr_in,
    input  wire         ce_in,
    input  wire         we_in,
    input  wire [127:0] wd_in,
    output wire [127:0] rd_out
);
endmodule

(* blackbox *)
module fakeram_2048x128 (
    input  wire         clk,
    input  wire [10:0]  addr_in,
    input  wire         ce_in,
    input  wire         we_in,
    input  wire [127:0] wd_in,
    output wire [127:0] rd_out
);
endmodule

(* blackbox *)
module fakeram_256x64 (
    input  wire        clk,
    input  wire [7:0]  addr_in,
    input  wire        ce_in,
    input  wire        we_in,
    input  wire [63:0] wd_in,
    output wire [63:0] rd_out
);
endmodule

(* blackbox *)
module fakeram7_256x32 (
    input  wire        clk,
    input  wire [7:0]  addr_in,
    input  wire        ce_in,
    input  wire        we_in,
    input  wire [31:0] wd_in,
    output wire [31:0] rd_out
);
endmodule

(* blackbox *)
module fakeram_512x8 (
    input  wire       clk,
    input  wire [8:0] addr_in,
    input  wire       ce_in,
    input  wire       we_in,
    input  wire [7:0] wd_in,
    output wire [7:0] rd_out
);
endmodule
`endif

/* verilator lint_on UNDRIVEN */
/* verilator lint_on UNUSEDSIGNAL */
/* verilator lint_on DECLFILENAME */
