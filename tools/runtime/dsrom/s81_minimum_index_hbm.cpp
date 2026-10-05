#include "s81_minimum_index_hbm.hpp"
#include "svdpi.h"
#include <filesystem>
#include <fstream>
namespace dsrom_s81_minimum {
NativeIndexHbm::NativeIndexHbm(DsromS81MinimumRuntime&r,const std::string&name)
 :runtime(r),model(r.context,name.c_str()) {
 if(!r.context||!r.cycle||r.identity)throw std::runtime_error("index backend requires cold shared runtime");
 model.clk=0;model.rst_n=0;model.eval();
}
void NativeIndexHbm::preload_ring(const std::string&directory) {
 if(admitted||runtime.identity||model.history_ready||!drained())
  throw std::runtime_error("ring image initialization after context/debt admission");
 for(unsigned st=0;st<4;st++) {
  std::ifstream f(std::filesystem::path(directory)/("ikring_s"+std::to_string(st)+".hex"));
  if(!f)throw std::runtime_error("missing literal ring stack image");
  std::string a,w;bool any=false;
  while(f>>a) {
   if(!(f>>w)||a.empty()||a.size()>16||a.find_first_not_of("0123456789abcdefABCDEF")!=std::string::npos||
      w.size()!=64||w.find_first_not_of("0123456789abcdefABCDEF")!=std::string::npos||
      std::stoull(a,nullptr,16)>=model.capacity_words)
    throw std::runtime_error("invalid physical ring ADDRESS DATA image");
   any=true;
  }
  if(!any)throw std::runtime_error("empty literal ring stack image");
 }
 auto scope=svGetScopeFromName((std::string(model.name())+".DsromS81IndexHbm").c_str());
 if(!scope)throw std::runtime_error("native ring image scope absent");
 auto old=svSetScope(scope);VDsromS81IndexHbm::s81_index_preload_ring(directory.c_str());
 svSetScope(old);model.eval();
 if(!initialized())throw std::runtime_error("native ring history initialization incomplete");
}
bool NativeIndexHbm::drained()const {
 if(model.busy||model.w_v)return false;
 for(unsigned p=0;p<128;p++)if(reads[p]||writes[p])return false;
 return true;
}
bool NativeIndexHbm::current_committed()const {
 return initialized()&&model.rst_n&&!model.fault&&!model.w_v&&!model.busy&&
  model.dbg_records==current_record.accepted_records&&
  model.dbg_writes==current_record.acknowledged_writes&&
  current_record.accepted_records!=0&&
  current_record.committed_records==current_record.accepted_records;
}
void NativeIndexHbm::bind_wiring(std::function<void(VDsromS81IndexHbm&)>f) {
 if(join||!f)throw std::runtime_error("index backend duplicate/empty wiring");
 join=[this,f](){f(model);model.eval();};
}
DsromS81MinimumParticipant NativeIndexHbm::participant() {
 auto self=shared_from_this();
 return {"native-128PC-index-ring-HBM",
 [self](const auto&) {
  if(!self->join||!self->initialized())throw std::runtime_error("index backend lacks native wiring/history");
  self->model.clk=0;self->join();self->join();auto&m=self->model;
  self->old_record_accept=m.w_v&&m.w_rdy;
  self->old_record_position=m.w_csec;
  for(unsigned p=0;p<128;p++) {
   auto&e=self->edges[p];unsigned word=p/32,bit=p%32;
   e.accept=(m.accepted[word]>>bit)&1;e.we=(m.accepted_we[word]>>bit)&1;
   e.response=(m.returned[word]>>bit)&1;e.done=(m.committed[word]>>bit)&1;
   e.length=(m.accepted_len[p/8]>>(4*(p%8)))&15;
   e.migration=(m.accepted_tag[p/2]>>(16*(p%2)+12))&1;
   e.response_migration=(m.r_rsp_tag[p/2]>>(16*(p%2)+12))&1;
   e.strobe=m.accepted_strb[p];
  }
  self->prepared=self->runtime.cycle();
 },
 [self](bool released) {
  if(!released&&!self->drained())throw std::runtime_error("index reset would erase accepted debt");
  if(released) {
   if(self->prepared!=self->runtime.cycle())throw std::runtime_error("index missing common pre-edge sampling");
   if(self->old_record_accept) {
    ++self->current_record.accepted_records;
    self->current_record.last_position=self->old_record_position;
    self->current_record.accepted_cycle=self->runtime.cycle();
    self->current_record.committed_cycle.reset();
   }
   for(unsigned p=0;p<128;p++) {
    const auto&e=self->edges[p];auto&c=self->counters.pc[p];
    if(e.accept){self->admitted=true;
     if(e.we){++self->writes[p];++self->current_record.accepted_writes;++c.accepted_write_beats;c.accepted_write_bytes+=__builtin_popcount(e.strobe);}
     else {self->reads[p]+=e.length;c.accepted_read_beats+=e.length;if(e.migration){c.migration_read_beats+=e.length;self->writer_reads[p]+=e.length;}}
    }
    if(e.response){if(!self->reads[p])throw std::runtime_error("index response without read debt");--self->reads[p];++c.delivered_read_beats;if(e.response_migration){if(!self->writer_reads[p])throw std::runtime_error("migration response without writer debt");--self->writer_reads[p];++c.migration_delivered_beats;}}
    if(e.done){if(!self->writes[p])throw std::runtime_error("index commit without write debt");--self->writes[p];++self->current_record.acknowledged_writes;++c.write_done;}
    if(e.accept||e.response||e.done){if(!c.first_cycle)c.first_cycle=self->runtime.cycle();c.last_cycle=self->runtime.cycle();}
   }
  }
  self->model.rst_n=released;self->model.clk=1;self->model.eval();
  // Inspect the native writer AFTER its real clock edge. dbg_records counts
  // records popped to the writer, not host offers. busy includes final ACK.
  // Scan read debt is independent and must not revoke already-published history.
  if(released&&self->current_record.accepted_records&&!self->model.fault&&
     !self->model.busy&&!self->model.w_v&&
     self->model.dbg_records==self->current_record.accepted_records&&
     self->current_record.accepted_writes>=3*self->current_record.accepted_records&&
     self->current_record.acknowledged_writes==self->current_record.accepted_writes&&
     self->model.dbg_writes==self->current_record.acknowledged_writes) {
   bool writer_drained=true;
   for(unsigned p=0;p<128;p++)if(self->writes[p]||self->writer_reads[p])writer_drained=false;
   if(writer_drained&&self->current_record.committed_records!=self->current_record.accepted_records) {
    self->current_record.committed_records=self->current_record.accepted_records;
    self->current_record.committed_cycle=self->runtime.cycle();
   }
  }
 },
 [self](bool released){self->model.rst_n=released;self->model.clk=0;self->model.eval();},
 [self](){return bool(self->model.fault);}};
}
}
