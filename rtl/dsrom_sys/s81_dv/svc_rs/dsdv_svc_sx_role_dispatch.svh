// Generated actual-role SX selection; no generic hard HROW fallback.
generate
if (FM_GI==4'h0 && FM_GO==4'h1 && FM_SI==4'h1 && FM_SO==4'h0) begin:g_sx_0110
    dsdv_svc_sx_fv_0110 u_sx (.ck(ck),.rst(rst),.sid(sid),.l_v(l_v || pl_v),.l_d(pl_v ? pl_d : l_d),.go_v_n(go_v[0]),.go_d_n(go_d[0 +: 2132]),.si_v_n(si_v[0]),.si_d_n(si_d[0 +: 1076]),.rt_v(rt_v),.rt_d(rt_d),.t_v(t_v),.t_tag(t_tag),.t_y(t_y),.t_f(t_f),.fault(x_f));
assign go_v[1]=0; assign go_d[2132 +: 2132]=0;
assign go_v[2]=0; assign go_d[4264 +: 2132]=0;
assign go_v[3]=0; assign go_d[6396 +: 2132]=0;
assign so_v[0]=0; assign so_d[0 +: 1076]=0;
assign so_v[1]=0; assign so_d[1076 +: 1076]=0;
assign so_v[2]=0; assign so_d[2152 +: 1076]=0;
assign so_v[3]=0; assign so_d[3228 +: 1076]=0;
end
else if (FM_GI==4'h1 && FM_GO==4'h1 && FM_SI==4'h1 && FM_SO==4'h1) begin:g_sx_1111
    dsdv_svc_sx_fv_1111 u_sx (.ck(ck),.rst(rst),.sid(sid),.l_v(l_v || pl_v),.l_d(pl_v ? pl_d : l_d),.gi_v_n(gi_v[0]),.gi_d_n(gi_d[0 +: 2132]),.go_v_n(go_v[0]),.go_d_n(go_d[0 +: 2132]),.si_v_n(si_v[0]),.si_d_n(si_d[0 +: 1076]),.so_v_n(so_v[0]),.so_d_n(so_d[0 +: 1076]),.rt_v(rt_v),.rt_d(rt_d),.t_v(t_v),.t_tag(t_tag),.t_y(t_y),.t_f(t_f),.fault(x_f));
assign go_v[1]=0; assign go_d[2132 +: 2132]=0;
assign go_v[2]=0; assign go_d[4264 +: 2132]=0;
assign go_v[3]=0; assign go_d[6396 +: 2132]=0;
assign so_v[1]=0; assign so_d[1076 +: 1076]=0;
assign so_v[2]=0; assign so_d[2152 +: 1076]=0;
assign so_v[3]=0; assign so_d[3228 +: 1076]=0;
end
else if (FM_GI==4'h1 && FM_GO==4'h2 && FM_SI==4'h2 && FM_SO==4'h1) begin:g_sx_1221
    dsdv_svc_sx_fv_1221 u_sx (.ck(ck),.rst(rst),.sid(sid),.l_v(l_v || pl_v),.l_d(pl_v ? pl_d : l_d),.gi_v_n(gi_v[0]),.gi_d_n(gi_d[0 +: 2132]),.go_v_e(go_v[1]),.go_d_e(go_d[2132 +: 2132]),.si_v_e(si_v[1]),.si_d_e(si_d[1076 +: 1076]),.so_v_n(so_v[0]),.so_d_n(so_d[0 +: 1076]),.rt_v(rt_v),.rt_d(rt_d),.t_v(t_v),.t_tag(t_tag),.t_y(t_y),.t_f(t_f),.fault(x_f));
assign go_v[0]=0; assign go_d[0 +: 2132]=0;
assign go_v[2]=0; assign go_d[4264 +: 2132]=0;
assign go_v[3]=0; assign go_d[6396 +: 2132]=0;
assign so_v[1]=0; assign so_d[1076 +: 1076]=0;
assign so_v[2]=0; assign so_d[2152 +: 1076]=0;
assign so_v[3]=0; assign so_d[3228 +: 1076]=0;
end
else if (FM_GI==4'h3 && FM_GO==4'h3 && FM_SI==4'h3 && FM_SO==4'h3) begin:g_sx_3333
    dsdv_svc_sx_fv_3333 u_sx (.ck(ck),.rst(rst),.sid(sid),.l_v(l_v || pl_v),.l_d(pl_v ? pl_d : l_d),.gi_v_n(gi_v[0]),.gi_d_n(gi_d[0 +: 2132]),.gi_v_e(gi_v[1]),.gi_d_e(gi_d[2132 +: 2132]),.go_v_n(go_v[0]),.go_d_n(go_d[0 +: 2132]),.go_v_e(go_v[1]),.go_d_e(go_d[2132 +: 2132]),.si_v_n(si_v[0]),.si_d_n(si_d[0 +: 1076]),.si_v_e(si_v[1]),.si_d_e(si_d[1076 +: 1076]),.so_v_n(so_v[0]),.so_d_n(so_d[0 +: 1076]),.so_v_e(so_v[1]),.so_d_e(so_d[1076 +: 1076]),.rt_v(rt_v),.rt_d(rt_d),.t_v(t_v),.t_tag(t_tag),.t_y(t_y),.t_f(t_f),.fault(x_f));
assign go_v[2]=0; assign go_d[4264 +: 2132]=0;
assign go_v[3]=0; assign go_d[6396 +: 2132]=0;
assign so_v[2]=0; assign so_d[2152 +: 1076]=0;
assign so_v[3]=0; assign so_d[3228 +: 1076]=0;
end
else if (FM_GI==4'h4 && FM_GO==4'h2 && FM_SI==4'h2 && FM_SO==4'h4) begin:g_sx_4224
    dsdv_svc_sx_fv_4224 u_sx (.ck(ck),.rst(rst),.sid(sid),.l_v(l_v || pl_v),.l_d(pl_v ? pl_d : l_d),.gi_v_s(gi_v[2]),.gi_d_s(gi_d[4264 +: 2132]),.go_v_e(go_v[1]),.go_d_e(go_d[2132 +: 2132]),.si_v_e(si_v[1]),.si_d_e(si_d[1076 +: 1076]),.so_v_s(so_v[2]),.so_d_s(so_d[2152 +: 1076]),.rt_v(rt_v),.rt_d(rt_d),.t_v(t_v),.t_tag(t_tag),.t_y(t_y),.t_f(t_f),.fault(x_f));
assign go_v[0]=0; assign go_d[0 +: 2132]=0;
assign go_v[2]=0; assign go_d[4264 +: 2132]=0;
assign go_v[3]=0; assign go_d[6396 +: 2132]=0;
assign so_v[0]=0; assign so_d[0 +: 1076]=0;
assign so_v[1]=0; assign so_d[1076 +: 1076]=0;
assign so_v[3]=0; assign so_d[3228 +: 1076]=0;
end
else if (FM_GI==4'h6 && FM_GO==4'ha && FM_SI==4'ha && FM_SO==4'h6) begin:g_sx_6aa6
    dsdv_svc_sx_fv_6aa6 u_sx (.ck(ck),.rst(rst),.sid(sid),.l_v(l_v || pl_v),.l_d(pl_v ? pl_d : l_d),.gi_v_e(gi_v[1]),.gi_d_e(gi_d[2132 +: 2132]),.gi_v_s(gi_v[2]),.gi_d_s(gi_d[4264 +: 2132]),.go_v_e(go_v[1]),.go_d_e(go_d[2132 +: 2132]),.go_v_w(go_v[3]),.go_d_w(go_d[6396 +: 2132]),.si_v_e(si_v[1]),.si_d_e(si_d[1076 +: 1076]),.si_v_w(si_v[3]),.si_d_w(si_d[3228 +: 1076]),.so_v_e(so_v[1]),.so_d_e(so_d[1076 +: 1076]),.so_v_s(so_v[2]),.so_d_s(so_d[2152 +: 1076]),.rt_v(rt_v),.rt_d(rt_d),.t_v(t_v),.t_tag(t_tag),.t_y(t_y),.t_f(t_f),.fault(x_f));
assign go_v[0]=0; assign go_d[0 +: 2132]=0;
assign go_v[2]=0; assign go_d[4264 +: 2132]=0;
assign so_v[0]=0; assign so_d[0 +: 1076]=0;
assign so_v[3]=0; assign so_d[3228 +: 1076]=0;
end
else if (FM_GI==4'h8 && FM_GO==4'h8 && FM_SI==4'h8 && FM_SO==4'h8) begin:g_sx_8888
    dsdv_svc_sx_fv_8888 u_sx (.ck(ck),.rst(rst),.sid(sid),.l_v(l_v || pl_v),.l_d(pl_v ? pl_d : l_d),.gi_v_w(gi_v[3]),.gi_d_w(gi_d[6396 +: 2132]),.go_v_w(go_v[3]),.go_d_w(go_d[6396 +: 2132]),.si_v_w(si_v[3]),.si_d_w(si_d[3228 +: 1076]),.so_v_w(so_v[3]),.so_d_w(so_d[3228 +: 1076]),.rt_v(rt_v),.rt_d(rt_d),.t_v(t_v),.t_tag(t_tag),.t_y(t_y),.t_f(t_f),.fault(x_f));
assign go_v[0]=0; assign go_d[0 +: 2132]=0;
assign go_v[1]=0; assign go_d[2132 +: 2132]=0;
assign go_v[2]=0; assign go_d[4264 +: 2132]=0;
assign so_v[0]=0; assign so_d[0 +: 1076]=0;
assign so_v[1]=0; assign so_d[1076 +: 1076]=0;
assign so_v[2]=0; assign so_d[2152 +: 1076]=0;
end
else if (FM_GI==4'h9 && FM_GO==4'h9 && FM_SI==4'h9 && FM_SO==4'h9) begin:g_sx_9999
    dsdv_svc_sx_fv_9999 u_sx (.ck(ck),.rst(rst),.sid(sid),.l_v(l_v || pl_v),.l_d(pl_v ? pl_d : l_d),.gi_v_n(gi_v[0]),.gi_d_n(gi_d[0 +: 2132]),.gi_v_w(gi_v[3]),.gi_d_w(gi_d[6396 +: 2132]),.go_v_n(go_v[0]),.go_d_n(go_d[0 +: 2132]),.go_v_w(go_v[3]),.go_d_w(go_d[6396 +: 2132]),.si_v_n(si_v[0]),.si_d_n(si_d[0 +: 1076]),.si_v_w(si_v[3]),.si_d_w(si_d[3228 +: 1076]),.so_v_n(so_v[0]),.so_d_n(so_d[0 +: 1076]),.so_v_w(so_v[3]),.so_d_w(so_d[3228 +: 1076]),.rt_v(rt_v),.rt_d(rt_d),.t_v(t_v),.t_tag(t_tag),.t_y(t_y),.t_f(t_f),.fault(x_f));
assign go_v[1]=0; assign go_d[2132 +: 2132]=0;
assign go_v[2]=0; assign go_d[4264 +: 2132]=0;
assign so_v[1]=0; assign so_d[1076 +: 1076]=0;
assign so_v[2]=0; assign so_d[2152 +: 1076]=0;
end
else if (FM_GI==4'ha && FM_GO==4'h3 && FM_SI==4'h3 && FM_SO==4'ha) begin:g_sx_a33a
    dsdv_svc_sx_fv_a33a u_sx (.ck(ck),.rst(rst),.sid(sid),.l_v(l_v || pl_v),.l_d(pl_v ? pl_d : l_d),.gi_v_e(gi_v[1]),.gi_d_e(gi_d[2132 +: 2132]),.gi_v_w(gi_v[3]),.gi_d_w(gi_d[6396 +: 2132]),.go_v_n(go_v[0]),.go_d_n(go_d[0 +: 2132]),.go_v_e(go_v[1]),.go_d_e(go_d[2132 +: 2132]),.si_v_n(si_v[0]),.si_d_n(si_d[0 +: 1076]),.si_v_e(si_v[1]),.si_d_e(si_d[1076 +: 1076]),.so_v_e(so_v[1]),.so_d_e(so_d[1076 +: 1076]),.so_v_w(so_v[3]),.so_d_w(so_d[3228 +: 1076]),.rt_v(rt_v),.rt_d(rt_d),.t_v(t_v),.t_tag(t_tag),.t_y(t_y),.t_f(t_f),.fault(x_f));
assign go_v[2]=0; assign go_d[4264 +: 2132]=0;
assign go_v[3]=0; assign go_d[6396 +: 2132]=0;
assign so_v[0]=0; assign so_d[0 +: 1076]=0;
assign so_v[2]=0; assign so_d[2152 +: 1076]=0;
end
else if (FM_GI==4'ha && FM_GO==4'h4 && FM_SI==4'h4 && FM_SO==4'ha) begin:g_sx_a44a
    dsdv_svc_sx_fv_a44a u_sx (.ck(ck),.rst(rst),.sid(sid),.l_v(l_v || pl_v),.l_d(pl_v ? pl_d : l_d),.gi_v_e(gi_v[1]),.gi_d_e(gi_d[2132 +: 2132]),.gi_v_w(gi_v[3]),.gi_d_w(gi_d[6396 +: 2132]),.go_v_s(go_v[2]),.go_d_s(go_d[4264 +: 2132]),.si_v_s(si_v[2]),.si_d_s(si_d[2152 +: 1076]),.so_v_e(so_v[1]),.so_d_e(so_d[1076 +: 1076]),.so_v_w(so_v[3]),.so_d_w(so_d[3228 +: 1076]),.rt_v(rt_v),.rt_d(rt_d),.t_v(t_v),.t_tag(t_tag),.t_y(t_y),.t_f(t_f),.fault(x_f));
assign go_v[0]=0; assign go_d[0 +: 2132]=0;
assign go_v[1]=0; assign go_d[2132 +: 2132]=0;
assign go_v[3]=0; assign go_d[6396 +: 2132]=0;
assign so_v[0]=0; assign so_d[0 +: 1076]=0;
assign so_v[2]=0; assign so_d[2152 +: 1076]=0;
end
else if (FM_GI==4'ha && FM_GO==4'ha && FM_SI==4'ha && FM_SO==4'ha) begin:g_sx_aaaa
    dsdv_svc_sx_fv_aaaa u_sx (.ck(ck),.rst(rst),.sid(sid),.l_v(l_v || pl_v),.l_d(pl_v ? pl_d : l_d),.gi_v_e(gi_v[1]),.gi_d_e(gi_d[2132 +: 2132]),.gi_v_w(gi_v[3]),.gi_d_w(gi_d[6396 +: 2132]),.go_v_e(go_v[1]),.go_d_e(go_d[2132 +: 2132]),.go_v_w(go_v[3]),.go_d_w(go_d[6396 +: 2132]),.si_v_e(si_v[1]),.si_d_e(si_d[1076 +: 1076]),.si_v_w(si_v[3]),.si_d_w(si_d[3228 +: 1076]),.so_v_e(so_v[1]),.so_d_e(so_d[1076 +: 1076]),.so_v_w(so_v[3]),.so_d_w(so_d[3228 +: 1076]),.rt_v(rt_v),.rt_d(rt_d),.t_v(t_v),.t_tag(t_tag),.t_y(t_y),.t_f(t_f),.fault(x_f));
assign go_v[0]=0; assign go_d[0 +: 2132]=0;
assign go_v[2]=0; assign go_d[4264 +: 2132]=0;
assign so_v[0]=0; assign so_d[0 +: 1076]=0;
assign so_v[2]=0; assign so_d[2152 +: 1076]=0;
end
else if (FM_GI==4'hc && FM_GO==4'h6 && FM_SI==4'h6 && FM_SO==4'hc) begin:g_sx_c66c
    dsdv_svc_sx_fv_c66c u_sx (.ck(ck),.rst(rst),.sid(sid),.l_v(l_v || pl_v),.l_d(pl_v ? pl_d : l_d),.gi_v_s(gi_v[2]),.gi_d_s(gi_d[4264 +: 2132]),.gi_v_w(gi_v[3]),.gi_d_w(gi_d[6396 +: 2132]),.go_v_e(go_v[1]),.go_d_e(go_d[2132 +: 2132]),.go_v_s(go_v[2]),.go_d_s(go_d[4264 +: 2132]),.si_v_e(si_v[1]),.si_d_e(si_d[1076 +: 1076]),.si_v_s(si_v[2]),.si_d_s(si_d[2152 +: 1076]),.so_v_s(so_v[2]),.so_d_s(so_d[2152 +: 1076]),.so_v_w(so_v[3]),.so_d_w(so_d[3228 +: 1076]),.rt_v(rt_v),.rt_d(rt_d),.t_v(t_v),.t_tag(t_tag),.t_y(t_y),.t_f(t_f),.fault(x_f));
assign go_v[0]=0; assign go_d[0 +: 2132]=0;
assign go_v[3]=0; assign go_d[6396 +: 2132]=0;
assign so_v[0]=0; assign so_d[0 +: 1076]=0;
assign so_v[1]=0; assign so_d[1076 +: 1076]=0;
end
else if (FM_GI==4'hc && FM_GO==4'hc && FM_SI==4'hc && FM_SO==4'hc) begin:g_sx_cccc
    dsdv_svc_sx_fv_cccc u_sx (.ck(ck),.rst(rst),.sid(sid),.l_v(l_v || pl_v),.l_d(pl_v ? pl_d : l_d),.gi_v_s(gi_v[2]),.gi_d_s(gi_d[4264 +: 2132]),.gi_v_w(gi_v[3]),.gi_d_w(gi_d[6396 +: 2132]),.go_v_s(go_v[2]),.go_d_s(go_d[4264 +: 2132]),.go_v_w(go_v[3]),.go_d_w(go_d[6396 +: 2132]),.si_v_s(si_v[2]),.si_d_s(si_d[2152 +: 1076]),.si_v_w(si_v[3]),.si_d_w(si_d[3228 +: 1076]),.so_v_s(so_v[2]),.so_d_s(so_d[2152 +: 1076]),.so_v_w(so_v[3]),.so_d_w(so_d[3228 +: 1076]),.rt_v(rt_v),.rt_d(rt_d),.t_v(t_v),.t_tag(t_tag),.t_y(t_y),.t_f(t_f),.fault(x_f));
assign go_v[0]=0; assign go_d[0 +: 2132]=0;
assign go_v[1]=0; assign go_d[2132 +: 2132]=0;
assign so_v[0]=0; assign so_d[0 +: 1076]=0;
assign so_v[1]=0; assign so_d[1076 +: 1076]=0;
end
else begin:g_bad_sx OT_SVC_ROLE_MASK_NOT_IMPLEMENTED invalid_role(); end
endgenerate
