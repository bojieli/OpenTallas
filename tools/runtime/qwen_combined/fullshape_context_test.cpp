#include "fullshape_context.hpp"
#include <cassert>
#include <vector>
#include <tuple>
#include <iostream>
using namespace qwen_combined;
template<class F> void refusal(F f) { bool refused=false;try { f(); }catch(const std::exception&) {refused=true;}assert(refused); }
int main() {
  require_join_geometry(6144,64,18,44,true,true);
  refusal([]{require_join_geometry(4,64,18,44,true,true);});
  refusal([]{require_join_geometry(6144,64,18,40,true,true);});
  refusal([]{require_join_geometry(6144,64,18,44,false,true);});
  refusal([]{require_join_geometry(6144,64,18,44,true,false);});
  Context c{3,35,128,151935};
  // Source constants independent of locate's algebra, matching held RTL ports.
  auto k=locate(c,Kind::K,1,127),v=locate(c,Kind::V,1,127);
  assert(k.scalar_address==1066992 && k.sector_address==4620863 && k.byte_in_sector==16);
  assert(k.tile==287 && k.slice_word==1 && k.byte_in_slice==48);
  assert(v.scalar_address==3162239 && v.sector_address==4686339 && v.byte_in_sector==31);
  assert(v.tile==928 && v.slice_word==23 && v.byte_in_slice==15);
  // Every E4M3 payload byte has a unique HBM and tile home, all 8192 positions.
  // No simulated response or arithmetic oracle is invoked by this check.
  std::vector<unsigned char> hbm(131072*32);
  std::vector<unsigned char> sram(tiles*128*64);
  uint64_t checked=0;
  for(unsigned p=0;p<positions;p++) for(unsigned h=0;h<2;h++) for(unsigned d=0;d<128;d++) for(auto kind:{Kind::K,Kind::V}) {
    auto x=locate({0,0,p,11},kind,h,d);
    auto hi=x.sector_address*32+x.byte_in_sector; assert(!hbm.at(hi)); hbm.at(hi)=1;
    auto si=(x.tile*128+x.slice_word)*64+x.byte_in_slice; assert(!sram.at(si)); sram.at(si)=1; ++checked;
    auto y=locate({0,35,p,11},kind,h,d);
    assert(y.sector_address-x.sector_address==35*layer_sectors);
    assert(y.stack==x.stack && y.scalar_address==x.scalar_address);
  }
  c={0,0,5,11}; auto a=collective_tag(c,1,7); c.position=261;
  auto b=collective_tag(c,1,7);assert(a!=b && b-a==(uint64_t(256)<<24));
  c.position=8191;assert((collective_tag(c,3,63)>>42)==3);
  refusal([]{locate({0,0,8192,11},Kind::K,0,0);});
  refusal([]{locate({4,0,128,11},Kind::K,0,0);});
  refusal([]{locate({0,36,128,11},Kind::K,0,0);});
  refusal([]{locate({0,0,128,151936},Kind::K,0,0);});
  refusal([]{collective_tag({0,0,128,11},4,0);});
  refusal([]{locate({0,0,128,11},Kind::K,2,0);});
  std::cout<<"PASS fullshape_raw_context_locations="<<checked<<"; geometry/position-alias/bounds mutants rejected; no RTL/token credit\n";
}
