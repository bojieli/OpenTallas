`timescale 1ns/1ps
// Tiny changed-component test. Borrowed checked port / publication are fixture
// authorities, NOT production provider qualification or a full index replay.
module tb_hbm_index_order_adapter;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0,start=0;
 wire sr,retained,rv,rrsp,lv,lid,loaded,done,fault,release_r;
 wire [31:0] hj;wire [3:0] hg;wire [19:0] hp;
 wire[6:0]rank;wire[5:0]wordidx;wire[15:0]tag;
 reg[31:0]rj=32'h12345678;reg[3:0]rg=4'hb;reg[19:0]rp=20'hfffff;
 reg rspv=0;reg[511:0]pairs;reg[6:0]rsprank;reg[5:0]rspword;reg[15:0]rsptag;
 reg pub=0,rev=0,releasev=0;
 integer cyc=0,readcount=0,loadcount=0,caseid=0,delayleft=0;
 wire loadpermit=cyc%7!=0;
 wire readready=cyc%5!=0&&!rspv&&delayleft==0;
 wire[0:0]lr,lw;wire[511:0]ld;
 reg merger_done=0,go=0;wire mbusy,mdone,mfault,ov,ol;
 wire [0:0]onw;wire[511:0]odata;wire[31:0]stats;
 reg[5:0]kval=1;
 ot_hbm_accel_index_order_adapter #(.ENABLE(1),.N(2),.NPER(16)) dut(
 .clk(clk),.por_n(por_n),.start(start),.start_ready(sr),
 .source_job(32'h12345678),.source_gen(4'hb),.source_pos(20'hfffff),
 .gather_exclusive(1'b1),.gather_writers_drained(1'b1),.result_capacity_reserved(1'b1),
 .retained(retained),.held_job(hj),.held_gen(hg),.held_pos(hp),
 .read_v(rv),.read_r(readready),.read_rank(rank),.read_word(wordidx),.read_tag(tag),
 .rsp_v(rspv),.rsp_r(rrsp),.rsp_pairs(pairs),.rsp_job(rj),.rsp_gen(rg),.rsp_pos(rp),
 .rsp_rank(rsprank),.rsp_word(rspword),.rsp_tag(rsptag),.rsp_checked(1'b1),.rsp_uncorrectable(1'b0),
 .merger_load_permit(loadpermit),.ld_valid(lv),.ld_id(lid),.ld_rank(lr),.ld_word(lw),.ld_data(ld),
 .ordered_loaded(loaded),.merger_done(merger_done),.release_v(releasev),.release_r(release_r),
 .release_job(32'h12345678),.release_gen(4'hb),.release_pos(20'hfffff),
 .result_published(pub),.source_reverse_done(rev),.done(done),.fault(fault));
 ot_coll_topk_merge #(.N(2),.NMAX(16),.P(16),.PF(16)) merger(
 .clk(clk),.rst_n(por_n),.ld_valid(lv),.ld_id(lid),.ld_rank(lr),.ld_word(lw),.ld_data(ld),
 .go(go),.n(6'd16),.k(kval),.stride(32'b0),.busy(mbusy),.done(mdone),.fault(mfault),
 .out_valid(ov),.out_nw(onw),.out_data(odata),.out_last(ol),.stat_cycles(stats));
 integer expected_id,slot,prev=-1,outseen=0;
 function automatic[511:0] payload(input integer r,input integer w);
  reg[511:0] x;integer z,id;begin
   x=0;
   for(z=0;z<8;z=z+1)begin
    id=8*(96*((r==0?1:0)+w)+r)+z;
    x[64*z+32+:32]=id;
    x[64*z+:32]=(w==0&&z==0)?32'h3f800000:32'h3f000000;
   end
   payload=x;
  end
 endfunction
 always @(posedge clk)begin
  cyc<=cyc+1;
  if(por_n)begin
   if(rv&&readready)begin
    pairs<=payload(rank,wordidx);rsprank<=rank;rspword<=wordidx;rsptag<=tag;
    delayleft<=3;readcount<=readcount+1;
   end else if(delayleft>0)begin
    delayleft<=delayleft-1;if(delayleft==1)rspv<=1;
   end
   if(rspv&&rrsp)rspv<=0;
   if(lv)begin
    loadcount<=loadcount+1;
    if(lid)for(slot=0;slot<16;slot=slot+1)begin
     expected_id=ld[32*slot+:32];
     if(expected_id<=prev)$fatal(1,"noncanonical ID order %0d <= %0d",expected_id,prev);
     prev=expected_id;
    end
   end
   if(ov)begin
    if(odata[31:0]!=8)$fatal(1,"equal-score lower-ID failure: %0d",odata[31:0]);
    if(kval==2&&odata[63:32]!=768)$fatal(1,"ascending second-ID failure");
    outseen<=outseen+1;
   end
   if(mdone)merger_done<=1;
   if(caseid<2&&fault)$fatal(1,"unexpected adapter fault");
   if(mfault)$fatal(1,"unchanged W15 merger fault");
  end
 end
 task automatic reset_case;
 begin
  @(negedge clk);por_n=0;start=0;rspv=0;delayleft=0;readcount=0;loadcount=0;
  prev=-1;outseen=0;pub=0;rev=0;releasev=0;merger_done=0;go=0;rg=4'hb;
  repeat(3)@(negedge clk);por_n=1;@(negedge clk);start=1;
  @(negedge clk);start=0;
 end endtask
 initial begin
  for(caseid=0;caseid<2;caseid=caseid+1)begin
   kval=caseid+1;reset_case();wait(loaded);@(negedge clk);go=1;
   @(negedge clk);go=0;wait(mdone);@(negedge clk);
   if(readcount!=4||loadcount!=4||outseen!=1)$fatal(1,"finite source counts %0d %0d %0d",readcount,loadcount,outseen);
   releasev=1;repeat(3)@(negedge clk);
   if(!retained||release_r)$fatal(1,"premature release before publication");
   pub=1;repeat(3)@(negedge clk);
   if(!retained||release_r)$fatal(1,"premature release before reverse");
   rev=1;wait(done);@(negedge clk);releasev=0;
   if(retained)$fatal(1,"matched terminal did not release");
   $display("PASS_ORDERED_W15_TIE k=%0d ID8_before768 reads4 loads4",kval);
  end
  caseid=2;reset_case();rg=4'ha;wait(rspv);@(negedge clk);
  if(rrsp)$fatal(1,"foreign generation ACK");
  wait(fault);repeat(3)@(negedge clk);
  if(!retained||rrsp||lv)$fatal(1,"foreign response lost retained debt");
  $display("PASS_ORDERED_FOREIGN_GENERATION_HELD");
  $display("PASS_INDEX_ORDER_ADAPTER_COMPONENT_ONLY");$finish;
 end
endmodule
