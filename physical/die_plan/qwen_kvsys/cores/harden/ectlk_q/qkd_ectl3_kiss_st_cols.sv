// DIE-KV-59/hg 2026-10-31: kit/bind variant of the hg-frame ectl (qkd_ectl3_kiss_st) as the four ECTLK quarter
// hard cores qkd_ectlk_q0..q3 (plan kv3_hg* hard_cores ectl_q0..3, physical_inst u_bound.u_ectl.u_cols.u_columns.u_q<k>).
// Same port ABI as qkd_ectl3_kiss_st; the body is qkd_ectlk_columns_legacy (ectlk_q/qkd_ectlk_columns.sv, parameterised).  KV-ECTLK-RL 11-15: QK_ISSUE_AGE / RESPONSE_LAT are PARAMETERS of qkd_ectlk_q0..q3 (default 37 / 26 = the
// KV plan krsp +5 round trip: kv_regen RESPONSE_LAT = 8 + krq + krs, QK = max(34, RL + 11)); a re-hardened core at other values
// needs no RTL edit, only a rebuild with -GQK_ISSUE_AGE / -GRESPONSE_LAT (core.json params) and CORE_QK / CORE_RL below
// set to the values of the signed views.  A parent value other than the views' still fails elaboration (no silent
// latency change); the bind param_regen (kv_regen ECTL) sets the parent values.
// KV-KT-E0 11-18: HXK (the score tag depth) is a parameter of qkd_ectlk_reference / qkd_ectlk_q0..q3 too (default 13 = the
// views of record); CORE_HXK below follows the signed views (ectlk_hxk.py --set N rewrites the five defaults and CORE_HXK
// together; the head kt input stations of KV event D25 need 15 = re-hardened q0..q3).
`default_nettype none
module qkd_ectl3_kiss_st_cols #(
    parameter integer HXK = 13,
    parameter integer MUT = 0,
    parameter integer QK_ISSUE_AGE = 37,
    parameter integer RESPONSE_LAT = 26
) (
    input wire [15:0] rsp_epoch, input wire [5:0] rsp_layer, input wire [13:0] rsp_t, input wire [0:0] rsp_v,
    input wire [0:0] rsp_valid, input wire [33:0] s2, input wire [33:0] s3, output wire [412:0] so, output wire [1558:0] t0,
    output wire [1558:0] t1, input wire [2:0] ck, output wire [15:0] e0, output wire [15:0] e1, input wire [0:0] rst_n,
    input wire [33:0] s0, input wire [33:0] s1, input wire [632:0] si, input wire [4:0] cfg, output wire [15:0] e2,
    output wire [15:0] e3, input wire [15:0] epoch, output wire [0:0] fault, input wire [0:0] kgo, input wire [5:0] layer,
    output wire [15:0] req_epoch, output wire [5:0] req_layer, output wire [13:0] req_t, output wire [0:0] req_v,
    output wire [0:0] req_valid, input wire [1023:0] rsp_data
);
    // the values the hardened qkd_ectlk_q0..q3 views of record were built at (one pair, edited only with a new signed set)
    localparam integer CORE_QK = 37;
    localparam integer CORE_RL = 26;
    localparam integer CORE_HXK = 13;
    generate
        if (HXK != CORE_HXK || MUT != 0 || QK_ISSUE_AGE != CORE_QK || RESPONSE_LAT != CORE_RL) begin : g_param_mismatch
            qkd_ectl3_kiss_st_cols__columns_built_for_other_params u_param_mismatch ();
        end
    endgenerate
    qkd_ectlk_columns_legacy #(.QK_ISSUE_AGE(QK_ISSUE_AGE), .RESPONSE_LAT(RESPONSE_LAT)) u_cols (.rsp_epoch(rsp_epoch), .rsp_layer(rsp_layer), .rsp_t(rsp_t), .rsp_v(rsp_v),
        .rsp_valid(rsp_valid), .s2(s2), .s3(s3), .so(so), .t0(t0), .t1(t1), .ck(ck), .e0(e0), .e1(e1), .rst_n(rst_n),
        .s0(s0), .s1(s1), .si(si), .cfg(cfg), .e2(e2), .e3(e3), .epoch(epoch), .fault(fault), .kgo(kgo), .layer(layer),
        .req_epoch(req_epoch), .req_layer(req_layer), .req_t(req_t), .req_v(req_v), .req_valid(req_valid),
        .rsp_data(rsp_data));
endmodule
`default_nettype wire
