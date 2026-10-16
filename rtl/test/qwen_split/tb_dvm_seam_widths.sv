// Elaboration/ABI assertion only; this is not a functional qualification bench.
module tb #(parameter NCH=4);
wire clk=0,rst_n=0;
ot_qfd_xs_leaf #(.NCH(NCH)) leaf(.clk(clk),.rst_n(rst_n));
qfd_xhead_e head(.ck(clk),.rst_n(rst_n));
initial begin
$display("LEAF_INPUT %0d",$bits(leaf.w_v)+$bits(leaf.w_ep)+$bits(leaf.w_off)+$bits(leaf.w_m)+$bits(leaf.w_d)+$bits(leaf.w_ctl)+$bits(leaf.c_v)+$bits(leaf.c_ep));
$display("LEAF_OUTPUT %0d",$bits(leaf.wo_v)+$bits(leaf.wo_ep)+$bits(leaf.wo_off)+$bits(leaf.wo_m)+$bits(leaf.wo_d)+$bits(leaf.wo_ctl)+$bits(leaf.co_v)+$bits(leaf.co_ep));
$display("HEAD_N %0d",$bits(head.cn_wv)+$bits(head.cn_wep)+$bits(head.cn_woff)+$bits(head.cn_wm)+$bits(head.cn_wd)+$bits(head.cn_wctl)+$bits(head.cn_cv)+$bits(head.cn_cep));
$display("HEAD_S %0d",$bits(head.cs_wv)+$bits(head.cs_wep)+$bits(head.cs_woff)+$bits(head.cs_wm)+$bits(head.cs_wd)+$bits(head.cs_wctl)+$bits(head.cs_cv)+$bits(head.cs_cep));
if ($bits(leaf.w_ctl)!=72 || $bits(leaf.wo_ctl)!=72)
$fatal(1,"Production chain width changed from NCH4");
$display("PASS production seam ABI, four actualRTL faces each1170bits");
$finish;
end
endmodule
