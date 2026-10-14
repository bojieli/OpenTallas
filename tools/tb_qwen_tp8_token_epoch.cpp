#include "Vot_qwen_tp8_token_epoch_allocator.h"
#include "verilated.h"
#include <iostream>
#include <stdexcept>
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);Vot_qwen_tp8_token_epoch_allocator m;unsigned checks=0;
 auto step=[&](){m.clk=0;m.eval();m.clk=1;m.eval();};
 auto must=[&](bool ok,const char* why){++checks;if(!ok)throw std::runtime_error(why);};
 auto all_drains=[&](bool v){m.terminal_kv_drained=m.terminal_vm_drained=m.terminal_collective_drained=m.terminal_host_drained=v;};
 m.por_n=0;m.warm_ready=1;m.request_valid=0;m.grant_ready=0;m.terminal_valid=0;m.terminal_fault=0;m.terminal_done=1;
 m.wrap_fence_valid=0;m.wrap_links_drained=0;m.wrap_link_reset_seen=0;m.wrap_retraining_done=0;all_drains(0);step();m.por_n=1;step();
 auto request=[&](unsigned epoch,unsigned token,unsigned pos,unsigned gen){m.request_token=token;m.request_position=pos;m.request_generation=gen;m.request_valid=1;m.clk=0;m.eval();must(m.request_ready,"request not admitted");step();m.request_valid=0;
 must(m.grant_valid&&m.busy,"accepted token has no held grant");must(m.grant_epoch==epoch&&m.grant_token==token&&m.grant_position==pos&&m.grant_generation==gen,"grant identity mismatch");
 must(m.grant_tag==((uint64_t(epoch)<<43)|(uint64_t(token)<<19)|(uint64_t(pos)<<6)),"grant TAG59 packing");};
 auto deliver=[&](){m.grant_ready=1;step();m.grant_ready=0;must(!m.grant_valid&&m.busy,"delivered token lost ownership");};
 auto terminal=[&](unsigned epoch,unsigned token,unsigned pos,unsigned gen){m.terminal_tag=(uint64_t(epoch)<<43)|(uint64_t(37)<<37)|(uint64_t(token)<<19)|(uint64_t(pos)<<6);m.terminal_generation=gen;m.terminal_valid=1;};
 request(65534,151935,8191,3);uint64_t held=m.grant_tag;
 m.warm_ready=0;for(unsigned i=0;i<17;++i){step();must(m.grant_tag==held&&!m.grant_valid&&m.busy&&!m.request_ready,"warmreset dropped active epoch");}m.warm_ready=1;deliver();
 terminal(65534,151935,8191,3);all_drains(1);
 for(unsigned bit:{43u,37u,19u,6u,0u}){m.terminal_tag^=uint64_t(1)<<bit;step();must(m.busy&&!m.terminal_accepted,"stale identity released token");m.terminal_tag^=uint64_t(1)<<bit;}
 m.terminal_generation^=1;step();must(m.busy&&!m.terminal_accepted,"stale generation released token");m.terminal_generation^=1;
 m.terminal_kv_drained=0;step();must(m.busy&&!m.terminal_accepted,"early KV completion");all_drains(1);
 m.terminal_vm_drained=0;step();must(m.busy&&!m.terminal_accepted,"early VM completion");all_drains(1);
 m.terminal_collective_drained=0;step();must(m.busy&&!m.terminal_accepted,"early collective completion");all_drains(1);
 m.terminal_host_drained=0;step();must(m.busy&&!m.terminal_accepted,"early HOST completion");all_drains(1);
 step();must(!m.busy&&m.terminal_accepted,"real committed terminal not accepted");m.terminal_valid=0;step();must(!m.request_ready,"identity fault admitted later token");
 m.wrap_fence_valid=1;m.wrap_links_drained=1;m.wrap_link_reset_seen=1;m.wrap_retraining_done=1;step();must(!m.identity_fault,"actual fault recovery fence not accepted");m.wrap_fence_valid=0;m.wrap_link_reset_seen=0;step();
 request(65535,65536,7935,0);deliver();terminal(65535,65536,7935,0);m.terminal_done=0;m.terminal_fault=1;all_drains(1);step();must(!m.busy&&m.terminal_accepted&&m.wrap_locked,"drained abort/FFFF lock");m.terminal_valid=0;
 for(unsigned i=0;i<5;++i){step();must(!m.request_ready&&m.wrap_locked,"FFFF reused without real link fence");}
 m.wrap_fence_valid=1;m.wrap_links_drained=1;m.wrap_retraining_done=1;step();must(m.wrap_locked,"missing link reset accepted");m.wrap_link_reset_seen=1;step();must(!m.wrap_locked,"actual retraining fence not accepted");m.wrap_fence_valid=0;step();
 m.request_position=8192;m.request_token=0;m.request_valid=1;step();must(!m.request_ready&&!m.busy&&!m.grant_valid,"invalid position silently truncated");
 m.request_position=0;m.request_token=151936;step();must(!m.request_ready&&!m.busy&&!m.grant_valid,"invalid vocabulary token admitted");m.request_valid=0;must(m.identity_fault,"invalid request did not fault");
 m.wrap_fence_valid=1;step();must(!m.identity_fault,"invalid-request recovery fence");m.wrap_fence_valid=0;step();
 request(0,0,0,1);std::cout<<"PASS epoch allocator checks="<<checks<<" retainedwarmreset/tag59/staledrains/FFFFfence/failclosed\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}}
