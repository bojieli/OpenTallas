`timescale 1ns/1ps
`default_nettype none
// Configuration-only form of ot_hbm_host_cfg_leaf2 copyA. Exact2edgeforwarding;
// no dormant target status inputs or unused copyB are exposed or tied.
module ot_hnx_calendar_cfg_leaf #(parameter integer MUT=0) (
 input wire clk,rst_n,
 input wire cfg_v,input wire[7:0]cfg_target,input wire[11:0]cfg_addr,input wire[255:0]cfg_data,
 input wire desc_v,input wire[11:0]desc_base,input wire[12:0]desc_limit,input wire[15:0]desc_loops,
 input wire launch_v,
 output wire a_cfg_v,output wire[7:0]a_cfg_target,output wire[11:0]a_cfg_addr,output wire[255:0]a_cfg_data,
 output wire a_desc_v,output wire[11:0]a_desc_base,output wire[12:0]a_desc_limit,output wire[15:0]a_desc_loops,
 output wire a_launch_v
);
 wire[1:0]rr;
 ot_rst_relay #(.REGIONS(2),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 reg[316:0]pl_p,pl_c;
 reg cv_p,dv_p,lv_p,cv_c,dv_c,lv_c;
 always @(posedge clk)begin
  pl_p<={desc_loops,desc_limit,desc_base,cfg_data,cfg_addr,cfg_target};
  pl_c<=pl_p;
 end
 always @(posedge clk or negedge rr[0])begin
  if(!rr[0])begin cv_p<=0;dv_p<=0;lv_p<=0;cv_c<=0;dv_c<=0;lv_c<=0;end
  else begin cv_p<=cfg_v;dv_p<=desc_v;lv_p<=launch_v;cv_c<=cv_p;dv_c<=dv_p;lv_c<=lv_p;end
 end
 assign a_cfg_v=cv_c;assign a_desc_v=dv_c;assign a_launch_v=lv_c;
 assign a_cfg_target=pl_c[0+:8];assign a_cfg_addr=pl_c[8+:12];assign a_cfg_data=(MUT==1)?(pl_c[20+:256]^256'd1):pl_c[20+:256];
 assign a_desc_base=pl_c[276+:12];assign a_desc_limit=pl_c[288+:13];assign a_desc_loops=pl_c[301+:16];
endmodule
`default_nettype wire
