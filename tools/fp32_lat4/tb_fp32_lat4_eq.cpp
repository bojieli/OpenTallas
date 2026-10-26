// FP32 lane driver for tb_fp32_lat4_eq: (1) every ordered pair of 72 directed special values (signed zeros, smallest /
// largest subnormals, smallest normal, 1 +- ulp, halfway ties, max finite, inf, quiet / signalling NaN payloads,
// exponent-difference edges 23..28), (2) biased random (rtl/test/tb_su_fp32_f12.cpp stimulus classes).
#include "Vtb_fp32_lat4_eq.h"
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <random>
#include <cstring>
#include <vector>
static float f_(uint32_t u){float f; memcpy(&f,&u,4); return f;}
static uint32_t u_(float f){uint32_t u; memcpy(&u,&f,4); return u;}
static uint32_t pick(std::mt19937_64& r){
  uint32_t s=r()&0x80000000u; int k=r()%16; uint32_t e,m=r()&0x7fffff;
  if(k==0) e=0; else if(k==1) e=255; else if(k==2){e=0;m=0;} else if(k<6) e=1+r()%3; else if(k<8) e=250+r()%5; else e=r()%256;
  if(k==3) m &= (0x7fffff >> (r()%23));
  return s|(e<<23)|m;}
static const char* NAMES[14]={"add_lat4","add_lat4i","add_lat5","add_f12_l4","add_f12_l5","add_f12_l5x","add_f12_l5s",
  "s81_ve_fadd_l4","mul_f12_l5","mul_f12_l6","mul_lat4","mul_lat5","s81_ve_fmul_l5","add_lat6"};
int main(int argc,char**argv){
  long n=argc>1?atol(argv[1]):2000000; uint64_t seed=argc>2?strtoull(argv[2],0,0):12345; std::mt19937_64 r(seed);
  std::vector<uint32_t> sp={0x00000000u,0x00000001u,0x00000002u,0x003fffffu,0x00400000u,0x007ffffeu,0x007fffffu,
    0x00800000u,0x00800001u,0x00ffffffu,0x01000000u,0x0b800000u,0x0c000000u,0x0c000001u,0x33800000u,0x34000000u,
    0x3f7fffffu,0x3f800000u,0x3f800001u,0x3f800002u,0x3fc00000u,0x3fffffffu,0x40000000u,0x4b000000u,0x4b000001u,
    0x4b800000u,0x4c000000u,0x4c800000u,0x4d000000u,0x7effffffu,0x7f000000u,0x7f7ffffeu,0x7f7fffffu,0x7f800000u,
    0x7f800001u,0x7fc00000u};
  size_t ns=sp.size(); for(size_t i=0;i<ns;i++) sp.push_back(sp[i]^0x80000000u);     // 72 values
  long bad[14]={0}, cmp=0, dir=0;
  Vtb_fp32_lat4_eq t; t.clk=0; t.rst_n=0; t.v=0; t.a=0; t.b=0;
  long ndir=(long)(sp.size()*sp.size());
  long total=8+ndir+n+24;
  for(long c=0;c<total;c++){
    t.rst_n = c>4;
    long k=c-8;
    if(k>=0 && k<ndir){ t.a=sp[k/sp.size()]; t.b=sp[k%sp.size()]; t.v=1; dir++; }
    else if(k>=ndir && k<ndir+n){ uint32_t a=pick(r), b; int q=r()%7;
      if(q==0){ b=a^0x80000000u; b=(b&~0x7u)|(r()&7);} else if(q==1){ b=(a^0x80000000u)+(int)(r()%5)-2;}
      else if(q==2){ b=(r()&0x80000000u)|(r()&0x7fffff);}
      else if(q==3){ b=(r()&0x80000000u)|((uint32_t)(253-((a>>23)&0xff)+(int)(r()%5)-2)&0xff)<<23|(r()&0x7fffff);}
      else if(q==4){ float qq=(r()%2?2.0f:1.0f)/f_(a); b=u_(qq)+(int)(r()%5)-2; if(r()%4==0) b=(b&0x807fffffu)|((uint32_t)(r()%256)<<23);}
      else if(q==5){ int d=23+(int)(r()%6); uint32_t ea=(a>>23)&0xff; b=(r()&0x80000000u)|((uint32_t)((ea>(uint32_t)d)?ea-d:0)<<23)|(r()&0x7fffff);} // align-out edges
      else b=pick(r);
      t.v=r()%8!=0; t.a=a; t.b=b; }
    else t.v=0;
    t.clk=0; t.eval(); t.clk=1; t.eval();
    if(c>20) for(int i=0;i<14;i++) if(t.mism&(1<<i)) bad[i]++;
    cmp++;
  }
  printf("FP32_LAT4_EQ cycles=%ld directed_pairs=%ld random=%ld seed=%llu\n",cmp,dir,n,(unsigned long long)seed);
  long s=0; for(int i=0;i<14;i++){ printf("  %-16s mismatches=%ld\n",NAMES[i],bad[i]); s|=bad[i]; }
  printf("FP32_LAT4_EQ %s\n", s?"FAIL":"PASS");
  return s?1:0;}
