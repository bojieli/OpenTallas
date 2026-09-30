#include "Vtb_w11_fp32_add_lat.h"
#include <cstdio>
#include <cstdint>
#include <random>
static uint32_t pick(std::mt19937_64& r){
  uint32_t s=r()&0x80000000u; int k=r()%16; uint32_t e,m=r()&0x7fffff;
  if(k==0) e=0; else if(k==1) e=255; else if(k==2){e=0;m=0;} else if(k<6) e=1+r()%3; else if(k<8) e=250+r()%5; else e=r()%256;
  return s|(e<<23)|m;}
int main(int argc,char**argv){
  long n=argc>1?atol(argv[1]):2000000; std::mt19937_64 r(12345);
  Vtb_w11_fp32_add_lat t; t.clk=0; t.rst_n=0; t.v=0; t.a=0;t.b=0;
  long bad[4]={0,0,0,0}, cmp=0;
  for(long c=0;c<n+20;c++){
    t.rst_n = c>4; 
    if(c>4 && c<n){ uint32_t a=pick(r), b;
      int k=r()%4; if(k==0){ b=a^0x80000000u; b = (b & ~0x7u) | (r()&7);} else if(k==1){ b=(a^0x80000000u)+ (int)(r()%5)-2;} else b=pick(r);
      t.v=1; t.a=a; t.b=b; } else t.v=0;
    t.clk=0; t.eval(); t.clk=1; t.eval();
    for(int i=0;i<4;i++) if(t.mism&(1<<i)) bad[i]++;
    cmp++;
  }
  printf("W11_FPADD_EQ cycles=%ld mism_lat3=%ld lat4=%ld lat5=%ld lat6=%ld\n",cmp,bad[0],bad[1],bad[2],bad[3]);
  return (bad[0]|bad[1]|bad[2]|bad[3])?1:0;}
