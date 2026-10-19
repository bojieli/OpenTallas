`timescale 1ns/1ps
// L2H-BW (10-19): SAFE-face physical PC controller, successor of ot_hbm_svc_pc_ctrl_leaf_cfg_safe_legacy.
//
// Why (c1f1c2c0c native boundary audit of the legacy top): 281 of 1228 signal ports had a non-FF first/last contact:
// kr_data[255:0]/kr_tag[16:0]/kr_beat[3:0]/kr_v came from the legacy same-edge KR collar (3-entry ring read mux and
// count compare), kr_rdy drove that ring's pop/count logic, pc_fault was an OR, and k_v met 22 synchronous-reset ANDs.
//
// Structure (every port is a flop D or Q):
//  * KR leaves the PC on the native READY-LATENCY-1 ABI: kr_v / kr_tag / kr_beat / kr_data are the skid head flops,
//    kr_rdy is captured by 18 pure region flops (PURE_FACE=1), and a beat transfers at edge e when kr_v(e) and kr_rdy
//    sampled at e-1.  The consumer lands it in the existing 3-slot RL1 ring (ot_hbm_svc_kr_ready_bridge, REGIONAL_VALID
//    0) on ITS side of the crossing -- the same convention ot_hbm_svc_vm_kshare already uses for c_kr_rdy.  The ring's
//    831 payload flops move out of this tile into the consumer; the edge count end to end is unchanged (0 added cycles).
//  * K keeps its released RL1 ABI: k_v and all K fields are pure captures (k_v: 22 region D pins, PURE_FACE=1);
//    k_rdy is the registered k_rdy_q.
//  * pc_fault is registered here (+1 observation edge of a sticky fault; no data or schedule effect).
//  * Every store is a ceil(W/64) x ot_sram_1r1w_128x64_m1_p192 array (SRAM_P192=1): 5.2 contacts/um on each W/E face.
//  * Reset: two kept face landing stages (rst_l0/rst_l1), then the native relay, exactly as the legacy top.
module ot_hbm_svc_pc_ctrl_leaf_cfg_safe_face #(
    parameter integer MRKEY=1,
    parameter integer RQ=128,
    parameter integer QD=64,
    parameter integer OREG=1,
    parameter integer KREG=1,
    parameter integer KRREG=1,
    parameter integer RREG=1,
    parameter integer WPAY=1,
    parameter integer BW_MUT_ID_TAG=0,
    parameter integer RESET_LANDING=2,
    parameter integer SRAM_P192=1,
    parameter integer PURE_FACE=1
)(
    input wire clk,rst_n,
    input wire [4:0]pc_id,
    input wire [7:0]refresh_reload,
    input wire k_v,output wire k_rdy,input wire k_we,
    input wire[29:0]k_addr,input wire[3:0]k_len,input wire[16:0]k_tag,
    input wire[255:0]k_wdata,input wire[31:0]k_wstrb,
    output wire kr_v,input wire kr_rdy,
    output wire[16:0]kr_tag,output wire[3:0]kr_beat,output wire[255:0]kr_data,
    output wire k_wr_done,
    output wire row_v,output wire[2:0]row_op,output wire[4:0]row_bank,output wire[18:0]row_row,
    output wire col_v,col_we,output wire[4:0]col_bank,col_col,
    output wire[255:0]col_data,output wire[31:0]col_strb,
    input wire dram_rvalid,input wire[255:0]dram_rdata,
    output wire pc_fault,output wire[5:0]owner_fault_split
);
    initial if(KRREG==0||KREG==0||OREG==0)$fatal(1,"SAFE face requires KREG/KRREG/OREG=1 (registered ports)");
    wire core_rst_n;
    generate if(RESET_LANDING==2)begin:g_reset_face
      (* keep="true",dont_touch="true" *) reg rst_l0,rst_l1;
      always @(posedge clk)begin rst_l0<=rst_n;rst_l1<=rst_l0;end
      assign core_rst_n=rst_l1;
    end else begin:g_reset_diagnostic
      assign core_rst_n=rst_n;
    end endgenerate
    initial if(RESET_LANDING!=0&&RESET_LANDING!=2)$fatal(1,"RESET_LANDING must be0 or2");
    wire native_fault;
    ot_hbm_svc_pc_ctrl_leaf_cfg_safe #(.MRKEY(MRKEY),.RQ(RQ),.QD(QD),
      .OREG(OREG),.KREG(KREG),.KRREG(KRREG),.RREG(RREG),.WPAY(WPAY),
      .BW_MUT_ID_TAG(BW_MUT_ID_TAG),.SRAM_P192(SRAM_P192),.PURE_FACE(PURE_FACE)) u_native(
      .clk(clk),.rst_n(core_rst_n),.pc_id(pc_id),.refresh_reload(refresh_reload),
      .k_v(k_v),.k_rdy(k_rdy),.k_we(k_we),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),
      .k_wdata(k_wdata),.k_wstrb(k_wstrb),
      .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),
      .k_wr_done(k_wr_done),
      .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
      .col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),
      .dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),
      .pc_fault(native_fault),.owner_fault_split(owner_fault_split),.kr_v_regions());
    // registered sticky fault output (pure output flop)
    (* keep="true",dont_touch="true" *) reg pc_fault_q;
    always @(posedge clk)pc_fault_q<=native_fault;
    assign pc_fault=pc_fault_q;
endmodule
