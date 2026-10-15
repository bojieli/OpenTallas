#include "host_owner.hpp"
#include "embedding_owner.hpp"
#include <filesystem>
#include <iostream>
using namespace qwen_native_host;
struct ActualVM {std::vector<uint32_t>vm=std::vector<uint32_t>(56816,0);uint32_t load(unsigned a)const{return vm.at(a);}void external_commit(unsigned a,uint32_t v,const char*){vm.at(a)=v;}};
struct VMRank {ActualVM vm;};
int main(int argc,char**argv){try{
 if(argc!=4)throw std::runtime_error("actual_embedding_program code_scale_banks fresh_output required");
 std::filesystem::create_directories(argv[3]);HostOwner host;Inputs in;VerilatedContext ctx;ctx.threads(1);EmbeddingOwner embed(ctx,argv[1]);
 std::array<std::unique_ptr<VMRank>,8>r;for(auto&x:r)x=std::make_unique<VMRank>();
 unsigned phase=0,bar_index=0,bar_baseline=0;uint64_t delayed_begin=0,dispatch_edge=0,embedding_edge=0;bool paused=false,started=false;
 uint64_t held_tag=0;unsigned held_gen=0;
 const std::array<std::pair<unsigned,unsigned>,9> bars={{{0x10,0x100},{0x14,0},{0x18,2},{0x24,0x800},{0x28,0},{0x2c,5},{0x3c,1},{0x08,1},{0x1c,1}}};
 for(unsigned n=0;n<1600000;n++){
  // Explicit external startup/board fixtures inherited from qualified HOST
  // gate. SYS/service/reset/endpoint admission signals remain actual DUT pins.
  in.por_n=n>=8;in.link_up=n>=24?63:0;for(unsigned rank=0;rank<8;rank++)in.boot[rank]=n>=24?3:0;
  unsigned sys=0,permission=0,service=0;bool reset=true;
  for(unsigned rank=0;rank<8;rank++){auto*h=host.host_for_rank(rank);sys|=unsigned(h->sys_ready)<<rank;permission|=unsigned(h->ingest_permission)<<rank;service|=unsigned(h->service_ready)<<rank;reset&=h->host_rst_n&&h->die_rst_n;}
  if(phase==0&&sys==255){if(!host.router.service_begin())throw std::runtime_error("service reservation");phase=1;}
  if(phase==1&&permission==255){for(unsigned id=0;id<8;id++)if(!host.router.boot_end(id))throw std::runtime_error("BOOT fixture reservation");phase=2;}
  if(phase==2&&service==255){host.router.pause_ctrl_destination(7,true);paused=true;host.router.fmt1_descriptor(0x100,0x400,{0},1);phase=3;}
  if(phase==3&&bar_index<bars.size()&&host.router.bar_responses().size()>=bar_baseline){auto[a,v]=bars[bar_index++];bar_baseline=host.router.bar_responses().size()+1;if(!host.router.write_bar(0,a,v,15,bar_index))throw std::runtime_error("FMT1 reservation");}
  if(host.accepted_ranks()==127&&paused){if(!delayed_begin)delayed_begin=n;if(host.dispatch()||started)throw std::runtime_error("embedding before delayed actual peer7");if(n-delayed_begin>=1000){host.router.pause_ctrl_destination(7,false);paused=false;}}
  in.engine_admit_ready=embed.admit_ready();host.low(in);ctx.time(host.time_fs);
  if(host.dispatch()&&!started){
   if(paused||!delayed_begin||host.accepted_ranks()!=255||host.actual_allocations!=1||host.actual_grants!=1||host.admissions.size()!=8||host.token()!=0||host.position()!=0)throw std::runtime_error("missing actual eight endpoint/cohort provenance");
   for(auto&x:r)for(auto word:x->vm.vm)if(word)throw std::runtime_error("hidden initial VM preload before actual embedding");
   held_tag=host.tag();held_gen=host.generation();dispatch_edge=host.core_edges;embedding_edge=n;
   for(auto&a:host.admissions)if(a.tag!=held_tag||a.generation!=held_gen||a.token!=host.token()||a.position!=host.position())throw std::runtime_error("actual endpoint tuple mismatch");
   embed.begin_after_actual_dispatch(argv[2],held_tag,held_gen,host.token(),host.position());started=true;
  }
  if(started&&(!reset||!host.dispatch()))throw std::runtime_error("actual reset/lost cohort during embedding");
  embed.low(r,reset);host.rise();embed.rise(r);host.fall();ctx.time(host.time_fs);embed.fall();
  if(host.fault())throw std::runtime_error("actual owner identity fault");
  for(unsigned id=0;id<8;id++)if(host.hosts[id]->service_abort||host.hosts[id]->service_faults||host.boards[id]->faults)throw std::runtime_error("actual HOST/board fault");
  if(!started||!embed.done())continue;
  auto x=qwen_native::read_hex<1>(std::string(argv[2])+"/token0/expected_X.hex"),ssx=qwen_native::read_hex<1>(std::string(argv[2])+"/token0/expected_SSX.hex");if(x.size()!=4096||ssx.size()!=1)throw std::runtime_error("comparison-only dimensions");
  for(unsigned rank=0;rank<8;rank++){for(unsigned j=0;j<4096;j++)if(r[rank]->vm.vm[4096+j]!=x[j][0])throw std::runtime_error("actual after-cohort X differs");if(r[rank]->vm.vm[14240]!=ssx[0][0])throw std::runtime_error("actual after-cohort SSX differs");}
  std::ofstream a(std::string(argv[3])+"/actual_admissions.txt");for(auto&e:host.admissions)a<<e.rank<<" "<<e.edge<<" "<<std::hex<<e.tag<<std::dec<<" "<<e.generation<<" "<<e.token<<" "<<e.position<<"\n";
  std::ofstream meta(std::string(argv[3])+"/actual_program_metadata.txt");for(auto&e:host.admissions){meta<<e.rank;for(auto word:e.program_metadata){meta<<" "<<std::hex<<word<<std::dec;if(word)throw std::runtime_error("unexpected actual HOST program override");}meta<<"\n";}
  std::ofstream w(std::string(argv[3])+"/actual_embedding_commits.txt");for(auto&e:embed.commits){if(e.tag!=held_tag||e.generation!=held_gen||e.edge<embedding_edge)throw std::runtime_error("actual embedding write outside held cohort lifetime");w<<e.address<<" "<<std::hex<<e.value<<" "<<e.tag<<std::dec<<" "<<e.generation<<" "<<e.edge<<"\n";}
  std::ofstream raw(std::string(argv[3])+"/actual_embedding_words.txt");for(auto&e:embed.raw_events){raw<<e.pc<<" "<<e.edge<<" ";for(unsigned j=0;j<32;j++)raw<<std::hex<<std::setw(8)<<std::setfill('0')<<e.bits[31-j];raw<<std::dec<<"\n";}
  std::cout<<"{\"scope\":\"ACTUAL_EIGHT_HOST_COHORT_THEN_REAL_NW18_EMBEDDING_STAGE0\",\"startup\":\"explicit_board_and_zero_row_BOOT_fixtures\",\"HOST_physical_ID\":\"2PKG+DIE\",\"native_rank\":\"4DIE+PKG\",\"actual_endpoint_admissions\":8,\"epoch\":"<<host.epoch()<<",\"generation\":"<<held_gen<<",\"dispatch_core_edge\":"<<dispatch_edge<<",\"embedding_start_core_edge\":"<<embedding_edge<<",\"embedding_cycles\":"<<embed.cycles()<<",\"actual_addressed_write_faces\":4097,\"exact_rank_VM_words\":32776,\"pre_cohort_numerical_execution\":false,\"whole_token\":false,\"physical_rate_qualified\":false}\n";return 0;
 }
 throw std::runtime_error("actual HOST/embedding timeout");
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";return 2;}}
