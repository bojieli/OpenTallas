#include "embedding_owner.hpp"
#include <iostream>
struct RankFixture {struct VM{std::vector<uint32_t>vm=std::vector<uint32_t>(56816,0);uint32_t load(unsigned a)const{return vm.at(a);}void external_commit(unsigned a,uint32_t v,const char*){vm.at(a)=v;}}vm;};
int main(int argc,char**argv){try{
 if(argc!=3)throw std::runtime_error("actual_embedding_program code_and_scale_banks required");
 VerilatedContext ctx;ctx.threads(1);EmbeddingOwner embed(ctx,argv[1]);
 std::array<std::unique_ptr<RankFixture>,8>r;for(unsigned rank=0;rank<8;rank++){r[rank]=std::make_unique<RankFixture>();r[rank]->vm.vm[100]=0x12345600+rank;}
 auto edge=[&](bool reset){ctx.timeInc(833334);embed.low(r,reset);embed.rise(r);embed.fall();};
 for(unsigned n=0;n<8;n++)edge(false);for(unsigned n=0;n<8;n++)edge(true);
 unsigned total=0,frame=0;
 for(unsigned token:{0u,65536u,151935u}){
  uint64_t tag=(uint64_t(frame)<<43)|(uint64_t(token)<<19); // explicit identity fixture; no HOST claim
  embed.begin_after_actual_dispatch(argv[2],tag,2,token,0);unsigned watchdog=0;while(!embed.done()&&watchdog++<10000)edge(true);
  if(!embed.done())throw std::runtime_error("actual embedding timeout");
  auto x=qwen_native::read_hex<1>(std::string(argv[2])+"/token"+std::to_string(token)+"/expected_X.hex");auto ssx=qwen_native::read_hex<1>(std::string(argv[2])+"/token"+std::to_string(token)+"/expected_SSX.hex");
  if(x.size()!=4096||ssx.size()!=1)throw std::runtime_error("comparison-only observer dimensions");
  for(unsigned rank=0;rank<8;rank++){if(r[rank]->vm.vm[100]!=0x12345600+rank)throw std::runtime_error("warm embedding broadcast replaced unrelated live VM state");for(unsigned j=0;j<4096;j++)if(r[rank]->vm.vm[4096+j]!=x[j][0])throw std::runtime_error("actual broadcast X differs");if(r[rank]->vm.vm[14240]!=ssx[0][0])throw std::runtime_error("actual broadcast SSX differs");total+=4097;}
  for(auto&w:embed.commits)if(w.tag!=tag||w.generation!=2)throw std::runtime_error("captured fixture identity lost at actual write face");
  std::cout<<"ACTUAL_REUSABLE_EMBED token="<<token<<" cycles="<<embed.cycles()<<" observed_raw=2 addressed_commits="<<embed.commits.size()<<" unchanged_non_destination_VM=true\n";
  embed.retire();for(unsigned n=0;n<16;n++)edge(true);++frame;
 }
 std::cout<<"{\"scope\":\"ACTUAL_REUSABLE_NW18_EMBEDDING_VM_BROADCAST_COMPONENT_ONLY\",\"identity_source\":\"explicit_fixture_not_actual_HOST_cohort\",\"same_DUT_frames\":3,\"reset_after_boot\":0,\"exact_comparison_words\":"<<total<<",\"whole_token\":false}\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";return 2;}}
