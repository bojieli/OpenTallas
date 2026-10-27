`timescale 1ns/1ps
// ROWX packed-slot <-> existing S81 XB/MU landing format. No arbitration or backpressure.
// TX and RX each add exactly one registered edge. The compiler includes both in each physical link's latency.
// Insert TX before the endpoint's existing ro pin pipeline; receive ml_wv/ml_wd before the normal MU landing store.
// tx_book/rx_book and identities are compiler-booked static controls, held through their complete windows.
// Normal MU landing traffic outside rx_book passes untouched; collision/malformed traffic sets sticky assertions.
// This codec does not select a PHY copy. The plan/compiler must provide a legal circuit for each chain direction.
module dsdv_rowx_xb #(parameter integer MUT = 0) (
    input wire clk, input wire rst_n,
    input wire tx_book, input wire [3:0] sid,
    input wire [9:0] user_id, input wire [20:0] position,
    input wire tx_v, input wire [1023:0] tx_d, input wire [7:0] tx_index,
    output reg ring_v, output reg [1103:0] ring_d,
    input wire rx_book, input wire ml_v, input wire [1103:0] ml_d,
    output reg rx_v, output reg [1023:0] rx_d,
    output wire pass_v, output wire [1103:0] pass_d,
    output reg fault
);
    wire [1023:0] payload = (MUT == 1) ? {tx_d[511:0],tx_d[1023:512]} : tx_d;
    wire [9:0] user_tx = (MUT == 2) ? (user_id ^ 10'd1) : user_id;
    wire [1103:0] encoded = {26'd0,position,user_tx,1'b1,1'b1,payload,tx_index,sid,5'd0,3'd2,1'b1};
    wire rx_bad = !ml_d[0] || ml_d[3:1] != 3'd2 || !ml_d[1045] || !ml_d[1046] ||
                  ml_d[1056:1047] != user_id || ml_d[1077:1057] != position || |ml_d[1103:1078];
    reg previous_tx;
    assign pass_v = ml_v && !rx_book;
    assign pass_d = ml_d;
    always @(posedge clk) begin
        if (tx_v && tx_book) ring_d <= encoded;
        if (ml_v && rx_book) rx_d <= ml_d[1044:21];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ring_v<=1'b0; rx_v<=1'b0; fault<=1'b0; previous_tx<=1'b0; end
        else begin
            ring_v <= tx_v && tx_book;
            rx_v <= ml_v && rx_book;
            previous_tx <= tx_v;
            if (tx_v && (!tx_book || previous_tx)) fault<=1'b1; // PK=1: at most one packed beat every two edges
            if (ml_v && rx_book && rx_bad) fault<=1'b1;
        end
    end
endmodule
