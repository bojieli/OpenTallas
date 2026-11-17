// Actual accepted-start and witness-generate fragment from reconstructed
// qfd_tt_ctlm_dv_gi_hp13 (candidate parts source sha984f7357b0323da298448f0abe2837fa444c4b6b5d3127ca6cd4e0d532d4b74e).
// Surrounding unrelated TT logic omitted: this fixture tests source selection.
module qfd_tt_ctlm_dv_gi_hp13 #(
    parameter integer HEAD_STAGE37 = 0,
    parameter integer F16WTN = 0
) (
    input wire ck,rst_n,
    input wire [74:0] pw,
    input wire [82:0] f16_auth,
    input wire [37:0] f16_obs,
    output wire [16:0] f16_st
);
    wire w_fault;
    wire l_start=0;
    wire [1:0] l_user=0,u_user=0,c_done_user=0;
    wire [15:0] tok_b[0:3];
    wire [23:0] s_tok=0;
    wire u_start=0,c_done=0,ag_stn_busy=0;
    wire [5:0] u_stage=0;
    wire [15:0] u_tokid = l_start ? tok_b[l_user][15:0] : s_tok[15:0];   // the context's token identity at its start
    generate if (F16WTN != 0) begin : g_wtn
        qfd_tt_ctlm_dv_wtn u_wtn (.ck(ck), .rst_n(rst_n), .pw(pw), .auth(f16_auth),
            .start({u_start, 2'(u_user), u_stage, u_tokid}), .retire({c_done, 2'(c_done_user), !ag_stn_busy}), .obs(f16_obs),
            .st(f16_st));
        assign w_fault = f16_st[16];
    end else begin : g_no_wtn
        assign f16_st = 17'd0; assign w_fault = 1'b0;
        wire unused_w = &{1'b0, pw, f16_auth, f16_obs};
    end endgenerate
endmodule
