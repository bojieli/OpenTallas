#include "Vtb_hgi_hc_engine_sys1_split_mtp_static.h"
#include "verilated.h"
double sc_time_stamp(){return 0;}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vtb_hgi_hc_engine_sys1_split_mtp_static t;unsigned long c=0;while(!Verilated::gotFinish()){t.clk=0;t.sink_clk=0;t.eval();t.clk=1;t.sink_clk=(c%7==0);t.eval();c++;}t.final();}
