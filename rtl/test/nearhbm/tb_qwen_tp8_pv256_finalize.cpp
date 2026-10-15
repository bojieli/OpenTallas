#include "Vot_qwen_tp8_pv256_finalize_tb.h"
#include "verilated.h"
#include <vector>
#include <string>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <cstdint>
template<class T>std::vector<T>rd(std::string p,size_t n){std::vector<T>x(n);std::ifstream f(p,std::ios::binary);if(!f.read((char*)x.data(),n*sizeof(T)))throw std::runtime_error(p);return x;}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);if(argc<3)return 2;
 std::string dir=argv[1],mode=argv[2];auto p0=rd<uint32_t>(dir+"/pair0.bin",512),p1=rd<uint32_t>(dir+"/pair1.bin",512),
  rz=rd<uint32_t>(dir+"/reciprocal.bin",4),gold=rd<uint32_t>(dir+"/gold.bin",512);
 Vot_qwen_tp8_pv256_finalize_tb d;uint64_t cyc=0,bad=0,outputs=0,first_output_age=0;unsigned acks0=0,acks1=0,acksr=0;
 auto tick=[&](){d.clk=0;d.eval();d.clk=1;d.eval();cyc++;};
 d.rst_n=0;d.start=0;d.p0_valid=0;d.p1_valid=0;d.reciprocal_valid=0;d.out_ready=0;tick();tick();d.rst_n=1;tick();
 d.epoch=71;d.start=1;tick();d.start=0;
 const auto start_edge=cyc;
 for(unsigned i=0;i<512;i++){d.p0_partial[i]=p0[i];d.p1_partial[i]=p1[i];}
 if(mode=="data")d.p0_partial[19]^=0x80000000u;
 for(unsigned i=0;i<4;i++)d.reciprocal[i]=rz[i];
 if(mode=="reciprocal_data")d.reciprocal[2]^=0x80000000u;
 d.p0_epoch=mode=="epoch"?70:71;d.p1_epoch=71;d.reciprocal_epoch=mode=="reciprocal_epoch"?70:71;
 uint32_t saved[512]={0};bool held=false,stable=true;
 while(cyc<1000){
  d.p0_valid=!acks0&&cyc>7;d.p1_valid=!acks1&&cyc>19;
  // Denominator reciprocal may become ready after both pair partials.
  d.reciprocal_valid=!acksr&&cyc>47;
  d.out_ready=mode=="steady"||(cyc>100&&cyc%7!=2);
#ifdef PV_STATIC
  const auto age=cyc-start_edge+1;
  d.p0_valid=age==8;d.p1_valid=age==20;d.reciprocal_valid=age==48;
  if(mode=="missing0")d.p0_valid=0;
  if(mode=="missing1")d.p1_valid=0;
  if(mode=="missing_r")d.reciprocal_valid=0;
  if(mode=="late0")d.p0_valid=age==9;
  if(mode=="early1")d.p1_valid=age==19;
  d.out_ready=mode!="output_late";
#endif
  d.start=mode=="restart"&&cyc==22;
  d.clk=0;d.eval();
  if(d.p0_valid&&d.p0_ready)acks0++;if(d.p1_valid&&d.p1_ready)acks1++;if(d.reciprocal_valid&&d.reciprocal_ready)acksr++;
  if(d.out_valid){
   if(!held){for(unsigned i=0;i<512;i++)saved[i]=d.out_data[i];held=true;}
   else for(unsigned i=0;i<512;i++)stable &= saved[i]==d.out_data[i];
   if(d.out_ready){if(!outputs)first_output_age=cyc-start_edge+1;outputs++;for(unsigned i=0;i<512;i++)bad+=d.out_data[i]!=gold[i];if(d.out_epoch!=71)return 3;}
  }
  tick();
  if(d.fault){bool expected=mode=="epoch"||mode=="reciprocal_epoch"||mode=="restart"||mode=="missing0"||mode=="missing1"||mode=="missing_r"||mode=="late0"||mode=="early1"||mode=="output_late";
   std::cout<<"{\"mode\":\""<<mode<<"\",\"observed_fault\":true,\"cycles\":"<<cyc<<"}\n";return expected?0:1;}
  if(outputs&&cyc>120)break;
 }
 bool mutated=mode=="data"||mode=="reciprocal_data";
 bool pass=outputs==1&&acks0==1&&acks1==1&&acksr==1&&stable&&(mutated?bad>0:bad==0);
 std::cout<<"{\"mode\":\""<<mode<<"\",\"cycles\":"<<cyc<<",\"first_output_age\":"<<first_output_age<<",\"output_batches\":"<<outputs<<",\"output_words\":"<<outputs*512
  <<",\"mismatches\":"<<bad<<",\"acks\":["<<acks0<<","<<acks1<<","<<acksr<<"],\"stable\":"<<(stable?"true":"false")<<",\"pass\":"<<(pass?"true":"false")<<"}\n";
 return pass?0:1;
}
