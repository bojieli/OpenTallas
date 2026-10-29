#include "Vprofile_eq.h"
#include <random>
#include <cstdio>
#include <cstdlib>
int main(int argc,char**argv){Vprofile_eq t;std::mt19937 r(20261029);unsigned bad=0,n=0,classes[4]={};
const unsigned sp[]={0,0x80000000,1,0x7fffff,0x800000,0x3f800000,0xbf800000,0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,0x7fc00001,0x7f800001,0x800001,0x3f000000,0x1234};
t.mut=argc>1?std::atoi(argv[1]):0;
for(unsigned c=0;c<100024;c++){t.rst_n=(c%25000)>5;t.v=(r()%8)!=0;t.a=r();t.b=r();if(c<4096){t.a=sp[c%16];t.b=sp[(c/16)%16];}else if(c%4==0){t.a=r()&0x807fffff;}t.clk=0;t.eval();t.clk=1;t.eval();if((c%25000)>20){bad+=t.mismatch!=0;for(int i=0;i<4;i++)classes[i]+=(t.mismatch>>i)&1;n++;}}
printf("NATIVE_F12 compare=%u bad=%u classes_add4_mul4_mul5_date=%u,%u,%u,%u mutant=%u\n",n,bad,classes[0],classes[1],classes[2],classes[3],t.mut);return bad?1:0;}
