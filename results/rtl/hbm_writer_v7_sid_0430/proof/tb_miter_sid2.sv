`timescale 1ns/1ps
module tb_vmwrite_v6_equiv;
reg clk, rst_n;
reg [1:0] sid;
reg [3:0] rgx_v;
reg [159:0] rgx_addr;
reg [2047:0] rgx_data;
reg rgx_vm;
reg tkw_v;
reg [567:0] tkw_d;
reg [4:0] ingress_slot;
reg [7:0] slot_valid;
reg [31:0] slot_owner;
wire [8*281-1:0] kq;
wire [8*281-1:0] kq_ref;
wire [4:0] launch_done;
wire [4:0] launch_done_ref;
wire fault;
wire fault_ref;
integer fault_rises=0;
ot_hgi_coll_static_vmwrite_roots_v7_sid2 dut(.clk_rgx_data0(clk),.clk_rgx_data1(clk),.clk_rgx_data2(clk),.clk_rgx_data3(clk),.clk_rgx_ctrl(clk),.clk_tkw(clk),.clk_bank0(clk),.clk_bank1(clk),.clk_bank2(clk),.clk_bank3(clk),.clk_bank4(clk),.clk_bank5(clk),.clk_bank6(clk),.clk_bank7(clk),.clk_meta(clk),.clk_body(clk),.rst_n(rst_n),.rgx_v(rgx_v),.rgx_addr(rgx_addr),.rgx_data0(rgx_data[0+:512]),.rgx_data1(rgx_data[512+:512]),.rgx_data2(rgx_data[1024+:512]),.rgx_data3(rgx_data[1536+:512]),.rgx_vm(rgx_vm),.tkw_v(tkw_v),.tkw_d(tkw_d),.ingress_slot(ingress_slot),.slot_valid(slot_valid),.slot_owner(slot_owner),.kq0(kq[0+:281]),.kq1(kq[281+:281]),.kq2(kq[562+:281]),.kq3(kq[843+:281]),.kq4(kq[1124+:281]),.kq5(kq[1405+:281]),.kq6(kq[1686+:281]),.kq7(kq[1967+:281]),.launch_done(launch_done),.fault(fault));
ot_hgi_coll_static_vmwrite ref_dut(.clk(clk),.rst_n(rst_n),.sid(sid),.rgx_v(rgx_v),.rgx_addr(rgx_addr),.rgx_data(rgx_data),.rgx_vm(rgx_vm),.tkw_v(tkw_v),.tkw_d(tkw_d),.ingress_slot(ingress_slot),.slot_valid(slot_valid),.slot_owner(slot_owner),.kq(kq_ref),.launch_done(launch_done_ref),.fault(fault_ref));
initial begin
clk=0; rst_n=0; sid=2; rgx_v=0; rgx_addr=0; rgx_data=0; rgx_vm=0; tkw_v=0; tkw_d=0; ingress_slot=0; slot_valid=0; slot_owner=0;
for(integer n=0;n<4096;n=n+1)begin
 #5; clk=0; rst_n=(n%17!=0); sid=2; rgx_v=$random; rgx_vm=$random; tkw_v=$random; ingress_slot=$random; slot_valid=$random; slot_owner=$random;
 for(integer k=0;k<5;k=k+1)rgx_addr[k*32+:32]=$random;
 for(integer k=0;k<64;k=k+1)rgx_data[k*32+:32]=$random;
 for(integer k=0;k<17;k=k+1)tkw_d[k*32+:32]=$random;
 tkw_d[567:544]=$random;
 #5; clk=1; #1;
 // All sixteen physical entry clocks receive the same logical edge here.
 // Every data/completion/exception bit must equal the existing pin-capture v4.
 if(n>3 && ({kq,launch_done,fault} !== {kq_ref,launch_done_ref,fault_ref}))$fatal(1,"writer roots mismatch n=%0d",n);
 if(n>3 && fault_ref && rst_n) fault_rises=fault_rises+1;
end
$display("VMWRITE_V6_EQUIV PASS edges=4096 full_shape=RGX4x512_TKW568 resets=241 invalid_slots=enabled clock_roots=16 same_edge=1 fault_latency=equal checked_fault_edges=%0d",fault_rises);$finish;
end
endmodule
