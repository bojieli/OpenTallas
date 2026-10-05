// tb_chip_v41_pg_ctrl -- self-checking bench of the stage power-gating controller (W18).
// Each ring segment is modelled as a daisy chain whose ack follows its enable after a random 1..8-cycle
// delay (rise) and 1..4 (fall).  Checked on every cycle:
//   * isolation is on whenever any segment is off or reset is asserted;
//   * clk_en only with every segment acknowledged; pwr_good only with iso released, reset released, clk on;
//   * consecutive segment enables are >= cfg_step cycles apart and in order (bounded rush current);
//   * the domain reset is held >= cfg_rst clocked cycles after the last ack;
//   * wake latency (req_on -> pwr_good) at NSUB = 100, cfg_step = 10 is reported in cycles.
// A dead segment (ack stuck low) must latch fault and keep the domain isolated.
`timescale 1ns/1ps
module tb_chip_v41_pg_ctrl;
    localparam int NSUB = 100;
    logic clk = 0, rst_n = 0, req_on = 0;
    logic [15:0] cfg_step = 16'd10, cfg_ack_to = 16'd64;
    logic [7:0]  cfg_rst = 8'd8;
    logic [NSUB-1:0] sw_en, sw_ack;
    logic iso_n, dom_rst_n, clk_en, pwr_good, fault;
    int dead = -1;                                     // index of a stuck segment (fault test)
    always #0.46 clk = ~clk;                           // 1.087 GHz

    ot_chip_v41_pg_ctrl #(.NSUB(NSUB)) dut (.*);

    // ring model
    int dly [NSUB];
    always @(posedge clk) begin
        for (int i = 0; i < NSUB; i++) begin
            if (sw_en[i] != sw_ack[i]) begin
                if (dly[i] == 0) dly[i] <= sw_en[i] ? 1 + $urandom_range(7) : 1 + $urandom_range(3);
                else if (dly[i] == 1) begin sw_ack[i] <= (i == dead) ? 1'b0 : sw_en[i]; dly[i] <= 0; end
                else dly[i] <= dly[i] - 1;
            end
        end
    end
    initial begin sw_ack = '0; foreach (dly[i]) dly[i] = 0; end

    // checkers
    int errors = 0, last_en_cyc = -1000, cyc = 0, last_ack_cyc = 0, rst_hold = 0, n_en = 0;
    logic [NSUB-1:0] prev_en = '0;
    logic prev_rst_n = 1'b0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (rst_n) begin
            if (iso_n && (!(&sw_ack) || !dom_rst_n)) begin errors++; $display("ERR iso released while unpowered/reset @%0d", cyc); end
            if (clk_en && !(&sw_ack)) begin errors++; $display("ERR clk_en without all acks @%0d", cyc); end
            if (pwr_good && !(iso_n && dom_rst_n && clk_en)) begin errors++; $display("ERR pwr_good early @%0d", cyc); end
            for (int i = 0; i < NSUB; i++) if (sw_en[i] && !prev_en[i]) begin
                if (i > 0 && !prev_en[i-1]) begin errors++; $display("ERR out-of-order enable %0d @%0d", i, cyc); end
                if (cyc - last_en_cyc < cfg_step && !(i == 0)) begin errors++; $display("ERR spacing %0d @%0d", i, cyc); end
                last_en_cyc <= cyc; n_en++;
            end
            if (&sw_ack && !dom_rst_n && clk_en) rst_hold <= rst_hold + 1;
            if (dom_rst_n && !prev_rst_n && rst_hold < cfg_rst - 1) begin errors++; $display("ERR reset too short %0d", rst_hold); end
            if (!dom_rst_n && !clk_en) rst_hold <= 0;
        end
        prev_en <= sw_en;
        prev_rst_n <= dom_rst_n;
    end

    task automatic wake(output int lat);
        int t0;
        req_on = 1; t0 = cyc;
        while (!pwr_good && !fault) @(posedge clk);
        lat = cyc - t0;
    endtask
    task automatic sleep_(output int lat);
        int t0;
        req_on = 0; t0 = cyc;
        while (dut.st != dut.S_OFF && !fault) @(posedge clk);
        lat = cyc - t0;
    endtask

    int wl[4], sl[4];
    initial begin
        repeat (5) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
        for (int k = 0; k < 4; k++) begin
            wake(wl[k]); repeat (20 + k * 7) @(posedge clk);
            sleep_(sl[k]); repeat (5) @(posedge clk);
        end
        // request change mid-sequence: drop req during power-up, then raise during power-down
        req_on = 1; repeat (300) @(posedge clk); req_on = 0;
        while (dut.st != dut.S_OFF) @(posedge clk);
        req_on = 1; while (!pwr_good) @(posedge clk); req_on = 0; @(posedge clk); req_on = 1;
        while (!pwr_good) @(posedge clk);
        req_on = 0; while (dut.st != dut.S_OFF) @(posedge clk);
        if (fault) begin errors++; $display("ERR spurious fault"); end
        // dead segment -> fault, domain stays isolated
        dead = 37; req_on = 1; repeat (2000) @(posedge clk);
        if (!fault || iso_n || pwr_good) begin errors++; $display("ERR dead ring not detected"); end
        $display("W18_PG_RESULT nsub=%0d step=%0d wake_cycles=%0d,%0d,%0d,%0d sleep_cycles=%0d,%0d,%0d,%0d wake_ns=%.1f enables=%0d fault_detected=%0d errors=%0d",
                 NSUB, cfg_step, wl[0], wl[1], wl[2], wl[3], sl[0], sl[1], sl[2], sl[3], wl[0] * 0.92, n_en, fault, errors);
        if (errors == 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
