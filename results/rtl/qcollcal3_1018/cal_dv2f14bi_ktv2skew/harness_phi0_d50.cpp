#include "Vtb_coll_tp8_static_links.h"
#include "verilated.h"
#include <cstring>
#include <cstdlib>
int main(int argc, char** argv) { Verilated::commandArgs(argc, argv);
  unsigned tick=0;int fphi=0;for(int i=1;i<argc;i++)if(!strncmp(argv[i],"+FDIPHI=",8))fphi=atoi(argv[i]+8);
  auto* t = new Vtb_coll_tp8_static_links; t->clk = 0; t->lck = 0; t->fdi_ck=0; t->blk_ck=0; t->eval();
  while (!Verilated::gotFinish()) { bool ce=(tick%10)<5,fe=((tick+120-2*fphi)%12)<6,be=(tick%60)<30;t->clk=ce;t->lck=ce;t->fdi_ck=fe;t->blk_ck=be;t->eval();tick++; }
  t->final(); delete t; return 0; }
