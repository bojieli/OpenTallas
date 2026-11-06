// Unadopted full-clock R2 reference provider. Exact rawOUT from41ba3e486d3.
// Equivalent to face_shell on/reset-relay2/pass-all-signals; no ready/valid/data FF insertion.
module ot_wbq_sw_split_out (
 input wire hbm_clk,hbm_rst_n,
 input wire [15:0] in_v,output wire [15:0] in_ready,
 input wire [479:0] in_addr,input wire [4095:0] in_data,
 output wire [15:0] w_k_v,input wire [15:0] w_k_rdy,
 output wire [479:0] w_k_addr,output wire [4095:0] w_k_wdata
);
 wire rst_native;
 ot_hbm_face_rst_relay #(.N(2)) u_rst(.clk(hbm_clk),.rst_ni(hbm_rst_n),.rst_no(rst_native));
 ot_wbq_sw_split_out__native_r2_fcore u_fcore(.hbm_clk(hbm_clk),.hbm_rst_n(rst_native),
 .in_v(in_v),.in_ready(in_ready),.in_addr(in_addr),.in_data(in_data),
 .w_k_v(w_k_v),.w_k_rdy(w_k_rdy),.w_k_addr(w_k_addr),.w_k_wdata(w_k_wdata));
endmodule

module ot_wbq_sw_split_out__native_r2_fcore #(parameter integer MUT=0)(
 input wire hbm_clk,hbm_rst_n,
 input wire [15:0] in_v,output wire [15:0] in_ready,
 input wire [479:0] in_addr,input wire [4095:0] in_data,
 output wire [15:0] w_k_v,input wire [15:0] w_k_rdy,
 output wire [479:0] w_k_addr,output wire [4095:0] w_k_wdata
);
 genvar p;
 generate for(p=0;p<16;p=p+1)begin:pc_pin
  wire krst;
  ot_reset_sync u_krst(.clk(hbm_clk),.async_rst_n(hbm_rst_n),.sync_rst_n(krst));
  ot_hbm_svc_pin_skid2 #(.WIDTH(286),.MUT(MUT)) u_k(.clk(hbm_clk),.rst_n(krst),.in_v(in_v[p]),.in_r(in_ready[p]),
   .in_data({in_addr[30*p+:30],in_data[256*p+:256]}),.out_v(w_k_v[p]),.out_r(w_k_rdy[p]),
   .out_data({w_k_addr[30*p+:30],w_k_wdata[256*p+:256]}));
 end endgenerate
endmodule
