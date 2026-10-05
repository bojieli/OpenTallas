`timescale 1ns/1ps
// Full actual N96/n512 component, unchanged arithmetic/selector. The source is
// a frozen, SECDED-checked plane-major fixture, not a production VM provider.
module tb_hbm_index_w15_full96;
 localparam integer N=96,NPER=512,TOTAL=N*NPER,WORDS=6144,BASE_ID=999424;
 localparam [31:0] BASE=32'h00010000,JOB=32'hfedcba98;
 localparam [3:0] GEN=4'hf;
 localparam [19:0] POS=20'hfffff;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0,start=0;
 reg [31:0] live_job=JOB;reg[3:0]live_gen=GEN;reg[19:0]live_pos=POS;
 wire sr,fsv,retained,fret,rv,fr,rspv,rrsp,fault,ffault,loaded,done;
 wire [31:0] hj;wire[3:0]hg;wire[19:0]hp;
 wire[6:0]rank;wire[5:0]wordidx;wire[15:0]tag;
 wire[511:0]pairs;wire[31:0]pj;wire[3:0]pg;wire[19:0]pp;
 wire[6:0]prank;wire[5:0]pword;wire[15:0]ptag;wire pchecked,pue;
 wire rawv,rawready,rawid,rawrr;
 wire[31:0]ra,rawjob;wire[3:0]rawgen;wire[19:0]rawpos;
 wire[6:0]rawrank;wire[15:0]rawtag;
 reg rawrspv=0,rawrspid=0,rawchecked=0,rawue=0;
 reg[511:0]rawdata=0;
 reg[31:0]raddr=0,rjob=0;reg[3:0]rgen=0;reg[19:0]rpos=0;
 reg[6:0]rrank=0;reg[15:0]rtag=0;
 reg pub=0,rev=0,releasev=0;wire frelease_r,release_r;
 reg grant=0,lease=0,sink_reserved=0,writers_drained=0;
 integer cyc=0,readcount=0,loadcount=0,loaded_ids=0,outcount=0,delayleft=0;
 integer mode=0,slots_pending=0,rank95reads=0,stall_edges=0;
 wire loadpermit=grant&&cyc%11!=0&&cyc%13!=0;
 assign rawready=grant&&cyc%5!=0&&!rawrspv&&delayleft==0;
 wire lv,lid;wire[6:0]lr;wire[11:0]lw;wire[511:0]ld;
 reg go=0;wire mbusy,mdone,mfault,ov,ol;wire[0:0]onw;
 wire[511:0]odata;wire[31:0]stats;
 reg[31:0]actual_result[0:511];
 reg[6143:0]load_seen=0;
 reg[71:0]source_code[0:WORDS-1][0:7];
 import ot_gpu_w6_secded_pkg::*;
 ot_hbm_accel_index_w15_planemajor_formatter #(.ENABLE(1),.N(N),.NPER(NPER)) fmt(
 .clk(clk),.por_n(por_n),.start(start),.start_ready(fsv),
 .source_job(live_job),.source_gen(live_gen),.source_pos(live_pos),
 .gather_base(BASE),.gather_limit(33'h11800),.gather_exclusive(lease),.gather_writers_drained(writers_drained),
 .retained(fret),.fault(ffault),.pair_v(rv),.pair_r(fr),.pair_job(hj),.pair_gen(hg),.pair_pos(hp),
 .pair_rank(rank),.pair_word(wordidx),.pair_tag(tag),
 .pairs_v(rspv),.pairs_r(rrsp),.pairs(pairs),.pairs_job(pj),.pairs_gen(pg),.pairs_pos(pp),
 .pairs_rank(prank),.pairs_word(pword),.pairs_tag(ptag),.pairs_checked(pchecked),.pairs_uncorrectable(pue),
 .read_v(rawv),.read_r(rawready),.read_addr(ra),.read_id(rawid),.read_rank(rawrank),.read_tag(rawtag),
 .read_job(rawjob),.read_gen(rawgen),.read_pos(rawpos),
 .rsp_v(rawrspv),.rsp_r(rawrr),.rsp_data(rawdata),.rsp_addr(raddr),.rsp_id(rawrspid),
 .rsp_rank(rrank),.rsp_tag(rtag),.rsp_job(rjob),.rsp_gen(rgen),.rsp_pos(rpos),
 .rsp_checked(rawchecked),.rsp_uncorrectable(rawue),
 .release_v(releasev),.release_r(frelease_r),.release_job(JOB),.release_gen(GEN),.release_pos(POS),
 .publication_done(pub),.source_reverse_done(rev));
 ot_hbm_accel_index_order_adapter #(.ENABLE(1),.N(N),.NPER(NPER)) dut(
 .clk(clk),.por_n(por_n),.start(start),.start_ready(sr),
 .source_job(live_job),.source_gen(live_gen),.source_pos(live_pos),
 .gather_exclusive(lease),.gather_writers_drained(writers_drained),.result_capacity_reserved(sink_reserved),
 .retained(retained),.held_job(hj),.held_gen(hg),.held_pos(hp),
 .read_v(rv),.read_r(fr),.read_rank(rank),.read_word(wordidx),.read_tag(tag),
 .rsp_v(rspv),.rsp_r(rrsp),.rsp_pairs(pairs),.rsp_job(pj),.rsp_gen(pg),.rsp_pos(pp),
 .rsp_rank(prank),.rsp_word(pword),.rsp_tag(ptag),.rsp_checked(pchecked),.rsp_uncorrectable(pue),
 .merger_load_permit(loadpermit),.ld_valid(lv),.ld_id(lid),.ld_rank(lr),.ld_word(lw),.ld_data(ld),
 .ordered_loaded(loaded),.merger_done(mdone),.release_v(releasev),.release_r(release_r),
 .release_job(JOB),.release_gen(GEN),.release_pos(POS),
 .result_published(pub),.source_reverse_done(rev),.done(done),.fault(fault));
 // Original selector, no software done/selected data and no altered tie logic.
 ot_coll_topk_merge #(.N(N),.NMAX(NPER),.P(64),.PF(16)) merger(
 .clk(clk),.rst_n(por_n),.ld_valid(lv),.ld_id(lid),.ld_rank(lr),.ld_word(lw),.ld_data(ld),
 .go(go),.n(16'd512),.k(16'd512),.stride(32'b0),.busy(mbusy),.done(mdone),.fault(mfault),
 .out_valid(ov),.out_nw(onw),.out_data(odata),.out_last(ol),.stat_cycles(stats));
 integer i,j,r,w,l,b,id,ix;
 reg[511:0]sword,iword;
 initial begin
  // Every literal ID in [999424,1048575] occurs ONCE. Rank-major order is wrong:
  // rank0 starts999936, while rank32..95 own999424..999935. All scores +1, so
  // lower-global-ID tie rule MUST select first512, including all8 rank95 IDs.
  for(r=0;r<N;r=r+1)for(w=0;w<32;w=w+1)begin
   sword=0;iword=0;
   for(l=0;l<16;l=l+1)begin
    b=(r<32?1302:1301)+(16*w+l)/8;
    id=8*(96*b+r)+(l%8);
    sword[32*l+:32]=32'h3f800000;iword[32*l+:32]=id;
   end
   for(l=0;l<8;l=l+1)begin
    source_code[r*32+w][l]=encode64(sword[64*l+:64]);
    source_code[3072+r*32+w][l]=encode64(iword[64*l+:64]);
   end
  end
 end
 integer read_index,load_index,z;
 reg[65:0]decoded;
 reg[511:0]pending_data;
 reg pending_checked,pending_ue;
 reg[31:0]last_ra;reg last_kind;
 reg[6:0]last_rrank;reg[15:0]last_rtag;
 reg held_read=0,held_reply=0,held_load=0;
 reg[511:0]last_data,last_ld;
 reg[31:0]last_job;reg[3:0]last_gen;reg[19:0]last_pos;
 reg[6:0]last_lrank;reg[11:0]last_lword;reg last_lid;
 always @(posedge clk)begin
  cyc<=cyc+1;
  if(por_n)begin
   if(mode==0&&(fault||ffault||mfault))$fatal(1,"unexpected connected fault atcycle%0d",cyc);
   if(retained&&(hj!=JOB||hg!=GEN||hp!=POS))$fatal(1,"held full source tuple changed");
   if(held_read&&rawv&&{ra,rawid,rawrank,rawtag,rawjob,rawgen,rawpos}!={last_ra,last_kind,last_rrank,last_rtag,last_job,last_gen,last_pos})
    $fatal(1,"request changed under backpressure");
   held_read<=rawv&&!rawready;
   last_ra<=ra;last_kind<=rawid;last_rrank<=rawrank;last_rtag<=rawtag;last_job<=rawjob;last_gen<=rawgen;last_pos<=rawpos;
   if(held_reply&&rawrspv&&rawdata!=last_data)$fatal(1,"reply changed while held");
   held_reply<=rawrspv&&!rawrr;last_data<=rawdata;
   if(held_load&&{ld,lr,lw,lid}!={last_ld,last_lrank,last_lword,last_lid})$fatal(1,"W15 load changed under backpressure");
   held_load<=(dut.enabled.state==5||dut.enabled.state==6)&&!loadpermit;
   last_ld<=ld;last_lrank<=lr;last_lword<=lw;last_lid<=lid;
   if(rawv&&!rawready)stall_edges<=stall_edges+1;
   if(rawv&&rawready)begin
    if(slots_pending!=0||rawrspv)$fatal(1,"more than one provider read outstanding");
    if(rawjob!=JOB||rawgen!=GEN||rawpos!=POS)$fatal(1,"provider full32 job/gen/position narrowing");
    if(ra!=BASE+rawrank*32+(wordidx>>1)+(rawid?3072:0))$fatal(1,"plane-major address/rank/stride mismatch");
    read_index=ra-BASE;
    if(read_index<0||read_index>=6144)$fatal(1,"read outside real allocated fixture extent");
    pending_data=0;pending_checked=1;pending_ue=0;
    for(z=0;z<8;z=z+1)begin
     decoded=decode64(source_code[read_index][z]);
     pending_data[64*z+:64]=decoded[63:0];pending_ue=pending_ue||decoded[65];
    end
    rawdata<=pending_data;rawchecked<=pending_checked&&!pending_ue;rawue<=pending_ue;
    raddr<=ra;rawrspid<=rawid;rrank<=rawrank;rtag<=rawtag;rjob<=rawjob;rgen<=rawgen;rpos<=rawpos;
    if(mode==1)rjob<=rawjob^32'h80000000;
    if(mode==2)rgen<=rawgen^4'h8;
    if(mode==3)rrank<=rawrank^7'h40;
    delayleft<=3+(rawtag%4);slots_pending<=1;readcount<=readcount+1;
    if(rawrank==95)rank95reads<=rank95reads+1;
   end else if(delayleft>0)begin
    delayleft<=delayleft-1;if(delayleft==1)rawrspv<=1;
   end
   if(rawrspv&&rawrr)begin
    if(mode!=0)$fatal(1,"foreign provider tuple ACKed");
    rawrspv<=0;slots_pending<=0;
   end
   if(lv)begin
    load_index=lr*64+(lid?32:0)+lw;
    if(lr>=96||lw>=32||load_index>=6144||load_seen[load_index])$fatal(1,"duplicate/out-of-range logical load");
    load_seen[load_index]=1;loadcount<=loadcount+1;
    if(lid)begin
     for(z=0;z<16;z=z+1)
      if(ld[32*z+:32]!=BASE_ID+loaded_ids+z)$fatal(1,"canonical full ID sequence mismatch at%0d got%0d expected%0d",loaded_ids+z,ld[32*z+:32],BASE_ID+loaded_ids+z);
     loaded_ids<=loaded_ids+16;
    end
   end
   if(ov)begin
    if(!sink_reserved||onw!=1||outcount+16>512)$fatal(1,"unreserved no-ready output/overflow");
    for(z=0;z<16;z=z+1)begin
     actual_result[outcount+z]<=odata[32*z+:32];
     if(odata[32*z+:32]!=BASE_ID+outcount+z)$fatal(1,"full512 numerical ID mismatch at%0d got%0d",outcount+z,odata[32*z+:32]);
    end
    if(ol!=(outcount+16==512))$fatal(1,"wrong actual last output");
    outcount<=outcount+16;
   end
  end else begin
   held_read<=0;held_reply<=0;held_load<=0;
  end
 end
 task automatic cold_case;
 begin
  @(negedge clk);por_n=0;start=0;rawrspv=0;delayleft=0;slots_pending=0;
  readcount=0;loadcount=0;loaded_ids=0;outcount=0;rank95reads=0;load_seen=0;
  pub=0;rev=0;releasev=0;go=0;grant=0;lease=1;sink_reserved=1;writers_drained=1;
  live_job=JOB;live_gen=GEN;live_pos=POS;
  repeat(3)@(negedge clk);por_n=1;
  @(negedge clk);if(!sr||!fsv)$fatal(1,"missing real fixture admission");start=1;
  @(negedge clk);start=0;grant=1;
  // Descriptor pins may change AFTER accepted source edge. Captured owner cannot.
  live_job=32'h01234567;live_gen=0;live_pos=0;
 end endtask
 initial begin
  cold_case();wait(loaded);@(negedge clk);
  if(readcount!=12288||loadcount!=6144||loaded_ids!=49152||rank95reads!=128||slots_pending!=0)
   $fatal(1,"full finite counts failed reads%0d loads%0d IDs%0d rank95%0d debt%0d",readcount,loadcount,loaded_ids,rank95reads,slots_pending);
  if(load_seen!={6144{1'b1}})$fatal(1,"missing real W15 source load");
  $display("PASS_FULL96_INPUT reads=%0d loads=%0d IDs=%0d rank95reads=%0d cycle=%0d",readcount,loadcount,loaded_ids,rank95reads,cyc);
  go=1;@(negedge clk);go=0;wait(mdone);@(negedge clk);
  if(outcount!=512)$fatal(1,"actual selector did not emit512 IDs");
  for(i=0;i<512;i=i+1)if(actual_result[i]!=BASE_ID+i)$fatal(1,"actual sink512 comparison failed");
  $display("PASS_FULL96_SELECT512 first=%0d last=%0d W15cycles=%0d cycle=%0d",actual_result[0],actual_result[511],stats,cyc);
  releasev=1;repeat(5)@(negedge clk);
  if(!retained||!fret||release_r||frelease_r)$fatal(1,"release on mere mergerdone");
  pub=1;repeat(5)@(negedge clk);
  if(!retained||!fret||release_r||frelease_r)$fatal(1,"release without positive reverse");
  rev=1;wait(done);@(negedge clk);releasev=0;
  if(retained||fret||stall_edges==0)$fatal(1,"terminal release/backpressure test failed");
  $display("PASS_FULL96_PUBLICATION_REVERSE_HELD stalls=%0d",stall_edges);
  // Early foreign replies are independent cold component cases; no second full
  // numeric pass and no claimed live-reset/rearm recovery.
  for(mode=1;mode<=3;mode=mode+1)begin
   cold_case();wait(rawrspv);@(negedge clk);
   if(rawrr)$fatal(1,"foreign full32job/gen/rank ACK");
   wait(ffault);repeat(5)@(negedge clk);
   if(rawrr||lv||!retained||!fret||slots_pending!=1)$fatal(1,"foreign read debt not retained");
   $display("PASS_FULL96_FOREIGN_NOACK kind=%0d",mode);
  end
  $display("PASS_W15_FULL96_512_COMPONENT_ONLY");$finish;
 end
endmodule
