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
 assert(backend->drained()&&!backend->current_committed());
 bool offer=false,ready=false,response=false,consume=false;
 bool record_offer=false,record_ready=false;uint32_t position=0;
 std::array<uint32_t,16> codes{};uint32_t scale=0;
 {
  std::ifstream raw(std::string(argv[1])+"/ikring_s0.hex");std::string a,w;
  while(raw>>a>>w){auto addr=std::stoull(a,nullptr,16);
   if(addr==0)scale=std::stoul(w.substr(56,8),nullptr,16);
   if(addr==128||addr==129)for(int i=0;i<8;i++)codes[(addr-128)*8+i]=std::stoul(w.substr(64-8*(i+1),8),nullptr,16);
   if(addr>=129)break;
  }
 }
 std::array<uint32_t,8> actual{};
 backend->bind_wiring([&](auto&m){
  m.r_v={};m.r_addr={};m.r_len={};m.r_tag={};m.r_rsp_rdy={};
  m.w_v=record_offer;m.w_csec=position;m.w_ssec=0;m.w_codes={};m.w_scales=scale;m.w_sslot=0;
  for(int i=0;i<16;i++)m.w_codes[i]=codes[i];
  if(offer){m.r_v[0]=1;m.r_len[0]=1;m.r_tag[0]=5;}
  if(consume)m.r_rsp_rdy[0]=1;
  m.eval();record_ready=m.w_rdy;ready=m.r_rdy[0]&1;response=m.r_rsp_v[0]&1;
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
 assert(backend->drained()&&!backend->current_committed());
 std::ifstream f(std::string(argv[1])+"/ikring_s0.hex");std::string address,raw;f>>address>>raw;
 assert(std::stoull(address,nullptr,16)==0&&raw.size()==64);
 for(int i=0;i<8;i++)assert(actual[i]==std::stoul(raw.substr(64-8*(i+1),8),nullptr,16));
 auto c=backend->traffic().pc[0];
 assert(c.accepted_read_beats==1&&c.delivered_read_beats==1&&c.accepted_write_beats==0&&c.write_done==0&&c.migration_read_beats==0);
 assert(!backend->current_committed());
 // Protocol-only raw record stimulus, copied from prior source bits; no current
 // encoder or numerical/L20 coverage is implied. All ACKs are native.
 for(uint32_t pos:{0u,31u}) {
  position=pos;record_offer=true;
  do{tick(true);assert(!backend->current_committed());}while(!record_ready);
  record_offer=false;
  do{tick(true);}while(!backend->current_committed());
  assert(backend->current_committed(pos)&&!backend->current_committed(pos+1));
 }
 auto status=backend->current_record_status();
 assert(status.accepted_records==2&&status.committed_records==2);
 assert(status.accepted_writes==108&&status.acknowledged_writes==108);
 assert(status.accepted_cycle&&status.committed_cycle&&*status.committed_cycle>*status.accepted_cycle);
 // Native downstream query read must not revoke committed current history.
 offer=true;consume=false;
 do{tick(true);assert(backend->current_committed(31));}while(!ready);
 offer=false;
 do{tick(true);assert(backend->current_committed(31));}while(!response);
 for(int i=0;i<3;i++){tick(true);assert(backend->current_committed(31)&&!backend->drained());}
 consume=true;tick(true);assert(backend->drained()&&backend->current_committed(31));
 std::cout<<"PASS absent-writer denied; 2 native accepted records/108 actual write ACKs including migration; committed history survives held scan read; edges="<<edge<<"; protocol stimulus only, NOT L20 encoder/scan qualification\n";
}
