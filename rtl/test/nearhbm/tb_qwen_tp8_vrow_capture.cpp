#include "Vot_qwen_tp8_vrow_capture.h"
#include "verilated.h"
#include <array>
#include <deque>
#include <cstdio>
#ifndef CAPTURE_LATENCY
#define CAPTURE_LATENCY 1
#endif
struct Beat{unsigned valid=0,slot=0,tag=0,epoch=0;std::array<unsigned,64>rows{};};
int main(){
 Vot_qwen_tp8_vrow_capture t;auto tick=[&](){t.clk=0;t.eval();t.clk=1;t.eval();};
 t.rst_n=0;t.in_valid=t.in_slot=t.in_t=t.in_epoch=0;for(int i=0;i<64;i++)t.in_rows[i]=0;
 tick();t.rst_n=1;std::deque<Beat> expected;unsigned errors=0,words=0;
 for(unsigned cy=0;cy<512+CAPTURE_LATENCY;cy++){
  Beat b;if(cy<512){b.valid=cy%7==6?1:3;b.slot=(cy&7)|(((cy+1)&7)<<3);
   b.tag=(cy&16383)|(((cy+4096)&16383)<<14);b.epoch=(17+cy)|((77+cy)<<16);
   for(unsigned i=0;i<64;i++)b.rows[i]=(0x10204081u*(cy+1))^(0x01010101u*i);
  }
  t.in_valid=b.valid;t.in_slot=b.slot;t.in_t=b.tag;t.in_epoch=b.epoch;
  for(int i=0;i<64;i++)t.in_rows[i]=b.rows[i];expected.push_back(b);tick();
  Beat want;if(expected.size()>=CAPTURE_LATENCY){want=expected.front();expected.pop_front();}
  if(t.out_valid!=want.valid)errors++;
  for(unsigned face=0;face<2;face++)if(want.valid&(1u<<face)){
   if(((t.out_slot>>(3*face))&7)!=((want.slot>>(3*face))&7))errors++;
   if(((t.out_t>>(14*face))&16383)!=((want.tag>>(14*face))&16383))errors++;
   if(((t.out_epoch>>(16*face))&65535)!=((want.epoch>>(16*face))&65535))errors++;
   for(unsigned i=32*face;i<32*(face+1);i++){if(t.out_rows[i]!=want.rows[i])errors++;words++;}
  }
 }
 std::printf("{\"scope\":\"V_ROW_CAPTURE_COMPONENT_ONLY\",\"latency\":%u,\"words\":%u,\"errors\":%u,\"exact\":%s}\n",CAPTURE_LATENCY,words,errors,errors?"false":"true");
 return errors!=0;
}
