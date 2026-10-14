#include "Vot_qwen_tp8_vrow_prod_tb.h"
#include "verilated.h"
#include <fstream>
#include <iostream>
#include <vector>
#include <deque>
#include <string>
#include <algorithm>
#include <cstdint>
#include <stdexcept>
template<class T>std::vector<T>read(const std::string&p,size_t n){std::vector<T>a(n);std::ifstream f(p,std::ios::binary);if(!f.read((char*)a.data(),n*sizeof(T)))throw std::runtime_error("vector "+p);return a;}
struct Reply{unsigned slot,t;uint64_t due;};
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);if(argc!=4)return 2;
 std::string dir=argv[1],mode=argv[3];unsigned pair=std::stoul(argv[2]);
 auto v=read<uint8_t>(dir+"/v-fp8.bin",8192*128);
 auto e=read<uint16_t>(dir+"/exp-bf16.bin",8192*4);
 auto p=read<uint32_t>(dir+"/products.bin",8192*4*128);
 std::vector<unsigned>order;for(unsigned g=0;g<16;g++)for(unsigned n=0;n<32;n++)for(unsigned j=0;j<8;j++)order.push_back(pair*128+8*g+j+256*n);
 Vot_qwen_tp8_vrow_prod_tb d;uint64_t cyc=0,errors=0,words=0,rows=0,reordered=0;unsigned wanted=0,emitted=0;
 std::vector<Reply> replies;std::deque<unsigned>mul_tags;
 auto tick=[&](){d.clk=0;d.eval();d.clk=1;d.eval();cyc++;};
 d.rst_n=0;d.start=0;d.want_valid=0;d.lo_rsp_valid=0;d.hi_rsp_valid=0;d.out_ready=0;tick();tick();d.rst_n=1;tick();
 d.start=1;d.epoch=52;d.context_len=8192;tick();d.start=0;
 while(cyc<100000){
  d.want_valid=wanted<order.size();d.want_t=wanted<order.size()?order[wanted]:0;
  if(mode=="order"&&wanted==8)d.want_t^=256;
  d.lo_req_ready=cyc%5!=2;d.hi_req_ready=cyc%7!=3;
  d.out_ready=cyc%11!=4;
  d.lo_rsp_valid=0;d.hi_rsp_valid=0;
  int chosen=-1;
  // Reverse due-slot selection exercises genuine out-of-order memory responses.
  for(int i=0;i<(int)replies.size();i++)if(replies[i].due<=cyc)chosen=i;
  if(chosen>=0&&cyc%3!=1){
   Reply r=replies[chosen];if(chosen>0)reordered++;
   bool upper=(r.t>>8)&1;
   d.lo_rsp_slot=r.slot;d.hi_rsp_slot=r.slot;d.lo_rsp_t=r.t;d.hi_rsp_t=r.t;
   d.lo_rsp_epoch=52;d.hi_rsp_epoch=52;
   if(mode=="epoch"&&r.t==pair*128+256){d.lo_rsp_epoch=51;d.hi_rsp_epoch=51;}
   if(mode=="tag"&&r.t==pair*128+256){d.lo_rsp_t^=1;d.hi_rsp_t^=1;}
   for(unsigned b=0;b<32;b++){
    uint32_t q=0;for(unsigned k=0;k<4;k++)q|=(uint32_t)v[r.t*128+b*4+k]<<(8*k);
    if(mode=="data"&&r.t==pair*128+256&&b==0)q^=0x80;
    d.lo_vrow[b]=q;d.hi_vrow[b]=q;
   }
   uint64_t exp=0;for(unsigned h=0;h<4;h++)exp|=(uint64_t)e[r.t*4+h]<<(16*h);
   d.lo_exp=exp;d.hi_exp=exp;d.lo_rsp_valid=!upper;d.hi_rsp_valid=upper;
  }
  d.clk=0;d.eval();
  if(d.want_valid&&d.want_ready)wanted++;
  bool issued=(d.lo_req_valid&&d.lo_req_ready)||(d.hi_req_valid&&d.hi_req_ready);
  Reply fresh{(unsigned)d.req_slot,(unsigned)d.req_t,cyc+2+(d.req_t%5)};
  bool returned=(d.lo_rsp_valid&&d.lo_rsp_ready)||(d.hi_rsp_valid&&d.hi_rsp_ready);
  if(returned)replies.erase(replies.begin()+chosen);
  if(issued)replies.push_back(fresh);
  if(d.out_valid&&d.out_ready){if(emitted>=order.size()||d.out_t!=order[emitted])return 2;mul_tags.push_back(d.out_t);emitted++;rows++;}
  tick();
  if(d.fault){std::cout<<"{\"observed_fault\":true,\"pair\":"<<pair<<",\"cycles\":"<<cyc<<",\"mutant\":\""<<mode<<"\"}\n";return (mode=="epoch"||mode=="tag"||mode=="order")?0:1;}
  if(d.product_valid){
   if(mul_tags.empty()||d.product_fault)return 2;
   unsigned t=mul_tags.front();mul_tags.pop_front();
   for(unsigned h=0;h<4;h++)for(unsigned j=0;j<128;j++){errors+=(d.products[h*128+j]!=p[(h*8192+t)*128+j]);words++;}
  }
  if(emitted==4096&&mul_tags.empty())break;
 }
 if(rows!=4096||words!=4096*512||!replies.empty()||cyc>=100000)return 2;
 std::cout<<"{\"pair\":"<<pair<<",\"cycles\":"<<cyc<<",\"rows\":"<<rows<<",\"product_words\":"<<words<<",\"mismatches\":"<<errors<<",\"out_of_order_responses\":"<<reordered<<",\"mutant\":\""<<mode<<"\"}\n";
 return mode=="data"?!errors:(errors||mode!="none");
}
