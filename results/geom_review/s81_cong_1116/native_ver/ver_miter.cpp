#include "Vver_top.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
using Words=std::array<uint32_t,8>;
static uint64_t cycle_id=0,checks=0,resets=0;
static uint32_t rng_state=0x83a17f29U;
static uint32_t rng(){rng_state^=rng_state<<13;rng_state^=rng_state>>17;rng_state^=rng_state<<5;return rng_state;}
static unsigned bit(const Words&a,unsigned b){return(a[b/32]>>(b%32))&1U;}
static Words views(const Words&a,unsigned v){Words out{};unsigned pos=0;
 auto put=[&](unsigned b){out[pos/32]|=(b&1U)<<(pos%32);++pos;};
 auto data=[&](unsigned lo,unsigned n){for(unsigned j=0;j<n;++j)put(bit(a,lo+j));};
 auto valid=[&](unsigned ch){put((v>>ch)&1U);};
 valid(2);data(178,16);data(210,16);data(146,16);data(227,1);data(64,64);valid(1);data(129,1);valid(0);valid(2);data(162,16);data(194,16);data(130,16);data(226,1);valid(0);data(0,64);valid(1);data(128,1);valid(0);
 if(pos!=235)throw std::runtime_error("view shape");return out;
}
static void check(Vver_top&t,const Words&ref,unsigned valid,const char*phase){
 ++checks;
 for(unsigned j=0;j<8;++j)if(t.q1[j]!=ref[j])throw std::runtime_error(std::string("MISMATCH payload ")+phase+" cycle="+std::to_string(cycle_id)+" word="+std::to_string(j));
 if(t.v1!=valid)throw std::runtime_error(std::string("MISMATCH valid ")+phase+" cycle="+std::to_string(cycle_id)+" want="+std::to_string(valid)+" got="+std::to_string(t.v1));
 Words vw=views(ref,valid);for(unsigned j=0;j<8;++j)if(t.views[j]!=vw[j])throw std::runtime_error(std::string("MISMATCH terminal19 ")+phase+" cycle="+std::to_string(cycle_id));
}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);unsigned mut=argc>1?unsigned(std::stoul(argv[1])):0U;Vver_top t;Words ref{};unsigned ev=0;
 try{
 t.mutsel=mut;t.clk=0;t.rst_n=0;t.vin=0;for(unsigned j=0;j<8;++j)t.din[j]=0;t.eval();t.clk=1;t.eval();t.clk=0;t.eval();t.rst_n=1;t.eval();
 for(cycle_id=0;cycle_id<200000;++cycle_id){
  t.clk=0;t.eval();
  bool hold_reset=cycle_id>4093 && cycle_id%4093<3;
  if(hold_reset && t.rst_n){t.rst_n=0;t.eval();ev=0;++resets;check(t,ref,ev,"held_assert");}
  if(!hold_reset && !t.rst_n){t.rst_n=1;t.eval();check(t,ref,ev,"held_release");}
  if(!hold_reset && cycle_id>1000 && cycle_id%257==0){t.rst_n=0;t.eval();ev=0;++resets;check(t,ref,ev,"warm_low_assert");t.rst_n=1;t.eval();check(t,ref,ev,"warm_low_release");}
  Words stim{};if(cycle_id<228){stim[cycle_id/32]=uint32_t(1)<<(cycle_id%32);}else for(auto&w:stim)w=rng();stim[7]&=15U;
  unsigned vv=cycle_id<100000?7U:rng()&7U;
  for(unsigned j=0;j<8;++j)t.din[j]=stim[j];t.vin=vv;t.eval();
  //D1 must hold the previous capture while the nativeD0 reference already
  //shows the next producer word: this checks an actual clock of latency.
  check(t,ref,ev,"before_edge");
  Words captured{};for(unsigned j=0;j<8;++j)captured[j]=t.q0[j];unsigned cv=t.rst_n?t.v0:0U;
  t.clk=1;t.eval();ref=captured;ev=cv;check(t,ref,ev,"after_edge");
  if(!hold_reset && cycle_id>1000 && cycle_id%509==0){t.rst_n=0;t.eval();ev=0;++resets;check(t,ref,ev,"warm_high_assert");t.rst_n=1;t.eval();check(t,ref,ev,"warm_high_release");}
 }
 std::cout<<"PASS native_VER D0_to_D1 cycles="<<cycle_id<<" checks="<<checks<<" warm_resets="<<resets<<" payload_bits=228 valid_bits=3 terminal_views=235 groups=19 dense_cycles=100000 mutant="<<mut<<"\n";t.final();return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<" mutant="<<mut<<"\n";t.final();return 1;}
}
