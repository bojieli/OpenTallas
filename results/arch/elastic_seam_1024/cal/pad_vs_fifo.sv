// Sizing calibration only (ELASTIC lane, 2026-10-24): NOT design RTL, not instantiated anywhere.
// cal_pad  = the R8 landing pad as the binder realises it (ot_dp_dly: D reset-less stages, W bits).
// cal_erx  = elastic receive side of a credit seam: D-entry FIFO (reset-less data, reset ptrs/count),
//            enq on in_v, deq by the consumer's valid-gated issue, one credit pulse back per deq.
// cal_etx  = elastic send side: credit counter (starts at D), stall when 0.
module cal_pad #(parameter integer W = 64, parameter integer D = 2) (
    input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    reg [W-1:0] r [0:D-1];
    integer i;
    always @(posedge clk) begin
        r[0] <= d;
        for (i = 1; i < D; i = i + 1) r[i] <= r[i-1];
    end
    assign q = r[D-1];
endmodule

module cal_erx #(parameter integer W = 64, parameter integer D = 6) (
    input wire clk, input wire rst_n,
    input wire in_v, input wire [W-1:0] in_d,
    input wire deq, output wire out_v, output wire [W-1:0] out_d, output reg cr_o);
    localparam integer AW = (D > 1) ? $clog2(D) : 1;
    reg [W-1:0] m [0:D-1];
    reg [AW-1:0] wp, rp;
    reg [AW:0] cnt;
    wire do_deq = deq && (cnt != 0);
    always @(posedge clk) if (in_v) m[wp] <= in_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp <= 0; rp <= 0; cnt <= 0; cr_o <= 1'b0; end
        else begin
            if (in_v) wp <= (wp == D - 1) ? 0 : wp + 1'b1;
            if (do_deq) rp <= (rp == D - 1) ? 0 : rp + 1'b1;
            cnt <= cnt + in_v - do_deq;
            cr_o <= do_deq;
        end
    assign out_v = cnt != 0;
    assign out_d = m[rp];
endmodule

module cal_etx #(parameter integer D = 6) (
    input wire clk, input wire rst_n, input wire want, input wire cr_i, output wire send);
    reg [$clog2(D + 1):0] c;
    assign send = want && (c != 0);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) c <= D[$clog2(D + 1):0];
        else c <= c - send + cr_i;
endmodule
