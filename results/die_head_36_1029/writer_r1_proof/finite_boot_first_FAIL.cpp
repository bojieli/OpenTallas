#include "Vtb_ring_local_start.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);long checks=0,fail=0,mut=0,extra=0,cases=0,readycases=0,max_data_last_diff=-1,max_status_last_diff_valid=-1;
 const long T=833;
 for(int k=-63;k<=63;k++)for(int R=1;R<=2;R++)for(long L:{1L,100L,200L,416L,417L,500L,832L,833L,834L,1000L,1400L,1665L,1666L,1800L,2200L,2600L,3000L,3232L}){
  Vtb_ring_local_start v;long tw0=80*T,tr0=tw0+L-k*T;while(tr0<20*T){tw0+=T;tr0+=T;}
  long phi=(tr0%T+T)%T,end=(tw0>tr0?tw0:tr0)+220*T;v.fclk=0;v.clk=0;v.t_rst_n=0;v.rst_n=0;v.d=0;v.k=k&63;v.r2=R==2;v.eval();bool caught=false,extra_caught=false,hadready=false;long data_last=-1,status_last=-1;
  long nextt=0,nextr=phi;int it=0,ir=0;
  for(long t=0;t<=end;){long at=nextt<nextr?nextt:nextr;t=at;bool et=nextt==at,er=nextr==at;
   if(et){v.fclk=!v.fclk;nextt+=v.fclk?416:417;if(v.fclk){v.t_rst_n=t>=tw0;long count=(t-tw0)/T;v.d=0x5A000000u+count;}}
   if(er){v.clk=!v.clk;nextr+=v.clk?416:417;if(v.clk)v.rst_n=t>=tr0;}
   v.eval();
   if(er&&v.clk&&t>=tr0){long cc=(t-tr0)/T;if(v.qb!=v.qc||v.vb!=v.vc||v.lb!=v.lc||v.gb!=v.gc||v.hb!=v.hc)data_last=cc;if(v.rb!=v.rc||v.fb!=v.fc)status_last=cc;}
   if(er&&v.clk&&t>=tr0+140*T){checks++;if(v.qb!=v.qc||v.vb!=v.vc||v.lb!=v.lc||v.gb!=v.gc||v.hb!=v.hc||v.rb!=v.rc||v.fb!=v.fc){if(fail<10)printf("FAIL k%d R%d L%ld q%08x/%08x ready%d/%d fault%d/%d vlgh%d%d%d%d/%d%d%d%d\n",k,R,L,v.qb,v.qc,v.rb,v.rc,v.fb,v.fc,v.vb,v.lb,v.gb,v.hb,v.vc,v.lc,v.gc,v.hc);fail++;}
    if(v.rb)hadready=true;if(v.qb!=v.qm||v.fb!=v.fm||v.rb!=v.rm)caught=true;if(v.qb!=v.qx||v.fb!=v.fx||v.rb!=v.rx)extra_caught=true;}
   if(t==end)break;
  }
  if(data_last>=R+3){printf("FINITE_DATA_FAIL k%d R%d L%ld last%ld\n",k,R,L,data_last);fail++;} if(hadready&&status_last>=R+15){printf("FINITE_STATUS_FAIL k%d R%d L%ld last%ld\n",k,R,L,status_last);fail++;} if(!hadready&&(!v.fb||!v.fc)){printf("INVALID_NOT_CLOSED k%d R%d L%ld f%d/%d\n",k,R,L,v.fb,v.fc);fail++;} cases++;mut+=caught;extra+=extra_caught;readycases+=hadready;if(data_last>max_data_last_diff)max_data_last_diff=data_last;if(hadready&&status_last>max_status_last_diff_valid)max_status_last_diff_valid=status_last;
 }
 printf("BOOT data_last_diff=%ld valid_status_last_diff=%ld\n",max_data_last_diff,max_status_last_diff_valid);
 printf("RING_WRITER1_READER12 cases=%ld comparisons=%ld mismatch=%ld wrongK_caught=%ld extraedge_caught=%ld baseline_ready_cases=%ld\n",cases,checks,fail,mut,extra,readycases);return fail||mut!=cases||extra!=cases;
}
