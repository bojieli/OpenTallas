#include "s81_minimum_index_hbm.hpp"
#include <fstream>
#include <iostream>
#include <sstream>
#include <cassert>
using namespace dsrom_s81_minimum;
int main(int argc,char**argv) {
 if(argc!=2)return 2;
 VerilatedContext context;long edge=0;
 DsromS81MinimumRuntime runtime{};runtime.context=&context;runtime.cycle=[&](){return edge;};
 auto backend=std::make_shared<NativeIndexHbm>(runtime,"index_backend");
 backend->preload_ring(argv[1]);
 assert(backend->initialized()&&backend->capacity_words()==139520);
 bool offer=false,ready=false,response=false,consume=false;
 std::array<uint32_t,8> actual{};
 backend->bind_wiring([&](auto&m){
  m.r_v={};m.r_addr={};m.r_len={};m.r_tag={};m.r_rsp_rdy={};
  m.w_v=0;m.w_csec=0;m.w_ssec=0;m.w_codes={};m.w_scales=0;m.w_sslot=0;
  if(offer){m.r_v[0]=1;m.r_len[0]=1;m.r_tag[0]=5;}
  if(consume)m.r_rsp_rdy[0]=1;
  m.eval();ready=m.r_rdy[0]&1;response=m.r_rsp_v[0]&1;
  if(response){assert((m.r_rsp_tag[0]&65535)==5);assert((m.r_rsp_beat[0]&15)==0);for(int i=0;i<8;i++)actual[i]=m.r_rsp_data[i];}
 });
 auto p=backend->participant();
 auto tick=[&](bool release){p.prepare({});p.rising(release);p.falling(release);assert(!p.fault());++edge;context.timeInc(833);};
 tick(false);tick(false);offer=true;
 do{tick(true);}while(!ready);
 offer=false;
 do{tick(true);}while(!response);
 auto held=actual;
 for(int i=0;i<3;i++){tick(true);assert(response&&actual==held);}
 consume=true;tick(true);consume=false;
 assert(backend->drained());
 std::ifstream f(std::string(argv[1])+"/ikring_s0.hex");std::string address,raw;f>>address>>raw;
 assert(std::stoull(address,nullptr,16)==0&&raw.size()==64);
 for(int i=0;i<8;i++)assert(actual[i]==std::stoul(raw.substr(64-8*(i+1),8),nullptr,16));
 auto c=backend->traffic().pc[0];
 assert(c.accepted_read_beats==1&&c.delivered_read_beats==1&&c.accepted_write_beats==0&&c.write_done==0&&c.migration_read_beats==0);
 std::cout<<"PASS native raw ring importer + PC0 read + held native response; edges="<<edge<<"; NOT L20 scan/current-writer coverage\n";
}
