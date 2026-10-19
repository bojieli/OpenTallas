`timescale 1ns/1ps
// Fixed delay line: q is d delayed by D cycles (D = 0 is a wire).  Data lines
// carry no reset -- validity travels on a separate, reset delay line -- so a
// wide operand costs flops and no reset fan-out.
module ot_hdc_delay_ring #(
    parameter integer W = 32,
    parameter integer D = 1,
    parameter integer RESET = 0,
    // RING (CLAUDE HBM-ABSTRACTS views agent, default off): D >= 4 as a ring of D-1 slots plus an output register
    // (slot written at edge e is read into q at edge e + D - 1: the same q as the shift line) -- no flop-to-flop chain
    // for hold repair, every slot written / read through its own one-hot enable
    parameter integer RING = 0,
    // OHREP (LH-SU 10-19, safe-design item 3; default 0 = the g_ring form below, untouched): RING with OHREP > 0
    // keeps ceil(W / OHREP) replicated one-hot slot registers ((* keep *), ot_keep_regs.tcl); copy c drives only the
    // bits [c*OHREP, (c+1)*OHREP) -- each copy bit sees OHREP write enables + OHREP read ANDs instead of 2*W loads
    // (W = 460: 1,381). Same slot sequence, same q edge for edge.
    parameter integer OHREP = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D == 0) begin : g_wire
            assign q = d;
        end else if (D == 1) begin : g_one
            reg [W-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {W{1'b0}};
                    else line <= d;
            end else begin : g_nrst
                always @(posedge clk) line <= d;
            end
            assign q = line;
        end else if (RING != 0 && D >= 4 && OHREP > 0) begin : g_ringr
            localparam integer N = D - 1;
            localparam integer RW = (OHREP < W) ? OHREP : W;   // bits per one-hot copy
            localparam integer NC = (W + RW - 1) / RW;          // one-hot copies
            genvar c, j;
            wire [W-1:0] rd_c [0:NC-1];
            for (c = 0; c < NC; c = c + 1) begin : g_c
                localparam integer LO = c * RW, HI = ((c + 1) * RW > W) ? W : (c + 1) * RW, CW = HI - LO;
                (* keep = "true", dont_touch = "true" *) reg [N-1:0] oh;   // this copy's one-hot slot
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) oh <= {{(N-1){1'b0}}, 1'b1};
                    else oh <= {oh[N-2:0], oh[N-1]};
                wire [CW*N-1:0] slots;
                for (j = 0; j < N; j = j + 1) begin : g_s
                    reg [CW-1:0] m;
                    if (RESET != 0) begin : g_rst
                        always @(posedge clk or negedge rst_n)
                            if (!rst_n) m <= {CW{1'b0}}; else if (oh[j]) m <= d[HI-1:LO];
                    end else begin : g_nrst
                        always @(posedge clk) if (oh[j]) m <= d[HI-1:LO];
                    end
                    assign slots[j*CW +: CW] = m & {CW{oh[j]}};
                end
                reg [CW-1:0] r;
                integer i;
                always @(*) begin
                    r = {CW{1'b0}};
                    for (i = 0; i < N; i = i + 1) r = r | slots[i*CW +: CW];
                end
                reg [CW-1:0] qr;
                if (RESET != 0) begin : g_qrst
                    always @(posedge clk or negedge rst_n) if (!rst_n) qr <= {CW{1'b0}}; else qr <= r;
                end else begin : g_qnrst
                    always @(posedge clk) qr <= r;
                end
                assign q[HI-1:LO] = qr;
            end
        end else if (RING != 0 && D >= 4) begin : g_ring
            localparam integer N = D - 1;
            reg [W-1:0] m [0:N-1];
            reg [N-1:0] oh;                       // one-hot slot of this edge (read, then written)
            reg [W-1:0] qr;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) oh <= {{(N-1){1'b0}}, 1'b1};
                else oh <= {oh[N-2:0], oh[N-1]};
            reg [W-1:0] rd;
            integer i;
            always @(*) begin
                rd = {W{1'b0}};
                for (i = 0; i < N; i = i + 1) rd = rd | (m[i] & {W{oh[i]}});
            end
            genvar j;
            for (j = 0; j < N; j = j + 1) begin : g_s
                if (RESET != 0) begin : g_rst
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) m[j] <= {W{1'b0}}; else if (oh[j]) m[j] <= d;
                end else begin : g_nrst
                    always @(posedge clk) if (oh[j]) m[j] <= d;
                end
            end
            if (RESET != 0) begin : g_qrst
                always @(posedge clk or negedge rst_n) if (!rst_n) qr <= {W{1'b0}}; else qr <= rd;
            end else begin : g_qnrst
                always @(posedge clk) qr <= rd;
            end
            assign q = qr;
        end else begin : g_line
            reg [W*D-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {(W*D){1'b0}};
                    else line <= {line[W*(D-1)-1:0], d};
            end else begin : g_nrst
                always @(posedge clk) line <= {line[W*(D-1)-1:0], d};
            end
            assign q = line[W*D-1 -: W];
        end
    endgenerate
endmodule
