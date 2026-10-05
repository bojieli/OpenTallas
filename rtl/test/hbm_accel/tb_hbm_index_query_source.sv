`timescale 1ns/1ps
// Actual cached native SU landing bytes are DUT operands. Archived expected AQ
// bytes are comparator ONLY. The VM response here is a directed component
// provider, not a production VM/clock/ownership qualification.
module tb_hbm_index_query_source;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0,start=0;wire src_ready,src_fault,src_done,q_ready,q_fault,q_done;
 wire bv,br;wire[4:0] bh;wire[1:0] bn;wire[1023:0] bd;wire[15:0] bw;
 wire rv,rr;reg rg=0,pv=0;wire pr;wire[31:0] ra,rjob;wire[7:0] rt;wire[5:0] rw;
 wire[3:0] rgen;wire[19:0] rp;wire[6:0] rank;
 reg[1023:0] pd;reg[7:0] pt;reg[3:0] pg=4'ha;
 wire qv;reg qr=0;wire[7:0] qh;wire[511:0] qc;wire[31:0] qs;wire[15:0] qw;
 wire begin_frame=start&&src_ready&&q_ready;
 ot_hbm_accel_index_query_source #(.ENABLE(1)) source_join(
 .clk(clk),.por_n(por_n),.start(begin_frame),.start_ready(src_ready),
 .source_job(32'hfeed0123),.source_gen(4'ha),.source_pos(20'd1048575),.source_rank(7'd0),
 .original_q_base(32'd64),.rotated_q_base(32'd4160),.scaled_weight_base(32'd8288),.source_tail_words(8'd64),
 .read_v(rv),.read_r(rg),.read_addr(ra),.read_tag(rt),.read_words(rw),
 .read_job(rjob),.read_gen(rgen),.read_pos(rp),.read_rank(rank),
 .rsp_v(pv),.rsp_r(pr),.rsp_data(pd),.rsp_tag(pt),.rsp_job(32'hfeed0123),.rsp_gen(pg),
 .rsp_pos(20'd1048575),.rsp_rank(7'd0),
 .block_v(bv),.block_r(br),.block_head(bh),.block_number(bn),.block_data(bd),.head_weight(bw),
 .fault(src_fault),.done(src_done));
 ot_hbm_accel_index_query #(.ENABLE(1)) query_join(
 .clk(clk),.por_n(por_n),.start(begin_frame),.start_ready(q_ready),
 .block_v(bv),.block_r(br),.block_head(bh),.block_number(bn),.block_data(bd),.head_weight(bw),
 .ql_v(qv),.ql_r(qr),.ql_head(qh),.ql_codes(qc),.ql_sc(qs),.ql_w(qw),.done(q_done),.fault(q_fault));
 reg[31:0] initial_vm[0:262143],native_vm[0:262143];reg[783:0] expected[0:127];
 string original_path,native_path,expected_path;
 integer i,n,l,b,cycles=0,reads=0,blocks=0,heads=0;
 reg source_finished=0,pending=0,bad_response=0;
 integer address,delay_edges;reg[7:0] tag;
 reg[511:0] want_codes;reg[31:0] want_scales;reg signed[11:0] e;
 always @(posedge clk)begin
  cycles<=cycles+1;
  if(src_done)source_finished<=1;
  if(bv&&br)blocks<=blocks+1;
  if(por_n && rv&&rg)begin
   if(pending)$fatal(1,"read exceeded prepaid capacity");
   if(rw!=32||rjob!=32'hfeed0123||rgen!=4'ha||rp!=1048575||rank!=0)$fatal(1,"source frame not held");
   if(rt==128)begin if(ra!=8288)$fatal(1,"wrong weight producer base");end
   else if(ra!=((rt[1]?4160:64)+(rt/4)*128+(rt%4)*32))$fatal(1,"wrong source view/original prefix");
   address<=ra;tag<=rt;pending<=1;delay_edges<=2+(rt%3);reads<=reads+1;
  end
  if(pending&&delay_edges>0)delay_edges<=delay_edges-1;
  if(pv&&pr)pending<=0;
 end
 always @(negedge clk)begin
  rg=por_n&&cycles%5!=0&&!pending;
  pv=pending&&delay_edges==0;
  pt=tag;pg=bad_response?4'hb:4'ha;
  if(pending)for(l=0;l<32;l=l+1)begin
   if(tag!=128&&tag[1]==0)begin
    if(initial_vm[address+l]!==native_vm[address+l])$fatal(1,"original Q changed in retained native landing");
    pd[l*32+:32]=initial_vm[address+l];
   end else pd[l*32+:32]=native_vm[address+l];
  end
 end
 initial begin
  if(!$value$plusargs("ORIGINAL=%s",original_path)||!$value$plusargs("NATIVE=%s",native_path)||!$value$plusargs("EXPECTED=%s",expected_path))$fatal(1,"actual source paths required");
  $readmemh(original_path,initial_vm);$readmemh(native_path,native_vm);$readmemh(expected_path,expected);
  repeat(3)@(negedge clk);por_n=1;
  @(negedge clk);start=1;@(negedge clk);start=0;
  // Source runs independently into the query's finite prepaid head storage.
  for(n=0;n<32;n=n+1)begin
   while(!qv)begin @(negedge clk);if(src_fault||q_fault)$fatal(1,"native query source fault");end
   want_codes=0;want_scales=0;
   for(b=0;b<4;b=b+1)begin
    i=4*n+b;e=expected[i][768+:12];
    if(expected[i][780+:4]!=0)$fatal(1,"cached comparator fault");
    want_scales[8*b+:8]=8'(e+127);
    for(l=0;l<32;l=l+1)want_codes[128*b+4*l+:4]=expected[i][512+8*l+:4];
   end
   if(qh!=n||qc!==want_codes||qs!==want_scales||qw!==native_vm[8288+n][31:16])$fatal(1,"actual native source/head mismatch %0d",n);
   repeat(3)@(negedge clk);qr=1;@(negedge clk);qr=0;heads=heads+1;
  end
  if(!source_finished||!q_done||blocks!=128||reads!=129||src_fault||q_fault)$fatal(1,"joined terminal/count mismatch");
  // A wrong generation remains unaccepted, preserving actual pending read.
  @(negedge clk);source_finished=0;bad_response=1;start=1;@(negedge clk);start=0;
  wait(src_fault);@(negedge clk);
  if(pr||!pending||bv)$fatal(1,"foreign response acknowledged or debt discarded");
  $display("PASS_HBM_NATIVE_VM_QUERY_JOIN heads=%0d blocks=%0d reads_first_frame=129 cycles=%0d wrong_generation_held=1 current_SU_clock_qualified=0",heads,blocks,cycles);
  $finish;
 end
endmodule
