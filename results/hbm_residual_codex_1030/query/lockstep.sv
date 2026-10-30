module probe #(parameter RT=171)(output reg done=0);
reg clk=0;always #5 clk=~clk; reg rst_n=0;
reg [1:0] sid=0;
reg weight_slot=0;
reg query_slot=0;
reg [6:0] query_index=0;
reg [15:0] weight_sector=0;
reg [15:0] query_sector=0;
wire [135:0] vm_rq;
wire [135:0] vm_rq_cand;
wire [135:0] vm_rq_mut;
reg [2055:0] vm_rr=0;
wire block_v;
wire block_v_cand;
wire block_v_mut;
wire [4:0] block_head;
wire [4:0] block_head_cand;
wire [4:0] block_head_mut;
wire [1:0] block_number;
wire [1:0] block_number_cand;
wire [1:0] block_number_mut;
wire [1023:0] block_data;
wire [1023:0] block_data_cand;
wire [1023:0] block_data_mut;
wire [15:0] head_weight;
wire [15:0] head_weight_cand;
wire [15:0] head_weight_mut;
wire fault;
wire fault_cand;
wire fault_mut;
ot_hbm_idx_vm_query_static_n12 #(.VM_RT_EXTRA(RT)) refdut(.clk(clk),.rst_n(rst_n),.sid(sid),.weight_slot(weight_slot),.query_slot(query_slot),.query_index(query_index),.weight_sector(weight_sector),.query_sector(query_sector),.vm_rq(vm_rq),.vm_rr(vm_rr),.block_v(block_v),.block_head(block_head),.block_number(block_number),.block_data(block_data),.head_weight(head_weight),.fault(fault));
generate if(RT==171) ot_hbm_idx_vm_query_static_n12__rt171 dut(.clk(clk),.rst_n(rst_n),.sid(sid),.weight_slot(weight_slot),.query_slot(query_slot),.query_index(query_index),.weight_sector(weight_sector),.query_sector(query_sector),.vm_rq(vm_rq_cand),.vm_rr(vm_rr),.block_v(block_v_cand),.block_head(block_head_cand),.block_number(block_number_cand),.block_data(block_data_cand),.head_weight(head_weight_cand),.fault(fault_cand)); else ot_hbm_idx_vm_query_static_n12__rt173 dut(.clk(clk),.rst_n(rst_n),.sid(sid),.weight_slot(weight_slot),.query_slot(query_slot),.query_index(query_index),.weight_sector(weight_sector),.query_sector(query_sector),.vm_rq(vm_rq_cand),.vm_rr(vm_rr),.block_v(block_v_cand),.block_head(block_head_cand),.block_number(block_number_cand),.block_data(block_data_cand),.head_weight(head_weight_cand),.fault(fault_cand)); endgenerate
ot_hbm_idx_vm_query_static_n12 #(.VM_RT_EXTRA(RT==171?173:171)) mutant(.clk(clk),.rst_n(rst_n),.sid(sid),.weight_slot(weight_slot),.query_slot(query_slot),.query_index(query_index),.weight_sector(weight_sector),.query_sector(query_sector),.vm_rq(vm_rq_mut),.vm_rr(vm_rr),.block_v(block_v_mut),.block_head(block_head_mut),.block_number(block_number_mut),.block_data(block_data_mut),.head_weight(head_weight_mut),.fault(fault_mut));
integer cycle=0,blocks=0,requests=0,returns=0,killed=0;
always @(negedge clk) begin
 cycle=cycle+1; rst_n=(cycle>16); weight_slot=(cycle==24); query_slot=(cycle==240 || cycle==260 || cycle==310); query_index=cycle==260?7:cycle==310?12:3; vm_rr=0;
 for(integer b=0;b<8;b=b+1)begin vm_rr[b*257+256]=rst_n && refdut.core.face.due[8+RT-2][b]; for(integer w=0;w<8;w=w+1)vm_rr[b*257+w*32+:32]=32'h3f800000+b*256+w; if(vm_rr[b*257+256])returns=returns+1;end
end
always @(posedge clk)begin #1; if(cycle>20)begin
if({vm_rq,block_v,block_head,block_number,block_data,head_weight,fault} !== {vm_rq_cand,block_v_cand,block_head_cand,block_number_cand,block_data_cand,head_weight_cand,fault_cand}) $fatal(1,"wrapper mismatch RT%0d cycle%0d",RT,cycle);
if(fault!==1'b0)$fatal(1,"reference fault RT%0d cycle%0d",RT,cycle);
if(fault_mut===1'b1)killed=1; if(block_v)blocks=blocks+1; for(integer b=0;b<8;b=b+1)if(vm_rq[b*17+16])requests=requests+1;
end
if(cycle==650)begin if(blocks!=3 || requests!=14 || returns!=14 || !killed)$fatal(1,"coverage RT%0d blocks%0d req%0d ret%0d mutant%0d",RT,blocks,requests,returns,killed); $display("PASS RT%0d cycles650 full-output lockstep blocks%0d requests%0d returns%0d wrong-RT mutant killed",RT,blocks,requests,returns); done=1;end
end
endmodule
module tb;wire a,b;probe #(171) p(a);probe #(173) q(b);always @(a or b)if(a&&b)$finish; initial begin #7000;$fatal(1,"timeout");end endmodule
