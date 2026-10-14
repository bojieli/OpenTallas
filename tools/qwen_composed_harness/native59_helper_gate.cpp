// Explicit fixture-only integration gate: real helpers own VM read/write faces,
// one actual collector handle stays live across two distinct stage identities.
#include "native59_helpers.hpp"
#include <iostream>
#include <cstring>
struct Fixture {struct {unsigned done=0,fault=0,next_token=0,next_val=0;} core;struct {std::vector<uint32_t>vm=std::vector<uint32_t>(4096);void external_commit(unsigned a,uint32_t v,const char*){vm.at(a)=v;}} vm;};
static uint32_t bits(float f){uint32_t x;std::memcpy(&x,&f,4);return x;}
int main(int argc,char**argv){try{
 if(argc!=3&&argc!=4)throw std::runtime_error("persistent_so actual_segment_bank required");
 VerilatedContext ctx;ctx.threads(1);Native59Helpers link(ctx,argv[1]);link.banks(argv[2]);if(argc==4)link.mutate_first_actual_return_tag(std::stoul(argv[3]));
 std::array<std::unique_ptr<Fixture>,8>r;for(auto&x:r)x=std::make_unique<Fixture>();
 for(unsigned edge=0;edge<8;edge++){ctx.time(edge*833334ULL);link.low(r,false,false,0,1,0,0);link.rise(r);link.fall();}
 unsigned outputs=0;
 for(unsigned frame=0;frame<2;frame++){
  for(unsigned rank=0;rank<8;rank++){r[rank]->core.done=0;std::fill(r[rank]->vm.vm.begin(),r[rank]->vm.vm.end(),bits(float((rank+1)*(frame+1))));}
  bool begun=false,finished=false;
  for(unsigned edge=0;edge<12000&&!finished;edge++){
   ctx.timeInc(833334);bool begin=!begun&&link.ready();
   link.low(r,true,begin,0,frame+1,0,0);if(begin)begun=true;
   std::array<bool,8> start{};for(unsigned rank=0;rank<8;rank++)start[rank]=link.rank(rank).core_start;
   try{link.rise(r);}catch(const std::exception&){if(argc==4&&link.mutation_applied()&&link.rank(0).fault&&link.writes[0]==0){std::cout<<"DETECTED_ACTUAL_RETURN_TAG_MUTANT bit="<<argv[3]<<" rank0_VM_writes=0 helper_fault=1\n";return 0;}throw;}for(unsigned rank=0;rank<8;rank++)if(start[rank])r[rank]->core.done=1;
   link.fall();finished=begun&&edge>4&&link.drained();for(unsigned rank=0;rank<8;rank++)finished&=link.rank(rank).done;
  }
  if(!finished)throw std::runtime_error("actual helper/collector timeout");
  for(unsigned rank=0;rank<8;rank++){if(link.writes[rank]!=256*(frame+1)||link.sent[rank]!=256*(frame+1)||link.received[rank]!=256*(frame+1)||link.reads[rank]!=256*(frame+1))throw std::runtime_error("missing actual read/send/return/write effects");for(auto value:r[rank]->vm.vm){if(value!=bits(float(36*(frame+1))))throw std::runtime_error("actual helper returned numerical mismatch");++outputs;}}
 }
 if(argc==4)throw std::runtime_error("tag mutant escaped actual helper guard");
 std::cout<<"{\"scope\":\"ACTUAL_HELPER_PERSISTENT_COLLECTOR_VM_FIXTURE_COMPONENT_ONLY\",\"frames\":2,\"reset_after_boot\":0,\"exact_outputs\":"<<outputs<<",\"cycles\":"<<link.cycles()<<",\"core_bound\":false,\"HOST_bound\":false,\"whole_token\":false}\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";return 2;}}
