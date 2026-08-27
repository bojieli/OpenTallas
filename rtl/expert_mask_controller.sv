// Converts top-k router IDs into wordline enables. Duplicate IDs are harmless.
module expert_mask_controller #(
    parameter integer NUM_EXPERTS = 4,
    parameter integer TOP_K = 2,
    parameter integer EXPERT_ID_W = $clog2(NUM_EXPERTS)
) (
    input  wire [TOP_K*EXPERT_ID_W-1:0] selected_expert_ids,
    input  wire [TOP_K-1:0]             selected_valid,
    output reg  [NUM_EXPERTS-1:0]       expert_mask
);
    integer slot;
    integer selected;
    always @* begin
        expert_mask = {NUM_EXPERTS{1'b0}};
        for (slot = 0; slot < TOP_K; slot = slot + 1) begin
            selected = selected_expert_ids[slot*EXPERT_ID_W +: EXPERT_ID_W];
            if (selected_valid[slot] && selected < NUM_EXPERTS)
                expert_mask[selected] = 1'b1;
        end
    end
endmodule
