#include "Vwct_native_top.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
#include <cstdint>
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vwct_native_top t;int checks=0,rd=0;uint32_t rng=0x42fa9ab9;int phase=argc>1?atoi(argv[1]):137;
t.tclk=0;t.rclk=0;t.rst_n=0;for(int i=0;i<18;i++)t.d[i]=0;t.eval();
for(int ps=1;ps<1500000;ps++){
 if(ps%1000==537){for(int i=0;i<18;i++){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;t.d[i]=rng;}}
 if(ps%500==0)t.tclk=!t.tclk;
 if(ps>=phase && (ps-phase)%500==0){t.rclk=!t.rclk;if(!t.rclk)t.rst_n=(rd>=12 && rd%257>=3);}
 t.eval();
 if(ps>=phase && (ps-phase)%1000==0){rd++;if(rd>3){if(!t.ctrlsame){printf("CONTROL_FAIL%d\n",rd);return 1;}if(t.ready){checks++;if(!t.same){printf("DATA_FAIL%d\n",rd);return 1;}}}}
}
printf("PASS actual_landing RDREG1 WNEG configured phase%d cycles%d checks%d warmresets%d\n",phase,rd,checks,rd/257);return checks>1000?0:2;}
