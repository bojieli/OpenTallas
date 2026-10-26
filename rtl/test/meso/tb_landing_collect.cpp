#include "Vtb_landing_collect.h"
#include "verilated.h"
#include <cstdio>
int main(int argc,char**argv){
    Verilated::commandArgs(argc,argv);Vtb_landing_collect m;
    unsigned errors=0,checks=0;bool prev_r=false,prev_f=false;
    for(unsigned n=0;n<512;n++){
        bool rst=n>=4&&!(n>=250&&n<256);
        unsigned r=(n*5)&7,f=(n*3+1)&7;
        m.clk=0;m.rst_n=rst;m.ready_i=r;m.fault_i=f;m.eval();
        m.clk=1;m.eval();
        bool er=rst?prev_r:false,ef=rst?prev_f:false;
        if(m.ready_o!=er||m.fault_o!=ef){if(errors++<4)printf("DIFF n=%u got=%d/%d expected=%d/%d\n",n,m.ready_o,m.fault_o,er,ef);}
        prev_r=rst&&(r==7);prev_f=rst&&(f!=0);checks++;
    }
    printf("collector checks=%u errors=%u\n",checks,errors);return errors?1:0;
}
