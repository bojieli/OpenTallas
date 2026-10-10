module ot_hbm_accel_smh_result_valid #(
    parameter integer NC = 8,
    parameter integer ENABLE = 0
) (
    input wire [NC-1:0] valids,
    input wire [NC-1:0] faults,
    output wire row_valid,
    output wire fault_event
);
    wire all_valid = &valids;
    wire partial_valid = (|valids) && !all_valid;
    assign row_valid = ENABLE ? valids[0] : valids[0];
    assign fault_event = ENABLE ? ((|(faults & valids)) | partial_valid) : (|faults);
endmodule
