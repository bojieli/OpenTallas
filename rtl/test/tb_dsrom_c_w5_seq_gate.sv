`timescale 1ns/1ps
module tb_dsrom_c_w5_seq_gate;
    reg clk=0;
    always #5 clk=~clk;
    reg rst=0, start=0, idle=1, engines=1, sleep=0, prewake=0;
    reg [55:0] payload=0;
    reg [7:0] debt=0, known=8'hff;
    reg isoack=1, good=1, relock=1, grant=0;
    wire ready, fire, pwr, iso, ce, wake, fault;
    wire [55:0] out;
    wire [31:0] debit;
    wire field_clk, engram_clk;
    wire bypass_fire, bypass_ready, bypass_power, bypass_iso, bypass_ce, bypass_fault;
    wire [55:0] bypass_payload;
    wire [31:0] bypass_debit;
    integer waits;
    ot_dsrom_c_w5_seq_gate #(.ENABLE_PG(1)) dut (
        .clk_aon(clk), .rst_n(rst), .start(start), .sequencer_idle(idle),
        .engines_idle(engines), .payload(payload), .sleep_req(sleep),
        .neighbor_prewake(prewake), .retained_live_debt(debt), .debt_known(known),
        .isolation_ack(isoack), .power_good(good), .relock_ack(relock),
        .inrush_grant(grant), .start_ready(ready), .core_start(fire),
        .core_payload(out), .power_req(pwr), .isolation_req(iso),
        .clock_enable(ce), .wake_request(wake), .fault(fault), .added_cycles(debit));
    ot_dsrom_c_w5_clock_gate #(.ENABLE_PG(1)) cg(clk,ce,field_clk);
    ot_dsrom_c_w5_clock_gate #(.ENABLE_PG(1),.ALWAYS_ON(1)) eg(clk,ce,engram_clk);
    ot_dsrom_c_w5_seq_gate disabled (
        .clk_aon(clk), .rst_n(rst), .start(start), .sequencer_idle(idle),
        .engines_idle(engines), .payload(payload), .sleep_req(sleep),
        .neighbor_prewake(prewake), .retained_live_debt(debt), .debt_known(known),
        .isolation_ack(isoack), .power_good(good), .relock_ack(relock),
        .inrush_grant(grant), .start_ready(bypass_ready), .core_start(bypass_fire),
        .core_payload(bypass_payload), .power_req(bypass_power), .isolation_req(bypass_iso),
        .clock_enable(bypass_ce), .wake_request(), .fault(bypass_fault), .added_cycles(bypass_debit));
    task step;
        begin
            @(posedge clk); #1; @(negedge clk); #1;
            if (bypass_fire!==start || bypass_payload!==payload || !bypass_ready ||
                !bypass_power || bypass_iso || !bypass_ce || bypass_fault || bypass_debit!=0)
                $fatal(1,"default-off changed existing sequencer inputs");
        end
    endtask
    task reset;
        begin rst=0; step; rst=1; step; end
    endtask
    initial begin
        reset;
        if (!ready || fire || !iso || pwr) $fatal(1,"cold admission");
        payload=56'h123456789abcde; start=1; step; start=0;
        payload=0; waits=1;
        repeat(3) begin
            if (fire || !wake || !iso || field_clk) $fatal(1,"grant wait");
            step; waits=waits+1;
        end
        grant=1;
        while (!fire) begin step; waits=waits+1; end
        // waits includes the release cycle whose debit is already counted.
        if (out!==56'h123456789abcde || debit!=waits || fault)
            $fatal(1,"retained payload/wait debit=%0d measured=%0d",debit,waits);
        $display("W5_SEQUENCER_ADMISSION late_start_added_cycles=%0d",debit);
        step;
        // Ready starts pass through without a register or latency debit.
        payload=56'hfedcba98765432; start=1; #1;
        if (!fire || out!==payload) $fatal(1,"ready passthrough");
        step; start=0;
        if (debit!=0) $fatal(1,"ready debit");
        idle=0; sleep=1;
        repeat(3) begin step; if (iso || !pwr) $fatal(1,"actual busy"); end
        idle=1; debt=8'h20;
        repeat(3) begin step; if (iso || !pwr) $fatal(1,"adder held debt"); end
        debt=0; known=8'hbf;
        repeat(3) begin step; if (iso || !pwr) $fatal(1,"unbound consumer debt"); end
        known=8'hff;
        step; step;
        if (!iso || pwr) $fatal(1,"sleep after retirement");
        // Low-phase latch must hold a clock pulse when enable changes high.
        force ce=1; #1; @(posedge clk); #1;
        if (!field_clk || !engram_clk) $fatal(1,"clock rise");
        force ce=0; #1;
        if (!field_clk || !engram_clk) $fatal(1,"truncated pulse");
        @(negedge clk); #1; @(posedge clk); #1;
        if (field_clk || !engram_clk) $fatal(1,"field gated Engram AON");
        release ce; @(negedge clk); #1;
        sleep=0; start=1; payload=1; step; start=0;
        start=1; payload=2; step; start=0;
        if (!fault || fire || !iso) $fatal(1,"duplicate start lost silently");
        reset;
        while (iso) step;
        idle=0; good=0; step;
        if (!fault || !iso) $fatal(1,"rail loss during execution");
        idle=1; good=1; reset;
        while (iso) step;
        sleep=1; step; step; sleep=0;
        start=1; payload=3; step; start=0;
        force dut.held_payload=56'h4; #1;
        if (!fault || fire) $fatal(1,"retained packet protection");
        release dut.held_payload;
        $display("PASS W5 sequencer-admission component, debt, latency and clock-gate checks");
        $finish;
    end
endmodule
