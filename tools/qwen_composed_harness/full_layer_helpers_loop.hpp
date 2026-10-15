#pragma once
#include "layer_models.hpp"
#include "native59_helpers.hpp"
#include "host_owner.hpp"
#include "embedding_owner.hpp"
#include "rank_parallel.hpp"
#include <chrono>
#include <iostream>
#include <functional>
// Startup/HC and HOST drain inputs are supplied by the actual owner. There is
// no default producer and no synthetic cohort-ready or terminal-ready value.
// Shared clock state lets a caller continue the identical CORE/HBM schedule
// (terminal, POST_TERMINAL retirement) after the helper sequence returns.
struct SequenceClock {uint64_t cn=553667,hn=512000,events=0;bool ch=false,hh=false;};
struct HelperSequenceResult {unsigned errors=0,layers=0;bool head=false;uint64_t core_edges=0,helper_edges=0;};
using ActualHostStartup=std::function<void(qwen_native_host::HostOwner&,qwen_native_host::Inputs&,uint64_t)>;
using ActualHostDrain=std::function<uint8_t(const qwen_native_host::HostOwner&)>;
static void save_actual_helper_streams(const Native59Helpers&link,const Layer&layer,const fs::path&out){
 for(unsigned segment=0;segment<2;segment++){
  auto dir=out/("collective"+std::to_string(segment))/"actual";fs::create_directories(dir);
  for(unsigned rank=0;rank<8;rank++){
   std::ofstream f(dir/("rank"+std::to_string(rank)+".hex")),tags(dir/("rank"+std::to_string(rank)+"_writes.txt"));unsigned n=0;
   for(auto&w:link.write_events)if(w.rank==rank&&((w.tag>>37)&63)==layer.number+1&&(w.tag&63)==segment){
    if(w.address!=16*n||n>=256)throw std::runtime_error("actual helper collective VM window/address/order differs");
    for(unsigned j=0;j<16;j++)f<<std::hex<<std::setfill('0')<<std::setw(8)<<w.data[15-j];f<<"\n";
    tags<<w.edge<<" "<<std::hex<<w.tag<<std::dec<<" "<<w.address<<"\n";++n;
   }
   if(n!=256)throw std::runtime_error("missing real helper collective VM writes");
  }
 }
}
static HelperSequenceResult run_actual_helper_layers(
 std::array<std::unique_ptr<Rank>,8>&r,const std::vector<Layer>&layers,
 VerilatedContext&ctx,Native59Helpers&link,qwen_native_host::HostOwner&host,
 qwen_native_host::Inputs&inputs,const ActualHostStartup&startup,
 const ActualHostDrain&host_drain,const fs::path&out,
 const std::string&head_image={},const std::string&head_program={},
 EmbeddingOwner*embedding=nullptr,const std::string&embedding_bank={},SequenceClock*clock_state=nullptr,bool head_first=false){
 if(!startup||!host_drain)throw std::runtime_error("actual HOST producer/drain binding required");
 if(layers.empty())throw std::runtime_error("missing actual layers");
 if(layers.size()==36&&!head_image.empty()&&!embedding)throw std::runtime_error("full38-stage token requires actual embedding after HOST dispatch");
 if(embedding&&embedding_bank.empty())throw std::runtime_error("actual embedding code/scale bank required");
 link.banks(layers.front().program);size_t layer_index=0;bool begun=false,head=false;
 // Per-rank core state: each actual helper starts its own core when its own
 // all-reduce return completes, so ranks legitimately start a segment on
 // different edges (collector delivery skew). One aggregate flag threw on that.
 std::array<bool,8> rank_running{};std::array<unsigned,8> rank_segment{};bool head_saved=false;
 auto any_running=[&]{for(bool b:rank_running)if(b)return true;return false;};
 if(head_first){
  if(head_image.empty()||head_program.empty()||layers.size()!=1)throw std::runtime_error("head-first run needs one plan layer plus head banks");
  for(auto&x:r)x->prepare_head_first(head_image,head_program);link.banks(head_program);head=true;
 }
 SequenceClock local_clock;SequenceClock&clock=clock_state?*clock_state:local_clock;
 uint64_t&cn=clock.cn,&hn=clock.hn;bool&ch=clock.ch,&hh=clock.hh;HelperSequenceResult result;
 bool grant_saved=false,embedding_started=false,embedding_complete=!embedding;uint64_t layer_helper_begin=0;
 const uint64_t event_limit=clock.events+8000000ULL*(layers.size()+1);
 for(uint64_t&events=clock.events;events<event_limit;events++){
  bool core=cn<=hn;ctx.time(core?cn:hn);
  if(!core){hn+=512000;hh=!hh;rank_pool().run([&](unsigned k){r[k]->backend.hbm_edge(hh);});continue;}
  cn+=416667;ch=!ch;
  if(!ch){rank_pool().run([&](unsigned k){r[k]->fall();});link.fall();if(embedding)embedding->fall();host.fall();continue;}
  startup(host,inputs,events);bool providers=true,boot=true;
  for(auto&x:r){boot&=x->backend.hbm_edges>=8;providers&=x->front.epoch_ready&&x->front.native_idle&&!x->front.fault;}
  inputs.engine_admit_ready=boot&&providers&&(!embedding||embedding->admit_ready());inputs.host_drained=host_drain(host);host.low(inputs);
  if(host.fault())throw std::runtime_error("actual HOST allocator/cohort fault");
  bool reset=true,can_begin=host.dispatch()&&link.ready()&&!begun&&embedding_complete;
  for(unsigned rank=0;rank<8;rank++){
   auto&x=*r[rank];bool rst=host.host_for_rank(rank)->die_rst_n&&host.host_for_rank(rank)->host_rst_n&&x.backend.hbm_edges>=8;
   if((begun||embedding_started)&&!rst)throw std::runtime_error("actual die reset during token: preserve failure, do not mask/restart computation");
   reset&=rst;x.host_reset_bound=true;x.host_die_reset_n=rst;
   if(host.dispatch()){
    if(host.accepted_ranks()!=255||host.token()!=0||host.position()!=layers[0].position||host.epoch()!=layers[0].epoch)
     throw std::runtime_error("actual HOST cohort differs from pinned token0 embedding/layer plan");
    x.front.epoch=host.epoch();x.front.token=host.token();x.front.pos=host.position();
   }
   x.token_grant_ready=host.dispatch();can_begin&=x.epoch_reserved;
  }
  if(host.dispatch()&&!grant_saved){
   if(host.admissions.size()!=8)throw std::runtime_error("missing actual HOST endpoint admission trace");
   std::array<bool,8> seen{};for(auto&a:host.admissions){if(a.rank>=8||seen[a.rank]||a.tag!=host.tag()||a.generation!=host.generation()||a.token!=host.token()||a.position!=host.position())throw std::runtime_error("actual endpoint acceptance tuple/ownership differs");seen[a.rank]=true;}
   fs::create_directories(out);std::ofstream g(out/"central_epoch_grant.json");
   g<<"{\"scope\":\"ACTUAL_HOST_ALLOCATOR_AND_EIGHT_ENDPOINT_COHORT\",\"delivered\":true,\"busy\":"<<(host.host_for_rank(0)->allocated_valid?"true":"false")<<",\"epoch\":"<<host.epoch()<<",\"token\":"<<host.token()<<",\"position\":"<<host.position()<<",\"generation\":"<<host.generation()<<",\"grant_tag\":"<<host.tag()<<",\"actual_accepted_ranks\":"<<host.accepted_ranks()<<"}\n";grant_saved=true;
  }
  if(embedding&&!embedding_started&&host.dispatch()&&reset){
   embedding->begin_after_actual_dispatch(embedding_bank,host.tag(),host.generation(),host.token(),host.position());embedding_started=true;
  }
  if(embedding)embedding->low(r,reset);
  link.low(r,reset,can_begin,host.epoch(),head?37:layers[layer_index].number+1,host.token(),host.position());
  std::array<bool,8> starts{};
  for(unsigned rank=0;rank<8;rank++){
   auto&h=link.rank(rank);bool start=h.core_start;
   if(start&&!host.dispatch())throw std::runtime_error("actual helper core start without actual eight-endpoint cohort dispatch");
   if(start){if(rank_running[rank])throw std::runtime_error("helper relaunched busy core (rank "+std::to_string(rank)+")");r[rank]->vm.segment_base=h.prog_base;}
   starts[rank]=start;
  }
  rank_pool().run([&](unsigned k){r[k]->low(starts[k]);});
  // Both read snapshots and inter-model pins are now frozen. Advance every
  // actual model, then apply its captured addressed writes without rewiring.
  rank_pool().run([&](unsigned k){r[k]->rise();});link.rise(r);if(embedding)embedding->rise(r);host.rise();
  static const auto wall0=std::chrono::steady_clock::now();
  if(host.core_edges%500==0){
   std::cerr<<"PROGRESS core_edges "<<host.core_edges<<" layer_index "<<layer_index<<" head "<<head<<" dispatch "<<host.dispatch()<<" begun "<<begun<<" running "<<std::count(rank_running.begin(),rank_running.end(),true)<<" core_evals "<<r[0]->core_evals<<" skipped "<<r[0]->core_evals_skipped<<" memo_hits "<<r[0]->memo_hits<<" memo_verified "<<r[0]->memo_verified<<" memo_records "<<r[0]->memo_records
    <<" wall_s "<<std::chrono::duration<double>(std::chrono::steady_clock::now()-wall0).count()<<std::endl;}
  if(embedding&&!embedding_complete&&embedding_started&&embedding->done()){
   embedding_complete=true;fs::create_directories(out/"embedding");std::ofstream f(out/"embedding"/"actual_commits.txt");for(auto&w:embedding->commits)f<<w.address<<" "<<std::hex<<std::setw(8)<<std::setfill('0')<<w.value<<" "<<w.tag<<std::dec<<" "<<w.generation<<" "<<w.edge<<"\n";
   std::ofstream words(out/"embedding"/"actual_accepted_words.txt");for(auto&w:embedding->raw_events){words<<w.pc<<" "<<w.edge<<" ";for(unsigned j=0;j<32;j++)words<<std::hex<<std::setw(8)<<std::setfill('0')<<w.bits[31-j];words<<std::dec<<"\n";}
   std::ofstream cycles(out/"embedding"/"functional_cycles.json");cycles<<"{\"actual_cycles\":"<<embedding->cycles()<<",\"after_actual_HOST_cohort_dispatch\":true,\"physical_rate_qualified\":false}\n";embedding->retire();
  }
  if(can_begin){begun=true;layer_helper_begin=link.cycles();}
  for(unsigned rank=0;rank<8;rank++)if(starts[rank])rank_running[rank]=true;
  // A rank's core segment ends when its own core reports done; its VM cannot
  // change before every rank has contributed to the following all-reduce.
  for(unsigned rank=0;rank<8;rank++){
   if(!rank_running[rank]||!r[rank]->core.done)continue;
   if(!head){
    auto dir=layer_output(layers[layer_index],out,layers.size());fs::create_directories(dir);
    std::ofstream f(dir/("rank"+std::to_string(rank)+"_segment"+std::to_string(rank_segment[rank])+"_VM.hex"));for(auto value:r[rank]->vm.vm)f<<std::hex<<std::setfill('0')<<std::setw(8)<<value<<"\n";
   }
   rank_running[rank]=false;++rank_segment[rank];
  }
  if(head&&!head_saved&&!any_running()&&*std::min_element(rank_segment.begin(),rank_segment.end())>=1){save_head(r,out/"head");head_saved=true;}
  bool helpers_done=begun&&!any_running()&&link.drained();for(unsigned rank=0;rank<8;rank++)helpers_done&=link.rank(rank).done;
  if(!helpers_done)continue;
  if(head){
   unsigned tok=link.rank(0).next_token,value=link.rank(0).next_val;
   if(tok>=151936)throw std::runtime_error("actual global18 token outside vocabulary");
   for(unsigned rank=0;rank<8;rank++)if(link.rank(rank).next_token!=tok||link.rank(rank).next_val!=value)throw std::runtime_error("actual global18 helper argmax disagreement");
   std::ofstream f(out/"head"/"global_argmax.txt");f<<tok<<" "<<std::hex<<std::setw(8)<<std::setfill('0')<<value<<std::dec<<"\n";
   // The caller owns credited result and genuine HOST terminal draining.
   uint64_t head_tag=link.rank(0).c_tag;
   if(head_tag!=(host.tag()|(uint64_t(37)<<37)))throw std::runtime_error("actual head result tag differs from held cohort/head37 identity");
   for(unsigned rank=0;rank<8;rank++)if(link.rank(rank).c_tag!=head_tag)throw std::runtime_error("actual head accepted identities disagree");
   inputs.result_tag=head_tag;inputs.result_generation=host.generation();inputs.result_token=tok;inputs.result_value=value;
   result.head=true;result.core_edges=r[0]->backend.core_edges;result.helper_edges=link.cycles();return result;
  }
  auto dir=layer_output(layers[layer_index],out,layers.size());
  for(auto&x:r)x->collector_cycles=link.cycles()-layer_helper_begin;
  save_actual_helper_streams(link,layers[layer_index],dir);result.errors+=save_layer(r,layers[layer_index],dir);++result.layers;
  if(result.errors)throw std::runtime_error("actual output mismatch; refusing warm bank transition");
  if(++layer_index==layers.size()){
   if(head_image.empty()){result.core_edges=r[0]->backend.core_edges;result.helper_edges=link.cycles();return result;}
   if(head_program.empty())throw std::runtime_error("missing actual head descriptor/program bank");
   for(auto&x:r)x->switch_head(head_image,head_program);link.banks(head_program);head=true;--layer_index;
  }else{for(auto&x:r)x->switch_layer(layers[layer_index]);link.banks(layers[layer_index].program);}
  begun=false;rank_segment={};head_saved=false;
 }
 throw std::runtime_error("actual helper-driven layer sequence timeout");
}
