`timescale 1ns/1ps
// Unselected candidate only. Production SerDes modules and callers stay unchanged.
// New pma_lock authority is required only by these new wrappers when LOCKSAFE=1.
// Boot cost: two recovered-clock synchronizer edges, HOLD_EDGES recovered edges,
// then the original core's reset synchronizers. No mission pipeline stage is added.
module ot_pdie_pma_reset_hold #(parameter integer HOLD_EDGES = 64) (
    input wire rst_n, pma_lock, pma_rck,
    output wire core_rst_n,
    output reg hold_ready
);
    // FACE-LOCK-1 (DIE-S81-51 11-03, FACE_GUARD sign-off gate): each reset authority lands ONLY on the asynchronous
    // clear pins of its own 2-flop release synchroniser (a reset-spine landing), never on a gate: the old
    // `permit = rst_n && pma_lock` put an AND2 on the pma_lock pad (face_guard 'unregistered', serdes__t2/t3/t4/t13/
    // t15/t16).  Same contract: async assert on rst_n low OR pma_lock low; release max(rst_n, pma_lock) + 2 rck edges
    // (synchronised) + HOLD_EDGES rck edges -> core_rst_n rises on rck edge HOLD_EDGES + 2 (66), as before.
    localparam integer CW = (HOLD_EDGES < 2) ? 1 : $clog2(HOLD_EDGES);
    (* async_reg = "true" *) reg [1:0] lock_sync;
    (* async_reg = "true" *) reg [1:0] rst_sync;
    reg [CW-1:0] count;
    initial if (HOLD_EDGES < 1) $error("HOLD_EDGES must be positive");
    always @(posedge pma_rck or negedge pma_lock)
        if (!pma_lock) lock_sync <= 2'b00;
        else lock_sync <= {lock_sync[0], 1'b1};
    always @(posedge pma_rck or negedge rst_n)
        if (!rst_n) rst_sync <= 2'b00;
        else rst_sync <= {rst_sync[0], 1'b1};
    wire permit = lock_sync[1] && rst_sync[1];     // synchronised release, asynchronous assert (flop clear)
    always @(posedge pma_rck or negedge permit)
        if (!permit) begin count <= 0; hold_ready <= 1'b0; end
        else if (!hold_ready) begin
            if (count == HOLD_EDGES - 1) hold_ready <= 1'b1;
            else count <= count + 1'b1;
        end
    assign core_rst_n = permit && hold_ready;
endmodule

module ot_pdie_serdes_locksafe #(
    parameter integer LOCKSAFE = 0, parameter integer HOLD_EDGES = 64,
    parameter integer PMA_LAT = 4, parameter integer EMUT = 0, parameter integer DMUT = 0
) (
    input wire clk, rst, pma_lock,
    input wire [511:0] tx,
    output wire [511:0] rx,
    output wire [1:0] st,
    output wire [543:0] pma_tx,
    output wire pma_tck,
    input wire [543:0] pma_rx,
    input wire pma_rck
);
    wire core_rst_n;
    generate if (LOCKSAFE != 0) begin : g_guard
        wire hold_ready;
        ot_pdie_pma_reset_hold #(.HOLD_EDGES(HOLD_EDGES)) u_hold
            (.rst_n(rst), .pma_lock(pma_lock), .pma_rck(pma_rck),
             .core_rst_n(core_rst_n), .hold_ready(hold_ready));
    end else begin : g_legacy
        assign core_rst_n = rst;
    end endgenerate
    ot_pdie_serdes #(.PMA_LAT(PMA_LAT), .EMUT(EMUT), .DMUT(DMUT)) u_core
        (.clk(clk), .rst(core_rst_n), .tx(tx), .rx(rx), .st(st),
         .pma_tx(pma_tx), .pma_tck(pma_tck), .pma_rx(pma_rx), .pma_rck(pma_rck));
endmodule

module ot_pdie_serdes_col_locksafe #(
    parameter integer LOCKSAFE = 0, parameter integer HOLD_EDGES = 64,
    parameter integer PMA_LAT = 4, parameter integer TXL = 2, parameter integer MUT = 0
) (
    input wire clk, rst, pma_lock,
    input wire [511:0] tx,
    output wire [511:0] rx,
    output wire [1:0] st,
    output wire [543:0] pma_tx,
    output wire pma_tck,
    input wire [543:0] pma_rx,
    input wire pma_rck
);
    wire core_rst_n;
    generate if (LOCKSAFE != 0) begin : g_guard
        wire hold_ready;
        ot_pdie_pma_reset_hold #(.HOLD_EDGES(HOLD_EDGES)) u_hold
            (.rst_n(rst), .pma_lock(pma_lock), .pma_rck(pma_rck),
             .core_rst_n(core_rst_n), .hold_ready(hold_ready));
    end else begin : g_legacy
        assign core_rst_n = rst;
    end endgenerate
    ot_pdie_serdes_col #(.PMA_LAT(PMA_LAT), .TXL(TXL), .MUT(MUT)) u_core
        (.clk(clk), .rst(core_rst_n), .tx(tx), .rx(rx), .st(st),
         .pma_tx(pma_tx), .pma_tck(pma_tck), .pma_rx(pma_rx), .pma_rck(pma_rck));
endmodule
