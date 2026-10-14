#include "Vot_qwen_tp8_token_cohort.h"
#include <cstdint>
#include <iostream>
#include <stdexcept>
static uint64_t tag(unsigned e,unsigned s,unsigned t,unsigned p,unsigned seg=0) {
 return (uint64_t(e)<<43)|(uint64_t(s)<<37)|(uint64_t(t)<<19)|(uint64_t(p)<<6)|seg;
}
int main(){
 Vot_qwen_tp8_token_cohort d; unsigned checks=0;
 auto ck=[&](bool ok,const char* why){++checks;if(!ok)throw std::runtime_error(why);};
 auto tick=[&](){d.clk=0;d.eval();d.clk=1;d.eval();d.clk=0;d.eval();};
 auto setrank=[&](unsigned r,uint64_t t,unsigned g){
  // Verilator packed wide fields are little-endian 32-bit words.
  for(unsigned bit=0;bit<59;++bit){unsigned b=59*r+bit;uint32_t mask=uint32_t(1)<<(b%32);
   d.request_tag[b/32]=(d.request_tag[b/32]&~mask)|((t>>bit&1)?mask:0);}
  d.request_generation=(d.request_generation&~(3u<<(2*r)))|(g<<(2*r));
 };
 auto begin=[&](uint64_t t,unsigned g){d.begin_tag=t;d.begin_generation=g;d.begin_valid=1;d.eval();ck(d.begin_ready,"begin blocked");tick();d.begin_valid=0;d.eval();};
 auto pulse=[&](unsigned mask){d.request_valid=mask;tick();d.request_valid=0;d.eval();};
 auto reset=[&](){d.por_n=0;tick();d.por_n=1;d.warm_ready=1;d.begin_valid=0;d.request_valid=0;d.terminal_valid=0;d.recovery_valid=0;tick();};
 auto drains=[&](bool yes){d.kv_drained=yes;d.vm_drained=yes;d.collective_drained=yes;d.host_drained=yes;};
 try {
  d.dispatch_ready=1;reset();auto t=tag(0,0,151935,8191);begin(t,3);
  for(unsigned r=0;r<8;++r)setrank(r,t,3);
  pulse(0x7f);ck(d.accepted_ranks==0x7f && d.request_credit==0x7f,"seven actual accepts");
  for(unsigned n=0;n<1000;++n){tick();ck(!d.dispatch_valid&&!d.dispatched,"early start before delayed peer7");}
  pulse(0x80);ck(d.accepted_ranks==255&&d.request_credit==128,"peer7 accepted");
  ck(d.dispatch_valid,"missing all-rank barrier");tick();ck(d.dispatched&&!d.dispatch_valid,"dispatch once");
  d.terminal_tag=tag(0,37,151935,8191);d.terminal_generation=3;d.terminal_done=1;d.terminal_fault=0;d.terminal_valid=1;
  drains(true);d.host_drained=0;tick();ck(d.active&&!d.terminal_accepted,"premature HOST drain");
  d.host_drained=1;tick();ck(!d.active&&d.terminal_accepted,"terminal not accepted");
  tick();ck(!d.identity_fault&&!d.begin_ready,"registered held terminal rearm");d.terminal_valid=0;tick();
  ck(d.begin_ready,"face not rearmed");
  // Real accepted duplicate and mismatched peer suppress the potential launch.
  for(unsigned kind=0;kind<7;++kind){reset();t=tag(5,0,65536,7935);begin(t,2);for(unsigned r=0;r<8;++r)setrank(r,t,2);
   pulse(127);if(kind==0){pulse(1);}else {uint64_t bad=t;unsigned g=2;
    if(kind==1)bad^=uint64_t(1)<<43;if(kind==2)bad^=uint64_t(1)<<37;if(kind==3)bad^=uint64_t(1)<<19;
    if(kind==4)bad^=uint64_t(1)<<6;if(kind==5)bad^=1;if(kind==6)g^=1;setrank(7,bad,g);pulse(128);}
   ck(d.identity_fault&&!d.dispatched&&!d.dispatch_valid,"identity/duplicate admitted");
   d.terminal_tag=tag(5,37,65536,7935);d.terminal_generation=2;d.terminal_valid=1;d.terminal_done=0;d.terminal_fault=1;drains(true);
   tick();ck(d.terminal_accepted&&!d.active,"matching drained cancellation failed");
   tick();ck(!d.begin_ready,"fault silently recovered");d.terminal_valid=0;tick();
   d.links_drained=1;d.link_reset_seen=1;d.retraining_done=0;d.recovery_valid=1;tick();ck(d.identity_fault,"missing retraining accepted");
   d.retraining_done=1;tick();ck(!d.identity_fault,"actual fence did not recover");d.recovery_valid=0;
  }
  reset();t=tag(9,0,0,0);begin(t,0);for(unsigned r=0;r<8;++r)setrank(r,t,0);pulse(1);
  d.warm_ready=0;tick();ck(d.active&&d.accepted_ranks==1&&d.cohort_tag==t,"warm identity lost");
  d.warm_ready=1;pulse(254);tick();ck(d.dispatched,"warm-resume barrier failed");
  d.terminal_tag=tag(8,37,0,0);d.terminal_generation=0;d.terminal_done=1;d.terminal_fault=0;d.terminal_valid=1;drains(true);
  tick();ck(d.identity_fault&&d.active&&!d.terminal_accepted,"stale terminal released cohort");
  std::cout<<"PASS checks="<<checks<<" delayed_peer7_edges=1000 identity_fault_cases=8\n";return 0;
 } catch(const std::exception& e){std::cerr<<"FAIL checks="<<checks<<" "<<e.what()<<"\n";return 1;}
}
