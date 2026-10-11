`timescale 1ns/1ps
`default_nettype none
// mtp-fixlat-1011: P2 slab composition = dsfd_p2_lnk (dsfd_p2_lnk.sv) at the pins of the unchanged rb4 core.
// P2 slab = core + its link ends (composition used by the stationed bench; the core keeps its closed outline).
module dsfd_p2_rtt #(parameter integer FWD_V = 12, parameter integer RET_V = 14,
                     parameter integer FWD_C = 8, parameter integer RET_C = 9) (
 input wire [0:0] ck, rst,
 input wire f_l0v, input wire [603:0] f_l0d, output wire t_l0g,
 input wire f_l1v, input wire [603:0] f_l1d, output wire t_l1g,
 input wire f_sv,  input wire [100:0] f_sd,  output wire t_sg,
 output wire t_ov, output wire [593:0] t_od, input wire f_og,
 input wire f_abort, output wire t_done, t_fault, t_corrected
);
 wire [1:0] iv, ir; wire [1207:0] id; wire sv, sr; wire [100:0] sd; wire ov, orr; wire [511:0] od; wire [73:0] oid;
 wire [6:0] ow; wire ol;
 wire clk = ck[0];
 wire rst_n;
 ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rst_n));
 dsfd_p2_lnk #(.FWD_V(FWD_V),.RET_V(RET_V),.FWD_C(FWD_C),.RET_C(RET_C)) u_lnk(.ck(ck),.rst(rst),
  .f_l0v(f_l0v),.f_l0d(f_l0d),.t_l0g(t_l0g),.f_l1v(f_l1v),.f_l1d(f_l1d),.t_l1g(t_l1g),.f_sv(f_sv),.f_sd(f_sd),.t_sg(t_sg),
  .t_ov(t_ov),.t_od(t_od),.f_og(f_og),.c_in_v(iv),.c_in_r(ir),.c_in_d(id),.c_start_v(sv),.c_start_r(sr),.c_start_d(sd),
  .c_out_v(ov),.c_out_r(orr),.c_out_d({od,oid,ow,ol}));
 ot_mtp_p2_prefix_path #(.ENABLE(1),.REGB(1),.ROOTPIPE(1)) u_core(.clk(clk),.rst_n(rst_n),
  .start_v(sv),.start_r(sr),.start_identity(sd[100:27]),.start_ids(sd[26:0]),
  .in_v(iv),.in_r(ir),.in_identity({id[1207:1134],id[603:530]}),.in_expert({id[1133:1125],id[529:521]}),
  .in_shared({id[1124],id[520]}),.in_last({id[1123],id[519]}),.in_word({id[1122:1116],id[518:512]}),
  .in_data({id[1115:604],id[511:0]}),
  .out_v(ov),.out_r(orr),.out_data(od),.out_identity(oid),.out_word(ow),.out_last(ol),
  .abort(f_abort),.done(t_done),.fault(t_fault),.corrected(t_corrected));
endmodule

`default_nettype wire
