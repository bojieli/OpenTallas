`timescale 1ps/1fs
module current_middle(input wire ck,rst_n,inject,own_v,
 input wire[275:0]va_g,vb_g,va_b,vb_b,va_e,vb_e, output wire[275:0]gno,gso,bno,bso,eno,eso,
 output wire[3:0]fault);
wire[275:0]gn[0:6],gs[0:6];
ot_hdc_delay #(.W(276),.D(78),.RESET(1)) gni(.clk(ck),.rst_n(rst_n),.d(va_g),.q(gn[0]));
ot_hdc_delay #(.W(276),.D(24),.RESET(1)) gsi(.clk(ck),.rst_n(rst_n),.d(vb_g),.q(gs[6]));
for(genvar j=0;j<6;j=j+1)begin:g_leaf
 if(j==2)begin:g_l2
 ot_dsdv_vstop #(.V(276),.JREG(0)) u_vs(.clk(ck),.rst_n(rst_n),.tap_k(8'ha0),.sink_k(8'ha0),.bk_uid(8'd0),
 .vi_s(gn[j]),.vo_n(gn[j+1]),.vi_n(gs[j+1]),.vo_s(gs[j]),
 .in_nv(inject),.in_n(276'd3),.in_sv(inject),.in_s(276'd3),.fault(fault[0]),
 .dl_nv(),.dl_n(),.dl_sv(),.dl_s(),.ra_s(),.ra_n(),.dk_n(),.dk_s());
 end else begin:g_pass
 dsdv_gunit_pass #(.W(276),.N(2)) u_up(.clk(ck),.rst_n(rst_n),.d(gn[j]),.q(gn[j+1]));
 dsdv_gunit_pass #(.W(276),.N(2)) u_dn(.clk(ck),.rst_n(rst_n),.d(gs[j+1]),.q(gs[j]));
 end end
ot_hdc_delay #(.W(276),.D(24),.RESET(1)) gno_d(.clk(ck),.rst_n(rst_n),.d(gn[6]),.q(gno));
ot_hdc_delay #(.W(276),.D(60),.RESET(1)) gso_d(.clk(ck),.rst_n(rst_n),.d(gs[0]),.q(gso));
wire[275:0]bni,bsi,brn,brs,bkn,bks,bs,bn,bmidn,bmids;
ot_hdc_delay #(.W(276),.D(66),.RESET(1)) bni_d(.clk(ck),.rst_n(rst_n),.d(va_b),.q(bni));
ot_hdc_delay #(.W(276),.D(58),.RESET(1)) bsi_d(.clk(ck),.rst_n(rst_n),.d(vb_b),.q(bsi));
dsfd_dvrly_276_SN u_rs(.ck(ck),.rs(rst_n),.i(bni),.o(brn),.ck_o());
dsfd_dvrly_276_NS u_rn(.ck(ck),.rs(rst_n),.i(bmids),.o(brs),.ck_o());
ot_dsdv_vstop #(.V(276),.BK_DRAIN_SINK(1)) u_bk_vs(.clk(ck),.rst_n(rst_n),.tap_k(8'hff),.sink_k(8'hff),.bk_uid(8'd4),
 .vi_s(brn),.vo_n(bkn),.vi_n(brs),.vo_s(bks),.in_nv(1'b0),.in_n(276'd0),.in_sv(1'b0),.in_s(276'd0),
 .fault(fault[1]),.dl_nv(),.dl_n(),.dl_sv(),.dl_s(),.ra_s(),.ra_n(),.dk_n(),.dk_s());
dsdv_sh_vc u_sh(.ck(ck),.rst_n(rst_n),.tap_k(8'hff),.sink_k(8'hff),.vi_s(bmidn),.vo_n(bn),.vi_n(bsi),.vo_s(bs),
 .tw_i(194'd0),.cn_i(85'd0),.cs_i(85'd0),.cf_i(267'd0),.cg_i(85'd0),.dn_o(),.vf_o(fault[2]),.cw_v(),.cw_a(),.cw_d());
ot_hdc_delay #(.W(276),.D(104),.RESET(1)) bmidn_d(.clk(ck),.rst_n(rst_n),.d(bkn),.q(bmidn));
ot_hdc_delay #(.W(276),.D(106),.RESET(1)) bmids_d(.clk(ck),.rst_n(rst_n),.d(bs),.q(bmids));
ot_hdc_delay #(.W(276),.D(60),.RESET(1)) bno_d(.clk(ck),.rst_n(rst_n),.d(bn),.q(bno));
ot_hdc_delay #(.W(276),.D(60),.RESET(1)) bso_d(.clk(ck),.rst_n(rst_n),.d(bks),.q(bso));
wire[275:0]evi_s,evi_n,evo_s,evo_n;
ot_hdc_delay #(.W(276),.D(54),.RESET(1)) eni_d(.clk(ck),.rst_n(rst_n),.d(va_e),.q(evi_s));
ot_hdc_delay #(.W(276),.D(95),.RESET(1)) esi_d(.clk(ck),.rst_n(rst_n),.d(vb_e),.q(evi_n));
ot_s81eng_xq_n32 u_xq(.ck(ck),.rst_n(rst_n),.o_v(own_v),.o_col(5'd0),.o_beat(3'd1),.o_d(264'd0),
 .vi_a(evi_s),.vo_a(evo_s),.vi_b(evi_n),.vo_b(evo_n),.fault(fault[3]));
ot_hdc_delay #(.W(276),.D(93),.RESET(1)) eno_d(.clk(ck),.rst_n(rst_n),.d(evo_n),.q(eno));
ot_hdc_delay #(.W(276),.D(54),.RESET(1)) eso_d(.clk(ck),.rst_n(rst_n),.d(evo_s),.q(eso));
endmodule
