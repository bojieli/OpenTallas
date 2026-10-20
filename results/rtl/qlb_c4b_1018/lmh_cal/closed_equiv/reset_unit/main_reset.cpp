#include "Vtb.h"
#include "verilated.h"
#include <cstdio>
#include <cstdint>
#include <cstdlib>
static double tm=0;double sc_time_stamp(){return tm;}
static Vtb *t;static bool qualify=false;static int checks=0,issues=0,ends=0;
static void ev(){t->eval();if(qualify){++checks;if(t->mismatch){std::printf("DEFAULT_OFF_RESET_FAIL mismatch t=%f\n",tm);std::exit(1);}}}
static void step(){t->ck=0;ev();tm+=0.5;bool i=t->issue_new,e=t->end_new;t->ck=1;ev();if(i){++issues;t->candidate_pc=1;t->candidate_unit=0;}if(e)++ends;tm+=0.5;t->ck=0;ev();}
static void resetHeld(){t->pw_v=0;t->start=0;t->candidate_v=0;t->rst_n=0;ev();qualify=true;for(int k=0;k<3;k++)step();t->rst_n=1;ev();step();}
static uint64_t word(int a){if(a==976)return (uint64_t(1)<<44)|10;if(a==977)return (uint64_t(1)<<46)|(uint64_t(1)<<32)|20;if(a==1016)return (uint64_t(0x43414c31)<<32)|20;if(a==1017)return (uint64_t(0x43414c53)<<32)|(uint64_t(1)<<18)|2;if(a==1023)return (uint64_t(0x58504631)<<32)|6;return 0;}
static void load(int count){t->candidate_v=0;for(int a=0;a<count;a++){t->pw_v=1;t->pw_addr=a;t->pw_data=word(a);step();}t->pw_v=0;step();if(count==1024 && (!t->ready_new||t->fault_new)){std::printf("DEFAULT_OFF_RESET_FAIL seal ready=%d fault=%d\n",t->ready_new,t->fault_new);std::exit(1);}}
static void startRun(){t->candidate_v=0;t->start=1;step();t->start=0;t->candidate_v=1;t->candidate_pc=0;t->candidate_unit=1;}
static void completeRun(){int oi=issues,oe=ends;startRun();for(int k=0;k<30;k++)step();t->candidate_v=0;if(issues-oi!=1||ends-oe!=1||t->fault_new){std::printf("DEFAULT_OFF_RESET_FAIL issue=%d end=%d fault=%d\n",issues-oi,ends-oe,t->fault_new);std::exit(1);}}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);t=new Vtb;t->ck=0;t->rst_n=1;t->pw_v=0;t->start=0;t->candidate_v=0;ev();resetHeld();load(500);resetHeld();if(t->ready_new||t->active_new)return 2;load(1024);startRun();for(int k=0;k<4;k++)step();if(!t->active_new)return 3;
// Pulse entirely between active clock edges: async2sync does not prove this.
tm+=0.125;t->rst_n=0;ev();tm+=0.125;t->rst_n=1;ev();if(t->ready_new||t->active_new)return 4;t->candidate_v=0;load(1024);completeRun();startRun();for(int k=0;k<4;k++)step();resetHeld();load(1024);completeRun();std::printf("DEFAULT_OFF_RESET_PASS checks=%d issues=%d ends=%d config_reset=1 inflight_held=1 inflight_short=1 first_valid=2\n",checks,issues,ends);t->final();delete t;}
