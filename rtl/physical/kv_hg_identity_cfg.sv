// Candidate for the declared-position HG configuration path. No state or new ID.
// row_id is the existing HG row counter; stack_id is existing hroot u_id_stk.y.
// Legal release identities only: this does not replace arbitrary boot config.
module kv_hg_identity_cfg (
    input wire [4:0] row_id,
    input wire [1:0] stack_id,
    output wire [4:0] cfg
);
    wire [2:0] logical_group = {~(row_id[2] ^ row_id[1]), row_id[2], row_id[0]};
    assign cfg = {logical_group, stack_id};
endmodule
