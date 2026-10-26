#include "Vprobe.h"
#include "verilated.h"
#include <cstdio>
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vprobe p;int count=0,last=-1,gap=999,outputs=0,errors=0;
for(int c=0;c<660;c++){p.ck=0;p.rst_n=c>=5;p.go=c==10;p.train_start=c==296;p.eval();
if(p.rst_n&&p.ov){if(last>=0&&c-last<gap)gap=c-last;last=c;count++;printf("ACTUAL_PREEDGE_CAPTURE cycle=%d\n",c);}
p.ck=1;p.eval();
bool expected=c>=299&&c<=467&&(c-299)%24==0;
if(bool(p.rbv)!=expected){errors++;printf("BAD_OUTPUT_SLOT c=%d valid=%d expected=%d\n",c,int(p.rbv),expected);}
if(p.rbv){outputs++;int i=(c-299)/24;if(p.row!=768+i||p.omask!=65535)errors++;printf("ACTUAL_CANDIDATE_OUTPUT c=%d row=%d mask=%x\n",c,int(p.row),int(p.omask));}}
printf("ACTUAL_RESULT count=%d min_gap=%d old_fault=%d candidate_fault=%d outputs=%d errors=%d\n",count,gap,int(p.fault),int(p.candidate_fault),outputs,errors);
return count==8&&gap==1&&p.fault&&!p.candidate_fault&&outputs==8&&!errors?0:2;}
