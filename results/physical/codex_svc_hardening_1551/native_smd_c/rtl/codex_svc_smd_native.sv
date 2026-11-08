module codex_svc_smd_native #(parameter integer MUT=0)(
 input wire ck,
 input wire rst,
 input wire [2:0] cfg_p,
 input wire i_pv,
 input wire [63:0] i_pa,
 input wire i_dv,
 input wire [31:0] i_den,
 input wire i_csv,
 input wire [4:0] i_csi,
 input wire [63:0] i_csd,
 output wire o_ov,
 output wire [31:0] o_o,
 output wire o_f
);
 wire native_fault;
 assign o_f=(MUT==2)?1'b0:native_fault;
 codex_svc_smd_isolated #(.LPH(16),.LM(5),.LA(4)) u_native(.clk(ck),.rst_in(rst),.cfg_p(cfg_p),.i_pv(i_pv),.i_pa(i_pa),.i_dv(i_dv),.i_den((MUT==1 ? (i_den ^ 32'h00800000) : i_den)),.i_csv(i_csv),.i_csi(i_csi),.i_csd(i_csd),.o_ov(o_ov),.o_o(o_o),.o_f(native_fault));
endmodule
