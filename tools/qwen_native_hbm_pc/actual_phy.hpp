#pragma once
#include <array>
#include <cstdint>
#include <deque>
#include <map>
#include <stdexcept>
#include <vector>
#include "Vqwen_native_hbm_pc_provider.h"
namespace qwen_actual_phy {
using Codeword = std::array<uint32_t,9>;
inline uint32_t bits(const uint32_t* w,unsigned offset,unsigned count) {
 uint64_t x=w[offset/32] >> (offset%32);
 if(offset%32 && count>32-offset%32)x|=uint64_t(w[offset/32+1])<<(32-offset%32);
 return uint32_t(x)&(count==32?~0u:((1u<<count)-1));
}
inline void put(uint32_t* w,unsigned offset,unsigned count,uint32_t value) {
 for(unsigned i=0;i<count;i++){unsigned b=offset+i;uint32_t m=1u<<(b%32);w[b/32]=(w[b/32]&~m)|(((value>>i)&1u)?m:0);}
}
inline uint64_t key(uint32_t row,uint32_t bank,uint32_t col){return (uint64_t(row)<<10)|(bank<<5)|col;}
// No expected payload or ECC encoder exists here. All memory writes copy actual
// po.wd; reads copy the exact stored 288-bit codeword in issue order.
class Backing {
 struct Pending {uint64_t due,address;};
 std::array<uint32_t,32> rows{}; std::array<bool,32> open{};
 std::deque<Pending> wr;
 struct Read {uint64_t due;Codeword word;}; std::deque<Read> rd;
 public:
 uint64_t h_edges=0,acts=0,pres=0,writes=0,reads=0,returns=0;
 std::map<uint64_t,Codeword> memory;
 std::vector<uint64_t> written_keys;
 unsigned read_latency=14; // authoritative tb_qkd_ctrl_pc_host RL=14
 bool corrupt_read=false;
 // Call BEFORE HBM rising eval, sampling settled output pins. After evaluating
 // that rising edge, assign the returned pi and eval again (SV NBA semantics).
 std::array<uint32_t,10> sample_hbm(const Vqwen_native_hbm_pc_provider& model){
  ++h_edges; std::array<uint32_t,10> pi{};
  if(!model.hrst){open.fill(false);wr.clear();rd.clear();return pi;}
  while(!wr.empty()&&wr.front().due==h_edges){
   Codeword w{};for(unsigned i=0;i<9;i++)w[i]=bits(model.po.data(),40+32*i,32);
   memory[wr.front().address]=w;written_keys.push_back(wr.front().address);wr.pop_front();++writes;
  }
  if(!rd.empty()&&rd.front().due==h_edges){
   auto w=rd.front().word;if(corrupt_read)w[0]^=0x28; // two real codeword data-bit errors
   put(pi.data(),0,1,1);for(unsigned i=0;i<9;i++)put(pi.data(),1+32*i,32,w[i]);
   rd.pop_front();++returns;
  }
  if(bits(model.po.data(),0,1)){
   auto bank=bits(model.po.data(),4,5),op=bits(model.po.data(),1,3);
   if(op==1){open[bank]=true;rows[bank]=bits(model.po.data(),9,19);++acts;}
   else if(op==0){open[bank]=false;++pres;}
  }
  if(bits(model.po.data(),28,1)){
   auto bank=bits(model.po.data(),30,5),col=bits(model.po.data(),35,5);
   if(!open[bank])throw std::runtime_error("column on closed bank");
   auto address=key(rows[bank],bank,col);
   if(bits(model.po.data(),29,1))wr.push_back({h_edges+5,address});
   else {auto it=memory.find(address);if(it==memory.end())throw std::runtime_error("read from unwritten physical address");rd.push_back({h_edges+read_latency,it->second});++reads;}
  }
  return pi;
 }
};
}
