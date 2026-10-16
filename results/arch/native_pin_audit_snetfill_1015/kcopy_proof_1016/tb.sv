`timescale 1ns/1ps
module tb; reg ck, rst_n; integer n, k, err;
reg [1100:0] p0_di;
wire [1100:0] p0_dq, ref_p0_dq;
reg [514:0] p1_di;
wire [514:0] p1_dq, ref_p1_dq;
reg [1100:0] p2_di;
wire [1100:0] p2_dq, ref_p2_dq;
reg [291:0] p3_di;
wire [291:0] p3_dq, ref_p3_dq;
reg [4095:0] p4_di;
wire [4095:0] p4_dq, ref_p4_dq;
wire [0:0] p5_fo, ref_p5_fo;
reg [1100:0] p5_i;
wire [565:0] p5_oa, ref_p5_oa;
wire [537:0] p5_ob, ref_p5_ob;
wire [2:0] p5_st, ref_p5_st;
wire [0:0] p5_fo2, ref_p5_fo2;
wire [0:0] p6_fo, ref_p6_fo;
reg [1100:0] p6_i;
wire [565:0] p6_oa, ref_p6_oa;
wire [537:0] p6_ob, ref_p6_ob;
wire [2:0] p6_st, ref_p6_st;
wire [0:0] p6_fo2, ref_p6_fo2;
dsfd_hstnh_1101 ref0 (.ck(ck), .di(p0_di), .dq(ref_p0_dq));
dsfd_hstnh_515 ref1 (.ck(ck), .di(p1_di), .dq(ref_p1_dq));
dsfd_hstnv_1101 ref2 (.ck(ck), .di(p2_di), .dq(ref_p2_dq));
dsfd_hstnv_292 ref3 (.ck(ck), .di(p3_di), .dq(ref_p3_dq));
dsfd_hstnv_4096 ref4 (.ck(ck), .di(p4_di), .dq(ref_p4_dq));
dsfd_l2r_vr_1100x1__hx_E ref5 (.ck(ck), .cks(ck), .fo(ref_p5_fo), .i(p5_i), .oa(ref_p5_oa), .ob(ref_p5_ob), .rs(rst_n), .rss(rst_n), .st(ref_p5_st), .fo2(ref_p5_fo2));
dsfd_l2r_vr_1100x1__hx_W ref6 (.ck(ck), .cks(ck), .fo(ref_p6_fo), .i(p6_i), .oa(ref_p6_oa), .ob(ref_p6_ob), .rs(rst_n), .rss(rst_n), .st(ref_p6_st), .fo2(ref_p6_fo2));
kcopy_die dut (.p0_ck(ck), .p0_di(p0_di), .p0_dq(p0_dq), .p1_ck(ck), .p1_di(p1_di), .p1_dq(p1_dq), .p2_ck(ck), .p2_di(p2_di), .p2_dq(p2_dq), .p3_ck(ck), .p3_di(p3_di), .p3_dq(p3_dq), .p4_ck(ck), .p4_di(p4_di), .p4_dq(p4_dq), .p5_ck(ck), .p5_cks(ck), .p5_fo(p5_fo), .p5_i(p5_i), .p5_oa(p5_oa), .p5_ob(p5_ob), .p5_rs(rst_n), .p5_rss(rst_n), .p5_st(p5_st), .p5_fo2(p5_fo2), .p6_ck(ck), .p6_cks(ck), .p6_fo(p6_fo), .p6_i(p6_i), .p6_oa(p6_oa), .p6_ob(p6_ob), .p6_rs(rst_n), .p6_rss(rst_n), .p6_st(p6_st), .p6_fo2(p6_fo2));
initial begin ck = 0; rst_n = 0; err = 0;
for (n = 0; n < 2000; n = n + 1) begin
for (k = 0; k < 1101; k = k + 32) p0_di[k +: 32] = $random;
for (k = 0; k < 515; k = k + 32) p1_di[k +: 32] = $random;
for (k = 0; k < 1101; k = k + 32) p2_di[k +: 32] = $random;
for (k = 0; k < 292; k = k + 32) p3_di[k +: 32] = $random;
for (k = 0; k < 4096; k = k + 32) p4_di[k +: 32] = $random;
for (k = 0; k < 1101; k = k + 32) p5_i[k +: 32] = $random;
for (k = 0; k < 1101; k = k + 32) p6_i[k +: 32] = $random;
if (n == 3) rst_n = 1; if (n == 1000) rst_n = 0; if (n == 1010) rst_n = 1;
#2; ck = 1; #1;
if (p0_dq !== ref_p0_dq) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_hstnh_1101.dq cycle %0d", n); end
if (p1_dq !== ref_p1_dq) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_hstnh_515.dq cycle %0d", n); end
if (p2_dq !== ref_p2_dq) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_hstnv_1101.dq cycle %0d", n); end
if (p3_dq !== ref_p3_dq) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_hstnv_292.dq cycle %0d", n); end
if (p4_dq !== ref_p4_dq) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_hstnv_4096.dq cycle %0d", n); end
if (p5_fo !== ref_p5_fo) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_E.fo cycle %0d", n); end
if (p5_oa !== ref_p5_oa) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_E.oa cycle %0d", n); end
if (p5_ob !== ref_p5_ob) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_E.ob cycle %0d", n); end
if (p5_st !== ref_p5_st) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_E.st cycle %0d", n); end
if (p5_fo2 !== ref_p5_fo2) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_E.fo2 cycle %0d", n); end
if (p6_fo !== ref_p6_fo) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_W.fo cycle %0d", n); end
if (p6_oa !== ref_p6_oa) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_W.oa cycle %0d", n); end
if (p6_ob !== ref_p6_ob) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_W.ob cycle %0d", n); end
if (p6_st !== ref_p6_st) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_W.st cycle %0d", n); end
if (p6_fo2 !== ref_p6_fo2) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_W.fo2 cycle %0d", n); end
#2; ck = 0; #1;
if (p0_dq !== ref_p0_dq) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_hstnh_1101.dq cycle %0d", n); end
if (p1_dq !== ref_p1_dq) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_hstnh_515.dq cycle %0d", n); end
if (p2_dq !== ref_p2_dq) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_hstnv_1101.dq cycle %0d", n); end
if (p3_dq !== ref_p3_dq) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_hstnv_292.dq cycle %0d", n); end
if (p4_dq !== ref_p4_dq) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_hstnv_4096.dq cycle %0d", n); end
if (p5_fo !== ref_p5_fo) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_E.fo cycle %0d", n); end
if (p5_oa !== ref_p5_oa) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_E.oa cycle %0d", n); end
if (p5_ob !== ref_p5_ob) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_E.ob cycle %0d", n); end
if (p5_st !== ref_p5_st) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_E.st cycle %0d", n); end
if (p5_fo2 !== ref_p5_fo2) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_E.fo2 cycle %0d", n); end
if (p6_fo !== ref_p6_fo) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_W.fo cycle %0d", n); end
if (p6_oa !== ref_p6_oa) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_W.oa cycle %0d", n); end
if (p6_ob !== ref_p6_ob) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_W.ob cycle %0d", n); end
if (p6_st !== ref_p6_st) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_W.st cycle %0d", n); end
if (p6_fo2 !== ref_p6_fo2) begin err = err + 1; if (err < 6) $display("KCOPY_MISMATCH dsfd_l2r_vr_1100x1__hx_W.fo2 cycle %0d", n); end
end
if (err == 0) $display("KCOPY_EXACT PASS 7 FROM masters 2000 cycles every output both edges incl. mid-run reset");
else begin $display("KCOPY_FAIL %0d mismatches", err); $fatal(1); end
$finish; end

endmodule
