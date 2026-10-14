// Whole-token functional driver: eight actual HOSTs (sole allocator + cohort),
// actual NW18 embedding after cohort dispatch, 36 executed decoder layers on
// eight LV6/G3072 cores with the persistent TAG59 collector, the eight-rank head
// with actual global18 argmax, then the credited terminal and POST_TERMINAL
// retirement, all in ONE continuous DUT lifecycle (no reset after POR).
// Expected values are observers only: per-layer X comparison inside save_layer()
// and the final token/value comparison after retirement. Nothing is preloaded.
#include "full_layer_helpers_loop.hpp"
#include "qkd_host_drain_8bb.hpp"
#include <chrono>
using namespace qwen_native_host;

namespace {
struct Args {
 std::string plan,embedding_program,embedding_bank,head_image,head_program,collector,out;
 unsigned expected_token=0,expected_value=0;
};
uint32_t parse_u32(const char*s){return uint32_t(std::stoul(s,nullptr,0));}

// Board/startup stimulus identical to the qualified HOST->embedding gate
// (unit2734693): POR, link/boot straps, service BEGIN, BOOT_END, FMT1 prompt
// [token0] max_new1, nine BAR writes, peer7 CTRL held 1000 edges.
struct Startup {
 unsigned phase=0,bar_index=0;size_t bar_baseline=0;uint64_t delayed_begin=0;bool paused=false;
 const std::array<std::pair<unsigned,unsigned>,9> bars={{{0x10,0x100},{0x14,0},{0x18,2},
   {0x24,0x800},{0x28,0},{0x2c,5},{0x3c,1},{0x08,1},{0x1c,1}}};
 void operator()(HostOwner&host,Inputs&in){
  uint64_t n=host.core_edges;
  in.por_n=n>=8;in.link_up=n>=24?63:0;for(unsigned r=0;r<8;r++)in.boot[r]=n>=24?3:0;
  unsigned sys=0,permission=0,service=0;
  for(unsigned rank=0;rank<8;rank++){auto*h=host.host_for_rank(rank);sys|=unsigned(h->sys_ready)<<rank;
   permission|=unsigned(h->ingest_permission)<<rank;service|=unsigned(h->service_ready)<<rank;}
  if(phase==0&&sys==255){if(!host.router.service_begin())throw std::runtime_error("service reservation");phase=1;}
  if(phase==1&&permission==255){for(unsigned id=0;id<8;id++)if(!host.router.boot_end(id))throw std::runtime_error("BOOT reservation");phase=2;}
  if(phase==2&&service==255){host.router.pause_ctrl_destination(7,true);paused=true;host.router.fmt1_descriptor(0x100,0x400,{0},1);phase=3;}
  if(phase==3&&bar_index<bars.size()&&host.router.bar_responses().size()>=bar_baseline){
   auto[a,v]=bars[bar_index++];bar_baseline=host.router.bar_responses().size()+1;
   if(!host.router.write_bar(0,a,v,15,bar_index))throw std::runtime_error("FMT1 BAR reservation");}
  if(host.accepted_ranks()==127&&paused){if(!delayed_begin)delayed_begin=n;
   if(host.dispatch())throw std::runtime_error("cohort dispatch before delayed actual peer7");
   if(n-delayed_begin>=1000){host.router.pause_ctrl_destination(7,false);paused=false;}}
 }
 bool stimulus_complete(const HostOwner&host)const{
  return phase==3&&bar_index==bars.size()&&!paused&&delayed_begin&&host.router.bar_responses().size()>=bars.size();
 }
};

// PRE_TERMINAL accepted-traffic certificate: computed from the actual source-bound
// accessor on all eight HOSTs and boards plus router/FDI emptiness, only after the
// last board stimulus, bound to the held cohort tag and latched (never oscillated
// by the terminal's own TK/status traffic). Invalidated only by reset.
struct PreTerminal {
 bool latched=false;uint64_t tag=0,edge=0;uint32_t last_blocked=0;std::string first;
 bool predicate(const HostOwner&h){
  bool ok=h.router.router_empty()&&h.router.fdi_pipelines_empty();last_blocked=0;first.clear();
  for(unsigned id=0;id<8;id++){
   auto a=qkd_host_fixture::host_transport_drain(*h.hosts[id]);auto b=qkd_host_fixture::board_transport_drain(*h.boards[id]);
   if(!a.drained()){ok=false;last_blocked|=a.blocked;if(first.empty())first="HOST"+std::to_string(id)+":"+a.first;}
   if(!b.drained()){ok=false;last_blocked|=b.blocked<<8;if(first.empty())first="BOARD"+std::to_string(id)+":"+b.first;}
  }
  return ok;
 }
 uint8_t operator()(const HostOwner&h,const Startup&s){
  bool reset=true;for(unsigned id=0;id<8;id++)reset&=h.hosts[id]->host_rst_n&&h.hosts[id]->die_rst_n;
  if(latched&&!reset)throw std::runtime_error("coherent reset after PRE_TERMINAL certificate: preserve failure");
  if(latched){if(h.tag()!=tag)throw std::runtime_error("PRE_TERMINAL certificate identity changed");return 255;}
  if(h.dispatch()&&s.stimulus_complete(h)&&predicate(h)){latched=true;tag=h.tag();edge=h.core_edges;return 255;}
  return 0;
 }
};

template<class Ranks>void step_all(Ranks&r,VerilatedContext&ctx,SequenceClock&c,Native59Helpers&link,HostOwner&host,
  Inputs&in,EmbeddingOwner&embed,const std::function<void()>&before_low,const std::function<void()>&after_rise,
  unsigned stage,const std::function<bool()>&finished,uint64_t limit,const char*what){
 for(uint64_t start=c.events;c.events<start+limit;c.events++){
  bool core=c.cn<=c.hn;ctx.time(core?c.cn:c.hn);
  if(!core){c.hn+=512000;c.hh=!c.hh;for(auto&x:r)x->backend.hbm_edge(c.hh);continue;}
  c.cn+=416667;c.ch=!c.ch;
  if(!c.ch){for(auto&x:r)x->fall();link.fall();embed.fall();host.fall();continue;}
  before_low();host.low(in);
  if(host.fault())throw std::runtime_error(std::string("actual HOST allocator/cohort fault during ")+what);
  bool reset=true;
  for(unsigned rank=0;rank<8;rank++){auto*h=host.host_for_rank(rank);bool rst=h->die_rst_n&&h->host_rst_n&&r[rank]->backend.hbm_edges>=8;
   if(!rst)throw std::runtime_error(std::string("actual die reset during ")+what+": preserve failure");
   r[rank]->host_die_reset_n=rst;reset&=rst;}
  embed.low(r,reset);
  link.low(r,reset,false,host.epoch(),stage,host.token(),host.position());
  for(unsigned rank=0;rank<8;rank++){if(link.rank(rank).core_start)throw std::runtime_error("core start after head retirement");r[rank]->low(false);}
  for(auto&x:r)x->rise();link.rise(r);embed.rise(r);host.rise();
  for(unsigned id=0;id<8;id++)if(host.hosts[id]->service_abort||host.hosts[id]->package_abort||host.boards[id]->faults)
   throw std::runtime_error(std::string("actual HOST/board abort or fault during ")+what);
  after_rise();
  if(finished()){c.events++;return;}
 }
 throw std::runtime_error(std::string("timeout during ")+what);
}
} // namespace

int main(int argc,char**argv){try{
 if(argc!=10)throw std::runtime_error("usage: layer_plan embedding_program embedding_bank head_image head_program libnative59.so output expected_token expected_value_bits");
 Args a{argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7],parse_u32(argv[8]),parse_u32(argv[9])};
 fs::path out(a.out);if(fs::exists(out))throw std::runtime_error("output directory must be fresh");fs::create_directories(out);
 auto wall=std::chrono::steady_clock::now();
 auto layers=read_plan(a.plan);
 if(layers.front().number!=0||layers.front().position!=0)throw std::runtime_error("whole token starts at layer0 position0");
 VerilatedContext ctx;ctx.threads(1);
 HostOwner host;Inputs in;Startup startup;PreTerminal pre;
 EmbeddingOwner embed(ctx,a.embedding_program);
 std::array<std::unique_ptr<Rank>,8> r;
 for(unsigned rank=0;rank<8;rank++)r[rank]=std::make_unique<Rank>(ctx,rank,layers[0],std::string(),true);
 Native59Helpers link(ctx,a.collector);
 SequenceClock clock;
 auto start_fn=[&](HostOwner&h,Inputs&i,uint64_t){startup(h,i);};
 auto drain_fn=[&](const HostOwner&h)->uint8_t{return pre(h,startup);};
 auto result=run_actual_helper_layers(r,layers,ctx,link,host,in,start_fn,drain_fn,out,
   layers.size()==36?a.head_image:std::string(),layers.size()==36?a.head_program:std::string(),&embed,a.embedding_bank,&clock);
 std::cerr<<"layers executed "<<result.layers<<" head "<<result.head<<" core "<<result.core_edges<<" wall_s "
   <<std::chrono::duration<double>(std::chrono::steady_clock::now()-wall).count()<<"\n";
 if(!result.head){
  std::ofstream f(out/"receipt.json");f<<"{\"scope\":\"ACTUAL_HOST_EMBEDDING_AND_EXECUTED_LAYER_PREFIX\",\"layers\":"<<result.layers<<",\"errors\":"<<result.errors<<",\"whole_token\":false}\n";
  std::cout<<"PASS executed layer prefix "<<result.layers<<" errors "<<result.errors<<"\n";return result.errors?1:0;
 }
 if(!pre.latched)throw std::runtime_error("no PRE_TERMINAL accepted-traffic certificate before head retirement (last block "+pre.first+")");
 // Credited terminal: one result pulse with the actual head37/seg0 identity and
 // genuine global18 result; drains come from actual provider state only.
 const uint64_t dispatch_tag=host.tag();const unsigned generation=host.generation();
 unsigned token=in.result_token,value=in.result_value;
 uint64_t head_edge=host.core_edges;bool pulsed=false;unsigned result_cr=0;uint64_t terminal_edge=0,post_edge=0;
 auto drains=[&](){uint8_t kv=0,vm=0;
  for(unsigned rank=0;rank<8;rank++){auto&x=*r[rank];
   if(x.writes.drained()&&x.reads.drained())kv|=1u<<rank;
   if(x.core.done&&x.core.su_is_idle&&x.front.native_idle&&x.receiver.acks.empty()&&x.receiver.responses.empty())vm|=1u<<rank;}
  in.kv_drained=kv;in.vm_drained=vm;in.collective_drained=link.drained()?255:0;in.host_drained=pre(host,startup);};
 step_all(r,ctx,clock,link,host,in,embed,[&]{startup(host,in);drains();
   in.result_valid=!pulsed;in.result_done=1;in.result_fault=0;in.result_cause=0;in.result_tag=dispatch_tag|(uint64_t(37)<<37);
   in.result_generation=generation;in.result_token=token;in.result_value=value;in.result_cycles=uint32_t(head_edge);pulsed=true;},
  [&]{for(unsigned id=0;id<8;id++)result_cr+=host.hosts[id]->native_result_cr;
   if(!terminal_edge&&host.awaiting_post_terminal_retirement())terminal_edge=host.core_edges;},
  37,[&]{return terminal_edge!=0;},200000,"credited terminal");
 in.result_valid=0;
 if(host.acknowledged_terminal_tag()!=(dispatch_tag|(uint64_t(37)<<37))||host.acknowledged_terminal_generation()!=generation)
  throw std::runtime_error("allocator accepted terminal identity differs from held cohort head37");
 // POST_TERMINAL: actual ND8 completion publication (class5 CQ) and IRQ on HOST0,
 // then the strict last-descriptor predicate on HOST0 and transport drains on all.
 size_t completions_before=0;bool cq=false,irq=false;std::string post_block;
 auto post_ok=[&](){
  cq=host.router.completions().size()>completions_before;irq=host.router.irq(0);
  bool ok=host.router.router_empty()&&host.router.fdi_pipelines_empty();post_block.clear();
  for(unsigned id=0;id<8;id++){
   auto d=id==0?qkd_host_fixture::host_last_descriptor_retired(*host.hosts[0],result_cr>=8,cq,irq):qkd_host_fixture::host_transport_drain(*host.hosts[id]);
   auto b=qkd_host_fixture::board_transport_drain(*host.boards[id]);
   if(!d.drained()){ok=false;if(post_block.empty())post_block="HOST"+std::to_string(id)+":"+d.first;}
   if(!b.drained()){ok=false;if(post_block.empty())post_block="BOARD"+std::to_string(id)+":"+b.first;}}
  return ok;};
 bool certified=false,retired=false;
 step_all(r,ctx,clock,link,host,in,embed,[&]{startup(host,in);drains();in.result_valid=0;
   in.post_terminal_retired=certified&&!retired;in.post_terminal_tag=host.acknowledged_terminal_tag();in.post_terminal_generation=generation;
   if(in.post_terminal_retired)retired=true;},
  [&]{for(unsigned id=0;id<8;id++)result_cr+=host.hosts[id]->native_result_cr;
   if(!certified&&post_ok()){certified=true;post_edge=host.core_edges;}
   if(host.core_edges%20000==0&&!certified)std::cerr<<"POST_TERMINAL block "<<post_block<<" cq="<<cq<<" irq="<<irq<<" result_cr="<<result_cr<<"\n";},
  37,[&]{return retired&&!host.awaiting_post_terminal_retirement();},400000,"POST_TERMINAL retirement");
 in.post_terminal_retired=false;
 bool match=token==a.expected_token&&value==a.expected_value;
 std::ofstream t(out/"terminal.json");
 t<<"{\n \"scope\": \"ACTUAL_EIGHT_HOST_WHOLE_TOKEN_CONTINUOUS_LIFECYCLE\",\n \"layers\": "<<result.layers<<",\n \"layer_errors\": "<<result.errors
  <<",\n \"global_token\": "<<token<<",\n \"global_value_bits\": "<<value<<",\n \"expected_token\": "<<a.expected_token<<",\n \"expected_value_bits\": "<<a.expected_value
  <<",\n \"bit_exact_match\": "<<(match?"true":"false")<<",\n \"cohort_tag\": "<<dispatch_tag<<",\n \"generation\": "<<generation
  <<",\n \"pre_terminal_certificate_core_edge\": "<<pre.edge<<",\n \"head_result_core_edge\": "<<head_edge<<",\n \"terminal_accepted_core_edge\": "<<terminal_edge
  <<",\n \"post_terminal_certificate_core_edge\": "<<post_edge<<",\n \"native_result_credits_observed\": "<<result_cr
  <<",\n \"cq_completions\": "<<host.router.completions().size()<<",\n \"irq_host0\": "<<(irq?"true":"false")
  <<",\n \"helper_edges\": "<<result.helper_edges<<",\n \"core_edges_total\": "<<host.core_edges
  <<",\n \"wall_seconds\": "<<std::chrono::duration<double>(std::chrono::steady_clock::now()-wall).count()
  <<",\n \"reset_after_por\": false,\n \"physical_rate_qualified\": false\n}\n";
 std::ofstream c(out/"cq_completions.txt");for(auto&e:host.router.completions())c<<e.rank<<" "<<std::hex<<e.data<<std::dec<<"\n";
 std::cout<<(match?"PASS":"FAIL")<<" whole token "<<token<<" value "<<value<<" expected "<<a.expected_token<<" "<<a.expected_value<<"\n";
 return match?0:1;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";return 2;}}
