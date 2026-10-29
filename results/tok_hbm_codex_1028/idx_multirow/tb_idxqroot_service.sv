`timescale 1ns/1ps
module tb_idxqroot_service;
parameter integer BAD_RT=0;
reg clk=0;always begin #0.416 clk=1;#0.417 clk=0;end
reg rst_n=0;reg[135:0]index_rq=0,argmax_rq=0;reg[2055:0]vm_rr=0;reg topk_go=0;
integer checks=0;reg compare=0;
wire[337:0]a_cq,b_cq;
wire[1:0]a_cq_seq,b_cq_seq;
wire[0:0]a_topk_busy,b_topk_busy;
wire[0:0]a_topk_done,b_topk_done;
wire[0:0]a_topk_fault,b_topk_fault;
wire[2055:0]a_index_rr,b_index_rr;
wire[263:0]a_argmax_m,b_argmax_m;
wire[135:0]a_vm_rq,b_vm_rq;
wire[0:0]a_share_fault,b_share_fault;
ot_hbm_idx_rootctl_static_am #(.VM_RT(75),.CR_RT(36),.SEL_LAT(40),.RSTL(1),.FAN32(1)) a(
 .clk(clk),.rst_n(rst_n),.program_we(1'b0),.program_addr(8'b0),.program_data(256'b0),.start(1'b0),.length(12'b0),
 .tree_ev(4'b0),.qfault(4'b0),.lf(1'b0),.topk_go(topk_go),.topk_k(4'd4),.topk_order(1'b0),.topk_n(20'd8),.topk_m(20'd1),
 .topk_a_mirror(1'b0),.topk_a_base(18'd0),.topk_a_str(18'd1),.topk_o_mirror(1'b0),.topk_o_base(18'd32),.topk_o_str(18'd1),
 .topk_has_r(1'b0),.topk_r_base(18'd64),.topk_r_str(18'd1),.cr(274'b0),.index_rq(index_rq),.argmax_rq(argmax_rq),.vm_rr(vm_rr),
.selected_v(4'b0),.sf(1'b0),.cq(a_cq),.cq_seq(a_cq_seq),.topk_busy(a_topk_busy),.topk_done(a_topk_done),.topk_fault(a_topk_fault),.index_rr(a_index_rr),.argmax_m(a_argmax_m),.vm_rq(a_vm_rq),.share_fault(a_share_fault));
ot_hnx_idxq_rootctl_static_am #(.VM_RT(BAD_RT?74:75),.CR_RT(36),.SEL_LAT(40),.RSTL(1),.FAN32(1)) b(
 .clk(clk),.rst_n(rst_n),.program_we(1'b0),.program_addr(8'b0),.program_data(256'b0),.start(1'b0),.length(12'b0),
 .tree_ev(4'b0),.qfault(4'b0),.lf(1'b0),.topk_go(topk_go),.topk_k(4'd4),.topk_order(1'b0),.topk_n(20'd8),.topk_m(20'd1),
 .topk_a_mirror(1'b0),.topk_a_base(18'd0),.topk_a_str(18'd1),.topk_o_mirror(1'b0),.topk_o_base(18'd32),.topk_o_str(18'd1),
 .topk_has_r(1'b0),.topk_r_base(18'd64),.topk_r_str(18'd1),.cr(274'b0),.index_rq(index_rq),.argmax_rq(argmax_rq),.vm_rr(vm_rr),
.n_rows(5'd1),.row_pitch(12'd128),.selected_v(16'b0),.sf(4'b0),.cq(b_cq),.cq_seq(b_cq_seq),.topk_busy(b_topk_busy),.topk_done(b_topk_done),.topk_fault(b_topk_fault),.index_rr(b_index_rr),.argmax_m(b_argmax_m),.vm_rq(b_vm_rq),.share_fault(b_share_fault));
always @(posedge clk)begin #0.001;if(compare)begin checks++;
if({a_cq,a_cq_seq,a_topk_busy,a_topk_done,a_topk_fault,a_index_rr,a_argmax_m,a_vm_rq,a_share_fault}!=={b_cq,b_cq_seq,b_topk_busy,b_topk_done,b_topk_fault,b_index_rr,b_argmax_m,b_vm_rq,b_share_fault})$fatal(1,"IDXQ_ROOT_SERVICE_FAIL edge%0d BAD_RT%0d",checks,BAD_RT);
end end
initial begin
 repeat(8)@(negedge clk);rst_n=1;repeat(40)@(negedge clk);compare=1;
 for(integer t=0;t<1200;t++)begin
  @(negedge clk);
  for(integer j=0;j<8;j++)begin
   index_rq[j*17+:17]={((t+j)%7==0),16'(t*13+j)};
   argmax_rq[j*17+:17]={((t+j)%11==0),16'(t*17+j)};
   vm_rr[j*257+:257]={1'b1,256'(t*31+j)};
  end
  topk_go=(t==32);
 end
 @(negedge clk);$display("IDXQ_ROOT_SERVICE_PASS checks=%0d BAD_RT%0d",checks,BAD_RT);$finish;
end
endmodule
