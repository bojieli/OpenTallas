#include "Vtb_hgi_hc_checkpoint_native_mtp_static.h"
#include "verilated.h"
#include "Vtb_hgi_hc_checkpoint_native_mtp_static___024root.h"
#include <cstdio>
double sc_time_stamp(){return 0;}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vtb_hgi_hc_checkpoint_native_mtp_static t;
unsigned long long now=0,next_stream=416666,next_hbm=512000,stream_edges=0;
t.clk=0;t.sink_clk=0;t.hbm_clk=0;t.eval();
while(!Verilated::gotFinish()){
 now=next_stream<next_hbm?next_stream:next_hbm;
 if(now==next_stream){t.clk=!t.clk;t.sink_clk=t.clk&&(stream_edges%7==0);if(t.clk)stream_edges++;next_stream+=416666;}
 if(now==next_hbm){t.hbm_clk=!t.hbm_clk;next_hbm+=512000;}
 t.eval();
 if(t.clk && now==next_stream-416666){auto*r=t.rootp;
 if(r->tb_hgi_hc_checkpoint_native_mtp_static__DOT__reserve_v || r->tb_hgi_hc_checkpoint_native_mtp_static__DOT__drain_v){
 printf("PHASE_EDGE edge=%llu cycle=%u state=%u age=%u row=%u reserve=%u rrow=%u half=%u drain=%u drow=%u\n",stream_edges,r->tb_hgi_hc_checkpoint_native_mtp_static__DOT__cycle,r->tb_hgi_hc_checkpoint_native_mtp_static__DOT__state,r->tb_hgi_hc_checkpoint_native_mtp_static__DOT__age,r->tb_hgi_hc_checkpoint_native_mtp_static__DOT__row,r->tb_hgi_hc_checkpoint_native_mtp_static__DOT__reserve_v,r->tb_hgi_hc_checkpoint_native_mtp_static__DOT__reserve_row,r->tb_hgi_hc_checkpoint_native_mtp_static__DOT__reserve_half,r->tb_hgi_hc_checkpoint_native_mtp_static__DOT__drain_v,r->tb_hgi_hc_checkpoint_native_mtp_static__DOT__drain_row);fflush(stdout);}}
 }
t.final();}
