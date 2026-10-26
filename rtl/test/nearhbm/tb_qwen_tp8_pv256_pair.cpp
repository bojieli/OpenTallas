#include "Vot_qwen_tp8_pv256_pair_tb.h"
#include "verilated.h"
#include <fstream>
#include <vector>
#include <string>
#include <iostream>
#include <stdexcept>
#include <cstdint>
#include <cstring>
template<class T>std::vector<T>rd(std::string p,size_t n){std::vector<T>x(n);std::ifstream f(p,std::ios::binary);if(!f.read((char*)x.data(),n*sizeof(T)))throw std::runtime_error(p);return x;}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);if(argc<4)return 2;
 std::string dir=argv[1],mode=argv[3];unsigned pair=std::stoul(argv[2]);unsigned ctx=argc>4?std::stoul(argv[4]):8192;if(pair>1||ctx>16383)throw std::runtime_error("PAIR/context exceeds RTL port capacity");
 auto v=rd<uint8_t>(dir+"/v-fp8.bin",8192*128);auto e=rd<uint16_t>(dir+"/exp-bf16.bin",8192*4);
 auto gold=rd<uint32_t>(dir+"/leaves.bin",4*256*128);
 if(ctx!=8192&&ctx<=8192){auto prod=rd<uint32_t>(dir+"/products.bin",4*8192*128);std::fill(gold.begin(),gold.end(),0);
  for(unsigned h=0;h<4;h++)for(unsigned r=0;r<256;r++)for(unsigned t=r;t<ctx;t+=256)for(unsigned j=0;j<128;j++){
   auto &dst=gold[(h*256+r)*128+j];uint32_t src=prod[(h*8192+t)*128+j];float a,b;std::memcpy(&a,&dst,4);std::memcpy(&b,&src,4);volatile float z=a+b;float zz=z;std::memcpy(&dst,&zz,4);if(!(dst&0x7fffffff))dst=0;
  }
 }
#ifdef PV_TREE
 for(unsigned h=0;h<4;h++)for(unsigned j=0;j<128;j++){
  uint32_t a[128];for(unsigned r=0;r<128;r++)a[r]=gold[(h*256+pair*128+r)*128+j];
  for(unsigned ns=128;ns>1;ns/=2)for(unsigned r=0;r<ns/2;r++){float x,y;std::memcpy(&x,&a[2*r],4);std::memcpy(&y,&a[2*r+1],4);volatile float z=x+y;float zz=z;std::memcpy(&a[r],&zz,4);if(!(a[r]&0x7fffffff))a[r]=0;}
  gold[(h*256+pair*128)*128+j]=a[0];
 }
 const unsigned expected_leaves=1;const std::string profile="tree";
#else
 const unsigned expected_leaves=128;const std::string profile="leaf";
#endif
 Vot_qwen_tp8_pv256_pair_tb d;unsigned c=0,n=0,leaves=0,frame=0,run_epoch=71;uint64_t cyc=0,bad=0,words=0;
 auto tick=[&](){d.clk=0;d.eval();d.clk=1;d.eval();cyc++;};
 d.rst_n=0;d.start=0;d.in_valid=0;d.out_ready=0;tick();tick();d.rst_n=1;tick();
 d.context_len=ctx;d.epoch=71;d.start=1;tick();d.start=0;bool sent=ctx<=pair*128;
 uint64_t start_edge=cyc;
 uint64_t feed_end=0;std::ofstream actual("actual-"+profile+"-p"+std::to_string(pair)+"-"+mode+"-"+std::to_string(ctx)+".bin",std::ios::binary);
 while(cyc<100000){unsigned t=sent?0:pair*128+c+256*n;d.in_valid=!sent && (mode=="steady"||cyc%7!=2);
#ifdef PV_STATIC
 const auto age=cyc-start_edge+1;
 d.in_valid=!sent && age>=146;
 if(mode=="gap"&&age==146)d.in_valid=0;
 if(mode=="early"&&age==145)d.in_valid=1;
#endif
 d.in_c=c;d.in_t=t;d.in_epoch=run_epoch;d.in_first=n==0;d.in_last=t+256>=ctx;
 if(t==pair*128){if(mode=="epoch")d.in_epoch=70;if(mode=="order")d.in_t^=1;if(mode=="first")d.in_first^=1;if(mode=="last")d.in_last^=1;}
 for(unsigned b=0;b<32;b++){uint32_t q=0;for(unsigned k=0;k<4;k++)q|=(uint32_t)v[(t<8192?t:0)*128+4*b+k]<<(8*k);if(mode=="data"&&t==pair*128&&b==0)q^=0x80;d.in_v[b]=q;}
 uint64_t ex=0;for(unsigned h=0;h<4;h++)ex|=(uint64_t)e[(t<8192?t:0)*4+h]<<(16*h);d.in_e=ex;
 d.start=(mode=="restart"&&cyc==100);d.out_ready=mode=="steady"||cyc%11!=4;d.clk=0;d.eval();
#ifdef PV_STATIC
 d.out_ready=mode!="output_late";d.eval();
#endif
 if(d.out_valid&&d.out_ready){if(d.out_c!=leaves)return 2;
  for(unsigned h=0;h<4;h++)for(unsigned j=0;j<128;j++){uint32_t x=d.out_leaf[h*128+j];words++;bad+=x!=gold[(h*256+pair*128+leaves)*128+j];actual.write((char*)&x,4);}leaves++;}
 bool take=d.in_valid&&d.in_ready;tick();
 if(d.fault){std::cout<<"{\"pair\":"<<pair<<",\"mode\":\""<<mode<<"\",\"observed_fault\":true,\"cycles\":"<<cyc<<"}\n";return(mode=="epoch"||mode=="order"||mode=="first"||mode=="last"||mode=="restart"||mode=="context"||mode=="gap"||mode=="early"||mode=="output_late")?0:1;}
 if(take){if(c==127||t+1>=ctx){c=0;n++;if(pair*128+256*n>=ctx){sent=true;feed_end=cyc;}}else c++;}
 if(leaves==expected_leaves&&!d.busy){
  if(mode=="reframe"&&frame==0){
   // Reuse the live SRAM after a full frame, without reset. All absent
   // residues in the following context=1 frame must be canonical +0.
   auto prod=rd<uint32_t>(dir+"/products.bin",4*8192*128);
   std::fill(gold.begin(),gold.end(),0);
   for(unsigned h=0;h<4;h++)for(unsigned j=0;j<128;j++)gold[(h*256)*128+j]=prod[(h*8192)*128+j];
   frame=1;ctx=1;run_epoch=72;c=0;n=0;leaves=0;sent=pair==1;
   d.context_len=ctx;d.epoch=run_epoch;d.in_valid=0;d.start=1;tick();d.start=0;
   start_edge=cyc;
  }else break;
 }
 }
 std::cout<<"{\"pair\":"<<pair<<",\"mode\":\""<<mode<<"\",\"context\":"<<ctx<<",\"cycles\":"<<cyc<<",\"feed_end\":"<<feed_end<<",\"rows\":"<<d.accepted<<",\"committed\":"<<d.committed<<",\"peak_inflight\":"<<(unsigned)d.peak_inflight<<",\"words\":"<<words<<",\"mismatches\":"<<bad<<"}\n";
 return leaves==expected_leaves&&((mode=="data")?bad>0:bad==0)?0:1;
}
