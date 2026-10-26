`timescale 1ns/1ps
// Full-shape miter: two-stage writer v4 (ot_hgi_coll_static_vmwrite) against
// the pin-capture v2 reference (vmwrite_v2_reference.sv, frozen from
// aaa5a06f7). Contract: kq/launch_done of v4 at edge n equal v2 at edge n-1
// (one relay edge), fault equal at the same edge (check timing unchanged).
// Reset protocol: rst_n low for >=1 edge; the first edge after release
// carries no valid/reservation (v4 deasserts reset one edge later through
// its single rst_n pin flop); an in-flight launch is aborted by reset.
module tb_vmwrite_v4_equiv;
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
wire [8*281-1:0] kq, kq_ref;
reg [8*281-1:0] kq_ref_d;
wire [4:0] launch_done, launch_done_ref;
reg [4:0] launch_done_ref_d;
wire fault, fault_ref;
integer fault_rises=0, live_banks=0, compared=0, valid_frac;
ot_hgi_coll_static_vmwrite dut(.clk(clk),.rst_n(rst_n),.sid(sid),.rgx_v(rgx_v),.rgx_addr(rgx_addr),.rgx_data(rgx_data),.rgx_vm(rgx_vm),.tkw_v(tkw_v),.tkw_d(tkw_d),.ingress_slot(ingress_slot),.slot_valid(slot_valid),.slot_owner(slot_owner),.kq(kq),.launch_done(launch_done),.fault(fault));
ot_hgi_coll_static_vmwrite_v2ref ref_dut(.clk(clk),.rst_n(rst_n),.sid(sid),.rgx_v(rgx_v),.rgx_addr(rgx_addr),.rgx_data(rgx_data),.rgx_vm(rgx_vm),.tkw_v(tkw_v),.tkw_d(tkw_d),.ingress_slot(ingress_slot),.slot_valid(slot_valid),.slot_owner(slot_owner),.kq(kq_ref),.launch_done(launch_done_ref),.fault(fault_ref));
initial begin
clk=0; rst_n=0; sid=0; rgx_v=0; rgx_addr=0; rgx_data=0; rgx_vm=0; tkw_v=0; tkw_d=0; ingress_slot=0; slot_valid=0; slot_owner=0;
kq_ref_d=0; launch_done_ref_d=0;
for(integer n=0;n<4096;n=n+1)begin
 #5; clk=0; rst_n=(n%17!=0); sid=$random; rgx_v=$random; rgx_vm=$random; tkw_v=$random; ingress_slot=$random; slot_valid=$random; slot_owner=$random;
 for(integer k=0;k<5;k=k+1)rgx_addr[k*32+:32]=$random;
 // half of the edges carry legal sid-0 sector addresses so payload compares are live
 if(n%2==0) for(integer k=0;k<4;k=k+1) rgx_addr[k*40+:40]={21'd0,2'b00,13'($random)&13'h1ffe,3'd0};
 for(integer k=0;k<64;k=k+1)rgx_data[k*32+:32]=$random;
 for(integer k=0;k<17;k=k+1)tkw_d[k*32+:32]=$random;
 tkw_d[567:544]=$random;
 if(n%2==0) tkw_d[567:528]={21'd0,2'b00,13'($random)&13'h1ffe,3'd0};
 if(n%17==1) begin rgx_v=0; tkw_v=0; ingress_slot=0; slot_valid=0; end
 #5; clk=1; #1;
 if(n>3 && n%17!=0) begin
  if({kq,launch_done} !== {kq_ref_d,launch_done_ref_d}) $fatal(1,"writer v4 relay mismatch n=%0d",n);
  compared=compared+1;
  for(integer b=0;b<8;b=b+1) if(kq[b*281+280]) live_banks=live_banks+1;
 end
 if(n>3 && fault !== fault_ref) $fatal(1,"writer v4 fault timing mismatch n=%0d",n);
 if(n>3 && fault_ref && rst_n) fault_rises=fault_rises+1;
 kq_ref_d=kq_ref; launch_done_ref_d=launch_done_ref;
end
$display("VMWRITE_V4_EQUIV PASS edges=4096 compared=%0d live_bank_launches=%0d full_shape=RGX4x512_TKW568 resets=241 relay=+1 fault_latency=equal fault_edges=%0d",compared,live_banks,fault_rises);$finish;
end
endmodule
