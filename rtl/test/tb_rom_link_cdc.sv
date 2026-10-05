`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Bench of rtl/rom/ot_rom_link_cdc.sv under two independent clocks (gate K3).
//
// The C++ harness (tools/rtl_v41_link_cdc_campaign.py writes it) toggles clk_tx
// and clk_rx at their own periods -- the RX period offset by +PPM parts per
// million -- and drives time_fs, the global simulation time.  The transmitter
// offers a flit in every slot; each flit carries {sequence number, send time}.
// The receiver checks the sequence is gap-free and in order (a dropped,
// duplicated or reordered flit is a mismatch) and measures each flit's
// crossing latency in RX cycles.  Stops after +FLITS flits received or on the
// first overflow; prints one LINKCDC line.
// ---------------------------------------------------------------------------
module tb_rom_link_cdc #(
    parameter integer AW = 4,
    parameter integer SYNC = 2,
    parameter integer SKIP_EVERY = 1024
) (
    input wire        clk_tx,
    input wire        clk_rx,
    input wire [63:0] time_fs,
    input wire [63:0] rx_period_fs
);
    localparam integer W = 128;
    reg [3:0] rt = 0, rr = 0;
    wire rst_tx_n = (rt == 4'hF), rst_rx_n = (rr == 4'hF);
    always @(posedge clk_tx) if (!rst_tx_n) rt <= rt + 1'b1;
    always @(posedge clk_rx) if (!rst_rx_n) rr <= rr + 1'b1;

    reg [63:0] seq_tx = 0;
    wire       slot, ovf, unf, rv;
    wire [W-1:0] rd;
    wire       tv = rst_tx_n && rst_rx_n;
    ot_rom_link_cdc #(.W(W), .AW(AW), .SYNC(SYNC), .SKIP_EVERY(SKIP_EVERY)) dut (
        .clk_tx(clk_tx), .rst_tx_n(rst_tx_n), .tx_valid(tv), .tx_data({seq_tx, time_fs}), .tx_slot(slot),
        .ovf(ovf), .clk_rx(clk_rx), .rst_rx_n(rst_rx_n), .rx_valid(rv), .rx_data(rd), .unf(unf));
    always @(posedge clk_tx) if (tv && slot) seq_tx <= seq_tx + 1;

    longint FLITS;
    longint got = 0, bad = 0, lat_min = 64'h7fffffffffffffff, lat_max = 0, lat_sum = 0;
    reg [63:0] seq_rx = 0;
    longint lat;
    initial if (!$value$plusargs("FLITS=%d", FLITS)) FLITS = 1000000;
    always @(posedge clk_rx) if (rst_rx_n) begin
        if (rv) begin
            if (rd[127:64] != seq_rx) begin
                bad = bad + 1;
                if (bad < 5) $display("SEQ expected=%0d got=%0d", seq_rx, rd[127:64]);
                seq_rx <= rd[127:64] + 1;
            end else seq_rx <= seq_rx + 1;
            lat = (time_fs - rd[63:0]);
            if (lat < lat_min) lat_min = lat;
            if (lat > lat_max) lat_max = lat;
            lat_sum = lat_sum + lat;
            got = got + 1;
        end
        if (got >= FLITS || ovf || unf) begin
            $display("LINKCDC skip_every=%0d aw=%0d sync=%0d flits=%0d mismatches=%0d ovf=%0d unf=%0d lat_min_fs=%0d lat_max_fs=%0d lat_mean_fs=%0d rx_period_fs=%0d",
                     SKIP_EVERY, AW, SYNC, got, bad, ovf, unf, lat_min, lat_max, got ? lat_sum / got : 0, rx_period_fs);
            $finish;
        end
    end
endmodule
