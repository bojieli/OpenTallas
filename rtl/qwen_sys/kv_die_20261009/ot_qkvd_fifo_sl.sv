`timescale 1ns/1ps
// el1011-q-kvd 2026-10-11: one SW-bit slice of a registered-head FIFO (the RH=1 behaviour of ot_qkvd_fifo), with its
// OWN copy of the control state (one-hot write / read pointers, head valid, array count).  A W-bit buffer is W/SW of
// these under keep_hierarchy, so no pointer / enable / select drives more than SW bits (textbook class 2: the binary
// rp / wp of the flat FIFO drove every bit of a 528-bit mux and decode).  Datapath (array, head) has no reset.
module ot_qkvd_fifo_sl #(
    parameter integer SW = 66,
    parameter integer D  = 8
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          push,
    input  wire [SW-1:0] din,
    input  wire          pop,
    output wire [SW-1:0] dout,
    output wire          empty,
    output reg  [$clog2(D+1)-1:0] count
);
    reg [SW-1:0] mem [0:D-1];
    reg [D-1:0]  woh, roh;
    reg [SW-1:0] hd;
    reg          hv;
    reg [$clog2(D+1)-1:0] mn;
    wire take = !hv || pop;
    wire byp  = take && (mn == 0) && push;
    wire ld   = take && (mn != 0);
    wire adv  = ld || byp;
    reg  [SW-1:0] rd;
    integer k;
    always @* begin
        rd = {SW{1'b0}};
        for (k = 0; k < D; k = k + 1) rd = rd | (roh[k] ? mem[k] : {SW{1'b0}});
    end
    assign dout  = hd;
    assign empty = !hv;
    always @(posedge clk) begin
        for (k = 0; k < D; k = k + 1) if (push && woh[k]) mem[k] <= din;
`ifdef KVD_FBMUT
        if (ld) hd <= rd; else if (byp) hd <= din ^ {{(SW-1){1'b0}}, 1'b1};   // bench mutant: bypass word corrupted
`else
        if (ld) hd <= rd; else if (byp) hd <= din;
`endif
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin woh <= {{(D-1){1'b0}}, 1'b1}; roh <= {{(D-1){1'b0}}, 1'b1}; mn <= 0; hv <= 1'b0; count <= 0; end
        else begin
            if (push) woh <= (woh << 1) | (woh >> (D - 1));
            if (adv)  roh <= (roh << 1) | (roh >> (D - 1));
            mn <= mn + (push ? 1'b1 : 1'b0) - (adv ? 1'b1 : 1'b0);
            if (ld || byp) hv <= 1'b1; else if (pop) hv <= 1'b0;
            count <= count + (push ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
        end
endmodule

// A W-bit registered-head FIFO as NS = W/SW keep_hierarchy slices (slice 0 supplies empty / count).
module ot_qkvd_fifo_sliced #(
    parameter integer W  = 528,
    parameter integer SW = 66,
    parameter integer D  = 8,
    parameter integer PIQ = 0                // 1: pop registered once per slice (pin register; pop acts one cycle later)
) (
    input  wire          clk,
    input  wire [W/SW-1:0] rst_n,            // one reset copy per slice (relay regions)
    input  wire          push,
    input  wire [W-1:0]  din,
    input  wire          pop,
    output wire [W-1:0]  dout,
    output wire          empty,
    output wire [$clog2(D+1)-1:0] count
);
    localparam integer NS = W / SW;
    wire [NS-1:0] e;
    wire [$clog2(D+1)-1:0] c [0:NS-1];
    genvar s;
    generate for (s = 0; s < NS; s = s + 1) begin : g_s
        wire pop_e;
        if (PIQ != 0) begin : g_piq
            (* keep *) reg pop_q;
            always @(posedge clk or negedge rst_n[s]) if (!rst_n[s]) pop_q <= 1'b0; else pop_q <= pop;
`ifdef KVD_PIQMUT
            assign pop_e = pop;            // mutant: pop pin not registered (acts a cycle early)
`else
            assign pop_e = pop_q;
`endif
        end else begin : g_npiq
            assign pop_e = pop;
        end
        (* keep_hierarchy *) ot_qkvd_fifo_sl #(.SW(SW), .D(D)) u_sl (.clk(clk), .rst_n(rst_n[s]), .push(push),
            .din(din[SW*s +: SW]), .pop(pop_e), .dout(dout[SW*s +: SW]), .empty(e[s]), .count(c[s]));
    end endgenerate
    assign empty = e[0];
    assign count = c[0];
endmodule
