`timescale 1ns/1ps
`default_nettype none
// WIRES + seven REAL children. Controller owns command/CDC/prefetch/join state;
// six projection leaves own arithmetic, resident ROM and local x SRAM. Each
// child has its OWN real clock entry, preserving native phi-R obligations.
// Stage/control/data and result links require physical matched relay calendars;
// RETURN_CYC/FAST_CYC must be regenerated from those paths before qualification.
module dsfd_sp_hcx_projection #(
 parameter integer RANK=0,RL=4,FAST_CYC=0,
 // HLAYOUT=1: VM H rows in the HC h_rows layout (the layer's H); ot_s81_hcx_hrow_transpose re-forms canonical
 // stage words (+4 stage edges, 16 cells x 1024 b + 4096 b output register). 0 = canonical rows (component receipts).
 HLAYOUT=0,
 parameter IMAGE_PREFIX="hcx",
 parameter[95:0]RETURN_CYC={6{16'd264}},
 parameter[31:0]NORM_EPS=32'h1e3ce508
)(
 input wire cck,crst_n,skctl,srst_n,
 input wire[5:0]sk_leaf,
 input wire[84:0]c_cmd,
 output wire[8:0]c_done,
 output wire[1:0]c_st,
 output wire[7:0]rq_v,
 output wire[111:0]rq_row,
 input wire[7:0]rs_v,
 input wire[4095:0]rs_d,
 output wire t_raw_v,
 output wire[191:0]t_raw_d
);
 wire sb,sv,pv,ffn;wire[5:0]layer;wire[6:0]sw;wire[5:0]ov,lf;wire[191:0]od;
 wire tv,tf;wire[6:0]tw;wire[4095:0]td;
 generate if(HLAYOUT)begin:g_tr
  ot_s81_hcx_hrow_transpose transpose(.clk(skctl),.rst_n(srst_n),.in_begin(sb),.in_v(sv),.in_word(sw),.in_d(rs_d),
   .out_v(tv),.out_word(tw),.out_d(td),.fault(tf));
 end else begin:g_direct
  assign tv=sv,tw=sw,td=rs_d,tf=1'b0;
 end endgenerate
 ot_s81_hcx_controller #(.RL(RL),.FAST_CYC(FAST_CYC),.RETURN_CYC(RETURN_CYC),.XLAT(HLAYOUT?4:0))controller(
  .cck(cck),.crst_n(crst_n),.sk(skctl),.srst_n(srst_n),.c_cmd(c_cmd),.c_done(c_done),.c_st(c_st),
  .rq_v(rq_v),.rq_row(rq_row),.rs_v(rs_v),.stage_begin(sb),.stage_v(sv),.stage_word(sw),
  .leaf_cmd_v(pv),.leaf_ffn(ffn),.leaf_layer(layer),.leaf_v(ov),.leaf_fault(lf|{5'd0,tf}),.leaf_d(od),.t_raw_v(t_raw_v),.t_raw_d(t_raw_d));
 generate for(genvar l=0;l<6;l=l+1)begin:g_leaf
  ot_s81_hcx_projection_leaf #(
`ifdef OT_HCX_ROM_HIERLOAD
   .IMAGE("hcx")
`else
   .IMAGE($sformatf("%s_r%0d_p%0d",IMAGE_PREFIX,RANK,l))
`endif
   ,.HLAYOUT(HLAYOUT))leaf(
   .clk(sk_leaf[l]),.rst_n(srst_n),.stage_begin(sb),.stage_v(tv),.stage_word(tw),.stage_d(td),
   .cmd_v(pv),.cmd_ffn(ffn),.cmd_layer(layer),.norm_eps(NORM_EPS),.o_v(ov[l]),.o_d(od[32*l+:32]),.fault(lf[l]));
 end endgenerate
endmodule
`default_nettype wire
