`timescale 1ps/1ps
// Actual qctl -> native n12 reader -> query/quant pins. The external VM
// returns only requests issued by the reader, at its current bound latency.
// Independent released-golden query vectors vary in every row.
module tb_idx_rows_numeric;
 parameter integer RT=173, LEN=1568, PITCH=328, NROWS=6;
 localparam integer DELAY=8+RT-3;
 reg clk=0;always begin #416 clk=1;#417 clk=0;end
 reg rst_n=0,pw=0,start=0;reg[7:0]pa=0;reg[255:0]pd=0;
 reg[31:0]prog[0:2047];reg[255:0]mem[0:65535];reg[559:0]gold[0:191];
 wire ws,qs,qe,ks,kv,pv,fs,rs,cf;wire[6:0]qi;wire[4:0]qh,kr;wire[7:0]ki,pi;wire[11:0]nq;
 wire bv,rf,qv,qf;wire[4:0]bh;wire[1:0]bn;wire[1023:0]bd;wire[15:0]hw;
 wire[7:0]oh;wire[511:0]oc;wire[31:0]os;wire[15:0]ow;
 wire[135:0]rq;wire[2055:0]rr;reg[135:0]pipe[0:DELAY-1];
 integer checks=0,blocks=0,requests=0,clears=0,frames=0,keys=0,cycle=0;
 integer drop_clear,wrong_stride,drop_return;
 initial begin
  drop_clear=$test$plusargs("DROP_CLEAR");wrong_stride=$test$plusargs("WRONG_STRIDE");drop_return=$test$plusargs("DROP_RETURN");
 end
 ot_hnx_idxq_qctl #(.DELIVERED_RESET(1),.ROW_CLEAR_DELAY(RT-2)) ctl(
  .clk_program(clk),.clk_program_mem(clk),.rst_n(rst_n),.slot(1'b0),.program_we(pw),.program_addr(pa),.program_data(pd),
  .start(start),.length(12'(LEN)),.n_rows(5'(NROWS)),.row_pitch(12'(PITCH)),.nkeys(14'd4096),
  .vf(rf),.qf(qf),.scf(1'b0),.kbf(1'b0),.weight_slot(ws),.query_slot(qs),.query_index(qi),
  .query_emit(qe),.query_emit_head(qh),.key_slot(ks),.key_v(kv),.key_index(ki),.key_row(kr),.pre_v(pv),.pre_index(pi),
  .nq(nq),.frame_start(fs),.row_start(rs),.fault(cf));
 ot_hnx_idx_vm_query_static_n12 #(.VM_RT_EXTRA(RT)) reader(.clk(clk),.rst_n(rst_n),.sid(RT==173?2'd2:2'd3),
  .weight_slot(ws),.query_slot(qs),.query_index(qi),.frame_start(fs),
  .weight_sector(RT==173?16'h4000:16'h6000),.query_sector(RT==173?16'h4400:16'h6400),.weight_row_stride(16'd8),.query_row_stride(wrong_stride?16'd0:16'd512),
  .vm_rq(rq),.vm_rr(rr),.block_v(bv),.block_head(bh),.block_number(bn),.block_data(bd),.head_weight(hw),.fault(rf));
 ot_hbm_idx_query_static query(.clk(clk),.clk_quant(clk),.clk_quant_delay(clk),.clk_bank({4{clk}}),.rst_n(rst_n),
  .frame_start(rs&&!drop_clear),.block_v(bv),.block_head(bh),.block_number(bn),.block_data(bd),.head_weight(hw),
  .emit_v(qe),.emit_head(qh),.ql_v(qv),.ql_head(oh),.ql_codes(oc),.ql_sc(os),.ql_w(ow),.fault(qf));
 always @(posedge clk)begin
  if(!rst_n)for(integer d=0;d<DELAY;d++)pipe[d]<=0;
  else begin pipe[0]<=rq;for(integer d=1;d<DELAY;d++)pipe[d]<=pipe[d-1];end
 end
 for(genvar b=0;b<8;b++)begin
  wire[15:0]sector=pipe[DELAY-1][b*17+:16];
  assign rr[b*257+:257]={pipe[DELAY-1][b*17+16]&&!(drop_return&&b==0),mem[sector]};
 end
 always @(negedge clk)begin
  cycle++;
  if(rst_n)begin
   if(cf||rf||qf)$fatal(1,"IDX_NUMERIC_FAIL fault at%0d ctl%0b reader%0b query%0b checks%0d blocks%0d",cycle,cf,rf,qf,checks,blocks);
   if(bv)blocks++;if(rs)clears++;if(fs)frames++;if(kv)keys++;
   for(integer b=0;b<8;b++)if(rq[b*17+16])requests++;
   if(qv)begin
    if(oh!==8'(checks%32)||{ow,os,oc}!==gold[checks])
     $fatal(1,"IDX_NUMERIC_FAIL numeric row%0d head%0d gothead%0d got%h expected%h",checks/32,checks%32,oh,{ow,os,oc},gold[checks]);
    checks++;
   end
  end
 end
 initial begin
  $readmemh("prog.hex",prog);$readmemh("vm.hex",mem);$readmemh("gold.hex",gold);
  repeat(8)@(negedge clk);rst_n=1;repeat(40)@(negedge clk);
  for(integer row=0;row*8<LEN;row++)begin
   pa=8'(row);for(integer j=0;j<8;j++)pd[j*32+:32]=(row*8+j<LEN)?prog[row*8+j]:32'd0;
   pw=1;@(negedge clk);pw=0;repeat(2)@(negedge clk);
  end
  start=1;@(negedge clk);start=0;repeat((NROWS-1)*PITCH+LEN+RT+64)@(negedge clk);
  if(checks!=32*NROWS||blocks!=128*NROWS||requests!=514*NROWS||clears!=NROWS||frames!=1||keys!=171*NROWS)
   $fatal(1,"IDX_NUMERIC_FAIL counts checks%0d blocks%0d requests%0d clears%0d frames%0d keys%0d",checks,blocks,requests,clears,frames,keys);
  $display("IDX_NUMERIC_PASS rt%0d pitch%0d rows%0d checks%0d blocks%0d requests%0d keys%0d edges%0d",RT,PITCH,NROWS,checks,blocks,requests,keys,cycle);$finish;
 end
endmodule
