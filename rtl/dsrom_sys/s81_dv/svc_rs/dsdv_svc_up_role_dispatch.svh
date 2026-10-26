// Generated actual-role status-up selection.
generate
if (UW==16 && FM_UI==4'h0 && FM_UO==4'h1) begin:g_up_01
 dsdv_svc_rs_up_fv_01 u_up (.ck(ck),.rn(rn),.chm(chm),.par(par),.done(done && !so_pend),.fl(hs_f),.hcr(hcr),.hack(hack),.hs_s(hs1),.uc(uc),.up_o_n(up_o[0 +: 16]));
assign up_o[16 +: 16]=0;
assign up_o[32 +: 16]=0;
assign up_o[48 +: 16]=0;
end
else if (UW==16 && FM_UI==4'h4 && FM_UO==4'h2) begin:g_up_42
 dsdv_svc_rs_up_fv_42 u_up (.ck(ck),.rn(rn),.chm(chm),.par(par),.done(done && !so_pend),.fl(hs_f),.hcr(hcr),.hack(hack),.hs_s(hs1),.uc(uc),.up_i_s(up_i[32 +: 16]),.up_o_e(up_o[16 +: 16]));
assign up_o[0 +: 16]=0;
assign up_o[32 +: 16]=0;
assign up_o[48 +: 16]=0;
end
else if (UW==16 && FM_UI==4'h4 && FM_UO==4'h8) begin:g_up_48
 dsdv_svc_rs_up_fv_48 u_up (.ck(ck),.rn(rn),.chm(chm),.par(par),.done(done && !so_pend),.fl(hs_f),.hcr(hcr),.hack(hack),.hs_s(hs1),.uc(uc),.up_i_s(up_i[32 +: 16]),.up_o_w(up_o[48 +: 16]));
assign up_o[0 +: 16]=0;
assign up_o[16 +: 16]=0;
assign up_o[32 +: 16]=0;
end
else if (UW==16 && FM_UI==4'h6 && FM_UO==4'h8) begin:g_up_68
 dsdv_svc_rs_up_fv_68 u_up (.ck(ck),.rn(rn),.chm(chm),.par(par),.done(done && !so_pend),.fl(hs_f),.hcr(hcr),.hack(hack),.hs_s(hs1),.uc(uc),.up_i_e(up_i[16 +: 16]),.up_i_s(up_i[32 +: 16]),.up_o_w(up_o[48 +: 16]));
assign up_o[0 +: 16]=0;
assign up_o[16 +: 16]=0;
assign up_o[32 +: 16]=0;
end
else if (UW==16 && FM_UI==4'hc && FM_UO==4'h2) begin:g_up_c2
 dsdv_svc_rs_up_fv_c2 u_up (.ck(ck),.rn(rn),.chm(chm),.par(par),.done(done && !so_pend),.fl(hs_f),.hcr(hcr),.hack(hack),.hs_s(hs1),.uc(uc),.up_i_s(up_i[32 +: 16]),.up_i_w(up_i[48 +: 16]),.up_o_e(up_o[16 +: 16]));
assign up_o[0 +: 16]=0;
assign up_o[32 +: 16]=0;
assign up_o[48 +: 16]=0;
end
else if (UW==16 && FM_UI==4'he && FM_UO==4'h0) begin:g_up_e0
 dsdv_svc_rs_up_fv_e0 u_up (.ck(ck),.rn(rn),.chm(chm),.par(par),.done(done && !so_pend),.fl(hs_f),.hcr(hcr),.hack(hack),.hs_s(hs1),.uc(uc),.up_i_e(up_i[16 +: 16]),.up_i_s(up_i[32 +: 16]),.up_i_w(up_i[48 +: 16]));
assign up_o[0 +: 16]=0;
assign up_o[16 +: 16]=0;
assign up_o[32 +: 16]=0;
assign up_o[48 +: 16]=0;
end
else begin:g_bad_up OT_SVC_ROLE_MASK_NOT_IMPLEMENTED invalid_role(); end
endgenerate
