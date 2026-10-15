#include "Vtb_hgi_hc_programme_static.h"
#include "verilated.h"
double sc_time_stamp(){return 0;}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vtb_hgi_hc_programme_static t;while(!Verilated::gotFinish()){t.clk=0;t.eval();t.clk=1;t.eval();}t.final();}
