// Same-process continuation. Only actual Noether publications enter the DUT.
// Sink gold is read-only; Gauss owns numerical consumer and kind4 RTL writer.
struct FormatterFixture {
 std::array<std::vector<Row>,2> plane;
 std::vector<Row> sink,descriptor,cfg;
 std::vector<std::array<uint32_t,4>> records;
 explicit FormatterFixture(const std::filesystem::path& dir):
  plane{hex(dir/"scores.mem",3072,512),hex(dir/"ids.mem",3072,512)},
  sink(hex(dir/"sink_gold.mem",32,512)),descriptor(hex(dir/"descriptor.mem",8,64)),
  cfg(hex(dir/"formatter.cfg",8,32)){
  require(std::filesystem::exists(dir/"formatter_fixture.json"),"pinned formatter preparation required");
  require(cfg[2][0]>0&&cfg[5][0]==20&&cfg[6][0]==20&&!cfg[7][0],"selected formatter phase/entry/aperture differs");
  std::ifstream f(dir/"records.mem");std::array<uint32_t,4> r{};
  while(f>>std::hex>>r[0]>>r[1]>>r[2]>>r[3])records.push_back(r);
  require(f.eof()&&records.size()==192+cfg[3][0],"actual installed span-record census differs");
 }
};

// Checker invoked on the PRE-edge accepted bus values. No return-ready,
// selected-ID data or publication offer is driven by this comparison.
template<class D> static void check_formatter_edge(const D& d,const FormatterFixture& f){
 if(d.fixture_formatter_consumer_v&&d.fixture_formatter_consumer_r){
  const auto& p=d.fixture_formatter_consumer_pairs;
  require(bits(p,1,1)&&!bits(p,0,1),"formatter accepted unchecked/UE payload");
  const auto& owner=d.fixture_formatter_consumer_frame;
  require(bits(owner,0,32)==0x9234abcf&&bits(owner,32,4)==11&&bits(owner,36,17)==0x10003&&bits(owner,53,20)==0xfffff&&
   bits(p,567,32)==0x9234abcf&&bits(p,563,4)==11&&bits(p,543,20)==0xfffff,"accepted formatter full73 owner changed");
  unsigned rank=bits(p,536,7),word=bits(p,530,6);
  require(rank<96&&word<64,"formatter accepted rank/word extent differs");
  for(unsigned lane=0;lane<8;++lane){unsigned offset=8*(word%2)+lane;
   require(bits(p,2+64*lane,32)==f.plane[0][rank*32+word/2][offset]&&
           bits(p,34+64*lane,32)==f.plane[1][rank*32+word/2][offset],
           "formatter accepted actual source pair differs");
  }
 }
 if((d.gather_rsp_v&1)&&(d.gather_rsp_r&1)&&bits(d.gather_rsp,1,3)==4){
  require(bits(d.gather_rsp,0,1),"actual selected sink response unchecked");
  require(bits(d.gather_rsp,564,32)==0x9234abcf&&bits(d.gather_rsp,596,4)==11&&
   bits(d.gather_rsp,600,17)==0x10003&&bits(d.gather_rsp,617,20)==0xfffff,"actual sink checked full73 differs");
  const auto addr=bits(d.gather_rsp,20,32);
  const auto base=f.descriptor[3][0],end=f.descriptor[3][1];
  require(addr>=base&&addr<end&&(addr%64)==0,"actual sink response address differs");
  const auto row=(addr-base)/64;
  for(unsigned k=0;k<16;++k)require(bits(d.gather_rsp,52+32*k,32)==f.sink[row][k],
   "actual checked sink readback differs from saved independent global512");
 }
}

static void run_formatter_source_next(Sim& s,const FormatterFixture& f){
 auto& d=s.dut;unsigned sink_checked=0;std::array<bool,32> sink_seen{};
 require(d.fixture_formatter_configuration_valid,"new formatter graph must select preinstall/direct-source-replay; preserve existing norm graph");
 for(unsigned i=0;i<8;++i)for(unsigned k=0;k<2;++k)
  require(bits(d.fixture_formatter_descriptor,64*i+32*k,32)==f.descriptor[i][k],"compiled helper geometry differs from actual installed recipe");
 s.preedge_observer=[&]{
  check_formatter_edge(d,f);
  if((d.gather_rsp_v&1)&&(d.gather_rsp_r&1)&&bits(d.gather_rsp,1,3)==4){
   unsigned row=(bits(d.gather_rsp,20,32)-f.descriptor[3][0])/64;
   require(row<32&&!sink_seen[row],"duplicate actual sink publication");sink_seen[row]=true;++sink_checked;
  }
 };
 constexpr uint32_t FJ=0x9234abcf,FG=11,FT=0x10003,FP=0xfffff;
 auto F=[](auto& p,bool foreign=false){put(p,0,32,FJ);put(p,32,4,FG);put(p,36,17,FT^(foreign?0x10000:0));put(p,53,20,FP);};
 auto O=[](const auto& p){return bits(p,0,32)==FJ&&bits(p,32,4)==FG&&bits(p,36,17)==FT&&bits(p,53,20)==FP;};
 s.neg();d.cp_reset_req=0;s.phase="formatter next actual CP reset release";
 s.wait([&]{return (d.db_rdy&1)!=0;});
 require(!(d.norm_retained&1)&&!(d.sfu_retained&1)&&!(d.sfu_vm_retained&1),"previous native owner debt remains");
 const auto old_db=d.fixture_db_accepts;
 s.neg();d.fixture_formatter_enable=1;d.cmd_we=1;put(d.cmd_addr,0,8,0);
 put(d.cmd_wdata,0,32,0);put(d.cmd_wdata,32,32,0x20000000);s.sm();s.neg();d.cmd_we=0;
 put(d.db_token,0,17,FT);put(d.db_pos,0,20,FP);put(d.db_job,0,32,FJ);put(d.db_generation,0,4,FG);
 d.db_v=1;s.phase="formatter distinct real CP context";
 s.wait([&]{return d.fixture_db_accepts==old_db+1;});s.neg();d.db_v=0;
 for(unsigned index=0;index<8;++index){
  s.neg();put(d.gather_desc_index,0,3,index);put(d.gather_desc_data,0,32,f.descriptor[index][0]);
  put(d.gather_desc_data,32,32,f.descriptor[index][1]);d.gather_desc_v=1;
  s.phase="formatter actual protected descriptor commit";
  const auto old=d.fixture_formatter_desc_accepts;
  s.wait([&]{return d.fixture_formatter_desc_accepts==old+1;});s.neg();d.gather_desc_v=0;
 }
 put(d.preinstall_score_base,0,32,f.cfg[0][0]);put(d.preinstall_id_base,0,32,f.cfg[1][0]);
 put(d.preinstall_capacity,0,32,f.cfg[2][0]);put(d.preinstall_capacity,32,1,0);
 put(d.preinstall_occupied_records,0,8,f.cfg[3][0]);
 put(d.preinstall_layer,0,5,20);put(d.preinstall_candidate_source_layer,0,5,20);d.preinstall_candidate_masked=0;
 // One integration negative: the incoming high TOKEN17 cannot acquire the
 // actual current CP borrower or publish a book under a foreign frame.
 s.neg();F(d.preinstall_begin_frame,true);d.preinstall_begin_v=1;s.settle();
 for(unsigned i=0;i<3;++i){require(!(d.preinstall_begin_r&1),"foreign formatter preinstall ready");s.sm();s.healthy();
  require(!(d.preinstall_retained&1)&&d.fixture_formatter_reservations==0&&d.fixture_formatter_source_accepts==0,"foreign preinstall acquired/published owner");}
 s.neg();F(d.preinstall_begin_frame);s.phase="formatter actual full73 preinstall admission";
 const auto old_begin=d.fixture_formatter_begin_accepts;
 s.wait([&]{return d.fixture_formatter_begin_accepts==old_begin+1;});s.neg();d.preinstall_begin_v=0;
 require((d.preinstall_retained&1)&&O(d.preinstall_frame),"accepted formatter owner not retained");
 F(d.preinstall_record_frame);
 for(const auto& record:f.records){s.neg();put(d.preinstall_record_kind,0,2,record[0]);
  put(d.preinstall_record_rank,0,7,record[1]);put(d.preinstall_record_base,0,32,record[2]);put(d.preinstall_record_end,0,32,record[3]);
  d.preinstall_record_v=1;s.phase="formatter actual installed span census";
  const auto old=d.fixture_formatter_record_accepts;
  s.wait([&]{return d.fixture_formatter_record_accepts==old+1;});s.neg();d.preinstall_record_v=0;
 }
 F(d.preinstall_source_frame);
 for(unsigned plane=0;plane<2;++plane)for(unsigned word=0;word<32;++word)for(unsigned rank=0;rank<96;++rank){
  unsigned ordinal=plane*3072+word*96+rank;
  s.neg();put(d.preinstall_source_plane,0,1,plane);put(d.preinstall_source_word,0,5,word);put(d.preinstall_source_rank,0,7,rank);
  for(unsigned k=0;k<16;++k)put(d.preinstall_source_data,32*k,32,f.plane[plane][rank*32+word][k]);
  d.preinstall_source_v=1;s.phase="formatter Noether accepted source word="+std::to_string(ordinal);
  s.wait([&]{return d.fixture_formatter_source_accepts==ordinal+1;});s.neg();d.preinstall_source_v=0;
  s.wait([&]{return (d.preinstall_source_ACK_v&1)!=0;});
  for(unsigned hold=0;hold<3;++hold){
   require(O(d.preinstall_source_ACK_frame)&&bits(d.preinstall_source_ACK_rank,0,7)==rank&&
    bits(d.preinstall_source_ACK_plane,0,1)==plane&&bits(d.preinstall_source_ACK_word,0,5)==word&&
    (d.preinstall_retained&1)&&O(d.preinstall_frame)&&!d.fixture_formatter_reservations,
    "held actual preinstall ACK/full73/source census changed");s.sm();s.healthy();
  }
  s.neg();d.preinstall_source_ACK_r=1;s.wait([&]{return d.fixture_formatter_source_ACKs==ordinal+1;});s.neg();d.preinstall_source_ACK_r=0;
 }
 s.phase="formatter real checked exclusive reservation receipt";
 s.wait([&]{return d.fixture_formatter_reservations==1;});
 require(d.fixture_formatter_source_accepts==6144&&d.fixture_formatter_source_ACKs==6144,
  "reservation published before all actual checked source ACKs");
 s.neg();const auto old_go=d.fixture_formatter_go_accepts;d.fixture_formatter_go=1;
 s.wait([&]{return d.fixture_formatter_go_accepts==old_go+1;});s.neg();d.fixture_formatter_go=0;s.wait([&]{return (d.gather_retained&1)!=0;});
 // Replay ACTUAL accepted native producer words as the gather's source stream.
 // The original bridge's kind0 aperture is only2KiB per local plane; this does
 // not claim a full-plane HBM kind0 read path. Every arena store gets its own
 // two-sector writes/readbacks and checked full73 return in the actual parent.
 for(unsigned plane=0;plane<2;++plane)for(unsigned word=0;word<32;++word)for(unsigned rank=0;rank<96;++rank){
  s.neg();zero(d.gather_req);put(d.gather_req,0,3,plane+1);
  uint32_t addr=f.descriptor[2][0]+plane*196608+rank*2048+word*64;
  uint32_t tag=plane*3072+word*96+rank;
  put(d.gather_req,3,32,addr);put(d.gather_req,35,16,tag);put(d.gather_req,51,7,rank);put(d.gather_req,58,6,word);
  for(unsigned k=0;k<16;++k)put(d.gather_req,64+32*k,32,f.plane[plane][rank*32+word][k]);
  put(d.gather_req,576,32,FJ);put(d.gather_req,608,4,FG);put(d.gather_req,612,17,FT);put(d.gather_req,629,20,FP);
  auto accepted=d.fixture_formatter_mem_requests;d.gather_req_v=1;s.phase="formatter actual arena store";
  s.wait([&]{return d.fixture_formatter_mem_requests==accepted+1;});s.neg();d.gather_req_v=0;
  s.wait([&]{return (d.gather_rsp_v&1)!=0;});
  require(bits(d.gather_rsp,0,1)&&bits(d.gather_rsp,1,3)==plane+1&&bits(d.gather_rsp,4,16)==tag&&bits(d.gather_rsp,20,32)==addr&&
   bits(d.gather_rsp,564,32)==FJ&&bits(d.gather_rsp,596,4)==FG&&bits(d.gather_rsp,600,17)==FT&&bits(d.gather_rsp,617,20)==FP,
   "arena checked actual response/frame differs");
  for(unsigned k=0;k<16;++k)require(bits(d.gather_rsp,52+32*k,32)==f.plane[plane][rank*32+word][k],"actual arena write readback differs");
  auto returned=d.fixture_formatter_mem_returns;s.neg();d.gather_rsp_r=1;
  s.wait([&]{return d.fixture_formatter_mem_returns==returned+1;});s.neg();d.gather_rsp_r=0;
 }
 require((d.gather_arena_visible&1)&&d.fixture_formatter_mem_returns==6144,"actual complete arena not published");
 // Gauss is sole numerical child/writer. Its literal header is required before
 // this wait can complete. No CPP pair query, ready tie, kind4 payload, source
 // reverse or release offer stands in for that child.
 s.phase="Gauss actual6144 consumer returns,32 checked sink stores and reverse drain";
 s.wait([&]{return d.fixture_formatter_pairs==6144&&(d.gather_sink_visible&1)&&d.fixture_formatter_reverses==1;});
 require(sink_checked==32,"all actual checked golden sink returns required before retirement");
 s.phase="actual formatter/gather/shared borrower retirement";
 s.wait([&]{return !(d.fixture_formatter_retained&1)&&!(d.gather_retained&1)&&!(d.preinstall_retained&1);});
 // END is a context terminal, not Jason's numerical RESULT and not a token.
 s.wait([&]{return (d.cpl_v&1)!=0;});
 require(bits(d.cpl_data,37,4)==2,"formatter stage context status differs");
 auto old_cpl=d.fixture_cpl_accepts;s.neg();d.cpl_rdy=1;
 s.wait([&]{return d.fixture_cpl_accepts==old_cpl+1;});s.neg();d.cpl_rdy=0;
 s.preedge_observer={};
 std::cout<<"PARENT_FORMATTER_STAGE_PASS source_ACK=6144 arena_checked=6144 consumer_returns=6144 sink_checked=32 full73_refusal=1 reverse_checked=1 source_phase=L20.op14.index_scores.pre_candidate_mask.local_top512 token_qualified=0 physical_qualified=0 cycles="<<s.cycles<<"\n";
}
