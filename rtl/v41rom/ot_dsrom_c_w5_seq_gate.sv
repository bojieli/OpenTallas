// Always-on start admission for the actual V4.1 sequencer successor.
// External debt and its known mask MUST come from retained/live signals, not
// a reset-cleared snapshot. No power/clock switch or CDC is fabricated here.
module ot_dsrom_c_w5_seq_gate #(
    parameter bit ENABLE_PG=1'b0,
    parameter integer PAYLOAD_W=56,
    parameter integer GUARD_CYCLES=2
) (
    input wire clk_aon, rst_n,
    input wire start, sequencer_idle, engines_idle,
    input wire [PAYLOAD_W-1:0] payload,
    input wire sleep_req, neighbor_prewake,
    input wire [7:0] retained_live_debt, debt_known,
    input wire isolation_ack, power_good, relock_ack, inrush_grant,
    output wire start_ready, core_start,
    output wire [PAYLOAD_W-1:0] core_payload,
    output wire power_req, isolation_req, clock_enable, wake_request,
    output wire fault,
    output reg [31:0] added_cycles
);
    reg pending, sticky_fault, parity;
    reg [PAYLOAD_W-1:0] held_payload;
    reg pending_d, fault_d;
    reg [PAYLOAD_W-1:0] payload_d;
    reg [31:0] cycles_d;
    wire parity_bad=^{pending, sticky_fault, held_payload, added_cycles, parity};
    wire adapter_bad=ENABLE_PG && (sticky_fault || parity_bad);
    wire pg_ready, pg_fault;
    wire [7:0] effective_debt=retained_live_debt | ~debt_known;
    assign fault=ENABLE_PG && (adapter_bad || pg_fault);
    // One retained packet. The upstream pulse is accepted even while waking;
    // any additional pulse is reported as an interface fault, never overwrites.
    assign start_ready=!ENABLE_PG || (rst_n && sequencer_idle && !pending && !fault);
    assign core_start=ENABLE_PG ? (rst_n && sequencer_idle && pg_ready && !fault &&
                                  (pending || (start && start_ready))) : start;
    assign core_payload=ENABLE_PG && pending ? held_payload : payload;
    ot_dsrom_c_w5_pg #(.ENABLE_PG(ENABLE_PG), .GUARD_CYCLES(GUARD_CYCLES)) pg (
        .clk_aon(clk_aon), .rst_n(rst_n), .sleep_req(sleep_req),
        .busy(!sequencer_idle || !engines_idle || pending || adapter_bad),
        .prewake(neighbor_prewake), .demand(start), .live_debt(effective_debt),
        .isolation_ack(isolation_ack), .power_good(power_good),
        .relock_ack(relock_ack), .inrush_grant(inrush_grant),
        .power_req(power_req), .isolation_req(isolation_req),
        .clock_enable(clock_enable), .wake_request(wake_request),
        .ready(pg_ready), .fault(pg_fault), .state_observe());
    always @* begin
        pending_d=pending; payload_d=held_payload;
        fault_d=sticky_fault; cycles_d=added_cycles;
        if (!ENABLE_PG) begin
            pending_d=0; payload_d=0; fault_d=0; cycles_d=0;
        end else if (adapter_bad) fault_d=1;
        else begin
            // Rail/clock loss during execution cannot be repaired by a wake.
            // Halt the successor and preserve externally held debt for recovery.
            if (!sequencer_idle && (!power_good || !relock_ack)) fault_d=1;
            if (start && !start_ready) fault_d=1;
            if (pending) begin
                if (core_start) pending_d=0;
                else if (&added_cycles) fault_d=1; // never wrap latency debit
                else cycles_d=added_cycles+1'b1;
            end else if (start && start_ready) begin
                payload_d=payload;
                cycles_d=core_start ? 0 : 1;
                pending_d=!core_start;
            end
        end
    end
    // rst_n is the cold AON/system reset, never a switched-domain reset.
    // External return/link debt is deliberately not reset by this module.
    always @(posedge clk_aon or negedge rst_n) begin
        if (!rst_n) begin
            pending<=0; sticky_fault<=0; held_payload<=0;
            added_cycles<=0; parity<=0;
        end else begin
            pending<=pending_d; sticky_fault<=fault_d; held_payload<=payload_d;
            added_cycles<=cycles_d;
            parity<=^{pending_d,fault_d,payload_d,cycles_d};
        end
    end
endmodule

// Digital low-phase latch clock gate for the switched field, never the AON
// sequencer or Engram. A physical ICG mapping/CTS/SS-FF proof is still required.
module ot_dsrom_c_w5_clock_gate #(
    parameter bit ENABLE_PG=1'b0,
    parameter bit ALWAYS_ON=1'b0
) (
    input wire clk_in, clock_enable,
    output wire clk_out
);
    generate if (!ENABLE_PG || ALWAYS_ON) begin: bypass
        assign clk_out=clk_in;
    end else begin: gated
        reg gate_open;
        always @* if (!clk_in) gate_open=clock_enable;
        assign clk_out=clk_in & gate_open;
    end endgenerate
endmodule
