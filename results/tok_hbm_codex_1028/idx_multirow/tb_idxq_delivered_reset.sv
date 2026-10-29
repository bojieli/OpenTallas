`timescale 1ns/1ps
module tb_idxq_delivered_reset;
reg clk=0;always begin #0.416 clk=1;#0.417 clk=0;end
reg rst_n=0,pw=0,start=0;reg[7:0]pa=0;reg[255:0]pd=0;reg[4:0]nr=1;
reg compare=0;integer checks=0,keys=0,live=0,pre=0,frames=0,rows=0;
wire[0:0]a_weight_slot,b_weight_slot;
wire[0:0]a_query_slot,b_query_slot;
wire[6:0]a_query_index,b_query_index;
wire[0:0]a_query_emit,b_query_emit;
wire[4:0]a_query_emit_head,b_query_emit_head;
wire[0:0]a_key_slot,b_key_slot;
wire[0:0]a_key_v,b_key_v;
wire[7:0]a_key_index,b_key_index;
wire[4:0]a_key_row,b_key_row;
wire[0:0]a_pre_v,b_pre_v;
wire[7:0]a_pre_index,b_pre_index;
wire[11:0]a_nq,b_nq;
wire[0:0]a_frame_start,b_frame_start;
wire[0:0]a_row_start,b_row_start;
wire[0:0]a_fault,b_fault;
wire observed_pre=$test$plusargs("DROP_PRE")?1'b0:b_pre_v;
ot_hnx_idxq_qctl #(.DELIVERED_RESET(0)) a(.clk_program(clk),.clk_program_mem(clk),.rst_n(rst_n),.slot(1'b0),.program_we(pw),.program_addr(pa),.program_data(pd),.start(start),.length(12'd64),.n_rows(nr),.row_pitch(12'd96),.nkeys(14'd4096),.vf(1'b0),.qf(1'b0),.scf(1'b0),.kbf(1'b0),.weight_slot(a_weight_slot),.query_slot(a_query_slot),.query_index(a_query_index),.query_emit(a_query_emit),.query_emit_head(a_query_emit_head),.key_slot(a_key_slot),.key_v(a_key_v),.key_index(a_key_index),.key_row(a_key_row),.pre_v(a_pre_v),.pre_index(a_pre_index),.nq(a_nq),.frame_start(a_frame_start),.row_start(a_row_start),.fault(a_fault));
ot_hnx_idxq_qctl #(.DELIVERED_RESET(1)) b(.clk_program(clk),.clk_program_mem(clk),.rst_n(rst_n),.slot(1'b0),.program_we(pw),.program_addr(pa),.program_data(pd),.start(start),.length(12'd64),.n_rows(nr),.row_pitch(12'd96),.nkeys(14'd4096),.vf(1'b0),.qf(1'b0),.scf(1'b0),.kbf(1'b0),.weight_slot(b_weight_slot),.query_slot(b_query_slot),.query_index(b_query_index),.query_emit(b_query_emit),.query_emit_head(b_query_emit_head),.key_slot(b_key_slot),.key_v(b_key_v),.key_index(b_key_index),.key_row(b_key_row),.pre_v(b_pre_v),.pre_index(b_pre_index),.nq(b_nq),.frame_start(b_frame_start),.row_start(b_row_start),.fault(b_fault));
always @(posedge clk)begin #0.001;if(compare)begin checks++;
if({a_weight_slot,a_query_slot,a_query_index,a_query_emit,a_query_emit_head,a_key_slot,a_key_v,a_key_index,a_key_row,a_pre_v,a_pre_index,a_nq,a_frame_start,a_row_start,a_fault}!=={b_weight_slot,b_query_slot,b_query_index,b_query_emit,b_query_emit_head,b_key_slot,b_key_v,b_key_index,b_key_row,observed_pre,b_pre_index,b_nq,b_frame_start,b_row_start,b_fault})$fatal(1,"IDXQ_RESET_FAIL edge%0d",checks);
if(b_fault)$fatal(1,"IDXQ_RESET_FAIL calendarfault");keys+=b_key_v;live+=b_key_slot;pre+=b_pre_v;frames+=b_frame_start;rows+=b_row_start;
end end
initial begin
for(integer n=1;n<=6;n+=5)begin
 @(negedge clk);compare=0;rst_n=0;pw=0;start=0;nr=5'(n);
 repeat(8)@(negedge clk);rst_n=1;repeat(40)@(negedge clk);
 for(integer word=0;word<8;word++)begin
  pa=8'(word);pd=0;
  for(integer j=0;j<8;j++)if(word*8+j==4||word*8+j==40)pd[j*32+:32]=(32'b1<<28)|(32'(word+5)<<20);
  pw=1;@(negedge clk);pw=0;repeat(2)@(negedge clk);
 end
 compare=1;start=1;@(negedge clk);start=0;repeat(800)@(negedge clk);
end
if(keys!=14||live!=4||pre!=10||frames!=2||rows!=7)$fatal(1,"IDXQ_RESET_FAIL eventcounts %0d %0d %0d %0d %0d",keys,live,pre,frames,rows);
$display("IDXQ_RESET_PASS checks%0d key%0d live%0d pre%0d frame%0d rows%0d",checks,keys,live,pre,frames,rows);$finish;
end
endmodule
