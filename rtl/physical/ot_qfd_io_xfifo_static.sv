`timescale 1ns/1ps
// Real compiler-commanded IO CDC composition, including local sequencer and
// all-gather return. Every transfer executes at its reserved address/cycle.
// Credit/ready counters and buffer demand arbitration are absent. Every
// channel has independent writer/reader clock entries and fault-only checks.
// The compiled calendar must include write1wck/read3rck, 64-slot reuse,
// version synchronization, domainphase, and the actual PHY/relay latencies.
module qfd_io_xfifo_static (
input wire rst_n,
 input wire up_wck,up_rck,up_w_slot,up_w_version,up_i_valid,up_r_slot,up_r_version,
 input wire [5:0] up_w_addr,up_r_addr,
 input wire [545:0] up_i_data,
 output wire up_o_valid,up_w_fault,up_r_fault,
 output wire [545:0] up_o_data,
 input wire dp_wck,dp_rck,dp_w_slot,dp_w_version,dp_i_valid,dp_r_slot,dp_r_version,
 input wire [5:0] dp_w_addr,dp_r_addr,
 input wire [545:0] dp_i_data,
 output wire dp_o_valid,dp_w_fault,dp_r_fault,
 output wire [545:0] dp_o_data,
 input wire ur_wck,ur_rck,ur_w_slot,ur_w_version,ur_i_valid,ur_r_slot,ur_r_version,
 input wire [5:0] ur_w_addr,ur_r_addr,
 input wire [513:0] ur_i_data,
 output wire ur_o_valid,ur_w_fault,ur_r_fault,
 output wire [513:0] ur_o_data,
 input wire dr_wck,dr_rck,dr_w_slot,dr_w_version,dr_i_valid,dr_r_slot,dr_r_version,
 input wire [5:0] dr_w_addr,dr_r_addr,
 input wire [513:0] dr_i_data,
 output wire dr_o_valid,dr_w_fault,dr_r_fault,
 output wire [513:0] dr_o_data,
 input wire sx0_wck,sx0_rck,sx0_w_slot,sx0_w_version,sx0_i_valid,sx0_r_slot,sx0_r_version,
 input wire [5:0] sx0_w_addr,sx0_r_addr,
 input wire [545:0] sx0_i_data,
 output wire sx0_o_valid,sx0_w_fault,sx0_r_fault,
 output wire [545:0] sx0_o_data,
 input wire sx1_wck,sx1_rck,sx1_w_slot,sx1_w_version,sx1_i_valid,sx1_r_slot,sx1_r_version,
 input wire [5:0] sx1_w_addr,sx1_r_addr,
 input wire [545:0] sx1_i_data,
 output wire sx1_o_valid,sx1_w_fault,sx1_r_fault,
 output wire [545:0] sx1_o_data,
 input wire sx2_wck,sx2_rck,sx2_w_slot,sx2_w_version,sx2_i_valid,sx2_r_slot,sx2_r_version,
 input wire [5:0] sx2_w_addr,sx2_r_addr,
 input wire [545:0] sx2_i_data,
 output wire sx2_o_valid,sx2_w_fault,sx2_r_fault,
 output wire [545:0] sx2_o_data,
 input wire sr0_wck,sr0_rck,sr0_w_slot,sr0_w_version,sr0_i_valid,sr0_r_slot,sr0_r_version,
 input wire [5:0] sr0_w_addr,sr0_r_addr,
 input wire [545:0] sr0_i_data,
 output wire sr0_o_valid,sr0_w_fault,sr0_r_fault,
 output wire [545:0] sr0_o_data,
 input wire sr1_wck,sr1_rck,sr1_w_slot,sr1_w_version,sr1_i_valid,sr1_r_slot,sr1_r_version,
 input wire [5:0] sr1_w_addr,sr1_r_addr,
 input wire [545:0] sr1_i_data,
 output wire sr1_o_valid,sr1_w_fault,sr1_r_fault,
 output wire [545:0] sr1_o_data,
 input wire sr2_wck,sr2_rck,sr2_w_slot,sr2_w_version,sr2_i_valid,sr2_r_slot,sr2_r_version,
 input wire [5:0] sr2_w_addr,sr2_r_addr,
 input wire [545:0] sr2_i_data,
 output wire sr2_o_valid,sr2_w_fault,sr2_r_fault,
 output wire [545:0] sr2_o_data,
 input wire seq_wck,seq_rck,seq_w_slot,seq_w_version,seq_i_valid,seq_r_slot,seq_r_version,
 input wire [5:0] seq_w_addr,seq_r_addr,
 input wire [545:0] seq_i_data,
 output wire seq_o_valid,seq_w_fault,seq_r_fault,
 output wire [545:0] seq_o_data,
 input wire cq_wck,cq_rck,cq_w_slot,cq_w_version,cq_i_valid,cq_r_slot,cq_r_version,
 input wire [5:0] cq_w_addr,cq_r_addr,
 input wire [516:0] cq_i_data,
 output wire cq_o_valid,cq_w_fault,cq_r_fault,
 output wire [516:0] cq_o_data
);
 wire [545:0] up_full; assign up_o_data=up_full[545:0];
 qfd_static_ch546 u_up (
 .wck(up_wck),.rck(up_rck),.rst_n(rst_n),
 .w_slot(up_w_slot),.w_addr(up_w_addr),.w_version(up_w_version),.i_valid(up_i_valid),.i_data(up_i_data),
 .r_slot(up_r_slot),.r_addr(up_r_addr),.r_version(up_r_version),
 .o_valid(up_o_valid),.o_data(up_full),.w_fault(up_w_fault),.r_fault(up_r_fault));
 wire [545:0] dp_full; assign dp_o_data=dp_full[545:0];
 qfd_static_ch546 u_dp (
 .wck(dp_wck),.rck(dp_rck),.rst_n(rst_n),
 .w_slot(dp_w_slot),.w_addr(dp_w_addr),.w_version(dp_w_version),.i_valid(dp_i_valid),.i_data(dp_i_data),
 .r_slot(dp_r_slot),.r_addr(dp_r_addr),.r_version(dp_r_version),
 .o_valid(dp_o_valid),.o_data(dp_full),.w_fault(dp_w_fault),.r_fault(dp_r_fault));
 wire [545:0] ur_full; assign ur_o_data=ur_full[513:0];
 qfd_static_ch546 u_ur (
 .wck(ur_wck),.rck(ur_rck),.rst_n(rst_n),
 .w_slot(ur_w_slot),.w_addr(ur_w_addr),.w_version(ur_w_version),.i_valid(ur_i_valid),.i_data({32'b0,ur_i_data}),
 .r_slot(ur_r_slot),.r_addr(ur_r_addr),.r_version(ur_r_version),
 .o_valid(ur_o_valid),.o_data(ur_full),.w_fault(ur_w_fault),.r_fault(ur_r_fault));
 wire [545:0] dr_full; assign dr_o_data=dr_full[513:0];
 qfd_static_ch546 u_dr (
 .wck(dr_wck),.rck(dr_rck),.rst_n(rst_n),
 .w_slot(dr_w_slot),.w_addr(dr_w_addr),.w_version(dr_w_version),.i_valid(dr_i_valid),.i_data({32'b0,dr_i_data}),
 .r_slot(dr_r_slot),.r_addr(dr_r_addr),.r_version(dr_r_version),
 .o_valid(dr_o_valid),.o_data(dr_full),.w_fault(dr_w_fault),.r_fault(dr_r_fault));
 wire [545:0] sx0_full; assign sx0_o_data=sx0_full[545:0];
 qfd_static_ch546 u_sx0 (
 .wck(sx0_wck),.rck(sx0_rck),.rst_n(rst_n),
 .w_slot(sx0_w_slot),.w_addr(sx0_w_addr),.w_version(sx0_w_version),.i_valid(sx0_i_valid),.i_data(sx0_i_data),
 .r_slot(sx0_r_slot),.r_addr(sx0_r_addr),.r_version(sx0_r_version),
 .o_valid(sx0_o_valid),.o_data(sx0_full),.w_fault(sx0_w_fault),.r_fault(sx0_r_fault));
 wire [545:0] sx1_full; assign sx1_o_data=sx1_full[545:0];
 qfd_static_ch546 u_sx1 (
 .wck(sx1_wck),.rck(sx1_rck),.rst_n(rst_n),
 .w_slot(sx1_w_slot),.w_addr(sx1_w_addr),.w_version(sx1_w_version),.i_valid(sx1_i_valid),.i_data(sx1_i_data),
 .r_slot(sx1_r_slot),.r_addr(sx1_r_addr),.r_version(sx1_r_version),
 .o_valid(sx1_o_valid),.o_data(sx1_full),.w_fault(sx1_w_fault),.r_fault(sx1_r_fault));
 wire [545:0] sx2_full; assign sx2_o_data=sx2_full[545:0];
 qfd_static_ch546 u_sx2 (
 .wck(sx2_wck),.rck(sx2_rck),.rst_n(rst_n),
 .w_slot(sx2_w_slot),.w_addr(sx2_w_addr),.w_version(sx2_w_version),.i_valid(sx2_i_valid),.i_data(sx2_i_data),
 .r_slot(sx2_r_slot),.r_addr(sx2_r_addr),.r_version(sx2_r_version),
 .o_valid(sx2_o_valid),.o_data(sx2_full),.w_fault(sx2_w_fault),.r_fault(sx2_r_fault));
 wire [545:0] sr0_full; assign sr0_o_data=sr0_full[545:0];
 qfd_static_ch546 u_sr0 (
 .wck(sr0_wck),.rck(sr0_rck),.rst_n(rst_n),
 .w_slot(sr0_w_slot),.w_addr(sr0_w_addr),.w_version(sr0_w_version),.i_valid(sr0_i_valid),.i_data(sr0_i_data),
 .r_slot(sr0_r_slot),.r_addr(sr0_r_addr),.r_version(sr0_r_version),
 .o_valid(sr0_o_valid),.o_data(sr0_full),.w_fault(sr0_w_fault),.r_fault(sr0_r_fault));
 wire [545:0] sr1_full; assign sr1_o_data=sr1_full[545:0];
 qfd_static_ch546 u_sr1 (
 .wck(sr1_wck),.rck(sr1_rck),.rst_n(rst_n),
 .w_slot(sr1_w_slot),.w_addr(sr1_w_addr),.w_version(sr1_w_version),.i_valid(sr1_i_valid),.i_data(sr1_i_data),
 .r_slot(sr1_r_slot),.r_addr(sr1_r_addr),.r_version(sr1_r_version),
 .o_valid(sr1_o_valid),.o_data(sr1_full),.w_fault(sr1_w_fault),.r_fault(sr1_r_fault));
 wire [545:0] sr2_full; assign sr2_o_data=sr2_full[545:0];
 qfd_static_ch546 u_sr2 (
 .wck(sr2_wck),.rck(sr2_rck),.rst_n(rst_n),
 .w_slot(sr2_w_slot),.w_addr(sr2_w_addr),.w_version(sr2_w_version),.i_valid(sr2_i_valid),.i_data(sr2_i_data),
 .r_slot(sr2_r_slot),.r_addr(sr2_r_addr),.r_version(sr2_r_version),
 .o_valid(sr2_o_valid),.o_data(sr2_full),.w_fault(sr2_w_fault),.r_fault(sr2_r_fault));
 wire [545:0] seq_full; assign seq_o_data=seq_full[545:0];
 qfd_static_ch546 u_seq (
 .wck(seq_wck),.rck(seq_rck),.rst_n(rst_n),
 .w_slot(seq_w_slot),.w_addr(seq_w_addr),.w_version(seq_w_version),.i_valid(seq_i_valid),.i_data(seq_i_data),
 .r_slot(seq_r_slot),.r_addr(seq_r_addr),.r_version(seq_r_version),
 .o_valid(seq_o_valid),.o_data(seq_full),.w_fault(seq_w_fault),.r_fault(seq_r_fault));
 wire [545:0] cq_full; assign cq_o_data=cq_full[516:0];
 qfd_static_ch546 u_cq (
 .wck(cq_wck),.rck(cq_rck),.rst_n(rst_n),
 .w_slot(cq_w_slot),.w_addr(cq_w_addr),.w_version(cq_w_version),.i_valid(cq_i_valid),.i_data({29'b0,cq_i_data}),
 .r_slot(cq_r_slot),.r_addr(cq_r_addr),.r_version(cq_r_version),
 .o_valid(cq_o_valid),.o_data(cq_full),.w_fault(cq_w_fault),.r_fault(cq_r_fault));
endmodule
