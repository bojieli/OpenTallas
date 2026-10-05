#include "Vtb_hcp_ml.h"
#include <cstdio>
#include <random>
int main(){ std::mt19937 r(3); Vtb_hcp_ml t; t.clk=0; t.rst_n=0; long n5=0,b6=0,b6f=0;
 for(long c=0;c<400000;c++){ t.rst_n=c>4; t.v=c>4&&c<399900; for(int i=0;i<10;i++){ uint32_t e=100+r()%50; t.d[i]=((r()&1)<<31)|(e<<23)|(r()&0x7fffff);} 
  t.clk=0;t.eval();t.clk=1;t.eval(); if(c>40&&t.vo5){n5++; if(t.mism&1)b6++; if(t.mism&2)b6f++;} }
 printf("HCPOST_ML_LOCKSTEP outputs=%ld ml6_main_mismatch=%ld ml6_m4_follows_ML_mismatch=%ld\n",n5,b6,b6f); return 0;}
