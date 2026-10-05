`timescale 1ns/1ps
`default_nettype none
module tb;
 localparam integer WA=15,FW=512,SRC=2000,DST=101,WORDS=266;
 reg fast_clk=1,slow_clk=1;always #3 fast_clk=~fast_clk;always #4 slow_clk=~slow_clk;
 reg cold_n=0,fast_rst_n=0,slow_rst_n=0;
 wire rst_n=fast_rst_n;
 reg go=0,topk=0,started=0;
 reg [WA-1:0] src=SRC,n=WORDS,dst=DST,ibase=5200;
 reg [15:0] k=8192;
 wire busy,fault,vm_re,vm_we,vm_reply_ready,ov_ready,ev,el,em;
 wire [WA-1:0] vm_ra,vm_wa,req_cookie;
 wire [511:0] vm_wd,ed;
 wire [3:0] we4;wire [4*WA-1:0] wa4;wire [2047:0] wd4;
 wire [31:0] tag,wo,wi;
 reg [31:0] cyc=0;integer sent=0,reads=0,writes=0,write_packets=0,holds=0,maxq=0;
 reg allow_write=1;reg [31:0] before_writes;
 // All-gather cannot return a word before its own rank produced that word.
 wire ov=started && sent<reads && sent<(topk ? 256 : WORDS);
 wire ol=sent==(topk ? 255 : WORDS-1);
 reg [2047:0] od;
 wire er=(cyc%11)<7;
 wire [4:0] rv,rr,qv;assign rv=5'b00100&{5{vm_re}};
 wire [4:0] qr=5'b00100&{5{vm_reply_ready}};
 wire [10239:0] qdata;wire [1139:0] qowner;
 wire [19:0] ren=20'h00100;
 wire [599:0] ra={{330{1'b0}},15'b0,vm_ra,{240{1'b0}}};
 wire [824:0] ctx={{330{1'b0}},150'b0,req_cookie,{330{1'b0}}};
 reg [3:0] me_en=0;reg [119:0] me_a=0;reg [63:0] me_mask=0;reg [2047:0] me_d=0;
 wire [2:0] wr,vis,pend;wire [127:0] row_visible;
 wire parent_fault,quar;wire [7:0] debt;wire [3:0] nwa,nack;wire nra;
 wire [494:0] wc={133'b0,tag,{330{1'b0}}};
 ot_ds_native_vm_related_parent #(.ENABLE(1)) provider(
 .fast_clk(fast_clk),.slow_clk(slow_clk),.cold_n(cold_n),.fast_rst_n(fast_rst_n),.slow_rst_n(slow_rst_n),.abort_fast(1'b0),.abort_slow(1'b0),
 .r_v(rv),.r_ready(rr),.r_enable(ren),.r_addr(ra),.r_context(ctx),.q_v(qv),.q_ready(qr),.q_data(qdata),.q_owner(qowner),
 .me_en(me_en),.me_wordaddr(me_a),.me_mask(me_mask),.me_data(me_d),.row_en(128'b0),.row_addr(3840'b0),.row_data(4096'b0),
 .coll_en(we4&{4{allow_write}}),.coll_wordaddr(wa4),.coll_data(wd4),.w_context(wc),.w_ready(wr),.w_visible(vis),.w_pending(pend),.row_visible_mask(row_visible),
 .fault(parent_fault),.quarantined(quar),.debt(debt),.debug_native_write_accept(nwa),.debug_native_visible(nack),.debug_native_read_accept(nra));
 ot_w15_coll_dma_related_vm #(.WA(WA),.FW(FW),.N(4),.GW(4),.TOPK(1),.TK_NMAX(2048),.TK_DIG(8),.VM_ALWAYS_READY(1),
 .VM_RESPONSE_WAIT(1),.VISIBLE_COMPLETION(1),.TOPK_OUTPUT_QUEUE(1)) dma(
 .clk(fast_clk),.rst_n(rst_n),.go(go),.mode(1'b1),.rnd(1'b0),.tag(32'd71),.src(src),.n(n),.dst(dst),.topk(topk),.ibase(ibase),.tk_k(k),.tk_stride(32'd2048),
 .busy(busy),.fault(fault),.words_out(wo),.words_in(wi),
 .vm_re(vm_re),.vm_raddr(vm_ra),.vm_rq(qdata[4096+:512]),.vm_we(vm_we),.vm_waddr(vm_wa),.vm_wdata(vm_wd),
 .vm_req_ready(rr[2]),.vm_reply_valid(qv[2]),.vm_reply_cookie(qowner[456+59+:15]),.vm_request_cookie(req_cookie),.vm_reply_ready(vm_reply_ready),
 .vm_write_visible(vis[2]),.vm_write_pending(pend[2]),.vm_ready4(wr[2]&&allow_write),.vm_we4(we4),.vm_waddr4(wa4),.vm_wdata4(wd4),
 .e_valid(ev),.e_ready(er),.e_data(ed),.e_last(el),.e_mode(em),.e_tag(tag),
 .o_valid(ov),.o_ready(ov_ready),.o_data(od),.o_last(ol),.o_rank(2'b0),.o_err(1'b0),.engine_fault(1'b0));
 function automatic [511:0] payload(input integer rank,input integer idx,input integer tk);
  reg [511:0] v;
  begin for(integer l=0;l<16;l=l+1)v[l*32+:32]=tk ? (idx<128 ? 32'b0 : (idx-128)*16+l) : (rank<<24)|(idx<<8)|l;payload=v;end
 endfunction
 always_comb for(integer r=0;r<4;r=r+1)od[r*512+:512]=payload(r,sent,topk);
 always @(posedge fast_clk)if(cold_n)begin
  cyc<=cyc+1;
  if(fault||parent_fault||quar)$fatal(1,"DMA/parent fault");
  if(ov&&ov_ready)sent<=sent+1;
  if(ov&&!ov_ready)holds<=holds+1;
  if(ev&&er)begin
   if(ed!==payload(0,reads,topk)||el!=(reads==(topk ? 255 : WORDS-1)))$fatal(1,"actual reply/skid order read%0d",reads);
   reads<=reads+1;
  end
  if(topk&&dma.tq_count>maxq)maxq<=dma.tq_count;
  if((|we4)&&wr[2]&&allow_write)begin
   integer count;count=0;
   for(integer b=0;b<4;b=b+1)if(we4[b])begin
    integer a,r,i;
    a=wa4[b*15+:15];r=(a-DST)/WORDS;i=(a-DST)%WORDS;
    if(!topk && (a<DST||a>=DST+4*WORDS||wd4[b*512+:512]!==payload(r,i,0)))$fatal(1,"collective gather write %0d",a);
    if(topk)for(integer l=0;l<16;l=l+1)if(wd4[b*512+l*32+:32]!==32'((a-10000)*16+l))$fatal(1,"topk exact ordered ID addr%0d lane%0d got%h",a,l,wd4[b*512+l*32+:32]);
    count=count+1;
   end
   writes<=writes+count;write_packets<=write_packets+1;
  end
  if(started&&!busy && (pend[2]||dma.write_debt||dma.tq_count!=0))$fatal(1,"caller retired accepted unwritten work");
 end
 task init_words(input integer base,input integer count,input integer tk);
 begin
  for(integer w=0;w<count;w=w+4)begin
   @(negedge fast_clk);me_en=15;me_mask={64{1'b1}};
   for(integer b=0;b<4;b=b+1)begin me_a[b*30+:30]=base+w+b;me_d[b*512+:512]=payload(0,w+b,tk);end
   do @(posedge fast_clk);while(!wr[0]);@(negedge fast_clk);me_en=0;wait(vis[0]);@(negedge fast_clk);
  end
 end endtask
 initial begin
  repeat(5)@(negedge slow_clk);cold_n=1;fast_rst_n=1;slow_rst_n=1;
  // Pad initialization to a full four-word packet; caller still reads exact266 words.
  init_words(SRC,268,0);
  @(negedge fast_clk);go=1;@(negedge fast_clk);go=0;started=1;allow_write=0;
  wait(holds>0);repeat(8)@(negedge fast_clk);allow_write=1;
  wait(!busy);@(negedge fast_clk);started=0;
  if(reads!=266||sent!=266||writes!=1064||wi!=1064||wo!=266||holds==0)$fatal(1,"gather counts read%0d sent%0d writes%0d",reads,sent,writes);
  wait(debt==0);$display("PASS DMA_GATHER_NATIVE words=266 writes=1064 reads=266 visible_retirement=1 held=%0d",holds);
  init_words(5000,256,1); // score words, followed by local-ID words at5128.
  @(negedge fast_clk);topk=1;src=5000;ibase=5128;n=128;dst=10000;sent=0;reads=0;before_writes=writes;allow_write=0;go=1;
  @(negedge fast_clk);go=0;started=1;
  wait(dma.tk_done);@(negedge fast_clk);
  if(dma.tq_count!=128||!busy)$fatal(1,"full retainedK8192 queue not reserved count%0d",dma.tq_count);
  repeat(8)@(negedge fast_clk);allow_write=1;
  wait(!busy);@(negedge fast_clk);started=0;wait(debt==0);
  if(reads!=256||sent!=256||writes-before_writes!=512||maxq!=128)$fatal(1,"topk counts read%0d sent%0d writes%0d maxq%0d",reads,sent,writes-before_writes,maxq);
  $display("PASS DMA_TOPK_NATIVE K=8192 NMAX=2048 queue=128 output_words=512 read_words=256 exact_order=1 visible_retirement=1");$finish;
 end
 initial begin repeat(2000000)@(posedge fast_clk);$fatal(1,"finite modeled service made no progress");end
endmodule
`default_nettype wire
