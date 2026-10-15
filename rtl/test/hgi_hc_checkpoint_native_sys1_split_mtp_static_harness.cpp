#include "Vtb_hgi_hc_checkpoint_native_sys1_split_mtp_static.h"
#include "verilated.h"
double sc_time_stamp(){return 0;}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vtb_hgi_hc_checkpoint_native_sys1_split_mtp_static t;
unsigned long long now=0,next_stream=416666,next_hbm=512000,stream_edges=0;
t.clk=0;t.sink_clk=0;t.hbm_clk=0;t.eval();
while(!Verilated::gotFinish()){
 now=next_stream<next_hbm?next_stream:next_hbm;
 if(now==next_stream){t.clk=!t.clk;t.sink_clk=t.clk&&(stream_edges%7==0);if(t.clk)stream_edges++;next_stream+=416666;}
 if(now==next_hbm){t.hbm_clk=!t.hbm_clk;next_hbm+=512000;}
 t.eval();}
t.final();}
