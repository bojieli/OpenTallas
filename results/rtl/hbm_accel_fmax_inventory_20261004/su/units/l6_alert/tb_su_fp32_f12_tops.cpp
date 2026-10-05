#include "Vtb_su_fp32_f12_tops.h"
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <random>
// stress classes: signed zeros, exact cancellation, wide exponents, subnormal results, plus random
static uint32_t rnd(std::mt19937_64& r){ return (uint32_t)r(); }
int main(int argc,char**argv){ long n=atol(argv[1]); std::mt19937_64 r(argc>2?atol(argv[2]):5);
  Vtb_su_fp32_f12_tops t; t.clk=0; t.rst_n=0; t.v=0; long bad[4]={0}; long cls[6]={0};
  for(long c=0;c<n+30;c++){ t.rst_n=c>4; uint32_t a=0,b=0; int k=r()%6;
    if(c>4&&c<n){ uint32_t s=r()&0x80000000u;
      switch(k){
      case 0: a=(r()%2)?0x80000000u:0; b=(r()%3==0)?((r()%2)?0x80000000u:0):rnd(r); if(r()%2){uint32_t x=a;a=b;b=x;} break; // signed zeros
      case 1: a=rnd(r)&0x7fffffffu; a|=s; b=a^0x80000000u; break;                       // exact cancellation (add) / x*-x
      case 2: a=s|((uint32_t)(1+r()%40)<<23)|(r()&0x7fffff); b=(r()&0x80000000u)|((uint32_t)(200+r()%54)<<23)|(r()&0x7fffff); break; // wide exponents
      case 3: a=s|((uint32_t)(r()%130)<<23)|(r()&0x7fffff); b=(r()&0x80000000u)|((uint32_t)(r()%130)<<23)|(r()&0x7fffff); break; // subnormal products
      case 4: a=(r()&0x807fffffu); b=(r()&0x807fffffu)|((uint32_t)(r()%3)<<23); break;            // subnormal sums / results
      default: a=rnd(r); b=rnd(r); }
      t.v=1; t.a=a; t.b=b; cls[k]++; } else t.v=0;
    t.clk=0; t.eval(); t.clk=1; t.eval();
    if(c>20) for(int i=0;i<4;i++) if(t.mism&(1<<i)) bad[i]++; }
  printf("SU_FP32_F12_TOPS_EQ n=%ld classes(zero,cancel,wideexp,subprod,subsum,rand)=%ld,%ld,%ld,%ld,%ld,%ld add_f12_l4=%ld add_f12_l5x=%ld mul_f12_l5=%ld mul_f12_l6=%ld\n",
    n,cls[0],cls[1],cls[2],cls[3],cls[4],cls[5],bad[0],bad[1],bad[2],bad[3]);
  return (bad[0]|bad[1]|bad[2]|bad[3])?1:0; }
