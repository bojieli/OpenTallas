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
