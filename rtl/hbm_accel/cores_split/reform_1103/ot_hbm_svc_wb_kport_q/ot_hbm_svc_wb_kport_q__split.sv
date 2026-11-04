`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-62/KPORT 2026-11-03: wires-only composition of the re-formed quadrant write-back partner: same ports as
// ot_hbm_svc_wb_kport_q.  Every sub-core pin carries its kit face shell (+1 in, +1 out), so a seam is +2 edges; SEAM (bench
// only, production 0) models them.  Roots: u_root0..3 on stream_fifo_clk[r], hub: u_hub (flat, no generate scope, so the physical paths stay simple).
module ot_hbm_svc_wb_kport_q__split #(parameter integer WOPEN=0, parameter integer MUT=0, parameter integer RMUT=0,
                               parameter integer SEAM=0, parameter [29:0] STACK_SECTORS=30'd703125000)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire[3:0]stream_fifo_clk,
 input wire[1:0]stk,
 input wire quad,
 input wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
 input wire[15:0]wb_reserve_epoch,wb_fill_epoch,
 input wire[11:0]wb_reserve_sectors,input wire[31:0]wb_reserve_base,
 input wire wb_fill_start,
 input wire[2311:0]wd,
 output wire wb_ready,output wire[11:0]wa,
 output wire wbw_v,output wire[29:0]wbw_base,output wire[11:0]wbw_total,
 output wire[15:0]w_k_v,input wire[15:0]w_k_rdy,output wire[479:0]w_k_addr,output wire[4095:0]w_k_wdata,
 input wire[15:0]w_k_wr_done,
 output wire fault
);
 wire[263:0]wd_ctl;wire[2047:0]wd_data;wire[7:0]wd_v;
 genvar s;
 generate for(s=0;s<8;s=s+1)begin:g_wd
  assign wd_ctl[33*s+:33]=wd[289*s+256+:33];
  assign wd_data[256*s+:256]=wd[289*s+:256];
  assign wd_v[s]=wd[289*s+288];
 end endgenerate
 wire c_active,c_bank,c_fault;wire[29:0]c_base;wire[11:0]c_committed;wire[3:0]root_ready,root_ready_s;
 wire[15:0]port_v,port_v_s,port_credit,port_credit_s;wire[31:0]port_pc,port_pc_s;wire[479:0]port_addr,port_addr_s;wire[4095:0]port_data,port_data_s;
 wire c_active_s,c_bank_s,c_fault_s;wire[29:0]c_base_s;wire[11:0]c_committed_s;
 ot_hbm_svc_wb_kp_hub #(.WOPEN(WOPEN),.MUT(MUT),.STACK_SECTORS(STACK_SECTORS)) u_hub(.stream_clk(stream_clk),.stream_rst_n(stream_rst_n),
  .hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),.stk(stk),.quad(quad),
  .wb_reserve_v(wb_reserve_v),.wb_reserve_bank(wb_reserve_bank),.wb_fill_bank(wb_fill_bank),.wb_reserve_epoch(wb_reserve_epoch),
  .wb_fill_epoch(wb_fill_epoch),.wb_reserve_sectors(wb_reserve_sectors),.wb_reserve_base(wb_reserve_base),.wb_fill_start(wb_fill_start),
  .wd_ctl(wd_ctl),.wb_ready(wb_ready),.wa(wa),.wbw_v(wbw_v),.wbw_base(wbw_base),.wbw_total(wbw_total),
  .w_k_v(w_k_v),.w_k_rdy(w_k_rdy),.w_k_addr(w_k_addr),.w_k_wdata(w_k_wdata),.w_k_wr_done(w_k_wr_done),.fault(fault),
  .c_active(c_active),.c_bank(c_bank),.c_fault(c_fault),.c_base(c_base),.c_committed(c_committed),.root_ready(root_ready_s),
  .port_v(port_v_s),.port_pc(port_pc_s),.port_addr(port_addr_s),.port_data(port_data_s),.port_credit(port_credit));
 generate if(SEAM==0)begin:g_w
  assign {c_active_s,c_bank_s,c_fault_s,c_base_s,c_committed_s}={c_active,c_bank,c_fault,c_base,c_committed};
  assign root_ready_s=root_ready;assign port_v_s=port_v;assign port_pc_s=port_pc;assign port_addr_s=port_addr;assign port_data_s=port_data;
  assign port_credit_s=port_credit;
 end else begin:g_s
  reg[44:0]f1,f2;always @(posedge stream_clk)begin f1<={c_active,c_bank,c_fault,c_base,c_committed};f2<=f1;end
  assign {c_active_s,c_bank_s,c_fault_s,c_base_s,c_committed_s}=f2;
  reg[3:0]rr1,rr2;always @(posedge stream_clk)begin rr1<=root_ready;rr2<=rr1;end assign root_ready_s=rr2;
  reg[15:0]v1,v2,cr1,cr2;reg[31:0]pc1,pc2;reg[479:0]a1,a2;reg[4095:0]d1,d2;
  always @(posedge hbm_clk or negedge hbm_rst_n)if(!hbm_rst_n)begin v1<=0;v2<=0;cr1<=0;cr2<=0;end
   else begin v1<=port_v;v2<=v1;cr1<=port_credit;cr2<=cr1;end
  always @(posedge hbm_clk)begin pc1<=port_pc;pc2<=pc1;a1<=port_addr;a2<=a1;d1<=port_data;d2<=d1;end
  assign port_v_s=v2;assign port_pc_s=pc2;assign port_addr_s=a2;assign port_data_s=d2;assign port_credit_s=cr2;
 end endgenerate
 wire[3:0]v0;wire[7:0]pc0;wire[29:0]a0_0,a0_1,a0_2,a0_3;wire[255:0]d0_0,d0_1,d0_2,d0_3;
 ot_hbm_svc_wb_kp_root #(.MUT(RMUT)) u_root0(.stream_clk(stream_fifo_clk[0]),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
  .strap_bsel(2'd0),.wb_fill_start(wb_fill_start),.wb_fill_bank(wb_fill_bank),.wd_data(wd_data),.wd_v(wd_v),
  .c_active(c_active_s),.c_bank(c_bank_s),.c_fault(c_fault_s),.c_base(c_base_s),.c_committed(c_committed_s),.root_ready(root_ready[0]),
  .port_v(v0),.port_pc(pc0),.port_addr0(a0_0),.port_addr1(a0_1),.port_addr2(a0_2),.port_addr3(a0_3),
  .port_data0(d0_0),.port_data1(d0_1),.port_data2(d0_2),.port_data3(d0_3),.port_credit(port_credit_s[0+:4]));
 assign port_v[0+:4]=v0;assign port_pc[0+:8]=pc0;assign port_addr[0+:120]={a0_3,a0_2,a0_1,a0_0};assign port_data[0+:1024]={d0_3,d0_2,d0_1,d0_0};
 wire[3:0]v1;wire[7:0]pc1;wire[29:0]a1_0,a1_1,a1_2,a1_3;wire[255:0]d1_0,d1_1,d1_2,d1_3;
 ot_hbm_svc_wb_kp_root #(.MUT(RMUT)) u_root1(.stream_clk(stream_fifo_clk[1]),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
  .strap_bsel(2'd1),.wb_fill_start(wb_fill_start),.wb_fill_bank(wb_fill_bank),.wd_data(wd_data),.wd_v(wd_v),
  .c_active(c_active_s),.c_bank(c_bank_s),.c_fault(c_fault_s),.c_base(c_base_s),.c_committed(c_committed_s),.root_ready(root_ready[1]),
  .port_v(v1),.port_pc(pc1),.port_addr0(a1_0),.port_addr1(a1_1),.port_addr2(a1_2),.port_addr3(a1_3),
  .port_data0(d1_0),.port_data1(d1_1),.port_data2(d1_2),.port_data3(d1_3),.port_credit(port_credit_s[4+:4]));
 assign port_v[4+:4]=v1;assign port_pc[8+:8]=pc1;assign port_addr[120+:120]={a1_3,a1_2,a1_1,a1_0};assign port_data[1024+:1024]={d1_3,d1_2,d1_1,d1_0};
 wire[3:0]v2;wire[7:0]pc2;wire[29:0]a2_0,a2_1,a2_2,a2_3;wire[255:0]d2_0,d2_1,d2_2,d2_3;
 ot_hbm_svc_wb_kp_root #(.MUT(RMUT)) u_root2(.stream_clk(stream_fifo_clk[2]),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
  .strap_bsel(2'd2),.wb_fill_start(wb_fill_start),.wb_fill_bank(wb_fill_bank),.wd_data(wd_data),.wd_v(wd_v),
  .c_active(c_active_s),.c_bank(c_bank_s),.c_fault(c_fault_s),.c_base(c_base_s),.c_committed(c_committed_s),.root_ready(root_ready[2]),
  .port_v(v2),.port_pc(pc2),.port_addr0(a2_0),.port_addr1(a2_1),.port_addr2(a2_2),.port_addr3(a2_3),
  .port_data0(d2_0),.port_data1(d2_1),.port_data2(d2_2),.port_data3(d2_3),.port_credit(port_credit_s[8+:4]));
 assign port_v[8+:4]=v2;assign port_pc[16+:8]=pc2;assign port_addr[240+:120]={a2_3,a2_2,a2_1,a2_0};assign port_data[2048+:1024]={d2_3,d2_2,d2_1,d2_0};
 wire[3:0]v3;wire[7:0]pc3;wire[29:0]a3_0,a3_1,a3_2,a3_3;wire[255:0]d3_0,d3_1,d3_2,d3_3;
 ot_hbm_svc_wb_kp_root #(.MUT(RMUT)) u_root3(.stream_clk(stream_fifo_clk[3]),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
  .strap_bsel(2'd3),.wb_fill_start(wb_fill_start),.wb_fill_bank(wb_fill_bank),.wd_data(wd_data),.wd_v(wd_v),
  .c_active(c_active_s),.c_bank(c_bank_s),.c_fault(c_fault_s),.c_base(c_base_s),.c_committed(c_committed_s),.root_ready(root_ready[3]),
  .port_v(v3),.port_pc(pc3),.port_addr0(a3_0),.port_addr1(a3_1),.port_addr2(a3_2),.port_addr3(a3_3),
  .port_data0(d3_0),.port_data1(d3_1),.port_data2(d3_2),.port_data3(d3_3),.port_credit(port_credit_s[12+:4]));
 assign port_v[12+:4]=v3;assign port_pc[24+:8]=pc3;assign port_addr[360+:120]={a3_3,a3_2,a3_1,a3_0};assign port_data[3072+:1024]={d3_3,d3_2,d3_1,d3_0};
endmodule
`default_nettype wire
// Bench alias: the unchanged tb instantiates the plan name.
`ifdef KP_SPLIT_BENCH
module ot_hbm_svc_wb_kport_q #(parameter integer WOPEN=0, parameter integer MUT=0, parameter [29:0] STACK_SECTORS=30'd703125000)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,input wire[3:0]stream_fifo_clk,input wire[1:0]stk,input wire quad,
 input wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,input wire[15:0]wb_reserve_epoch,wb_fill_epoch,
 input wire[11:0]wb_reserve_sectors,input wire[31:0]wb_reserve_base,input wire wb_fill_start,input wire[2311:0]wd,
 output wire wb_ready,output wire[11:0]wa,output wire wbw_v,output wire[29:0]wbw_base,output wire[11:0]wbw_total,
 output wire[15:0]w_k_v,input wire[15:0]w_k_rdy,output wire[479:0]w_k_addr,output wire[4095:0]w_k_wdata,input wire[15:0]w_k_wr_done,
 output wire fault);
 ot_hbm_svc_wb_kport_q__split #(.WOPEN(WOPEN),.MUT(MUT>=10?0:MUT),.RMUT(MUT>=10?MUT-10:0),.SEAM(`KP_SPLIT_BENCH),.STACK_SECTORS(STACK_SECTORS)) u(.*);
endmodule
`endif
