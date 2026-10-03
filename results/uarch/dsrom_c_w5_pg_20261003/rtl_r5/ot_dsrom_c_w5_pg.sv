// W5 digital handshake only. Instantiate in an always-on control island.
// All ACKs and debt bits must already be synchronized to clk_aon; CDC cost
// belongs in the model. No analog power-good/relock guarantee is generated.
module ot_dsrom_c_w5_pg #(
    parameter bit ENABLE_PG = 1'b0,
    parameter bit ALWAYS_ON = 1'b0,
    parameter integer DEBT_W = 8,
    parameter integer GUARD_CYCLES = 2
) (
    input wire clk_aon, rst_n,
    input wire sleep_req, busy, prewake, demand,
    // Retained outside the switched island: producer, consumer, CDC, replay,
    // transaction identity/tag, reverse ACK and link TX/RX/credit debt.
    input wire [DEBT_W-1:0] live_debt,
    input wire isolation_ack, power_good, relock_ack, inrush_grant,
    output wire power_req, isolation_req, clock_enable,
    output wire wake_request, ready,
    output reg fault,
    output wire [2:0] state_observe
);
    localparam [2:0] S_ON=0, S_ISOLATE=1, S_OFF=2, S_WAKE=3, S_RELEASE=4;
    localparam integer CW = 8;
    reg [2:0] state;
    reg [CW-1:0] guard_count;
    reg wake_pending;
    reg parity;
    reg [2:0] state_d;
    reg [CW-1:0] guard_d;
    reg pending_d;
    wire need_awake = busy | prewake | demand | (|live_debt);
    wire bypass = !ENABLE_PG || ALWAYS_ON;
    wire parity_bad = ^{state, guard_count, wake_pending, parity};
    wire corrupt = !bypass && (fault || parity_bad || state > S_RELEASE);
    // These outputs are requests, not a clock gate or power switch themselves.
    assign power_req = bypass || state != S_OFF;
    assign isolation_req = !bypass && (!rst_n || corrupt || state != S_ON || !power_good || !relock_ack);
    assign clock_enable = bypass || (!corrupt && power_good && (state == S_ON || state == S_WAKE || state == S_RELEASE));
    assign wake_request = !bypass && (need_awake || wake_pending) && state != S_ON;
    assign ready = rst_n && (bypass || (!corrupt && state == S_ON && power_good && relock_ack));
    assign state_observe = state;

    // Guard is a digitally priced minimum dwell, never an analog deadline.
    initial begin
        if (GUARD_CYCLES < 1 || GUARD_CYCLES > 255) $fatal(1, "guard out of range");
        if (DEBT_W < 1) $fatal(1, "debt width out of range");
    end
    always @* begin
        state_d = state;
        guard_d = guard_count;
        pending_d = wake_pending;
        if (bypass) begin
            state_d = S_ON;
            guard_d = 0;
            pending_d = 0;
        end else if (!corrupt) begin
            if (need_awake) pending_d = 1;
            case (state)
                S_ON: begin
                    guard_d = 0;
                    pending_d = 0;
                    // Power loss fails closed, even without a sleep request.
                    if (!power_good || !relock_ack) state_d = S_WAKE;
                    else if (sleep_req && !need_awake) state_d = S_ISOLATE;
                end
                S_ISOLATE: begin
                    guard_d = 0;
                    if (need_awake || wake_pending) state_d = S_WAKE;
                    else if (isolation_ack) state_d = S_OFF;
                end
                S_OFF: begin
                    guard_d = 0;
                    // Latch one-cycle prewake while PDN grants are delayed.
                    if ((need_awake || wake_pending) && inrush_grant) state_d = S_WAKE;
                end
                S_WAKE: begin
                    if (!power_good || !relock_ack) guard_d = 0;
                    else if (guard_count == GUARD_CYCLES-1) begin
                        state_d = S_RELEASE;
                        guard_d = 0;
                    end else guard_d = guard_count + 1'b1;
                end
                S_RELEASE: begin
                    // Isolation stays asserted for this complete cycle.
                    if (power_good && relock_ack) begin
                        state_d = S_ON;
                        pending_d = 0;
                    end else state_d = S_WAKE;
                end
                default: begin
                    state_d = S_WAKE;
                    guard_d = 0;
                end
            endcase
        end
    end
    always @(posedge clk_aon or negedge rst_n) begin
        if (!rst_n) begin
            // Reset cannot throw away external debt. Cold ramp needs a grant.
            state <= S_OFF;
            guard_count <= 0;
            wake_pending <= 1;
            parity <= ^{S_OFF, 8'b0, 1'b1};
            fault <= 0;
        end else begin
            state <= state_d;
            guard_count <= guard_d;
            wake_pending <= pending_d;
            parity <= ^{state_d, guard_d, pending_d};
            // Do not silently repair a corrupted mutable controller.
            if (corrupt) fault <= 1;
        end
    end
endmodule

// Explicit directed W2 adjacency; numeric stage ID adjacency is never assumed.
// Bit source*N+destination names an edge. Wake runs in the always-on island.
module ot_dsrom_c_w5_prewake #(
    parameter integer N = 1,
    parameter [N*N-1:0] SUCCESSOR_EDGES = {N*N{1'b0}}
) (
    input wire [N-1:0] phase_start,
    output wire [N-1:0] neighbor_prewake
);
    genvar destination, source;
    generate for (destination=0; destination<N; destination=destination+1) begin: dst
        wire [N-1:0] terms;
        for (source=0; source<N; source=source+1) begin: src
            assign terms[source] = phase_start[source] & SUCCESSOR_EDGES[source*N+destination];
        end
        assign neighbor_prewake[destination] = |terms;
    end endgenerate
endmodule

// Clamp data AND valid outside the switched island. No extra data registers.
module ot_dsrom_c_w5_isolation #(parameter integer WIDTH=32) (
    input wire isolation_req,
    input wire valid_in,
    input wire [WIDTH-1:0] data_in,
    output wire valid_out,
    output wire [WIDTH-1:0] data_out
);
    assign valid_out = valid_in & !isolation_req;
    assign data_out = isolation_req ? {WIDTH{1'b0}} : data_in;
endmodule

// A link may sleep only after both endpoints and BOTH directions are drained.
// TX/RX debt includes replay, outstanding credits, identity and reverse ACKs.
module ot_dsrom_c_w5_link_pg #(
    parameter bit ENABLE_PG=1'b0,
    parameter integer DEBT_W=8,
    parameter integer GUARD_CYCLES=2
) (
    input wire clk_aon, rst_n, sleep_req, demand,
    input wire [1:0] endpoint_busy, endpoint_prewake,
    input wire [DEBT_W-1:0] tx_live_debt, rx_live_debt,
    input wire isolation_ack, power_good, relock_ack, inrush_grant,
    output wire power_req, isolation_req, clock_enable, wake_request, ready, fault
);
    ot_dsrom_c_w5_pg #(.ENABLE_PG(ENABLE_PG), .DEBT_W(2*DEBT_W), .GUARD_CYCLES(GUARD_CYCLES)) pg (
        .clk_aon(clk_aon), .rst_n(rst_n), .sleep_req(sleep_req), .busy(|endpoint_busy),
        .prewake(|endpoint_prewake), .demand(demand), .live_debt({tx_live_debt,rx_live_debt}),
        .isolation_ack(isolation_ack), .power_good(power_good), .relock_ack(relock_ack), .inrush_grant(inrush_grant),
        .power_req(power_req), .isolation_req(isolation_req), .clock_enable(clock_enable),
        .wake_request(wake_request), .ready(ready), .fault(fault));
endmodule
