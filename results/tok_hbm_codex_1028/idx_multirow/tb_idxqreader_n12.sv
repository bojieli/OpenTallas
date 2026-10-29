`timescale 1ns/1ps
module tb_idxqreader_n12;
parameter integer RT=171,BAD_RT=0;
localparam integer DELAY=8+RT-3;
reg clk=0;always begin #0.416 clk=1;#0.417 clk=0;end
reg rst_n=0,fs=0,ws=0,qs=0;reg[6:0]qi=0;reg[15:0]wr=0,qr=0,wsec=16'h6000,qsec=16'h6400;
reg compare=0;integer checks=0,blocks=0,requests=0;
wire[2055:0]rr;reg[135:0]pipe[0:DELAY-1];
wire[135:0]a_vm_rq,b_vm_rq;
wire[0:0]a_block_v,b_block_v;
wire[4:0]a_block_head,b_block_head;
wire[1:0]a_block_number,b_block_number;
wire[1023:0]a_block_data,b_block_data;
wire[15:0]a_head_weight,b_head_weight;
wire[0:0]a_fault,b_fault;
always @(posedge clk)begin
 if(!rst_n)for(integer d=0;d<DELAY;d++)pipe[d]<=0;
 else begin pipe[0]<=a_vm_rq;for(integer d=1;d<DELAY;d++)pipe[d]<=pipe[d-1];end
end
for(genvar b=0;b<8;b++)begin
 wire[15:0]sector=pipe[DELAY-1][b*17+:16];
 assign rr[b*257+:257]={pipe[DELAY-1][b*17+16],{8{32'h3f803f80^32'(sector)}}};
end
ot_hbm_idx_vm_query_static_n12 #(.VM_RT_EXTRA(RT)) a(.clk(clk),.rst_n(rst_n),.sid(2'd3),.weight_slot(ws),.query_slot(qs),.query_index(qi),.vm_rr(rr),.weight_sector(wsec),.query_sector(qsec),.vm_rq(a_vm_rq),.block_v(a_block_v),.block_head(a_block_head),.block_number(a_block_number),.block_data(a_block_data),.head_weight(a_head_weight),.fault(a_fault));
ot_hnx_idx_vm_query_static_n12 #(.VM_RT_EXTRA(BAD_RT?2:RT)) b(.clk(clk),.rst_n(rst_n),.sid(2'd3),.weight_slot(ws),.query_slot(qs),.query_index(qi),.vm_rr(rr),.frame_start(fs),.weight_sector(16'h6000),.query_sector(16'h6400),.weight_row_stride(wr),.query_row_stride(qr),.vm_rq(b_vm_rq),.block_v(b_block_v),.block_head(b_block_head),.block_number(b_block_number),.block_data(b_block_data),.head_weight(b_head_weight),.fault(b_fault));
always @(posedge clk)begin #0.001;if(compare)begin
 checks++;
 if(a_fault||b_fault)$fatal(1,"IDXQ_READER_FAIL fault edge%0d a%b b%b",checks,a_fault,b_fault);
 for(integer j=0;j<8;j++)begin
  if(a_vm_rq[j*17+16]!==b_vm_rq[j*17+16])$fatal(1,"IDXQ_READER_FAIL request valid");
  if(a_vm_rq[j*17+16])begin requests++;if(a_vm_rq[j*17+:17]!==b_vm_rq[j*17+:17])$fatal(1,"IDXQ_READER_FAIL row address");end
 end
 if(a_block_v!==b_block_v)$fatal(1,"IDXQ_READER_FAIL block valid");
 if(a_block_v)begin blocks++;if({a_block_head,a_block_number,a_block_data,a_head_weight}!=={b_block_head,b_block_number,b_block_data,b_head_weight})$fatal(1,"IDXQ_READER_FAIL block data");end
end end
initial begin
for(integer mode=0;mode<2;mode++)begin
 @(negedge clk);compare=0;rst_n=0;fs=0;ws=0;qs=0;wsec=16'h6000;qsec=16'h6400;
 wr=mode?16'd8:0;qr=mode?16'd512:0;
 repeat(8)@(negedge clk);rst_n=1;repeat(40)@(negedge clk);
 fs=1;@(negedge clk);fs=0;repeat(4)@(negedge clk);compare=1;
 for(integer row=0;row<(mode?6:1);row++)begin
  ws=1;@(negedge clk);ws=0;repeat(220)@(negedge clk);
  qs=1;qi=0;@(negedge clk);qs=0;repeat(220)@(negedge clk);
  qs=1;qi=127;@(negedge clk);qs=0;
  wsec+=wr;qsec+=qr;repeat(220)@(negedge clk);
 end
end
if(blocks!=14||requests!=70)$fatal(1,"IDXQ_READER_FAIL counts blocks%0d requests%0d",blocks,requests);
$display("IDXQ_READER_PASS RT%0d checks%0d blocks%0d requests%0d",RT,checks,blocks,requests);$finish;
end
endmodule
