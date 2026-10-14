// Whole-token functional driver: eight actual HOSTs (sole allocator + cohort),
// actual NW18 embedding after cohort dispatch, 36 executed decoder layers on
// eight LV6/G3072 cores with the persistent TAG59 collector, the eight-rank head
// with actual global18 argmax, then the credited terminal and POST_TERMINAL
// retirement, all in ONE continuous DUT lifecycle (no reset after POR).
// Expected values are observers only: per-layer X comparison inside save_layer()
// and the final token/value comparison after retirement. Nothing is preloaded.
#include "full_layer_helpers_loop.hpp"
#include "host_lifecycle.hpp"
#include <chrono>
using namespace qwen_native_host;

namespace {
struct Args {
 std::string plan,embedding_program,embedding_bank,head_image,head_program,collector,out;
 unsigned expected_token=0,expected_value=0;
};
uint32_t parse_u32(const char*s){return uint32_t(std::stoul(s,nullptr,0));}

template<class Ranks>void step_all(Ranks&r,VerilatedContext&ctx,SequenceClock&c,Native59Helpers&link,HostOwner&host,
  Inputs&in,EmbeddingOwner&embed,const std::function<void()>&before_low,const std::function<void()>&after_rise,
  unsigned stage,const std::function<bool()>&finished,uint64_t limit,const char*what){
 for(uint64_t start=c.events;c.events<start+limit;c.events++){
  bool core=c.cn<=c.hn;ctx.time(core?c.cn:c.hn);
  if(!core){c.hn+=512000;c.hh=!c.hh;rank_pool().run([&](unsigned k){r[k]->backend.hbm_edge(c.hh);});continue;}
  c.cn+=416667;c.ch=!c.ch;
  if(!c.ch){rank_pool().run([&](unsigned k){r[k]->fall();});link.fall();embed.fall();host.fall();continue;}
  before_low();host.low(in);
  if(host.fault())throw std::runtime_error(std::string("actual HOST allocator/cohort fault during ")+what);
  bool reset=true;
  for(unsigned rank=0;rank<8;rank++){auto*h=host.host_for_rank(rank);bool rst=h->die_rst_n&&h->host_rst_n&&r[rank]->backend.hbm_edges>=8;
   if(!rst)throw std::runtime_error(std::string("actual die reset during ")+what+": preserve failure");
   r[rank]->host_die_reset_n=rst;reset&=rst;}
  embed.low(r,reset);
  link.low(r,reset,false,host.epoch(),stage,host.token(),host.position());
  for(unsigned rank=0;rank<8;rank++)if(link.rank(rank).core_start)throw std::runtime_error("core start after head retirement");
  rank_pool().run([&](unsigned k){r[k]->low(false);});
  rank_pool().run([&](unsigned k){r[k]->rise();});link.rise(r);embed.rise(r);host.rise();
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
 std::cerr<<"rank evaluation "<<(rank_pool().parallel()?"parallel x8":"sequential")<<std::endl;
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
 // Credited terminal and POST_TERMINAL retirement (host_lifecycle.hpp), on the
 // same continuous CORE/HBM schedule; drains come from actual provider state.
 const uint64_t dispatch_tag=host.tag();const unsigned generation=host.generation();
 unsigned token=in.result_token,value=in.result_value;uint64_t head_edge=host.core_edges;
 auto drains=[&](){uint8_t kv=0,vm=0;
  for(unsigned rank=0;rank<8;rank++){auto&x=*r[rank];
   if(x.writes.drained()&&x.reads.drained())kv|=1u<<rank;
   if(x.core.done&&x.core.su_is_idle&&x.front.native_idle&&x.receiver.acks.empty()&&x.receiver.inflight.empty()&&x.receiver.responses.empty())vm|=1u<<rank;}
  in.kv_drained=kv;in.vm_drained=vm;in.collective_drained=link.drained()?255:0;in.host_drained=pre(host,startup);};
 Terminal term;term.begin(host,token,value,uint32_t(head_edge));
 step_all(r,ctx,clock,link,host,in,embed,[&]{startup(host,in);drains();term.before_low(host,in);},
  [&]{term.after_rise(host);if(host.core_edges%20000==0&&!term.done())std::cerr<<"TERMINAL phase "<<term.phase<<" block "<<term.post_block<<"\n";},
  37,[&]{return term.done();},600000,"credited terminal and POST_TERMINAL retirement");
 in.result_valid=false;in.post_terminal_retired=false;
 bool match=token==a.expected_token&&value==a.expected_value;
 std::ofstream t(out/"terminal.json");
 t<<"{\n \"scope\": \"ACTUAL_EIGHT_HOST_WHOLE_TOKEN_CONTINUOUS_LIFECYCLE\",\n \"layers\": "<<result.layers<<",\n \"layer_errors\": "<<result.errors
  <<",\n \"global_token\": "<<token<<",\n \"global_value_bits\": "<<value<<",\n \"expected_token\": "<<a.expected_token<<",\n \"expected_value_bits\": "<<a.expected_value
  <<",\n \"bit_exact_match\": "<<(match?"true":"false")<<",\n \"cohort_tag\": "<<dispatch_tag<<",\n \"generation\": "<<generation
  <<",\n \"pre_terminal_certificate_core_edge\": "<<pre.edge<<",\n \"head_result_core_edge\": "<<head_edge<<",\n \"lifecycle\": "<<term.json()
  <<",\n \"cq_completions\": "<<host.router.completions().size()
  <<",\n \"helper_edges\": "<<result.helper_edges<<",\n \"core_edges_total\": "<<host.core_edges
  <<",\n \"wall_seconds\": "<<std::chrono::duration<double>(std::chrono::steady_clock::now()-wall).count()
  <<",\n \"reset_after_por\": false,\n \"physical_rate_qualified\": false\n}\n";
 std::ofstream c(out/"cq_completions.txt");for(auto&e:host.router.completions())c<<e.rank<<" "<<std::hex<<e.data<<std::dec<<"\n";
 std::cout<<(match?"PASS":"FAIL")<<" whole token "<<token<<" value "<<value<<" expected "<<a.expected_token<<" "<<a.expected_value<<"\n";
 return match?0:1;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";return 2;}}
