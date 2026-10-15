`timescale 1ns/1ps
module tb_vmwrite_decode_equiv;
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
ot_hgi_coll_static_vmwrite dut(.clk(clk),.rst_n(rst_n),.sid(sid),.rgx_v(rgx_v),.rgx_addr(rgx_addr),.rgx_data(rgx_data),.rgx_vm(rgx_vm),.tkw_v(tkw_v),.tkw_d(tkw_d),.ingress_slot(ingress_slot),.slot_valid(slot_valid),.slot_owner(slot_owner),.kq(kq),.launch_done(launch_done),.fault(fault));
ot_hgi_coll_static_vmwrite_reference ref_dut(.clk(clk),.rst_n(rst_n),.sid(sid),.rgx_v(rgx_v),.rgx_addr(rgx_addr),.rgx_data(rgx_data),.rgx_vm(rgx_vm),.tkw_v(tkw_v),.tkw_d(tkw_d),.ingress_slot(ingress_slot),.slot_valid(slot_valid),.slot_owner(slot_owner),.kq(kq_ref),.launch_done(launch_done_ref),.fault(fault_ref));
initial begin
clk=0; rst_n=0; sid=0; rgx_v=0; rgx_addr=0; rgx_data=0; rgx_vm=0; tkw_v=0; tkw_d=0; ingress_slot=0; slot_valid=0; slot_owner=0;
for(integer n=0;n<4096;n=n+1)begin
 #5; clk=0; rst_n=(n%17!=0); sid=$random; rgx_v=$random; rgx_vm=$random; tkw_v=$random; ingress_slot=$random; slot_valid=$random; slot_owner=$random;
 for(integer k=0;k<5;k=k+1)rgx_addr[k*32+:32]=$random;
 for(integer k=0;k<64;k=k+1)rgx_data[k*32+:32]=$random;
 for(integer k=0;k<17;k=k+1)tkw_d[k*32+:32]=$random;
 tkw_d[567:544]=$random;
 #5; clk=1; #1;
 if(n>3 && ({kq,launch_done,fault} !== {kq_ref,launch_done_ref,fault_ref}))$fatal(1,"writer structural mismatch n=%0d",n);
end
$display("VMWRITE_DECODE_EQUIV PASS edges=4096 full_shape=RGX4x512_TKW568 resets=241 invalid_slots=enabled");$finish;
end
endmodule
