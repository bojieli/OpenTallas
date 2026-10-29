#include "Vprofile_eq.h"
#include <random>
#include <cstdio>
#include <cstdlib>
int main(int argc,char**argv){Vprofile_eq t;std::mt19937 r(20261028);unsigned bad=0,n=0;t.mut=argc>1;for(unsigned c=0;c<200024;c++){t.rst_n=(c%50000)>5;t.v=(r()%8)!=0;t.a=r();t.b=r();if(c%4==0)t.a=(r()&0x807fffff);t.clk=0;t.eval();t.clk=1;t.eval();if((c%50000)>20){bad+=t.mism!=0;n++;}}printf("PROFILE_EQ compare=%u mismatches=%u mutant=%u\n",n,bad,t.mut);return bad?1:0;}
