`timescale 1ns/1ps
module tb_dsrom_c_w5_pg;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0;
    reg sleep_req=0,busy=0,prewake=0,demand=0;
    reg [7:0] debt=0;
    reg iso_ack=0,pgood=0,relock=0,grant=0;
    wire power_req,iso,clock_en,wake,ready;
    wire fault;
    wire [2:0] state;
    reg [1:0] endpoint_busy=0,endpoint_prewake=0;
    reg [7:0] tx_debt=0,rx_debt=0;
    wire link_power,link_iso,link_ready;
    ot_dsrom_c_w5_link_pg #(.ENABLE_PG(1)) link_pg (
        .clk_aon(clk),.rst_n(rst_n),.sleep_req(sleep_req),.demand(demand),
        .endpoint_busy(endpoint_busy),.endpoint_prewake(endpoint_prewake),
        .tx_live_debt(tx_debt),.rx_live_debt(rx_debt),.isolation_ack(iso_ack),
        .power_good(pgood),.relock_ack(relock),.inrush_grant(grant),
        .power_req(link_power),.isolation_req(link_iso),.ready(link_ready));
    ot_dsrom_c_w5_pg #(.ENABLE_PG(1)) dut(
        .clk_aon(clk),.rst_n(rst_n),.sleep_req(sleep_req),.busy(busy),.prewake(prewake),.demand(demand),
        .live_debt(debt),.isolation_ack(iso_ack),.power_good(pgood),.relock_ack(relock),.inrush_grant(grant),
        .power_req(power_req),.isolation_req(iso),.clock_enable(clock_en),.wake_request(wake),.ready(ready),.fault(fault),.state_observe(state));
    wire bypass_power,bypass_iso,bypass_ready,engram_power,engram_iso,engram_ready;
    ot_dsrom_c_w5_pg defaultoff(.clk_aon(clk),.rst_n(rst_n),.sleep_req(sleep_req),.busy(busy),.prewake(prewake),.demand(demand),
        .live_debt(debt),.isolation_ack(iso_ack),.power_good(pgood),.relock_ack(relock),.inrush_grant(grant),
        .power_req(bypass_power),.isolation_req(bypass_iso),.ready(bypass_ready));
    ot_dsrom_c_w5_pg #(.ENABLE_PG(1),.ALWAYS_ON(1)) engram(.clk_aon(clk),.rst_n(rst_n),.sleep_req(sleep_req),.busy(busy),.prewake(prewake),.demand(demand),
        .live_debt(debt),.isolation_ack(iso_ack),.power_good(pgood),.relock_ack(relock),.inrush_grant(grant),
        .power_req(engram_power),.isolation_req(engram_iso),.ready(engram_ready));
    reg [3:0] start=0;
    wire [3:0] neighbor;
    // 0->2, 2->1, 1->3, 3->0: a non-identity successor map.
    ot_dsrom_c_w5_prewake #(.N(4),.SUCCESSOR_EDGES(16'h1284)) map(.phase_start(start),.neighbor_prewake(neighbor));
    wire vout;
    wire [31:0] dout;
    reg [31:0] payload=32'hdeadbeef;
    ot_dsrom_c_w5_isolation clamp(.isolation_req(iso),.valid_in(1'b1),.data_in(payload),.valid_out(vout),.data_out(dout));
    integer cycle=0,idx,late,seen_wake=0;
    task tick;
        begin @(posedge clk); #1; cycle=cycle+1;
            if (!bypass_power || bypass_iso || !engram_power || engram_iso) $fatal(1,"bypass/Engram");
            if (iso && (vout || dout!=0)) $fatal(1,"isolation clamp");
            if (rst_n && (!bypass_ready || !engram_ready)) $fatal(1,"bypass readiness");
            if (!iso && (!vout || dout!==payload)) $fatal(1,"payload changed");
        end
    endtask
    task boot;
        begin rst_n=0;tick();rst_n=1;pgood=1;relock=1;grant=1;repeat(5)tick();if(!ready)$fatal(1,"boot");end
    endtask
    task park;
        begin sleep_req=1;busy=0;prewake=0;demand=0;debt=0;iso_ack=0;tick();
            if(!iso || !power_req)$fatal(1,"isolate before power off");
            repeat(2)tick();if(!power_req)$fatal(1,"no isolation acknowledgment");
            iso_ack=1;tick();if(power_req || ready)$fatal(1,"off");pgood=0;relock=0;grant=0;
        end
    endtask
    initial begin
        boot();
        sleep_req=1;busy=1;
        tx_debt=8'h80;repeat(2)tick();if(!link_power || link_iso)$fatal(1,"link TX debt");
        rx_debt=8'h01;tx_debt=0;repeat(2)tick();if(!link_power || link_iso)$fatal(1,"link RX debt");
        endpoint_busy=2'b10;rx_debt=0;repeat(2)tick();if(!link_power || link_iso)$fatal(1,"link endpoint 1");
        endpoint_busy=2'b01;repeat(2)tick();if(!link_power || link_iso)$fatal(1,"link endpoint 0");
        sleep_req=0;endpoint_busy=0;busy=0;
        for(idx=0;idx<4;idx=idx+1)begin start=1<<idx;#1;
            case(idx)
            0:if(neighbor!=4'b0100)$fatal(1,"0 successor");
            1:if(neighbor!=4'b1000)$fatal(1,"1 successor");
            2:if(neighbor!=4'b0010)$fatal(1,"2 successor");
            3:if(neighbor!=4'b0001)$fatal(1,"3 successor");
            endcase
        end
        start=0;
        // Every independently retained live-debt class inhibits sleep.
        sleep_req=1;
        for(idx=0;idx<8;idx=idx+1)begin debt=1<<idx;repeat(2)tick();
            if(!power_req || iso || !ready)$fatal(1,"live debt gated");end
        debt=0;sleep_req=0;
        park();
        prewake=1;tick();prewake=0;
        repeat(3)tick();if(power_req || !wake)$fatal(1,"prewake must latch while grant delayed");
        grant=1;tick();if(!power_req || !iso || ready)$fatal(1,"granted ramp");
        pgood=1;repeat(3)tick();if(ready || !iso)$fatal(1,"relock not free");
        relock=1;repeat(2)tick();if(ready)$fatal(1,"release dwell missing");
        tick();if(!ready || iso)$fatal(1,"wake complete");
        sleep_req=0;
        // A sleep request racing new debt during isolation must abort.
        sleep_req=1;iso_ack=0;tick();debt=8'h80;iso_ack=1;tick();
        if(!power_req)$fatal(1,"debt arrived during isolate");
        repeat(4)tick();if(!ready)$fatal(1,"debt abort");debt=0;sleep_req=0;
        // Explicit non-identity predecessor pulse drives the next wake.
        park();start=4'b0001;#1;prewake=neighbor[2];tick();start=0;prewake=0;
        grant=1;tick();pgood=1;tick();relock=1;repeat(3)tick();
        if(!ready)$fatal(1,"neighbor prewake");
        // Scheduled arrival has the exact same cycle and payload as bypass.
        sleep_req=0;demand=1;busy=1;tick();
        if(!ready || dout!==payload || !vout)$fatal(1,"scheduled token delayed");
        $display("MEASURED directed_nonidentity_prewake added_token_cycles=0 payload_exact=1");
        busy=0;demand=0;park();
        // Late wake exposes a positive stall, never a fabricated zero.
        demand=1;late=0;repeat(3)begin tick();if(!ready)late=late+1;end
        grant=1;tick();if(!ready)late=late+1;
        pgood=1;tick();if(!ready)late=late+1;
        relock=1;repeat(3)begin tick();if(!ready)late=late+1;end
        if(late==0 || !ready)$fatal(1,"late wake must stall");
        $display("MEASURED late_wake added_token_cycles=%0d",late);
        relock=0;tick();if(ready || !iso)$fatal(1,"lock loss failclosed");
        // Reset does not clear externally retained debt.
        debt=8'h40;rst_n=0;tick();rst_n=1;pgood=1;relock=1;repeat(5)tick();
        if(debt!=8'h40 || !ready || !power_req)$fatal(1,"retained debt across reset");
        // One control-state bit flips to another legal state: parity catches it.
        force dut.parity=1'b1;#1;
        if(ready || !iso || clock_en)$fatal(1,"control fault did not clamp");
        tick();release dut.parity;tick();if(!fault || ready || !iso)$fatal(1,"fault not sticky");
        $display("PASS W5 digital_fixture cycles=%0d analog_guarantee=0",cycle);$finish;
    end
endmodule
