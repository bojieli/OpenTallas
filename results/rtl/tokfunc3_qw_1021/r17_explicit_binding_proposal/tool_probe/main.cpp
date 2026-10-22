#include "Vtop.h"
#include "verilated.h"
#include <cstdio>
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vtop t;unsigned x=0x13579bdf;int nonzero=0,firstflat=-1,firstbound=-1;bool mut=argc>1;
for(int e=0;e<120;e++){t.clk=0;t.rst_n=!((e<3)||(e>=45&&e<48));x=x*1664525u+1013904223u;t.x_flat=x;t.x_bound=x^((mut&&e==60)?1u:0u);t.eval();
 if(t.y_flat!=t.y_bound){printf("BINDING_DATA_MISMATCH phase=fall edge=%d flat=%08x bound=%08x\n",e,t.y_flat,t.y_bound);return 1;}
 t.clk=1;t.eval();if(t.y_flat!=t.y_bound){printf("BINDING_DATA_MISMATCH phase=rise edge=%d flat=%08x bound=%08x\n",e,t.y_flat,t.y_bound);return 1;}
 if(t.y_flat){nonzero++;if(firstflat<0)firstflat=e;}if(t.y_bound&&firstbound<0)firstbound=e;}
 if(nonzero<20||firstflat!=firstbound){puts("BINDING_COVERAGE_FAIL");return 2;}
 printf("REAL_ARCHIVE_BINDING_PASS edges=120 halfchecks=240 resets=2 state_nonzero=%d firstflat=%d firstbound=%d\n",nonzero,firstflat,firstbound);t.final();return 0;}
