(* blackbox *)
module hfd_hgi_vm_calendar_f20 #(parameter integer RMUT=0) (
    input wire clk,clk_cap,clk_mem,clk_tgt,rst_n,
    input wire [7:0] tgt,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    output wire tgt_configured,tgt_fault,
    output wire calendar_v,active,done,fault,
    output wire [31:0] ordinal,
    output wire [9:0] client_seq,
    output wire [4:0] response_enable,
    output wire [9:0] response_seq,
    output wire [7:0] bank_enable,
    output wire [23:0] bank_client,
    output wire [1:0] hub_ring_enable,
    output wire [5:0] hub_ring_client,
    output wire [7:0] rslot_v,
    output wire [7:0] wslot_v,
    output wire [23:0] rslot,
    output wire [23:0] wslot,
    output wire [1:0] ring_tx_enable,
    output wire [5:0] ring_tx_source,
    output wire replay_enable,
    output wire replay_source,
    output wire [23:0] lg_local_read,
    output wire [23:0] lg_local_write
);

endmodule

(* blackbox *)
module hfd_hgi_vms_glue_nw_t (
    input wire clk,
    input wire rst_n,
    input wire [1:0] client_seq,
    input wire response_enable,
    input wire [1:0] response_seq,
    input wire [7:0] bank_enable,
    input wire [7:0] bank_client,
    input wire [1:0] hub_ring_enable,
    input wire [1:0] hub_ring_client,
    input wire [2223:0] cw_in,
    input wire [2223:0] ccw_in,
    output wire [2223:0] cw_out,
    output wire [2223:0] ccw_out,
    input wire [1:0] ring_tx_enable,
    input wire [5:0] ring_tx_source,
    input wire replay_enable,
    input wire replay_source,
    output wire [275:0] b0_xq,
    output wire [275:0] b0_xq2,
    input wire b0_xq_done,
    input wire b0_xq2_done,
    input wire [275:0] b0_eg,
    output wire [284:0] b0_pq,
    input wire [265:0] b0_pr,
    input wire [17:0] b0_status,
    input wire b0_flt,
    output wire [275:0] b1_xq,
    output wire [275:0] b1_xq2,
    input wire b1_xq_done,
    input wire b1_xq2_done,
    input wire [275:0] b1_eg,
    output wire [284:0] b1_pq,
    input wire [265:0] b1_pr,
    input wire [17:0] b1_status,
    input wire b1_flt,
    output wire [275:0] b2_xq,
    output wire [275:0] b2_xq2,
    input wire b2_xq_done,
    input wire b2_xq2_done,
    input wire [275:0] b2_eg,
    output wire [284:0] b2_pq,
    input wire [265:0] b2_pr,
    input wire [17:0] b2_status,
    input wire b2_flt,
    output wire [275:0] b3_xq,
    output wire [275:0] b3_xq2,
    input wire b3_xq_done,
    input wire b3_xq2_done,
    input wire [275:0] b3_eg,
    output wire [284:0] b3_pq,
    input wire [265:0] b3_pr,
    input wire [17:0] b3_status,
    input wire b3_flt,
    output wire [275:0] b4_xq,
    output wire [275:0] b4_xq2,
    input wire b4_xq_done,
    input wire b4_xq2_done,
    input wire [275:0] b4_eg,
    output wire [284:0] b4_pq,
    input wire [265:0] b4_pr,
    input wire [17:0] b4_status,
    input wire b4_flt,
    output wire [275:0] b5_xq,
    output wire [275:0] b5_xq2,
    input wire b5_xq_done,
    input wire b5_xq2_done,
    input wire [275:0] b5_eg,
    output wire [284:0] b5_pq,
    input wire [265:0] b5_pr,
    input wire [17:0] b5_status,
    input wire b5_flt,
    output wire [275:0] b6_xq,
    output wire [275:0] b6_xq2,
    input wire b6_xq_done,
    input wire b6_xq2_done,
    input wire [275:0] b6_eg,
    output wire [284:0] b6_pq,
    input wire [265:0] b6_pr,
    input wire [17:0] b6_status,
    input wire b6_flt,
    output wire [275:0] b7_xq,
    output wire [275:0] b7_xq2,
    input wire b7_xq_done,
    input wire b7_xq2_done,
    input wire [275:0] b7_eg,
    output wire [284:0] b7_pq,
    input wire [265:0] b7_pr,
    input wire [17:0] b7_status,
    input wire b7_flt,
    output wire [2:0] hub_status,
    output wire [1:0] mirror_busy,
    output wire [18:0] vmstat,
    output wire [2:0] ring_fault
);

endmodule

(* blackbox *)
module hfd_hgi_vms_glue_sw_t (
    input wire clk,
    input wire rst_n,
    input wire [675:0] cq,
    output wire [547:0] cr,
    input wire [5:0] client_seq,
    input wire [2:0] response_enable,
    input wire [5:0] response_seq,
    input wire [7:0] bank_enable,
    input wire [15:0] bank_client,
    input wire [1:0] hub_ring_enable,
    input wire [3:0] hub_ring_client,
    input wire [2223:0] cw_in,
    input wire [2223:0] ccw_in,
    output wire [2223:0] cw_out,
    output wire [2223:0] ccw_out,
    input wire [1:0] ring_tx_enable,
    input wire [5:0] ring_tx_source,
    input wire replay_enable,
    input wire replay_source,
    output wire [275:0] b0_xq,
    output wire [275:0] b0_xq2,
    input wire b0_xq_done,
    input wire b0_xq2_done,
    input wire [275:0] b0_eg,
    output wire [284:0] b0_pq,
    input wire [265:0] b0_pr,
    input wire [17:0] b0_status,
    output wire [275:0] b1_xq,
    output wire [275:0] b1_xq2,
    input wire b1_xq_done,
    input wire b1_xq2_done,
    input wire [275:0] b1_eg,
    output wire [284:0] b1_pq,
    input wire [265:0] b1_pr,
    input wire [17:0] b1_status,
    output wire [275:0] b2_xq,
    output wire [275:0] b2_xq2,
    input wire b2_xq_done,
    input wire b2_xq2_done,
    input wire [275:0] b2_eg,
    output wire [284:0] b2_pq,
    input wire [265:0] b2_pr,
    input wire [17:0] b2_status,
    output wire [275:0] b3_xq,
    output wire [275:0] b3_xq2,
    input wire b3_xq_done,
    input wire b3_xq2_done,
    input wire [275:0] b3_eg,
    output wire [284:0] b3_pq,
    input wire [265:0] b3_pr,
    input wire [17:0] b3_status,
    output wire [275:0] b4_xq,
    output wire [275:0] b4_xq2,
    input wire b4_xq_done,
    input wire b4_xq2_done,
    input wire [275:0] b4_eg,
    output wire [284:0] b4_pq,
    input wire [265:0] b4_pr,
    input wire [17:0] b4_status,
    output wire [275:0] b5_xq,
    output wire [275:0] b5_xq2,
    input wire b5_xq_done,
    input wire b5_xq2_done,
    input wire [275:0] b5_eg,
    output wire [284:0] b5_pq,
    input wire [265:0] b5_pr,
    input wire [17:0] b5_status,
    output wire [275:0] b6_xq,
    output wire [275:0] b6_xq2,
    input wire b6_xq_done,
    input wire b6_xq2_done,
    input wire [275:0] b6_eg,
    output wire [284:0] b6_pq,
    input wire [265:0] b6_pr,
    input wire [17:0] b6_status,
    output wire [275:0] b7_xq,
    output wire [275:0] b7_xq2,
    input wire b7_xq_done,
    input wire b7_xq2_done,
    input wire [275:0] b7_eg,
    output wire [284:0] b7_pq,
    input wire [265:0] b7_pr,
    input wire [17:0] b7_status,
    output wire [2:0] hub_status,
    output wire [1:0] mirror_busy,
    output wire [18:0] vmstat,
    output wire [2:0] ring_fault
);

endmodule

(* blackbox *)
module hfd_vms_bank_native_q0_faces (rq0, rr0, rq1, rr1, rq2, rr2, rq3, rr3, rq4, rr4, wq0, wq_done0, wq1, wq_done1, bid, sid, clk, clk_n, clk_s, clk_e, clk_w, clk_macro0, clk_macro1, clk_macro2, rst_n, rslot_v, rslot, wslot_v, wslot, dq, dq_done, kq, kq_done, xq, xq_done, xq2, xq2_done, eg, pq, pr, status);
  input [16:0] rq0;
  output [256:0] rr0;
  input [16:0] rq1;
  output [256:0] rr1;
  input [16:0] rq2;
  output [256:0] rr2;
  input [16:0] rq3;
  output [256:0] rr3;
  input [16:0] rq4;
  output [256:0] rr4;
  input [280:0] wq0;
  output wq_done0;
  input [280:0] wq1;
  output wq_done1;
  input [2:0] bid;
  input [1:0] sid;
  input clk, clk_n, clk_s, clk_e, clk_w, clk_macro0, clk_macro1, clk_macro2;
  input rst_n;
  input rslot_v;
  input [2:0] rslot;
  input wslot_v;
  input [2:0] wslot;
  input [280:0] dq;
  output dq_done;
  input [280:0] kq;
  output kq_done;
  input [275:0] xq;
  output xq_done;
  input [275:0] xq2;
  output xq2_done;
  output [275:0] eg;
  input [284:0] pq;
  output [265:0] pr;
  output [17:0] status;
endmodule

(* blackbox *)
module ot_hbm_hc_subtree32_core (
    input wire [0:0] clk,
    input wire [1023:0] data,
    output wire [30:0] node_fault,
    input wire [0:0] rst_n,
    output wire [31:0] sum,
    input wire [0:0] valid_in,
    output wire [0:0] valid_out
);

endmodule

(* blackbox *)
module ot_hbm_idx_qctl_static(
 input wire clk_program,clk_program_mem,input wire rst_n,
 input wire slot,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,input wire[13:0]nkeys,
 output reg weight_slot,query_slot,output reg[6:0]query_index,
 output reg query_emit,output reg[4:0]query_emit_head,
 output reg key_slot,output reg[7:0]key_index,
 output reg[11:0]nq,output reg frame_start,
 input wire vf,qf,scf,
 output reg fault
);

endmodule

(* blackbox *)
module ot_hbm_idx_query_static(
 input wire clk,clk_quant,clk_quant_delay,input wire [3:0] clk_bank,
 input wire rst_n,frame_start,
 input wire block_v,input wire [4:0] block_head,input wire [1:0] block_number,
 input wire [1023:0] block_data,input wire [15:0] head_weight,
 input wire emit_v,input wire [4:0] emit_head,
 output reg ql_v,output reg [7:0] ql_head,
 output reg [511:0] ql_codes,output reg [31:0] ql_sc,output reg [15:0] ql_w,
 output reg fault
);

endmodule

(* blackbox *)
module ot_hbm_idx_vm_query_static_n12 #(parameter integer VM_RT_EXTRA = 4)(
 input wire clk,rst_n,input wire[1:0]sid,
 input wire weight_slot,query_slot,input wire[6:0]query_index,
 input wire[15:0]weight_sector,query_sector,
 output reg[135:0]vm_rq,input wire[2055:0]vm_rr,
 output reg block_v,output reg[4:0]block_head,output reg[1:0]block_number,
 output reg[1023:0]block_data,output reg[15:0]head_weight,
 output reg fault
);

endmodule

(* blackbox *)
module ot_hbm_sm_vm_wr_q_t_lanes4 #(parameter integer DEPTH = 4, parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          clk_cal,
    input  wire          rst_n,
    input  wire [7:0]    tgt,
    input  wire [1:0]    quad,
    input  wire          lbase,     
    input  wire          cfg_v,
    input  wire [7:0]    cfg_target,
    input  wire [11:0]   cfg_addr,
    input  wire [255:0]  cfg_data,
    input  wire          desc_v,
    input  wire [11:0]   desc_base,
    input  wire [12:0]   desc_limit,
    input  wire [15:0]   desc_loops,
    input  wire          launch_v,
    input  wire          clk_l0, rv_s0, smf_s0, sms_s0,
    input  wire [11:0]   rrow_s0,
    input  wire [255:0]  rdata_s0,
    output wire [280:0]  wq_s0,
    output wire [280:0]  wq_t0,       
    input  wire          clk_l1, rv_s1, smf_s1, sms_s1,
    input  wire [11:0]   rrow_s1,
    input  wire [255:0]  rdata_s1,
    output wire [280:0]  wq_s1,
    output wire [280:0]  wq_t1,       
    input  wire          clk_l2, rv_s2, smf_s2, sms_s2,
    input  wire [11:0]   rrow_s2,
    input  wire [255:0]  rdata_s2,
    output wire [280:0]  wq_s2,
    output wire [280:0]  wq_t2,       
    input  wire          clk_l3, rv_s3, smf_s3, sms_s3,
    input  wire [11:0]   rrow_s3,
    input  wire [255:0]  rdata_s3,
    output wire [280:0]  wq_s3,
    output wire [280:0]  wq_t3,       
    output wire          configured,
    output wire          fault,
    output wire          active
);

endmodule

(* blackbox *)
module ot_hbm_su_programme_pslice_c5 #(
  parameter integer SB=2422, NC=(SB+255)/256,
  parameter [32*NC-1:0] DICT_CAP={32'd1,32'd1,32'd1,32'd1,32'd1,32'd2,32'd13,32'd9,32'd10,32'd3},
  parameter integer MUT=0, MUT_COL=1
  
  
)(input logic clk, rst_n,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [SB-1:0] command);

endmodule

(* blackbox *)

module ot_hbm_su_static_cxport_ij_q #(parameter integer SD=0, MUT=0, R=8, SAFE_GATHER=0)(
 input wire clk_q, rst_q_n,
 input wire [31:0] jb0, jb1,
 input wire [1023:0] inj_q0, inj_q1, inj_q2, inj_q3,   
 output reg [1023:0] ob0, ob1,
 input wire sfault_s, ins_coll,
 output reg fault
);
 localparam integer RN=SAFE_GATHER?64:R, RPW=SAFE_GATHER?RN+1:RN, RJ=SAFE_GATHER?RN:0;
endmodule

(* blackbox *)
module ot_hbm_su_static_qcore_r13_w2 #(parameter integer MUT=0,COLLPORT=1,RF_LOCAL=1,PRETREE=0,ROW_EN=0,WDEC=0,MUTW=0)(
 input wire clk_ctl,rst_n,
 input wire [6*9-1:0] rf_rd_cmd,
 input wire [73:0] red_cmd,
 input wire [1:0] rf_drain_cmd,
 input wire [4*32-1:0] slice_x,
 input wire [1:0] rf_wv, input wire [2*8-1:0] rf_wa, input wire [2*32-1:0] rf_wd,
 output wire [4*32-1:0] rf_bword,
 output wire [4*9-1:0] rf_bcmd,
 output wire [255:0] rf_dsec,
 output wire red_sv, output wire [31:0] red_tag, output wire [31:0] red_x,
 output wire red_rf_v,
 input wire rr_wv,
 input wire [4:0] rr_wa,
 input wire [255:0] rr_wd,
 input wire [31:0] sfu_x,
 input wire [4*67-1:0] slice_t,
 output wire fault
);

endmodule

(* blackbox *)
module ot_hbm_su_static_sfustore_hw #(parameter integer MUT=0)(
 input wire clk, rst_n,
 input wire [1:0] qid,
 input wire l00_vi_re, input wire [23:0] l00_vi_addr, output wire [31:0] l00_vi_q,
 input wire l00_kv_we, input wire [23:0] l00_kv_waddr, input wire [31:0] l00_kv_wdata,
 input wire l01_vi_re, input wire [23:0] l01_vi_addr, output wire [31:0] l01_vi_q,
 input wire l01_kv_we, input wire [23:0] l01_kv_waddr, input wire [31:0] l01_kv_wdata,
 input wire l02_vi_re, input wire [23:0] l02_vi_addr, output wire [31:0] l02_vi_q,
 input wire l02_kv_we, input wire [23:0] l02_kv_waddr, input wire [31:0] l02_kv_wdata,
 input wire l03_vi_re, input wire [23:0] l03_vi_addr, output wire [31:0] l03_vi_q,
 input wire l03_kv_we, input wire [23:0] l03_kv_waddr, input wire [31:0] l03_kv_wdata,
 input wire l04_vi_re, input wire [23:0] l04_vi_addr, output wire [31:0] l04_vi_q,
 input wire l04_kv_we, input wire [23:0] l04_kv_waddr, input wire [31:0] l04_kv_wdata,
 input wire l05_vi_re, input wire [23:0] l05_vi_addr, output wire [31:0] l05_vi_q,
 input wire l05_kv_we, input wire [23:0] l05_kv_waddr, input wire [31:0] l05_kv_wdata,
 input wire l06_vi_re, input wire [23:0] l06_vi_addr, output wire [31:0] l06_vi_q,
 input wire l06_kv_we, input wire [23:0] l06_kv_waddr, input wire [31:0] l06_kv_wdata,
 input wire l07_vi_re, input wire [23:0] l07_vi_addr, output wire [31:0] l07_vi_q,
 input wire l07_kv_we, input wire [23:0] l07_kv_waddr, input wire [31:0] l07_kv_wdata,
 input wire l08_vi_re, input wire [23:0] l08_vi_addr, output wire [31:0] l08_vi_q,
 input wire l08_kv_we, input wire [23:0] l08_kv_waddr, input wire [31:0] l08_kv_wdata,
 input wire l09_vi_re, input wire [23:0] l09_vi_addr, output wire [31:0] l09_vi_q,
 input wire l09_kv_we, input wire [23:0] l09_kv_waddr, input wire [31:0] l09_kv_wdata,
 input wire l10_vi_re, input wire [23:0] l10_vi_addr, output wire [31:0] l10_vi_q,
 input wire l10_kv_we, input wire [23:0] l10_kv_waddr, input wire [31:0] l10_kv_wdata,
 input wire l11_vi_re, input wire [23:0] l11_vi_addr, output wire [31:0] l11_vi_q,
 input wire l11_kv_we, input wire [23:0] l11_kv_waddr, input wire [31:0] l11_kv_wdata,
 input wire l12_vi_re, input wire [23:0] l12_vi_addr, output wire [31:0] l12_vi_q,
 input wire l12_kv_we, input wire [23:0] l12_kv_waddr, input wire [31:0] l12_kv_wdata,
 input wire l13_vi_re, input wire [23:0] l13_vi_addr, output wire [31:0] l13_vi_q,
 input wire l13_kv_we, input wire [23:0] l13_kv_waddr, input wire [31:0] l13_kv_wdata,
 input wire l14_vi_re, input wire [23:0] l14_vi_addr, output wire [31:0] l14_vi_q,
 input wire l14_kv_we, input wire [23:0] l14_kv_waddr, input wire [31:0] l14_kv_wdata,
 input wire l15_vi_re, input wire [23:0] l15_vi_addr, output wire [31:0] l15_vi_q,
 input wire l15_kv_we, input wire [23:0] l15_kv_waddr, input wire [31:0] l15_kv_wdata,
 output reg fault
);

endmodule

(* blackbox *)
module ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(
    parameter integer OREG=1,
    parameter integer KREG=1,
    parameter integer KRREG=1,
    parameter integer RREG=1,
    
    
    
    
    
    parameter integer WPAY=1,
    
    
    
    
    
    
    
    
    parameter integer QREG=1,
    parameter integer RMUT=0
)(
    input wire clk,rst_n,
    input wire [4:0]pc_id,
    input wire [7:0]refresh_reload,
    input wire k_v,output wire k_rdy,input wire k_we,
    input wire[29:0]k_addr,input wire[3:0]k_len,input wire[16:0]k_tag,
    input wire[255:0]k_wdata,input wire[31:0]k_wstrb,
    output wire kr_v,input wire kr_rdy,
    output wire[16:0]kr_tag,output wire[3:0]kr_beat,output wire[255:0]kr_data,
    output reg k_wr_done,
    output wire row_v,output wire[2:0]row_op,output wire[4:0]row_bank,output wire[18:0]row_row,
    output wire col_v,col_we,output wire[4:0]col_bank,col_col,
    output wire[255:0]col_data,output wire[31:0]col_strb,
    input wire dram_rvalid,input wire[255:0]dram_rdata,
    output reg pc_fault,
    output reg [5:0] owner_fault_split   
);

endmodule

(* blackbox *)
module ot_hbm_svc_sm_group_rel_id_rc #(parameter integer LBANKS=4,parameter integer LB=(LBANKS>2)?2:1,
 parameter integer NID=6,parameter integer IDW=9,parameter integer PAW=11,parameter integer PREL=1,parameter integer DD=256,parameter integer IMUT=0,
 parameter integer DAW=(DD>128)?8:7,parameter integer ID_COHORT=0,
 parameter integer XSLOT=0,parameter integer CTXW=(XSLOT!=0)?53:46,
 parameter integer OPEN_IL=0,
 parameter integer ATT_MARK=0,
 parameter integer RQD=2,parameter integer RQMUT=0)(
 input wire[1:0]id_stack,input wire[2:0]id_sm,
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire[1:0]stream_bank_clk,hbm_fifo_clk,input wire[3:0]hbm_pc_clk,
 input wire program_cfg_we,input wire[PAW-1:0]program_cfg_addr,input wire[255:0]program_cfg_data,
 input wire desc_we,input wire[DAW-1:0]desc_addr,input wire[255:0]desc_data,
 input wire run_v,input wire[DAW-1:0]run_base,input wire[DAW:0]run_count,input wire[7:0]run_layer,
 input wire ids_v,input wire[7:0]ids_layer,input wire[IDW*NID-1:0]ids,
 input wire[15:0]ids_cohort,
 output wire running,run_done,program_active,fault,
 output wire[1098:0]sm_packet,output wire[82:0]sm_command,
 input wire[42:0]sm_request,
 output wire[3:0]k_v,input wire[3:0]k_rdy,output wire[119:0]k_addr,
 output wire[15:0]k_len,output wire[67:0]k_tag,output wire[3:0]k_we,
 output wire[1023:0]k_wdata,output wire[127:0]k_wstrb,input wire[3:0]k_wr_done,
 input wire[3:0]kr_v,output wire[3:0]kr_rdy,input wire[67:0]kr_tag,input wire[15:0]kr_beat,input wire[1023:0]kr_data
);

endmodule

(* blackbox *)
module ot_hbm_svc_vm_kshare_splitstrap #(parameter integer MUT=0,KRL1=0) (
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
 
 
 input wire[2:0]sm_stream,sm_hbm,
 
 input wire[3:0]g_k_v,output wire[3:0]g_k_rdy,input wire[119:0]g_k_addr,input wire[15:0]g_k_len,input wire[67:0]g_k_tag,
 input wire[3:0]g_k_we,input wire[1023:0]g_k_wdata,input wire[127:0]g_k_wstrb,output reg[3:0]g_k_wr_done,
 output wire[3:0]g_kr_v,input wire[3:0]g_kr_rdy,output wire[67:0]g_kr_tag,output wire[15:0]g_kr_beat,output wire[1023:0]g_kr_data,
 
 output wire[3:0]c_k_v,input wire[3:0]c_k_rdy,output wire[119:0]c_k_addr,output wire[15:0]c_k_len,output wire[67:0]c_k_tag,
 output wire[3:0]c_k_we,output wire[1023:0]c_k_wdata,output wire[127:0]c_k_wstrb,input wire[3:0]c_k_wr_done,
 input wire[3:0]c_kr_v,output wire[3:0]c_kr_rdy,input wire[67:0]c_kr_tag,input wire[15:0]c_kr_beat,input wire[1023:0]c_kr_data,
 
 input wire vm_v,vm_bank,input wire[15:0]vm_epoch,input wire[14:0]vm_row,input wire[3:0]vm_col,
 
 input wire wbw_v,input wire[29:0]wbw_base,input wire[11:0]wbw_total,
 
 input wire[3:0]w_k_v,output wire[3:0]w_k_rdy,input wire[119:0]w_k_addr,input wire[1023:0]w_k_wdata,output reg[3:0]w_k_wr_done,
 
 output reg[3:0]fill_v,output reg[3:0]fill_bank,output reg[23:0]fill_slot,output reg[63:0]fill_epoch,output reg[1023:0]fill_data,
 output reg fault
);
 localparam integer KW=1+30+4+17+32+256;   
 localparam integer RW=17+4+256;            
 localparam integer FW=1+16+6+256;          
 localparam integer CMW=1+16+15+4;          
 localparam integer WQW=30+12+32;          
 localparam[2:0]NORM=0,PEND=1,ISSUE=2,WAIT=3,WPEND=4,WB=5;
endmodule

(* blackbox *)
module ot_hbm_svc_vmdel_lane_n #(parameter integer NPC = 4) (
 input wire clk,rst_n,input wire [2:0] bank_id,
 input wire begin_v_i,begin_bank_i,input wire [15:0] begin_epoch_i,
 input wire start_i,start_bank_i,input wire [15:0] start_epoch_i,start_base_sector_i,
 input wire [NPC-1:0] fill_v_i,fill_bank_i,input wire [6*NPC-1:0] fill_slot_i,input wire [16*NPC-1:0] fill_epoch_i,input wire [256*NPC-1:0] fill_data_i,
 input wire [7:0] full0_all,full1_all,pcbad_all,
 output reg full0,full1,pcbad,
 output reg [1:0] block_ready,output reg busy,output reg fault,
 output reg [280:0] dq
);

endmodule

(* blackbox *)
module ot_hbm_svc_wb_kport_q #(parameter integer WOPEN=0, parameter integer MUT=0,
                               parameter [29:0] STACK_SECTORS=30'd703125000)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire[3:0]stream_fifo_clk,                 
 input wire[1:0]stk,                             
 input wire quad,                                
 
 input wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
 input wire[15:0]wb_reserve_epoch,wb_fill_epoch,
 input wire[11:0]wb_reserve_sectors,input wire[31:0]wb_reserve_base,
 input wire wb_fill_start,
 input wire[2311:0]wd,
 output reg wb_ready,output reg[11:0]wa,
 
 output reg wbw_v,output reg[29:0]wbw_base,output reg[11:0]wbw_total,
 
 output wire[15:0]w_k_v,input wire[15:0]w_k_rdy,output wire[479:0]w_k_addr,output wire[4095:0]w_k_wdata,
 input wire[15:0]w_k_wr_done,
 output reg fault
);

endmodule

(* blackbox *)
module ot_hbm_xp_aq_tree13_fmt #(parameter integer FP4=0, parameter integer MUT=0,
    parameter integer RSMUT=0) (   
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [1023:0] x,
    output wire          vo,
    output wire [255:0]  q,
    output wire signed [9:0] e,
    output wire [511:0]  y,
    output wire          fault
);

endmodule

(* blackbox *)
module ot_hfd_coll_q2_hard_v8g__reduce__nw_actual (
    input wire [0:0] clk,
    input wire [0:0] rst_n,
    input wire [0:0] u_reduce_add_issue,
    input wire [0:0] u_reduce_add_read,
    input wire [0:0] u_reduce_clear,
    output wire [0:0] u_reduce_fault,
    input wire [544:0] u_reduce_in_flit,
    input wire [0:0] u_reduce_in_v,
    input wire [3:0] u_reduce_load_tag,
    input wire [0:0] u_reduce_load_v,
    output wire [544:0] u_reduce_out_flit,
    output wire [0:0] u_reduce_out_v,
    input wire [0:0] u_reduce_pub_bf16,
    input wire [0:0] u_reduce_pub_issue,
    input wire [23:0] u_reduce_pub_meta,
    input wire [0:0] u_reduce_pub_read,
    input wire [0:0] u_reduce_pub_release,
    input wire [3:0] u_reduce_pub_tag_a,
    input wire [3:0] u_reduce_pub_tag_b,
    input wire [3:0] u_reduce_read_tag
);

endmodule

(* blackbox *)
module ot_hfd_coll_q2_hard_v8g__ring_ag (
    output wire [511:0] ag_d,
    output wire [3:0] ag_src,
    output wire [5:0] ag_tag,
    output wire [1:0] ag_v,
    input wire [0:0] clk,
    input wire [279:0] pr_ccw_i,
    output wire [279:0] pr_ccw_o,
    input wire [279:0] pr_cw_i,
    output wire [279:0] pr_cw_o,
    input wire [0:0] ra_add_rhs_acc,
    input wire [1:0] ra_add_src,
    input wire [2:0] ra_add_tag,
    input wire [0:0] ra_add_v,
    input wire [255:0] ra_lp_data,
    input wire [2:0] ra_lp_tag,
    input wire [0:0] ra_lp_we,
    input wire [0:0] ra_rr_local,
    input wire [2:0] ra_rr_local_tag,
    input wire [3:0] ra_rx_kind,
    input wire [1:0] ra_rx_slot,
    input wire [3:0] ra_rx_src,
    input wire [5:0] ra_rx_tag,
    input wire [0:0] ra_state_add_rhs_acc,
    input wire [1:0] ra_state_add_src,
    input wire [2:0] ra_state_add_tag,
    input wire [0:0] ra_state_read_add,
    input wire [0:0] ra_state_read_rr,
    input wire [0:0] ra_state_read_tx,
    input wire [2:0] ra_state_rr_tag,
    input wire [0:0] ra_state_tx_acc,
    input wire [2:0] ra_state_tx_tag,
    input wire [0:0] ra_tx_acc,
    input wire [1:0] ra_tx_dst,
    input wire [1:0] ra_tx_forward,
    input wire [0:0] ra_tx_gather,
    input wire [1:0] ra_tx_inject,
    input wire [0:0] ra_tx_result,
    input wire [2:0] ra_tx_tag,
    input wire [3:0] ra_tx_ttl,
    output wire [255:0] rr_d,
    output wire [2:0] rr_tag,
    output wire [0:0] rr_v,
    input wire [0:0] rst_n,
    output wire [0:0] u_ring_fault,
    input wire [1:0] strap_qid
);

endmodule

(* blackbox *)
module ot_hfd_coll_q3_body_core (
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire [7:0] cfg_target,
    input wire [0:0] cfg_v,
    input wire [0:0] clk,
    output wire [2179:0] del_flit,
    output wire [3:0] del_valid,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire [0:0] desc_v,
    output wire [0:0] done,
    output wire [0:0] fault,
    output wire [15:0] fault_cause,
    output wire [0:0] hgi_busy,
    output wire [159:0] hgi_del_obase,
    output wire [159:0] hgi_inj_addr,
    input wire [1023:0] inj_d,
    output wire [31:0] inj_idx,
    output wire [1:0] inj_rd,
    output wire [57:0] isa_ring,
    input wire [0:0] launch_v,
    output wire [0:0] program_configured,
    output wire [0:0] program_fault,
    output wire [0:0] program_init_busy,
    input wire [2:0] rc_tag,
    input wire [0:0] rc_v,
    input wire [0:0] rst_n,
    output wire [31:0] stat_cycles,
    output wire [0:0] tkx_arg_mode,
    input wire [0:0] tkx_busy,
    output wire [7:0] tkx_cfg_g,
    output wire [7:0] tkx_cfg_gbase,
    output wire [0:0] tkx_cfg_has_r,
    output wire [12:0] tkx_cfg_k,
    output wire [11:0] tkx_cfg_n,
    output wire [12:0] tkx_cfg_nout,
    output wire [39:0] tkx_cfg_obase,
    output wire [15:0] tkx_cfg_pf,
    output wire [39:0] tkx_cfg_rbase,
    output wire [2179:0] tkx_del_flit,
    output wire [3:0] tkx_del_slot,
    output wire [3:0] tkx_del_valid,
    input wire [0:0] tkx_done,
    input wire [0:0] tkx_fault,
    output wire [0:0] tkx_start,
    output wire [23:0] u_body_g_q3_genblk1_n_u_control_r_u_control_held_epoch,
    output wire [47:0] u_body_g_q3_genblk1_n_u_control_r_u_control_rd_sequence_pin,
    output wire [159:0] u_body_g_q3_genblk1_n_u_control_r_u_control_rgx_addr_pin,
    output wire [47:0] u_body_g_q3_genblk1_n_u_control_r_u_control_rx_sequence_pin,
    output wire [23:0] u_body_g_q3_genblk1_n_u_control_r_u_control_vm_sel_d,
    output wire [47:0] u_body_g_q3_genblk1_n_u_control_r_u_control_wr_sequence_pin,
    input wire [0:0] u_body_g_q3_n_u_fj_u_fj_arg_fault,
    input wire [2:0] u_body_g_q3_n_u_fj_u_fj_link_abort,
    input wire [0:0] u_body_g_q3_n_u_fj_u_fj_reduce_fault,
    input wire [0:0] u_body_g_q3_n_u_fj_u_fj_ring_fault,
    input wire [0:0] u_body_g_q3_n_u_fj_u_fj_writer_fault,
    input wire [544:0] u_body_g_qcap_10_u_cap_src_d,
    input wire [0:0] u_body_g_qcap_10_u_cap_src_v,
    input wire [544:0] u_body_g_qcap_2_u_cap_src_d,
    input wire [0:0] u_body_g_qcap_2_u_cap_src_v,
    input wire [544:0] u_body_g_qcap_3_u_cap_src_d,
    input wire [0:0] u_body_g_qcap_3_u_cap_src_v,
    input wire [544:0] u_body_g_qcap_4_u_cap_src_d,
    input wire [0:0] u_body_g_qcap_4_u_cap_src_v,
    input wire [511:0] u_body_g_qcap_5_u_cap_src_d,
    input wire [511:0] u_body_g_qcap_6_u_cap_src_d,
    input wire [511:0] u_body_g_qcap_7_u_cap_src_d,
    input wire [511:0] u_body_g_qcap_8_u_cap_src_d,
    input wire [544:0] u_body_g_qcap_9_u_cap_src_d,
    input wire [0:0] u_body_g_qcap_9_u_cap_src_v,
    output wire [95:0] u_body_g_qout_0_g3_w_o_u_out_dst_d__b0,
    output wire [351:224] u_body_g_qout_0_g3_w_o_u_out_dst_d__b224,
    output wire [511:480] u_body_g_qout_0_g3_w_o_u_out_dst_d__b480,
    output wire [2:0] u_body_g_qout_0_g3_w_o_u_out_dst_v__b0,
    output wire [10:7] u_body_g_qout_0_g3_w_o_u_out_dst_v__b7,
    output wire [15:15] u_body_g_qout_0_g3_w_o_u_out_dst_v__b15,
    output wire [95:0] u_body_g_qout_10_g3_w_o_u_out_dst_d__b0,
    output wire [351:224] u_body_g_qout_10_g3_w_o_u_out_dst_d__b224,
    output wire [511:480] u_body_g_qout_10_g3_w_o_u_out_dst_d__b480,
    output wire [95:0] u_body_g_qout_11_g3_w_o_u_out_dst_d__b0,
    output wire [351:224] u_body_g_qout_11_g3_w_o_u_out_dst_d__b224,
    output wire [511:480] u_body_g_qout_11_g3_w_o_u_out_dst_d__b480,
    output wire [95:0] u_body_g_qout_12_g3_w_o_u_out_dst_d__b0,
    output wire [351:224] u_body_g_qout_12_g3_w_o_u_out_dst_d__b224,
    output wire [511:480] u_body_g_qout_12_g3_w_o_u_out_dst_d__b480,
    output wire [95:0] u_body_g_qout_13_g3_w_o_u_out_dst_d__b0,
    output wire [351:224] u_body_g_qout_13_g3_w_o_u_out_dst_d__b224,
    output wire [511:480] u_body_g_qout_13_g3_w_o_u_out_dst_d__b480,
    output wire [95:0] u_body_g_qout_14_g3_w_o_u_out_dst_d__b0,
    output wire [351:224] u_body_g_qout_14_g3_w_o_u_out_dst_d__b224,
    output wire [511:480] u_body_g_qout_14_g3_w_o_u_out_dst_d__b480,
    output wire [95:0] u_body_g_qout_15_g3_w_o_u_out_dst_d__b0,
    output wire [351:224] u_body_g_qout_15_g3_w_o_u_out_dst_d__b224,
    output wire [511:480] u_body_g_qout_15_g3_w_o_u_out_dst_d__b480,
    output wire [95:0] u_body_g_qout_16_g3_w_o_u_out_dst_d__b0,
    output wire [511:480] u_body_g_qout_16_g3_w_o_u_out_dst_d__b480,
    output wire [2:0] u_body_g_qout_17_g3_n_o_u_out_dst_d__b0,
    output wire [15:15] u_body_g_qout_17_g3_n_o_u_out_dst_d__b15,
    output wire [95:0] u_body_g_qout_1_g3_w_o_u_out_dst_d__b0,
    output wire [351:224] u_body_g_qout_1_g3_w_o_u_out_dst_d__b224,
    output wire [511:480] u_body_g_qout_1_g3_w_o_u_out_dst_d__b480,
    output wire [95:0] u_body_g_qout_2_g3_w_o_u_out_dst_d__b0,
    output wire [351:224] u_body_g_qout_2_g3_w_o_u_out_dst_d__b224,
    output wire [511:480] u_body_g_qout_2_g3_w_o_u_out_dst_d__b480,
    output wire [95:0] u_body_g_qout_3_g3_w_o_u_out_dst_d__b0,
    output wire [351:224] u_body_g_qout_3_g3_w_o_u_out_dst_d__b224,
    output wire [511:480] u_body_g_qout_3_g3_w_o_u_out_dst_d__b480,
    output wire [95:0] u_body_g_qout_4_g3_w_o_u_out_dst_d__b0,
    output wire [351:224] u_body_g_qout_4_g3_w_o_u_out_dst_d__b224,
    output wire [511:480] u_body_g_qout_4_g3_w_o_u_out_dst_d__b480,
    output wire [95:0] u_body_g_qout_5_g3_w_o_u_out_dst_d__b0,
    output wire [351:224] u_body_g_qout_5_g3_w_o_u_out_dst_d__b224,
    output wire [511:480] u_body_g_qout_5_g3_w_o_u_out_dst_d__b480,
    output wire [95:0] u_body_g_qout_6_g3_w_o_u_out_dst_d__b0,
    output wire [351:224] u_body_g_qout_6_g3_w_o_u_out_dst_d__b224,
    output wire [511:480] u_body_g_qout_6_g3_w_o_u_out_dst_d__b480,
    output wire [95:0] u_body_g_qout_7_g3_w_o_u_out_dst_d__b0,
    output wire [351:224] u_body_g_qout_7_g3_w_o_u_out_dst_d__b224,
    output wire [511:480] u_body_g_qout_7_g3_w_o_u_out_dst_d__b480,
    output wire [95:0] u_body_g_qout_8_g3_w_o_u_out_dst_d__b0,
    output wire [351:224] u_body_g_qout_8_g3_w_o_u_out_dst_d__b224,
    output wire [511:480] u_body_g_qout_8_g3_w_o_u_out_dst_d__b480,
    output wire [95:0] u_body_g_qout_9_g3_w_o_u_out_dst_d__b0,
    output wire [351:224] u_body_g_qout_9_g3_w_o_u_out_dst_d__b224,
    output wire [511:480] u_body_g_qout_9_g3_w_o_u_out_dst_d__b480,
    output wire [3:0] u_body_procdff_804_Q,
    output wire [3:0] u_body_procdff_805_Q,
    output wire [3:0] u_body_procdff_806_Q,
    output wire [3:0] u_body_procdff_807_Q,
    output wire [15:0] u_body_procdff_808_Q,
    output wire [352:350] u_body_u_upipe_d3__b350,
    output wire [373:371] u_body_u_upipe_d3__b371,
    output wire [394:392] u_body_u_upipe_d3__b392,
    output wire [423:413] u_body_u_upipe_d3__b413,
    output wire [629:584] u_body_u_upipe_d3__b584,
    output wire [711:705] u_body_u_upipe_d3__b705,
    output wire [713:713] u_body_u_upipe_d3__b713,
    output wire [1505:1505] u_body_u_upipe_d3__b1505,
    output wire [1510:1510] u_body_u_upipe_d3__b1510,
    output wire [1516:1515] u_body_u_upipe_d3__b1515,
    output wire [1535:1525] u_body_u_upipe_d3__b1525,
    output wire [135:0] vm_rq,
    input wire [256:256] vm_rr__b256,
    input wire [513:513] vm_rr__b513,
    input wire [770:770] vm_rr__b770,
    input wire [1027:1027] vm_rr__b1027,
    input wire [1284:1284] vm_rr__b1284,
    input wire [1541:1541] vm_rr__b1541,
    input wire [1798:1798] vm_rr__b1798,
    input wire [2055:2055] vm_rr__b2055
);

endmodule

(* blackbox *)
module ot_hfd_coll_q3_edge_core (
    input wire [7:0] arg_cfg_rank,
    output wire [0:0] arg_fault,
    input wire [0:0] arg_flush_slot,
    input wire [3:0] arg_in_slot,
    output wire [544:0] arg_out_flit,
    output wire [0:0] arg_out_v,
    input wire [0:0] arg_publish_slot,
    input wire [0:0] arg_rst_n,
    input wire [0:0] arg_start,
    input wire [0:0] clk,
    output wire [0:0] link0_epoch_abort,
    input wire [0:0] link0_epoch_begin,
    input wire [7:0] link0_epoch_new,
    input wire [7:0] link0_held_epoch,
    input wire [15:0] link0_rd_seq,
    input wire [0:0] link0_rd_v,
    input wire [15:0] link0_rx_expect_seq,
    input wire [0:0] link0_rx_expect_v,
    output wire [544:0] link0_rx_flit,
    output wire [0:0] link0_rx_v,
    input wire [544:0] link0_wr_flit,
    input wire [0:0] link0_wr_observed_v,
    input wire [15:0] link0_wr_seq,
    input wire [0:0] link0_wr_v,
    output wire [0:0] link1_epoch_abort,
    input wire [0:0] link1_epoch_begin,
    input wire [7:0] link1_held_epoch,
    input wire [15:0] link1_rd_seq,
    input wire [0:0] link1_rd_v,
    input wire [15:0] link1_rx_expect_seq,
    input wire [0:0] link1_rx_expect_v,
    output wire [544:0] link1_rx_flit,
    output wire [0:0] link1_rx_v,
    input wire [544:0] link1_wr_flit,
    input wire [0:0] link1_wr_observed_v,
    input wire [15:0] link1_wr_seq,
    input wire [0:0] link1_wr_v,
    output wire [0:0] link2_epoch_abort,
    input wire [0:0] link2_epoch_begin,
    input wire [7:0] link2_held_epoch,
    input wire [15:0] link2_rd_seq,
    input wire [0:0] link2_rd_v,
    input wire [15:0] link2_rx_expect_seq,
    input wire [0:0] link2_rx_expect_v,
    output wire [544:0] link2_rx_flit,
    output wire [0:0] link2_rx_v,
    input wire [544:0] link2_wr_flit,
    input wire [0:0] link2_wr_observed_v,
    input wire [15:0] link2_wr_seq,
    input wire [0:0] link2_wr_v,
    input wire [2:0] phy_up,
    output wire [2:0] retry_requested,
    input wire [1835:0] rx_pin_flit,
    input wire [2:0] rx_pin_v,
    input wire [0:0] tkx_arg_mode,
    input wire [7:0] tkx_cfg_g,
    input wire [7:0] tkx_cfg_gbase,
    input wire [63:0] tkx_del_flit__b0,
    input wire [608:512] tkx_del_flit__b512,
    input wire [1153:1057] tkx_del_flit__b1057,
    input wire [1698:1602] tkx_del_flit__b1602,
    input wire [2179:2147] tkx_del_flit__b2147,
    input wire [3:0] tkx_del_valid,
    output wire [1835:0] tx_pin_flit,
    output wire [2:0] tx_pin_v
);

endmodule

(* blackbox *)
module ot_hfd_coll_q3_vm_core (
    input wire [0:0] clk,
    input wire [39:0] tkx_w_addr,
    input wire [511:0] tkx_w_data,
    input wire [15:0] tkx_w_mask,
    input wire [0:0] tkx_w_v,
    output wire [2247:0] vm_kq,
    input wire [255:0] vm_rr__b0,
    input wire [512:257] vm_rr__b257,
    input wire [769:514] vm_rr__b514,
    input wire [1026:771] vm_rr__b771,
    input wire [1283:1028] vm_rr__b1028,
    input wire [1540:1285] vm_rr__b1285,
    input wire [1797:1542] vm_rr__b1542,
    input wire [2054:1799] vm_rr__b1799,
    output wire [2047:0] vmasm_as_il,
    input wire [23:0] vmasm_sel,
    output wire [0:0] writer_fault,
    input wire [4:0] writer_ingress_slot,
    input wire [159:0] writer_rgx_addr,
    input wire [511:0] writer_rgx_data0,
    input wire [511:0] writer_rgx_data1,
    input wire [511:0] writer_rgx_data2,
    input wire [511:0] writer_rgx_data3,
    input wire [3:0] writer_rgx_v,
    input wire [0:0] writer_rgx_vm,
    input wire [0:0] writer_rst_n,
    input wire [31:0] writer_slot_owner,
    input wire [7:0] writer_slot_valid
);

endmodule

(* blackbox *)
module ot_hgi_coll_gq_issue #(
    parameter integer MUT = 0,      
                                    
    parameter integer VM_RT = 0
)(
    input  wire          clk, rst_n,
    input  wire [1:0]    qid,
    input  wire [7:0]    tgt,
    
    input  wire          cfg_v,
    input  wire [7:0]    cfg_target,
    input  wire [11:0]   cfg_addr,
    input  wire [255:0]  cfg_data,
    input  wire          desc_v,
    input  wire [11:0]   desc_base,
    input  wire [12:0]   desc_limit,
    input  wire [15:0]   desc_loops,
    input  wire          launch_v,
    output wire          configured, tgt_fault,
    output reg           active, done,
    output reg           fault,
    
    input  wire [57:0]   isa_ring,
    input  wire [255:0]  isa_lp_data,
    
    output reg           ra_lp_we,
    output reg  [2:0]    ra_lp_tag,
    output reg  [255:0]  ra_lp_data,
    output reg           ra_state_read_add, ra_state_read_tx, ra_state_read_rr,
    output reg  [2:0]    ra_state_add_tag, ra_state_tx_tag, ra_state_rr_tag,
    output reg  [1:0]    ra_state_add_src,
    output reg           ra_state_add_rhs_acc, ra_state_tx_acc,
    output reg           ra_add_v,
    output reg  [2:0]    ra_add_tag,
    output reg  [1:0]    ra_add_src,
    output reg           ra_add_rhs_acc,
    output reg  [1:0]    ra_tx_inject, ra_tx_forward,
    output reg  [2:0]    ra_tx_tag,
    output reg  [1:0]    ra_tx_dst,
    output reg           ra_tx_result, ra_tx_acc, ra_tx_gather,
    output reg  [3:0]    ra_tx_ttl,
    output reg  [1:0]    ra_rx_slot,
    output reg  [3:0]    ra_rx_kind, ra_rx_src,
    output reg  [5:0]    ra_rx_tag,
    output reg           ra_rr_local,
    output reg  [2:0]    ra_rr_local_tag,
    
    output reg           rb_lp_we,
    output reg  [2:0]    rb_lp_tag,
    output reg  [255:0]  rb_lp_data,
    output reg           rb_state_read_tx,
    output reg  [2:0]    rb_state_tx_tag,
    output reg  [1:0]    rb_tx_inject, rb_tx_forward,
    output reg  [2:0]    rb_tx_tag,
    output reg  [3:0]    rb_tx_ttl,
    output reg  [1:0]    rb_rx_slot,
    output reg  [3:0]    rb_rx_kind, rb_rx_src,
    output reg  [5:0]    rb_rx_tag,
    
    output wire [67:0]   vm_rq_lo, vm_rq_hi,
    input  wire [1027:0] vm_rr_lo, vm_rr_hi,
    
    output reg           ld_fire,
    output reg  [52:0]   ld_desc,      
    output wire          ld_ev_v,
    output wire [9:0]    ld_ev_k,
    output wire [1:0]    ld_p_v,
    output wire [511:0]  ld_p_d
);
    localparam integer V = VM_RT;
    localparam integer ND = 40 + V;                  
    localparam integer S_QR = 0, S_PR = 15, S_QCAP = 8 + V, S_PCAP = 23 + V, S_P = 24 + V;
    localparam integer S_BLP = 24 + V, S_BRD = 25 + V, S_BINJ = 27 + V, S_BRX = 27 + V;   
endmodule

(* blackbox *)
module ot_hgi_coll_gq_land #(parameter integer MUT = 0)(
    input  wire          clk, rst_n,
    input  wire [1:0]    qid,
    input  wire          ld_fire,
    input  wire [52:0]   ld_desc,
    input  wire          ld_ev_v,
    input  wire [9:0]    ld_ev_k,
    input  wire [1:0]    ld_p_v,
    input  wire [511:0]  ld_p_d,
    input  wire [1:0]    pa_v, pb_v,
    input  wire [3:0]    pa_src, pb_src,
    input  wire [5:0]    pa_tag, pb_tag,
    input  wire [511:0]  pa_d, pb_d,
    output wire [1123:0] vm_kq_lo, vm_kq_hi,      
    output reg           fault
);
    localparam integer NL = 36;      
    localparam integer S_KQ = 31;    
endmodule

(* blackbox *)
module ot_hgi_coll_inj_idx_join_rg #(
 parameter integer INJLAT=12, MUT=0
)(
 input wire clk_r0, clk_r1, rst_n, rst_n_r1,
 input wire [1:0] inj_rd, inj_rd_r1,
 input wire [31:0] inj_idx, inj_idx_r1,
 input wire [159:0] inj_addr, inj_addr_r1,
 input wire [511:0] su_inj_d_r0, su_inj_d_r1,
 input wire [3:0] idx_tx_v, idx_tx_v_r1,
 input wire [131:0] idx_tx_h, idx_tx_h_r1,
 input wire [1023:0] idx_tx_r0, idx_tx_r1,
 output wire [511:0] inj_d_r0, inj_d_r1,
 output wire fault
);

endmodule

(* blackbox *)

module ot_hgi_dma_back_static_vp4_banks_cp #(
    parameter [35:0] STACK_BYTES=36'd22500000000,
    parameter integer MUT=0,     
    parameter integer CP_MUT=0,  
    parameter integer RST_MUT=0, 
    
    
    
    parameter integer RR_RT=7
)(
    input wire clk,rst_n,
    input wire clk_cp,              
    input wire clk_rst,             
    input wire [1:0] stk,
    input wire [7:0] tgt,
    input wire [7:0] clk_bank,
    
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    output wire cp_configured,cp_fault,cp_active,
    output wire mv_src,mv_done,mv_fault,
    output wire quiet,busy,
    output wire [8*17-1:0] rq,
    input wire [8*257-1:0] rr,
    output wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
    output wire [15:0] wb_reserve_epoch,wb_fill_epoch,
    output wire [11:0] wb_reserve_sectors,
    output wire [31:0] wb_reserve_base,
    output wire wb_fill_start,
    input wire wb_ready,
    output wire [8*289-1:0] wd,
    input wire [11:0] wa
);

endmodule

(* blackbox *)
module ot_hgi_qw_dec (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [127:0]  header,
    input  wire [1023:0] x,
    output reg           vo,
    output reg  [511:0]  y,
    output reg           fault,
    output reg           decode_fault
);

endmodule

(* blackbox *)
module ot_hgi_sfu_programme_store_r10 #(
 parameter integer PAGE_AW=1, AW=10+PAGE_AW
)(
 input wire clk,rst_n,
 input wire cfg_we,
 input wire [2:0] cfg_stripe,
 input wire [AW-1:0] cfg_addr,
 input wire [255:0] cfg_data,
 input wire [AW-1:0] start_base,
 input wire [AW:0] start_limit,
 input wire [15:0] start_loops,
 output reg programme_active,programme_done,
 output reg [31:0] programme_ordinal,
 input wire io_cfg_we,
 input wire [1:0] io_cfg_stripe,
 input wire [AW-1:0] io_cfg_addr,
 input wire [255:0] io_cfg_data,
 input wire io_start_v,
 input wire [AW-1:0] io_start_base,
 input wire [AW:0] io_start_limit,
 input wire [15:0] io_start_loops,
 output reg io_active,io_done,
 output reg [31:0] io_ordinal,
 output wire [470:0] io_word,
 output wire [1741:0] compiler_control,
 output reg fault
);

endmodule

(* blackbox *)
module ot_hgi_sm_xload_cl2_bdring #(
    parameter integer PMAX = 8,
    parameter integer NR   = 64
) (
    input  wire               clk,
    input  wire [15:0]        r_wsel,
    input  wire               zlo, zhi,
    input  wire [255:0]       qq_lo, qq_hi,
    input  wire signed [9:0]  qe_lo, qe_hi,
    input  wire [2*((PMAX*3152+2047)/2048)-1:0] bsel,  
    input  wire [PMAX*8-1:0]  lane_en_i,
    output wire [2047:0]      bq_d
);

endmodule

(* blackbox *)
module ot_hgi_sm_xload_cl2_bfqg (
    input wire clk, clk_n, clk_s, clk_ctrl,
    input wire clk_m0, clk_m1, clk_m2, clk_m3, clk_m4, clk_m5, clk_m6, clk_m7,
    input wire clk_l0, clk_l1, clk_l2, clk_l3, clk_l4, clk_l5, clk_l6, clk_l7,
    input wire rst_n,
    input wire [1023:0] c_d,
    input wire wce,
    input wire mhi0,mhi1,mhi2,mhi3,mhi4,mhi5,mhi6,mhi7,
    input wire mlo0,mlo1,mlo2,mlo3,mlo4,mlo5,mlo6,mlo7,
    input wire [6:0] wa,
    input wire [7:0] r_ce,
    input wire [6:0] r_a,
    output reg [255:0] rwq
);

endmodule

(* blackbox *)
module ot_hgi_sm_xload_cl2_ctlx #(
    parameter integer PMAX   = 8,
    parameter [63:0]  RD_LAT = 64'd6,    
    parameter integer MUT    = 0,
    parameter integer NR     = 32,
    parameter integer LEAD   = 8
) (
    input  wire               clk,
    input  wire               clk_cal,
    input  wire               rst_n,
    input  wire [7:0]         tgt,
    input  wire               cfg_v,
    input  wire [7:0]         cfg_target,
    input  wire [11:0]        cfg_addr,
    input  wire [255:0]       cfg_data,
    input  wire               desc_v,
    input  wire [11:0]        desc_base,
    input  wire [12:0]        desc_limit,
    input  wire [15:0]        desc_loops,
    input  wire               launch_v,
    output wire               configured,
    output wire               fault,
    output wire               active,
    output wire [8*17-1:0]    rq,
    input  wire [8*257-1:0]   rr,
    output wire               rn_o,
    output wire [1023:0]      c_d,
    output wire [3:0]         c_wce,
    output wire               c_mhi, c_mlo,
    output wire [6:0]         c_wa,
    output wire [7:0]         r_ce,
    output wire [6:0]         r_a,
    output wire [2047:0]      l_d_o,
    output wire               qv_lo, qv_hi,
    input  wire               qo_lo, qo_hi, qf_lo, qf_hi,
    output wire [15:0]        r_wsel,
    output wire               zlo, zhi,
    output wire [2*((PMAX*3152+2047)/2048)-1:0] bsel,
    output wire [PMAX*8-1:0]  lane_en,
    output wire [7:0]         eg_ed5,
    output wire [16:0]        eg_ede,
    output wire               eg_bqv, eg_bqlast,
    output wire [6:0]         eg_bqaddr, eg_bqb
);

endmodule

(* blackbox *)
module ot_hnx_fused_lane #(
    parameter integer D   = 5120,
    parameter integer KX  = 4,               
    parameter integer RR  = 10,              
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [4:0]    lid,
    output reg           rq_v,
    output reg  [15:0]   rq_s,
    input  wire          rr_v,
    input  wire [255:0]  rr_d,
    output reg           wq_v,
    output reg  [15:0]   wq_s,
    output reg  [255:0]  wq_d,
    input  wire          dn_v,
    input  wire [2:0]    dn_op,
    input  wire [7:0]    dn_x,
    input  wire [127:0]  dn_d,
    input  wire          r_v,
    input  wire [31:0]   r_d,
    output reg           up_v,
    output reg           up_t,
    output reg  [9:0]    up_x,
    output reg  [255:0]  up_d,
    output reg           fin,
    output reg           flt
);
    localparam integer SD = D / 8;           
    localparam integer NM = D / 256;         
    localparam integer KB = (KX > 1) ? $clog2(KX) : 1;
    localparam integer LM = 5, LA = 6, LMS = 6, ML = 7, AL = 6;
endmodule

(* blackbox *)

module ot_hnx_fused_tnode #(parameter integer LA = 6, parameter integer UW = 271, parameter integer DW = 173, parameter integer DELIVERED_RESET = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [5:0]    pad_k,      
    input  wire          pad_b,      
    input  wire [UW-1:0] ua,         
    input  wire [UW-1:0] ub,         
    output wire [UW-1:0] uo,         
    input  wire [DW-1:0] dn,         
    output wire [DW-1:0] da,         
    output wire [DW-1:0] db          
);

endmodule

(* blackbox *)
module ot_hnx_idxn_keybuf_slice(
 input wire clk,rst_n,clear,
 input wire [2:0] strap_lane_id,
 input wire live_v,input wire[7:0]live_index,input wire[1098:0]key_in,
 input wire pre_v,input wire[7:0]pre_index,
 input wire replay_v,input wire[7:0]replay_index,
 output wire[1098:0]key_out,output reg fault
);

endmodule
