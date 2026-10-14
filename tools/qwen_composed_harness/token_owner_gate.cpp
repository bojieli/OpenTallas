#include "token_epoch_owner.hpp"
#include <iostream>
int main(int argc,char**argv){try{
 if(argc!=2)throw std::runtime_error("fresh output directory required");std::filesystem::create_directories(argv[1]);
 VerilatedContext ctx;TokenEpochOwner owner(ctx,0,0,0);
 for(unsigned edge=0;edge<20;edge++){
  ctx.time(833334ULL*edge);owner.low(edge>=2,edge>=8);owner.rise();owner.fall();
  if(edge<8&&owner.delivered)throw std::runtime_error("grant delivered before receiver readiness");
 }
 if(!owner.delivered||owner.held_epoch!=0||owner.held_tag!=0||owner.grant_edge!=9)throw std::runtime_error("real epoch0 grant not held/delivered at observed edge");
 for(unsigned layer=0;layer<36;layer++)for(unsigned segment=0;segment<3;segment++)owner.identities(std::filesystem::path(argv[1])/("stage"+std::to_string(layer+1)+"_segment"+std::to_string(segment)+".json"),layer+1,segment);
 owner.save(std::filesystem::path(argv[1])/"held_grant.json");
 std::cout<<"PASS_ACTUAL_CENTRAL_EPOCH0_HELD_GRANT_BINDING edges="<<owner.edges<<" grant_edge="<<owner.grant_edge<<" busy="<<unsigned(owner.rtl.busy)<<" terminal_bound=0 link_fence_bound=0\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
