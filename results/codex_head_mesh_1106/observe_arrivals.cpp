#include <memory>
#include <cstdio>
#include "verilated.h"
#include "Vtb_s81hd_mesh_ep.h"
#include "Vtb_s81hd_mesh_ep___024root.h"
#include "Vtb_s81hd_mesh_ep_ot_s81hd_mesh_ep_core__B8_R1.h"
int main(int argc,char**argv){
 auto ctx=std::make_unique<VerilatedContext>();ctx->threads(1);ctx->commandArgs(argc,argv);
 auto top=std::make_unique<Vtb_s81hd_mesh_ep>(ctx.get(),"");bool oldck=false;int edge=0;
 while(!ctx->gotFinish()){
  top->eval();auto r=top->rootp;bool ck=r->tb_s81hd_mesh_ep__DOT__ck;
  if(ck&&!oldck){++edge;auto x=r->__PVT__tb_s81hd_mesh_ep__DOT__u_x;auto y=r->__PVT__tb_s81hd_mesh_ep__DOT__u_y;
   for(int side=0;side<2;side++){auto p=side?y:x;printf("ARR %d %d %u %u %u %u %u %u\n",side,edge,unsigned(r->tb_s81hd_mesh_ep__DOT__rst_n),unsigned(p->la),unsigned(p->lb),unsigned(p->na),unsigned(p->nb),unsigned(p->__PVT__iss_q));}
  }
  oldck=ck;if(!top->eventsPending())break;ctx->time(top->nextTimeSlot());
 }
 top->final();return 0;
}
