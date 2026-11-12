`timescale 1ns/1ps
// HBM-HALFWIDTH-1 formal miter (yosys sat, bounded): 1-beat reference lane (H+1 stages) delayed one more cycle vs
// TX -> H stations -> RX, under the premises P1/P2 built into the producer model (free data, free start, free payload garbage).
module hw_miter #(parameter integer W = 9, parameter integer H = 2, parameter integer BEATS = 2, parameter integer MUTT = 0, parameter integer MUTR = 0) (
    input wire clk, input wire go, input wire [W-1:0] r, input wire [W-1:0] r2
);
    localparam integer BW = (W + BEATS - 1) / BEATS;
    localparam integer PB = $clog2(BEATS);
    function [W-1:0] cls(input integer k);
        integer i;
        begin
            cls = {W{1'b0}};
            for (i = 0; i < W; i = i + 1)
                if (k == 0 ? (i % 8 == 0) : k == 1 ? (i % 8 >= 1 && i % 8 <= 3) : !(i % 8 <= 3)) cls[i] = 1'b1;
        end
    endfunction
    localparam [W-1:0] CM = cls(0), PM = cls(1), LM = cls(2);
    reg [2:0] cnt = 0;
    always @(posedge clk) if (cnt != 3'd7) cnt <= cnt + 1'b1;
    wire rst_n = (cnt >= 3'd2);
    reg started = 0; reg [PB-1:0] ph = 0;
    reg [W-1:0] lastd = 0;
    wire t0 = rst_n && ((!started && go) || (started && ph == 0));
    wire t1 = rst_n && started && ph != 0;
    wire [W-1:0] d0 = (r & CM) | (r & LM) | ((r2 & PM) & {W{r[0]}});
    wire [W-1:0] d1 = (lastd & ~CM & ~PM) | (r2 & PM);
    wire [W-1:0] d = t0 ? d0 : (t1 ? d1 : {W{1'b0}});
    always @(posedge clk) begin
        if (t0) begin lastd <= d0; started <= 1'b1; ph <= PB'(1); end
        else if (t1) ph <= (ph == PB'(BEATS-1)) ? 0 : ph + 1'b1;
    end
    wire [BW-1:0] b_o; wire f_o, fault;
    ot_hbm_hw_lane_tx #(.W(W), .HW(1), .BEATS(BEATS), .CONTROL_MASK(CM), .PAYLOAD_MASK(PM), .GUARD_LEVELS(1), .MUT(MUTT)) tx (.clk(clk), .rst_n(rst_n), .d(d), .b_o(b_o), .f_o(f_o), .fault_o(fault));
    reg [BW-1:0] sb [0:H]; reg [H:0] sf;
    wire [BW-1:0] bi_w = (H == 0) ? b_o : sb[(H > 0) ? H - 1 : 0];
    wire fi_w = (H == 0) ? f_o : sf[(H > 0) ? H - 1 : 0];
    integer s;
    always @(posedge clk) begin
        sb[0] <= b_o; sf[0] <= f_o;
        for (s = 1; s <= H; s = s + 1) begin sb[s] <= sb[s-1]; sf[s] <= sf[s-1]; end
    end
    wire [W-1:0] q;
    ot_hbm_hw_lane_rx #(.W(W), .HW(1), .BEATS(BEATS), .CONTROL_MASK(CM), .MUT(MUTR)) rx (.clk(clk), .rst_n(rst_n), .b_i(bi_w), .f_i(fi_w), .q(q));
    reg [W-1:0] rf [0:H+BEATS];
    integer k;
    initial for (k = 0; k <= H + BEATS; k = k + 1) rf[k] = 0;
    always @(posedge clk) begin
        rf[0] <= d;
        for (k = 1; k <= H + BEATS; k = k + 1) rf[k] <= rf[k-1];
    end
    wire [W-1:0] refq = rf[H+BEATS-1];
    wire [W-1:0] vmask = refq[0] ? {W{1'b1}} : ~PM;
    always @* begin
        if (cnt == 3'd7) begin
            assert (((q ^ refq) & vmask) == {W{1'b0}});
            assert (!fault);
        end
    end
endmodule
