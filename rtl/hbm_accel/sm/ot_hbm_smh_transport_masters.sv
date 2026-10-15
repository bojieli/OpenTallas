// Fixed production specializations: independent physical clock roots, unchanged pipeline.
module ot_smh_tr_w128_s2_m0 (input wire clk,rst_a,input wire [127:0] d,output wire [127:0] first,last);
ot_hbm_smh_transport_slice #(.W(128),.STAGES(2),.RESET_MASK(128'h0)) u_core (.clk(clk),.rst_a(rst_a),.d(d),.first(first),.last(last));
endmodule
module ot_smh_tr_w128_s1_m0 (input wire clk,rst_a,input wire [127:0] d,output wire [127:0] first,last);
ot_hbm_smh_transport_slice #(.W(128),.STAGES(1),.RESET_MASK(128'h0)) u_core (.clk(clk),.rst_a(rst_a),.d(d),.first(first),.last(last));
endmodule
module ot_smh_tr_w128_s2_m80 (input wire clk,rst_a,input wire [127:0] d,output wire [127:0] first,last);
ot_hbm_smh_transport_slice #(.W(128),.STAGES(2),.RESET_MASK(128'h80)) u_core (.clk(clk),.rst_a(rst_a),.d(d),.first(first),.last(last));
endmodule
module ot_smh_tr_w50_s2_m3000000000000 (input wire clk,rst_a,input wire [49:0] d,output wire [49:0] first,last);
ot_hbm_smh_transport_slice #(.W(50),.STAGES(2),.RESET_MASK(50'h3000000000000)) u_core (.clk(clk),.rst_a(rst_a),.d(d),.first(first),.last(last));
endmodule
module ot_smh_tr_w21_s2_m100000 (input wire clk,rst_a,input wire [20:0] d,output wire [20:0] first,last);
ot_hbm_smh_transport_slice #(.W(21),.STAGES(2),.RESET_MASK(21'h100000)) u_core (.clk(clk),.rst_a(rst_a),.d(d),.first(first),.last(last));
endmodule
module ot_smh_tr_w21_s1_m100000 (input wire clk,rst_a,input wire [20:0] d,output wire [20:0] first,last);
ot_hbm_smh_transport_slice #(.W(21),.STAGES(1),.RESET_MASK(21'h100000)) u_core (.clk(clk),.rst_a(rst_a),.d(d),.first(first),.last(last));
endmodule
module ot_hbm_smh_transport_hard #(parameter integer W=128,STAGES=2,parameter [W-1:0] RESET_MASK=0) (input wire clk,rst_a,input wire [W-1:0] d,output wire [W-1:0] first,last);
generate
if (W==128 && STAGES==2 && RESET_MASK==128'h0) begin:g_0
ot_smh_tr_w128_s2_m0 u_hard (.clk(clk),.rst_a(rst_a),.d(d),.first(first),.last(last));
end
else if (W==128 && STAGES==1 && RESET_MASK==128'h0) begin:g_1
ot_smh_tr_w128_s1_m0 u_hard (.clk(clk),.rst_a(rst_a),.d(d),.first(first),.last(last));
end
else if (W==128 && STAGES==2 && RESET_MASK==128'h80) begin:g_2
ot_smh_tr_w128_s2_m80 u_hard (.clk(clk),.rst_a(rst_a),.d(d),.first(first),.last(last));
end
else if (W==50 && STAGES==2 && RESET_MASK==50'h3000000000000) begin:g_3
ot_smh_tr_w50_s2_m3000000000000 u_hard (.clk(clk),.rst_a(rst_a),.d(d),.first(first),.last(last));
end
else if (W==21 && STAGES==2 && RESET_MASK==21'h100000) begin:g_4
ot_smh_tr_w21_s2_m100000 u_hard (.clk(clk),.rst_a(rst_a),.d(d),.first(first),.last(last));
end
else if (W==21 && STAGES==1 && RESET_MASK==21'h100000) begin:g_5
ot_smh_tr_w21_s1_m100000 u_hard (.clk(clk),.rst_a(rst_a),.d(d),.first(first),.last(last));
end
else begin:g_illegal
SMH_UNSUPPORTED_TRANSPORT_SPECIALIZATION must_fail_elaboration();
end endgenerate
endmodule
