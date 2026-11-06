`timescale 1ns/1ps
module captured_kshare_wb_faces(input wire hbm_clk,hbm_rst_n,
 input wire[3:0]w_k_v,output wire[3:0]w_k_rdy,input wire[119:0]w_k_addr,input wire[1023:0]w_k_wdata,
 output wire[3:0]rx_v,input wire[3:0]rx_rdy,output wire[119:0]rx_addr,output wire[1023:0]rx_data);
 wire[119:0]w_k_addr__fq;wire[3:0]w_k_rdy__fc,w_k_v__fq;wire[1023:0]w_k_wdata__fq;
 reg hrst_q;always @(posedge hbm_clk or negedge hbm_rst_n)if(!hbm_rst_n)hrst_q<=0;else hrst_q<=1;
    (* keep *) ot_hbm_face_reg #(.W(120)) u_bin_w_k_addr (.clk(hbm_clk), .d(w_k_addr), .q(w_k_addr__fq));
    (* keep *) ot_hbm_face_reg #(.W(4)) u_bout_w_k_rdy (.clk(hbm_clk), .d(w_k_rdy__fc), .q(w_k_rdy));
    (* keep *) ot_hbm_face_reg #(.W(4)) u_bin_w_k_v (.clk(hbm_clk), .d(w_k_v), .q(w_k_v__fq));
    (* keep *) ot_hbm_face_reg #(.W(1024)) u_bin_w_k_wdata (.clk(hbm_clk), .d(w_k_wdata), .q(w_k_wdata__fq));
 genvar l;
 generate for(l=0;l<4;l=l+1)begin:lane
 ot_hbm_svc_pin_skid2 #(.WIDTH(286)) u_e(.clk(hbm_clk),.rst_n(hrst_q),.in_v(w_k_v__fq[l]),.in_r(w_k_rdy__fc[l]),
 .in_data({w_k_addr__fq[30*l+:30],w_k_wdata__fq[256*l+:256]}),.out_v(rx_v[l]),.out_r(rx_rdy[l]),
 .out_data({rx_addr[30*l+:30],rx_data[256*l+:256]}));
 end endgenerate
endmodule
