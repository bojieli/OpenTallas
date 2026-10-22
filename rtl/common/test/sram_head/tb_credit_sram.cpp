#include "Vtb_credit_sram.h"
#include "verilated.h"
int main(int argc,char **argv){Verilated::commandArgs(argc,argv);Vtb_credit_sram t;for(int i=0;i<30000&&!Verilated::gotFinish();++i){t.clk=i&1;t.eval();}t.final();return 0;}
