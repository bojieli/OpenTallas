module qfd_tt_ctlm_dv_wtn #(
    parameter integer MUT = 0
) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [74:0]  pw,
    input  wire [82:0]  auth,
    input  wire [24:0]  start,
    input  wire [3:0]   retire,
    input  wire [37:0]  obs,
    output wire [16:0]  st
);
    wire        a_begin = auth[82];
    wire        a_all = auth[81] && (a_begin == 1'b0 || MUT == 1);
    wire [15:0] a_epoch = auth[15:0];
    wire [1:0]  r_user = (MUT == 3) ? {retire[1], retire[2]} : retire[2:1];
    wire        tr, gc, fl;
    wire [3:0]  ca, awc, cg;
    wire [1:0]  cu;
    qfd_dv_typed_witness_control #(.ENABLE(1), .SAFE_COMPARE(1), .SAFE_SELECT(1), .SAFE_PHYS(1)) u_ctl (
        .ck(ck), .rst_n(rst_n), .pw_v(pw[74]), .pw_addr(pw[73:64]), .pw_data(pw[63:0]),
        .all_copies_authenticated(a_all), .fusedcap(auth[80]), .installed_digest(auth[79:16]), .installed_epoch(a_epoch),
        .start_v(start[24]), .start_user(start[23:22]), .start_stage(start[21:16]),
        .start_epoch((MUT == 2) ? a_epoch : start[15:0]),
        .retire_v(retire[3]), .retire_user(r_user), .ME_XPF_retired(retire[0]),
        .observation(obs[37:22]), .event_stage(obs[21:16]), .event_epoch(obs[15:0]),
        .template_ready(tr), .context_active(ca), .all_witnesses_complete(awc),
        .group_complete(gc), .complete_user(cu), .complete_group(cg), .fault(fl));
    assign st = {fl, cg, cu, gc, awc, ca, tr};
endmodule
