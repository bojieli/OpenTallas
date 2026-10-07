`timescale 1ns/1ps
// Tagged request contract: acceptance is valid && ready; stalled offers may
// alternate. Check delivery as a set, because oq5 reorders tagged responses.
module tb_hbm_accel_smh_oreq;
    reg clk = 0, rst_n = 0, sv = 0, mr = 0;
    always #5 clk = ~clk;
    wire sr, mv;
    reg [41:0] sd = 0;
    wire [41:0] md;
    ot_hbm_accel_smh_oreq #(.W(42)) dut
        (.clk(clk), .rst_n(rst_n), .s_valid(sv), .s_ready(sr),
         .s_data(sd), .m_valid(mv), .m_ready(mr), .m_data(md));
    reg pending [0:8191];
    reg [31:0] rng = 32'h5a176bc9;
    integer sent, received, cycles, id, phase, i, reorder, last_id;
    function [41:0] payload(input integer n);
        payload = {10'h295, 16'hb71c ^ n[15:0], n[15:0]};
    endfunction
    task step(input bit valid_in, input bit ready_in);
        begin
            @(negedge clk);
            sv = valid_in; mr = ready_in; sd = payload(sent);
            @(posedge clk);
            if (mv && mr) begin
                id = md[15:0];
                if (id >= sent || !pending[id] || md !== payload(id))
                    $fatal(1, "OREQ unexpected/duplicate/corrupt delivery %h sent=%0d", md, sent);
                pending[id] = 0;
                received = received + 1;
                if (id < last_id) reorder = reorder + 1;
                last_id = id;
            end
            if (sv && sr) begin pending[sent] = 1; sent = sent + 1; end
            cycles = cycles + 1;
        end
    endtask
    initial begin
        reorder = 0;
        // Reset with occupied slots between phases, then verify no stale request.
        for (phase = 0; phase < 3; phase = phase + 1) begin
            @(negedge clk); rst_n = 0; sv = 0; mr = 0;
            repeat (3) @(negedge clk);
            for (i = 0; i < 8192; i = i + 1) pending[i] = 0;
            sent = 0; received = 0; cycles = 0; last_id = -1;
            rst_n = 1;
            repeat (5) step(0, 1);
            if (received != 0) $fatal(1, "OREQ stale request after reset");
            repeat (256) step(1, 1);
            if (received != 255) $fatal(1, "OREQ cannot sustain one request/cycle");
            repeat (64) step(1, 0);
            // Selectively accept alternating slots, then reverse parity.
            for (i = 0; i < 128; i = i + 1) step(1, i[0]);
            for (i = 0; i < 128; i = i + 1) step(1, !i[0]);
            for (i = 0; i < 8192; i = i + 1) begin
                rng = {rng[30:0], rng[31] ^ rng[21] ^ rng[1] ^ rng[0]};
                step(rng[0] | rng[3], rng[7] & rng[12]);
            end
            repeat (8) step(0, 1);
            if (sent != received) $fatal(1, "OREQ lost request sent=%0d got=%0d", sent, received);
            $display("OREQ phase=%0d PASS sent=%0d received=%0d cycles=%0d", phase, sent, received, cycles);
            repeat (4) step(1, 0);
        end
        if (reorder == 0) $fatal(1, "OREQ test did not exercise reordering");
        $display("OREQ PASS reordered=%0d", reorder);
        $finish;
    end
endmodule
