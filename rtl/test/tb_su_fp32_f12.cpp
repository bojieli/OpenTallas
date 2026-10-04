// hbm-fmax-su: drives tb_su_fp32_f12 (same biased stimulus as tb_w11_fp32_{add,mul}_lat.cpp, plus subnormal pairs)
#include "Vtb_su_fp32_f12.h"
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <random>
#include <cstring>
#include <cmath>
static float f_(uint32_t u){float f; memcpy(&f,&u,4); return f;}
static uint32_t u_(float f){uint32_t u; memcpy(&u,&f,4); return u;}
static uint32_t pick(std::mt19937_64& r){
  uint32_t s=r()&0x80000000u; int k=r()%16; uint32_t e,m=r()&0x7fffff;
  if(k==0) e=0; else if(k==1) e=255; else if(k==2){e=0;m=0;} else if(k<6) e=1+r()%3; else if(k<8) e=250+r()%5; else e=r()%256;
  if(k==3) m &= (0x7fffff >> (r()%23));          // subnormal-ish / short fractions
  return s|(e<<23)|m;}
int main(int argc,char**argv){
  long n=argc>1?atol(argv[1]):2000000; uint64_t seed=argc>2?strtoull(argv[2],0,0):12345; std::mt19937_64 r(seed);
  Vtb_su_fp32_f12 t; t.clk=0; t.rst_n=0; t.v=0; t.a=0;t.b=0;
  long bad[11]={0}, cmp=0;
  for(long c=0;c<n+24;c++){
    t.rst_n = c>4;
    if(c>4 && c<n){ uint32_t a=pick(r), b;
      int k=r()%7; if(k==0){ b=a^0x80000000u; b = (b & ~0x7u) | (r()&7);} else if(k==1){ b=(a^0x80000000u)+ (int)(r()%5)-2;}
      else if(k==2){ b=(r()&0x80000000u)|(r()&0x7fffff);}            // a subnormal operand
      else if(k==3){ b=(r()&0x80000000u)|((uint32_t)(253-((a>>23)&0xff)+(int)(r()%5)-2)&0xff)<<23|(r()&0x7fffff);} // product near over/underflow
      else if(k==4){ float q=(r()%2?2.0f:1.0f)/f_(a); b=u_(q)+(int)(r()%5)-2; if(r()%4==0) b=(b&0x807fffffu)|((uint32_t)(r()%256)<<23); } // rounding carry
      else b=pick(r);
      t.v=r()%8!=0; t.a=a; t.b=b; } else t.v=0;
    t.clk=0; t.eval(); t.clk=1; t.eval();
    if(c>20) for(int i=0;i<11;i++) if(t.mism&(1<<i)) bad[i]++;
    cmp++;
  }
  printf("SU_FP32_F12_EQ cycles=%ld seed=%llu add_l4=%ld add_l5=%ld add_l5a=%ld add_l6=%ld mul_l5=%ld mul_l6b=%ld mul_l6=%ld mul_l7=%ld add_l5i=%ld mul_l6i=%ld add_l5x=%ld\n",
         cmp,(unsigned long long)seed,bad[0],bad[1],bad[2],bad[3],bad[4],bad[5],bad[6],bad[7],bad[8],bad[9],bad[10]);
  long s=0; for(int i=0;i<11;i++) s|=bad[i]; return s?1:0;}
